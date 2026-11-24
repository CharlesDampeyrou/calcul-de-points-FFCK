# -*- coding: utf-8 -*-
"""Collecte des compétitions et de leurs courses/resultats."""

import sqlite3
import sys
import time

from . import api, config, phases, referentiel, team_events
from .bateaux import enregistrer_bateau
from .utils import date_courte, normaliser


def enregistrer_course(cur, conn, ev, race):
    race_id_api = str(race.get("id"))
    cur.execute("SELECT id FROM course WHERE id_api = ?", (race_id_api,))
    if cur.fetchone():
        print(f"    Course {race_id_api} déjà en base, ignorée.")
        return 0

    # course.date est obligatoire : une course sans date (ou avec le
    # placeholder API 2030-01-01, voir date_courte) n'est pas enregistrée.
    date_course = date_courte(race.get("date"))
    if date_course is None:
        print(f"    Course {race_id_api} ({race.get('name')!r}) : pas de date, ignorée.")
        return 0

    # v2 : identifiant de méthode en simple champ texte de COURSE.
    # L'API l'appelle "pointsCalculationMethodId" depuis 2025 (UUID) et
    # "officialPointsCalculationMethod" avant (ex "2025") : on prend l'un ou l'autre.
    pcmid = race.get("pointsCalculationMethodId") or race.get(
        "officialPointsCalculationMethod"
    )
    pcmid = str(pcmid) if pcmid else None

    # Phase de compétition, déduite du NOM de la course via phases_courses.json
    # (mapping alimenté interactivement ; PAS de classification automatique).
    nom_course = race.get("name")
    contexte = f"course {race_id_api}, {ev.get('name')} - {ev.get('place')}, {date_courte(ev.get('startDate') or ev.get('date'))}"
    phase = phases.determiner_phase(nom_course, contexte)
    ordre_explicite = phases.MAPPING_PHASES.get(normaliser(nom_course), {}).get("ordre")
    phase_ordre = phases.calculer_phase_ordre(nom_course, phase, ordre_explicite)

    cur.execute(
        "INSERT INTO course (id_api, competition_id, nom, date, nb_portes, "
        "penalites_completes, points_calculation_method_id, phase_competition, phase_ordre) "
        "VALUES (?, (SELECT id FROM competition WHERE id_api = ?), ?, ?, ?, ?, ?, ?, ?)",
        (
            race_id_api,
            str(ev.get("id")),
            nom_course,
            date_course,
            race.get("gateNumber"),
            (
                1
                if race.get("fullPenalties")
                else (0 if race.get("fullPenalties") is not None else None)
            ),
            pcmid,
            phase,
            phase_ordre,
        ),
    )
    course_id = cur.lastrowid

    # v2 : baseTime / coefficient -> table dédiée à la méthode FFCK
    # (avant : colonnes temps_base / coefficient de COURSE).
    if race.get("baseTime") is not None or race.get("coefficient") is not None:
        cur.execute(
            "INSERT OR REPLACE INTO course_methode_ffck (course_id, temps_base, coefficient) "
            "VALUES (?, ?, ?)",
            (course_id, race.get("baseTime"), race.get("coefficient")),
        )

    detail = api.get_json(f"{config.BASE}/ffck/race/{race_id_api}")
    nb = 0
    if not isinstance(detail, dict):
        return 0

    results = detail.get("results")
    if not isinstance(results, list):
        results = []

    for res in results:
        if not isinstance(res, dict):
            continue
        boat = res.get("boat")
        if not isinstance(boat, dict):
            boat = {}
        boat_id_api = res.get("boatId") or boat.get("_id")
        if not boat_id_api:
            continue
        type_code = (
            res.get("boatType") or None
        )  # or None pour le cas où la catégorie est "" au lieu de null
        bateau_id = enregistrer_bateau(
            cur, conn, boat_id_api, boat.get("label"), type_code
        )

        # clubs du résultat (source course : parfois plus complète que la fiche)
        clubs = res.get("clubs")
        if isinstance(clubs, list):
            for club in clubs:
                if isinstance(club, dict):
                    club_id = referentiel.ref_club(cur, club)
                    cur.execute(
                        "INSERT OR IGNORE INTO bateau_club (bateau_id, club_id) VALUES (?, ?)",
                        (bateau_id, club_id),
                    )

        cat_code = (
            res.get("category") or None
        )  # or None pour le cas où la catégorie est "" au lieu de null
        if type_code:
            referentiel.ref_type(cur, type_code)

        # INSERT OR IGNORE : un _id déjà vu (dans une autre course) ne doit pas
        # faire échouer toute la course.
        res_id_api = res.get("_id")
        cur.execute(
            "INSERT OR IGNORE INTO resultat (id_api, course_id, bateau_id, categorie_code, type_code, "
            "dossard, phase, score, score_scratch, compte_dans_classement, statut) "
            "SELECT ?, c.id, ?, ?, ?, ?, ?, ?, ?, ?, ? "
            "FROM course c WHERE c.id_api = ?",
            (
                res_id_api,
                bateau_id,
                cat_code,
                type_code,
                res.get("bibNumber"),
                res.get("phase") or "",
                res.get("score"),
                res.get("scratchScore"),
                1 if res.get("countInRanking") else 0,
                res.get("status"),
                race_id_api,
            ),
        )
        if res_id_api is not None:
            cur.execute("SELECT id FROM resultat WHERE id_api = ?", (res_id_api,))
            row = cur.fetchone()
            if not row:
                continue  # résultat ignoré (doublon d'id_api) : on passe au suivant
            resultat_id = row[0]
        else:
            resultat_id = cur.lastrowid

        # v2 : points / valeur calculés par la méthode FFCK -> table dédiée
        # (avant : colonnes points / valeur de RESULTAT).
        cur.execute(
            "INSERT OR REPLACE INTO resultat_methode_ffck (resultat_id, points, valeur) "
            "VALUES (?, ?, ?)",
            (resultat_id, res.get("points"), res.get("value")),
        )

        runs = res.get("runs")
        if not isinstance(runs, list):
            runs = []
        for num, run in enumerate(runs, start=1):
            if not isinstance(run, dict):
                continue
            cur.execute(
                "INSERT OR REPLACE INTO manche (resultat_id, numero, temps, penalites, total, statut) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    resultat_id,
                    num,
                    run.get("time"),
                    run.get("penalties"),
                    run.get("total"),
                    run.get("status"),
                ),
            )
            manche_id = cur.lastrowid
            pd = run.get("penaltiesDetail")
            if not isinstance(pd, list):
                pd = []
            for porte, val in enumerate(pd, start=1):
                if val is None:
                    val = 0  # valeur NOT NULL dans le schéma
                cur.execute(
                    "INSERT OR REPLACE INTO penalite (manche_id, numero_porte, valeur) "
                    "VALUES (?, ?, ?)",
                    (manche_id, porte, val),
                )
        nb += 1
    conn.commit()
    return nb


