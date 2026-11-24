# -*- coding: utf-8 -*-
"""
Correction des noms d'équipage des canoës biplace (C2H, C2D, C2M...).

Problème : sur les vieilles courses, l'API web ne renvoie parfois qu'UN seul
nom dans le libellé du bateau C2 (ex "Michel Andre" au lieu de
"Thibault Dhennin\\nMichel Andre"), et la fiche bateau ne contient qu'une
seule personne dans "people".

Correction : on retrouve les DEUX noms dans les anciens résultats CSV de la
fédération (dossier old_csv_database, fichiers "AAAA-MM-JJ-... Course N.csv",
en Latin-1), où les biplaces sont écrits "Prenom Nom1-Prenom Nom2" dans la
colonne "Athlète".

Pour chaque bateau C2 incomplet en base (libellé sans saut de ligne, ou moins
de 2 compétiteurs liés), on cherche dans les CSV une ligne de même catégorie
(C2H/C2D/C2M) dont un segment correspond au nom connu, de préférence à une
date où le bateau a couru. On met alors à jour :
  - bateau.libelle            -> "Nom1\\nNom2"
  - competiteur               -> créé si besoin (id_api NULL, nom/prénom du CSV)
  - bateau_competiteur        -> positions 1 et 2 (ordre du CSV)

La correction est idempotente et peut être relancée sans risque.

Appelée depuis collecte_bdd.py via --correction-noms-c2.
"""

import csv
import os
import re
import sqlite3
import sys

from . import config, referentiel
from .utils import normaliser

RE_DATE_FICHIER = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def normaliser_csv(texte):
    """Normalisation des noms issus des anciens CSV : tirets et apostrophes
    -> espaces, le reste de la ponctuation (ex ".") est conservé."""
    return normaliser(texte, separateurs_sup="- '", tout_non_alnum=False)


def lire_csv(chemin):
    """Lit un CSV en essayant utf-8 puis latin-1 ; renvoie la liste des lignes."""
    for enc in ("utf-8", "latin-1"):
        try:
            with open(chemin, encoding=enc, newline="") as f:
                return list(csv.reader(f, delimiter=",", quotechar='"'))
        except UnicodeDecodeError:
            continue
    with open(chemin, encoding="latin-1", errors="replace", newline="") as f:
        return list(csv.reader(f, delimiter=",", quotechar='"'))


def construire_index(dossier, verbose=False):
    """
    Index des lignes C2 des CSV :
      index_segments[nom_segment_normalisé] -> liste d'entrées
      entrees : dict(date, categorie, athlete, segments, fichier)
    """
    index_segments = {}
    entrees_par_cat = {}
    nb_fichiers = 0
    nb_lignes_c2 = 0
    for nom_fichier in sorted(os.listdir(dossier)):
        if not nom_fichier.lower().endswith(".csv"):
            continue
        m = RE_DATE_FICHIER.match(nom_fichier)
        date = m.group(1) if m else None
        chemin = os.path.join(dossier, nom_fichier)
        try:
            lignes = lire_csv(chemin)
        except Exception as e:
            print(f"  [csv ignoré] {nom_fichier}: {e}", file=sys.stderr)
            continue
        nb_fichiers += 1
        for ligne in lignes:
            if len(ligne) < 2:
                continue
            cat = ligne[1].strip().upper()
            if not cat.startswith("C2"):
                continue
            athlete = ligne[0].strip().strip('"').strip()
            if not athlete or "-" not in athlete:
                continue
            segments = [s.strip() for s in athlete.split("-") if s.strip()]
            if len(segments) < 2:
                continue
            entree = {"date": date, "categorie": cat, "athlete": athlete,
                      "segments": segments, "fichier": nom_fichier}
            nb_lignes_c2 += 1
            entrees_par_cat.setdefault(cat, []).append(entree)
            for seg in segments:
                index_segments.setdefault(normaliser_csv(seg), []).append(entree)
    if verbose:
        print(f"Index CSV : {nb_fichiers} fichiers, {nb_lignes_c2} lignes C2, "
              f"{len(index_segments)} noms indexés.")
    return index_segments, entrees_par_cat


def segment_match(seg_norm, connu_norm):
    """Le segment correspond au nom connu (égalité ou inclusion, ex accents)."""
    if not seg_norm or not connu_norm:
        return False
    return seg_norm == connu_norm or connu_norm in seg_norm or seg_norm in connu_norm


def trouver_equipage(index_segments, entrees_par_cat, type_code, nom_connu, dates):
    """
    Renvoie (nom1, nom2, entree) ou None.
    nom1/nom2 = les deux noms dans l'ordre du CSV.
    """
    connu_norm = normaliser_csv(nom_connu)
    candidats = []
    # 1) recherche directe via l'index des segments
    for seg, entrees in index_segments.items():
        if segment_match(seg, connu_norm):
            candidats.extend(entrees)
    # 2) repli : scan des entrées de la même catégorie (variantes de noms)
    if not candidats:
        cat = (type_code or "").upper()
        for c, entrees in entrees_par_cat.items():
            if c == cat or (cat and c.startswith(cat[:3])):
                for e in entrees:
                    if segment_match(normaliser_csv(e["athlete"]), connu_norm):
                        candidats.append(e)
    # filtrage par catégorie exacte si possible
    if type_code:
        exact = [e for e in candidats if e["categorie"] == type_code.upper()]
        if exact:
            candidats = exact
    # filtrage par date de participation du bateau
    if dates:
        avec_date = [e for e in candidats if e["date"] in dates]
        if avec_date:
            candidats = avec_date
    # dédoublonnage par (fichier, athlete)
    vus = set()
    uniq = []
    for e in candidats:
        cle = (e["fichier"], e["athlete"])
        if cle not in vus:
            vus.add(cle)
            uniq.append(e)
    if not uniq:
        return None
    # extraire les deux noms de chaque candidat et ne garder que ceux qui
    # donnent le même équipage
    equipages = {}
    for e in uniq:
        segs = e["segments"]
        nom1 = segs[0]
        nom2 = "-".join(segs[1:])
        # vérifier que le nom connu correspond bien à l'un des deux
        if not (segment_match(normaliser_csv(nom1), connu_norm) or segment_match(normaliser_csv(nom2), connu_norm)):
            continue
        equipages.setdefault((normaliser_csv(nom1), normaliser_csv(nom2)), (nom1, nom2, e))
    if len(equipages) == 1:
        return next(iter(equipages.values()))
    return None  # ambigu


