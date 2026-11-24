"""Classe d'accès au données de la base SQL pour le calcul des points et l'enregistrement des résultats."""

import os
import json
import logging
import re
import sqlite3
from datetime import date, datetime


class DBService:
    def __init__(self, db_path="../results.db"):
        self.logger = logging.getLogger("DatabaseService")
        if not os.path.exists(db_path):
            raise Exception(f"Path to database not found : {db_path}")
        self.conn = sqlite3.connect(db_path, timeout=60)
        self.conn.execute("PRAGMA busy_timeout = 60000")  # évite "database is locked"
        self.cur = self.conn.cursor()

    @staticmethod
    def _normalize_date(value):
        """Convertit une date en str "YYYY-MM-DD".

        Accepte une str (tronquée à 10 caractères, donc un ISO complet du type
        "2026-11-15T00:00:00.000Z" est accepté), un datetime.date ou un
        datetime.datetime.
        """
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)[:10]

    def get_competition_dates(self, start):
        """Retourne la liste des dates auxquelles au moins une course a eu lieu,
        de `start` (incluse) jusqu'à la date courante (incluse).

        Les dates sont stockées en texte "YYYY-MM-DD" dans course.date ;
        la liste retournée est une liste de datetime.date, triée par
        ordre croissant.

        Parameters
        ----------
        start : str, datetime.date ou datetime.datetime
            Date de début de la période. Une str est attendue au format
            "YYYY-MM-DD" (un ISO complet est tronqué à 10 caractères).

        Returns
        -------
        list de datetime.date
            Les dates distinctes de course entre `start` et aujourd'hui.
        """
        start = self._normalize_date(start)
        today = date.today().isoformat()
        self.cur.execute(
            "SELECT DISTINCT date FROM course "
            "WHERE date BETWEEN ? AND ? "
            "ORDER BY date",
            (start, today),
        )
        return [date.fromisoformat(row[0]) for row in self.cur.fetchall()]

    def get_courses_on_period(self, start, end, last_day_max_phase):
        """Retourne les id des courses ayant eu lieu de `start` (inclus) à `end`
        (inclus), avec une restriction sur le dernier jour.

        Pour les dates strictement antérieures à `end`, toutes les courses sont
        retenues, quelle que soit leur phase. Pour le dernier jour (`date = end`),
        seules les courses dont `phase_ordre <= last_day_max_phase` sont retenues
        (phase_ordre : 0 = pas de phase, 0.k = "Course n°k", 1 = qualification,
        2 = demi-finale, 3 = finale).

        Parameters
        ----------
        start, end : str, datetime.date ou datetime.datetime
            Bornes de la période. Une str est attendue au format "YYYY-MM-DD"
            (un ISO complet est tronqué à 10 caractères).
        last_day_max_phase : float
            phase_ordre maximal accepté pour les courses du dernier jour (`end`).

        Returns
        -------
        list de int
            Les id (clé primaire) des courses concernées, triés par date, puis
            phase_ordre, puis id.
        """
        start = self._normalize_date(start)
        end = self._normalize_date(end)
        self.cur.execute(
            "SELECT id FROM course "
            "WHERE date BETWEEN ? AND ? "
            "  AND (date < ? OR phase_ordre <= ?) "
            "ORDER BY date, phase_ordre, id",
            (start, end, end, last_day_max_phase),
        )
        return [row[0] for row in self.cur.fetchall()]

    def get_courses_on_date_phase(self, date, phase):
        """Retourne les id des courses ayant eu lieu à la date `date` et dont
        la phase (course.phase_ordre) est exactement égale à `phase`.

        Parameters
        ----------
        date : str, datetime.date ou datetime.datetime
            Date des courses recherchées. Une str est attendue au format
            "YYYY-MM-DD" (un ISO complet est tronqué à 10 caractères).
        phase : float
            phase_ordre recherché (0 = pas de phase, 0.k = "Course n°k",
            1 = qualification, 2 = demi-finale, 3 = finale).

        Returns
        -------
        list de int
            Les id (clé primaire) des courses concernées, triés par id.
        """
        date = self._normalize_date(date)
        self.cur.execute(
            "SELECT id FROM course "
            "WHERE date = ? AND phase_ordre = ? "
            "ORDER BY id",
            (date, phase),
        )
        return [row[0] for row in self.cur.fetchall()]

    def get_scores_on_period(self, start, end, last_day_max_phase):
        """Retourne les scores scratch des résultats des courses ayant eu lieu
        de `start` (inclus) à `end` (inclus), avec une restriction sur le
        dernier jour.

        Pour les dates strictement antérieures à `end`, toutes les courses sont
        retenues, quelle que soit leur phase. Pour le dernier jour
        (`course.date = end`), seules les courses dont
        `course.phase_ordre <= last_day_max_phase` sont retenues (phase_ordre :
        0 = pas de phase, 0.k = "Course n°k", 1 = qualification,
        2 = demi-finale, 3 = finale).

        Parameters
        ----------
        start, end : str, datetime.date ou datetime.datetime
            Bornes de la période. Une str est attendue au format "YYYY-MM-DD"
            (un ISO complet est tronqué à 10 caractères).
        last_day_max_phase : float
            phase_ordre maximal accepté pour les courses du dernier jour (`end`).

        Returns
        -------
        list de tuple (int, int, float)
            (resultat.course_id, resultat.bateau_id, resultat.score)
            pour chaque résultat concerné, triés par date de course, phase_ordre,
            course_id, puis bateau_id. score_scratch vaut None si NULL en base.
        """
        start = self._normalize_date(start)
        end = self._normalize_date(end)
        self.cur.execute(
            "SELECT r.course_id, r.bateau_id, r.score "
            "FROM resultat r JOIN course c ON c.id = r.course_id "
            "WHERE c.date BETWEEN ? AND ? "
            "  AND (c.date < ? OR c.phase_ordre <= ?) "
            "ORDER BY c.date, c.phase_ordre, r.course_id, r.bateau_id",
            (start, end, end, last_day_max_phase),
        )
        return self.cur.fetchall()

    def get_boat_infos_on_course(self, course_id):
        """Retourne, pour la course d'id `course_id`, la liste des informations
        par bateau (résultat) : type de bateau, score scratch, niveau de la
        compétition, phase de la course et finale A/B.

        Parameters
        ----------
        course_id : int
            Id (clé primaire) de la course.

        Returns
        -------
        list de tuple (int, str, float, int, float, str)
            (resultat.bateau_id, resultat.type_code, resultat.score,
             competition.niveau, course.phase_competition, resultat.phase)
            pour chaque résultat de la course, triés par bateau_id.
            niveau, phase_ordre et phase sont répétés sur chaque ligne
            (ils décrivent la course / la compétition, pas le bateau).
            Un champ vaut None si NULL en base.
        """
        self.cur.execute(
            "SELECT r.bateau_id, r.type_code, r.score, "
            "       comp.niveau, c.phase_ordre, r.phase "
            "FROM resultat r "
            "JOIN course c ON c.id = r.course_id "
            "JOIN competition comp ON comp.id = c.competition_id "
            "WHERE r.course_id = ? "
            "ORDER BY r.bateau_id",
            (course_id,),
        )
        return self.cur.fetchall()

    def get_points_from_boat_id(
        self, boat_id, points_name, start_date, end_date, last_day_phase
    ):
        """Retourne les points obtenus par un bateau sur la période, avec le
        niveau de la compétition associée.

        Les points sont lus dans la table de la méthode de calcul
        `resultat_methode_{points_name}` (ex "ffck" -> resultat_methode_ffck).

        Pour les dates strictement antérieures à `end_date`, toutes les
        courses sont retenues. Pour le dernier jour (`course.date = end_date`),
        seules les courses dont `course.phase_ordre <= last_day_phase` sont
        retenues.

        Parameters
        ----------
        boat_id : int
            Id (clé primaire) du bateau (resultat.bateau_id).
        points_name : str
            Nom de la méthode de calcul ; la table interrogée est
            `resultat_methode_{points_name}`. Doit être un identifiant SQL sûr
            (lettres, chiffres, "_", commençant par une lettre ou "_"),
            sinon ValueError.
        start_date, end_date : str, datetime.date ou datetime.datetime
            Bornes de la période, incluses ("YYYY-MM-DD" pour les str).
        last_day_phase : float
            phase_ordre maximal retenu pour les courses du dernier jour.

        Returns
        -------
        list de tuple (float, int)
            (resultat_methode_{points_name}.points, competition.niveau),
            triés par date de course, phase_ordre, puis id de résultat.
            points vaut None si NULL en base.
        """
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", points_name or ""):
            raise ValueError(f"Nom de méthode de points invalide : {points_name!r}")
        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)
        self.cur.execute(
            f"SELECT rm.points, comp.niveau "
            f"FROM resultat r "
            f"JOIN course c ON c.id = r.course_id "
            f"JOIN competition comp ON comp.id = c.competition_id "
            f"JOIN resultat_methode_{points_name} rm ON rm.resultat_id = r.id "
            f"WHERE r.bateau_id = ? "
            f"  AND c.date BETWEEN ? AND ? "
            f"  AND (c.date < ? OR c.phase_ordre <= ?) "
            f"ORDER BY c.date, c.phase_ordre, r.id",
            (boat_id, start_date, end_date, end_date, last_day_phase),
        )
        return self.cur.fetchall()

    def save_resultat_methode(self, bateau_id, course_id, point_name, points, valeur):
        """Enregistre les points et la valeur calculés par la méthode
        `point_name` pour le résultat identifié par (bateau_id, course_id).

        La ligne est créée dans la table `resultat_methode_{point_name}`
        (remplacée si elle existe déjà pour ce résultat).

        Parameters
        ----------
        bateau_id, course_id : int
            Identifient le résultat dans la table resultat ; le couple doit
            correspondre à un unique résultat.
        point_name : str
            Nom de la méthode de calcul (identifiant SQL sûr), ex "ffck".
        points, valeur : float
            Valeurs à stocker (None accepté -> NULL en base).

        Raises
        ------
        ValueError
            Si `point_name` n'est pas un identifiant SQL sûr, ou si le couple
            (bateau_id, course_id) ne correspond à aucun résultat ou à
            plusieurs résultats.
        """
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", point_name or ""):
            raise ValueError(f"Nom de méthode de points invalide : {point_name!r}")
        self.cur.execute(
            "SELECT id FROM resultat WHERE bateau_id = ? AND course_id = ?",
            (bateau_id, course_id),
        )
        rows = self.cur.fetchall()
        if len(rows) == 0:
            raise ValueError(
                f"Aucun resultat pour bateau_id={bateau_id}, course_id={course_id}"
            )
        if len(rows) > 1:
            raise ValueError(
                f"{len(rows)} resultats pour bateau_id={bateau_id}, "
                f"course_id={course_id} : le couple n'est pas unique"
            )
        resultat_id = rows[0][0]
        self.cur.execute(
            f"INSERT OR REPLACE INTO resultat_methode_{point_name} "
            f"(resultat_id, points, valeur) VALUES (?, ?, ?)",
            (resultat_id, points, valeur),
        )
        self.conn.commit()

    def save_point_computing_details(self, course_id, points_name, course_infos):
        """Sauvegarde les détails de calcul de points d'une course dans la table
        `course_methode_{points_name}`, colonne "details" : le dictionnaire
        `course_infos` sérialisé en JSON.

        La table `course_methode_{points_name}` doit déjà exister (sa création
        est gérée ailleurs) avec course_id en clé primaire et une colonne
        details TEXT.

        Parameters
        ----------
        course_id : int
            Id (clé primaire) de la course ; doit exister dans la table course.
        points_name : str
            Nom de la méthode de calcul (identifiant SQL sûr), ex "ffck".
        course_infos : dict
            Dictionnaire des détails à sérialiser (les objets non JSON, ex
            datetime, sont convertis en str).

        Raises
        ------
        ValueError
            Si `point_name` n'est pas un identifiant SQL sûr, ou si aucune
            course n'a cet id.
        """
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", points_name or ""):
            raise ValueError(f"Nom de méthode de points invalide : {points_name!r}")
        self.cur.execute("SELECT id FROM course WHERE id = ?", (course_id,))
        if self.cur.fetchone() is None:
            raise ValueError(f"Aucune course avec id={course_id}")
        table = f"course_methode_{points_name}"
        details_json = json.dumps(course_infos, ensure_ascii=False, default=str)
        self.cur.execute(
            f"INSERT INTO {table} (course_id, details) VALUES (?, ?) "
            f"ON CONFLICT(course_id) DO UPDATE SET details = excluded.details",
            (course_id, details_json),
        )
        self.conn.commit()

    def create_point_type(self, point_name):
        """Crée les tables dédiées à une méthode de calcul de points :
        - `course_methode_{point_name}` (course_id PK/FK, details TEXT)
        - `resultat_methode_{point_name}` (resultat_id PK/FK, points REAL,
          valeur REAL)

        Les tables ne sont créées que si elles n'existent pas déjà.

        Parameters
        ----------
        point_name : str
            Nom de la méthode de calcul (identifiant SQL sûr), ex "ffck".

        Raises
        ------
        ValueError
            Si `point_name` n'est pas un identifiant SQL sûr.
        """
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", point_name or ""):
            raise ValueError(f"Nom de méthode de points invalide : {point_name!r}")
        self.cur.execute(
            f"CREATE TABLE IF NOT EXISTS course_methode_{point_name} ("
            f"course_id INTEGER PRIMARY KEY REFERENCES course(id) ON DELETE CASCADE, "
            f"details TEXT)"
        )
        self.cur.execute(
            f"CREATE TABLE IF NOT EXISTS resultat_methode_{point_name} ("
            f"resultat_id INTEGER PRIMARY KEY REFERENCES resultat(id) ON DELETE CASCADE, "
            f"points REAL, "
            f"valeur REAL)"
        )
        self.conn.commit()

    def delete_point_type(self, point_name):
        """Supprime les tables `course_methode_{point_name}` et
        `resultat_methode_{point_name}`, et donc tous leurs enregistrements.

        Ne fait rien si les tables n'existent pas.

        Parameters
        ----------
        point_name : str
            Nom de la méthode de calcul (identifiant SQL sûr), ex "ffck".

        Raises
        ------
        ValueError
            Si `point_name` n'est pas un identifiant SQL sûr.
        """
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", point_name or ""):
            raise ValueError(f"Nom de méthode de points invalide : {point_name!r}")
        self.cur.execute(f"DROP TABLE IF EXISTS course_methode_{point_name}")
        self.cur.execute(f"DROP TABLE IF EXISTS resultat_methode_{point_name}")
        self.conn.commit()

    def get_point_type_computing_start_date(self, point_type):
        """Retourne la date de la première course (la plus ancienne) qui n'a
        pas encore de ligne dans `course_methode_{point_type}` — typiquement le
        point de départ pour calculer les points d'une méthode donnée.

        Si la table `course_methode_{point_type}` n'existe pas encore, aucune
        course n'a de détails enregistrés : on retourne alors la date de la
        plus ancienne course. Si toutes les courses ont une entrée (ou s'il
        n'y a aucune course datée), retourne None.

        Parameters
        ----------
        point_type : str
            Nom de la méthode de calcul (identifiant SQL sûr), ex "ffck".

        Returns
        -------
        str ou None
            Date "YYYY-MM-DD" de la première course sans entrée dans la table
            de la méthode, ou None.

        Raises
        ------
        ValueError
            Si `point_type` n'est pas un identifiant SQL sûr.
        """
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", point_type or ""):
            raise ValueError(f"Nom de méthode de points invalide : {point_type!r}")
        table = f"course_methode_{point_type}"
        self.cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        )
        if self.cur.fetchone() is None:
            # table inexistante : aucune course n'a de détails -> plus ancienne course
            self.cur.execute("SELECT MIN(date) FROM course WHERE date IS NOT NULL")
            return self.cur.fetchone()[0]
        self.cur.execute(
            f"SELECT c.date FROM course c "
            f"LEFT JOIN {table} cm ON cm.course_id = c.id "
            f"WHERE cm.course_id IS NULL AND c.date IS NOT NULL "
            f"ORDER BY c.date LIMIT 1"
        )
        row = self.cur.fetchone()
        return row[0] if row else None

    def remove_point_type_after_date(self, point_type, date):
        """Supprime les entrées de `course_methode_{point_type}` et
        `resultat_methode_{point_type}` pour les courses dont la date est
        supérieure ou égale à `date` (les courses sans date sont conservées).

        Si une des deux tables n'existe pas, elle est ignorée (rien à
        supprimer). Utile pour recalculer une méthode à partir d'une date.

        Parameters
        ----------
        point_type : str
            Nom de la méthode de calcul (identifiant SQL sûr), ex "ffck".
        date : str, datetime.date ou datetime.datetime
            Date seuil, incluse ("YYYY-MM-DD" pour les str).

        Returns
        -------
        tuple (int, int)
            (nb entrées supprimées dans course_methode_{point_type},
             nb entrées supprimées dans resultat_methode_{point_type})

        Raises
        ------
        ValueError
            Si `point_type` n'est pas un identifiant SQL sûr.
        """
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", point_type or ""):
            raise ValueError(f"Nom de méthode de points invalide : {point_type!r}")
        date = self._normalize_date(date)
        supprimes = []
        for table, requete in (
            (
                f"course_methode_{point_type}",
                f"DELETE FROM course_methode_{point_type} "
                f"WHERE course_id IN (SELECT id FROM course WHERE date >= ?)",
            ),
            (
                f"resultat_methode_{point_type}",
                f"DELETE FROM resultat_methode_{point_type} "
                f"WHERE resultat_id IN ("
                f"  SELECT r.id FROM resultat r JOIN course c ON c.id = r.course_id "
                f"  WHERE c.date >= ?"
                f")",
            ),
        ):
            self.cur.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            )
            if self.cur.fetchone() is None:
                supprimes.append(0)  # table inexistante : rien à supprimer
                continue
            self.cur.execute(requete, (date,))
            supprimes.append(self.cur.rowcount)
        self.conn.commit()
        return tuple(supprimes)