def collecter_annee(cur, conn, annee):
    print(f"Année {annee} : liste des compétitions...")
    data = api.get_json(f"{config.BASE}/ffck/events?year={annee}")
    if not data or not data.get("events"):
        print("  Aucune compétition.")
        return

    for ev in data["events"]:
        cur.execute("SELECT id FROM competition WHERE id_api = ?", (str(ev.get("id")),))
        if cur.fetchone():
            print(f"  {ev.get('place')} : déjà en base.")
        else:
            # foreignId "0"/vide = pas de vrai id externe (vieux events, répété :
            # plusieurs events ont "0" -> UNIQUE planterait) ; de même si un vrai
            # foreignId est déjà pris par une autre compétition. Dans les deux
            # cas on stocke NULL (UNIQUE SQLite autorise plusieurs NULL).
            id_ext = ev.get("foreignId")
            if id_ext in (None, "", "0"):
                id_ext = None
            elif id_ext:
                cur.execute(
                    "SELECT id FROM competition WHERE id_externe = ?", (id_ext,)
                )
                if cur.fetchone():
                    id_ext = None
            try:
                cur.execute(
                    "INSERT INTO competition (id_api, id_externe, nom, lieu, date_debut, "
                    "date_fin, niveau) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(ev.get("id")),
                        id_ext,
                        ev.get("name"),
                        ev.get("place"),
                        date_courte(ev.get("startDate")),
                        date_courte(ev.get("date")),
                        ev.get("level"),
                    ),
                )
            except sqlite3.IntegrityError:
                # ceinture : conflit inattendu sur id_externe -> réessaie sans
                cur.execute(
                    "INSERT INTO competition (id_api, id_externe, nom, lieu, date_debut, "
                    "date_fin, niveau) VALUES (?, NULL, ?, ?, ?, ?, ?)",
                    (
                        str(ev.get("id")),
                        ev.get("name"),
                        ev.get("place"),
                        date_courte(ev.get("startDate")),
                        date_courte(ev.get("date")),
                        ev.get("level"),
                    ),
                )
        print(
            f"  {ev.get('place')} : {ev.get('name')} ({len(ev.get('races') or [])} course(s))"
        )
        races = ev.get("races")
        if not isinstance(races, list):
            races = []
        for race in races:
            if not isinstance(race, dict) or not race.get("id"):
                continue
            # courses par équipe : on ne les sauvegarde pas (décision connue via
            # team_events.json, ou demandée interactivement ici)
            if team_events.est_course_equipe(race, ev):
                print(
                    f"    Course {race['id']} ({race.get('name')!r}) : course par équipe, ignorée."
                )
                continue
            try:
                n = enregistrer_course(cur, conn, ev, race)
            except Exception as e:
                # une course en erreur ne doit pas arrêter toute la collecte :
                # on annule la transaction en cours et on passe à la suivante.
                conn.rollback()
                print(
                    f"    Course {race.get('id')} EN ERREUR, ignorée : "
                    f"{type(e).__name__}: {e}",
                    file=sys.stderr,
                )
                continue
            print(f"    Course {race['id']} : {n} résultats.")
            time.sleep(config.DELAI)
    conn.commit()