def parser_nom_complet(nom_complet):
    """'Prenom Nom' -> (prenom, nom) ; 'Nom' seul -> (None, nom)."""
    morceaux = nom_complet.split(" ", 1)
    if len(morceaux) > 1:
        return morceaux[0].strip(), morceaux[1].strip()
    return None, morceaux[0].strip()


def trouver_ou_creer_competiteur(cur, prenom, nom):
    # Pas d'id_api côté CSV : matching par nom (exact puis normalisé) via le
    # référentiel, pour ne pas créer de doublon avec un compétiteur existant.
    if not nom:
        return None
    return referentiel.ref_competiteur(cur, None, nom, prenom)


def corriger_noms_c2(db, csv_dir=None, dry_run=False, verbose=False):
    """Corrige les noms d'équipage des C2 incomplets de la base `db`.

    db       : chemin de la base SQLite (ex "results.db")
    csv_dir  : dossier des anciens CSV FFCK (défaut : old_csv_database/)
    dry_run  : n'écrit rien en base
    verbose  : affiche chaque correction trouvée
    """
    if csv_dir is None:
        csv_dir = config.CSV_DIR_DEFAUT

    conn = sqlite3.connect(db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    cur = conn.cursor()

    print(f"Indexation des CSV de {csv_dir} ...")
    index_segments, entrees_par_cat = construire_index(csv_dir, verbose=verbose)

    # bateaux C2 incomplets : libellé sans saut de ligne OU moins de 2 compétiteurs
    # (HAVING car nb_comp est un alias d'agrégat, filtrable seulement après GROUP BY)
    cur.execute("""
        SELECT b.id, b.id_api, b.libelle, b.type_code, COUNT(bc.competiteur_id) AS nb_comp
        FROM bateau b
        LEFT JOIN bateau_competiteur bc ON bc.bateau_id = b.id
        WHERE b.type_code LIKE 'C2%'
        GROUP BY b.id
        HAVING b.libelle IS NULL OR b.libelle NOT LIKE '%' || char(10) || '%' OR nb_comp < 2
        ORDER BY b.id
    """)
    a_corriger = cur.fetchall()
    print(f"{len(a_corriger)} bateaux C2 incomplets à corriger.")

    nb_ok, nb_ambigu, nb_sans = 0, 0, 0
    for bateau_id, id_api, libelle, type_code, nb_comp in a_corriger:
        nom_connu = (libelle or "").split("\n")[0].strip() if libelle else ""
        # dates des courses où ce bateau a participé
        cur.execute("""SELECT DISTINCT c.date FROM resultat r
                       JOIN course c ON c.id = r.course_id
                       WHERE r.bateau_id = ? AND c.date IS NOT NULL""", (bateau_id,))
        dates = {r[0] for r in cur.fetchall()}

        trouve = trouver_equipage(index_segments, entrees_par_cat, type_code, nom_connu, dates) if nom_connu else None
        if not trouve:
            nb_sans += 1
            print(f"  [sans candidat] {id_api} ({type_code}) libelle={libelle!r}")
            continue
        nom1, nom2, entree = trouve
        # parfois le même nom des deux côtés ou un seul nom exploitable
        if normaliser_csv(nom1) == normaliser_csv(nom2):
            nb_ambigu += 1
            print(f"  [ambigu] {id_api} : {entree['athlete']!r} ({entree['fichier']})")
            continue
        # un seul candidat d'équipage -> OK ; sinon on a déjà filtré (trouver_equipage
        # ne renvoie que si un seul équipage distinct)
        if verbose:
            print(f"  [ok] {id_api} ({type_code}) : {libelle!r} -> {nom1!r} + {nom2!r} "
                  f"(source: {entree['fichier']})")
        if dry_run:
            nb_ok += 1
            continue
        # mise à jour en base
        pre1, nom_fam1 = parser_nom_complet(nom1)
        pre2, nom_fam2 = parser_nom_complet(nom2)
        c1 = trouver_ou_creer_competiteur(cur, pre1, nom_fam1)
        c2 = trouver_ou_creer_competiteur(cur, pre2, nom_fam2)
        cur.execute("UPDATE bateau SET libelle = ? WHERE id = ?", (nom1 + "\n" + nom2, bateau_id))
        if c1:
            cur.execute("INSERT OR REPLACE INTO bateau_competiteur (bateau_id, competiteur_id, position) "
                        "VALUES (?, ?, 1)", (bateau_id, c1))
        if c2:
            cur.execute("INSERT OR REPLACE INTO bateau_competiteur (bateau_id, competiteur_id, position) "
                        "VALUES (?, ?, 2)", (bateau_id, c2))
        nb_ok += 1

    if not dry_run:
        conn.commit()
    print(f"Terminé : {nb_ok} corrigés, {nb_ambigu} ambigus, {nb_sans} sans candidat"
          + (" (dry-run, rien d'écrit)" if dry_run else ""))
    conn.close()
