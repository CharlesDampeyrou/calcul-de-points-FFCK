#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alimentation d'une base SQLite avec les résultats de slalom FFCK (CNA Slalom),
plus post-traitements optionnels (correction des noms C2, revue des phases).

Point d'entrée unique du dossier data_collection/ ; la logique est dans le
package ./collecte/ :
  config.py        constantes et chemins par défaut
  utils.py         normaliser(), date_courte()
  api.py           get_json() (API https://slalom.ffck.org)
  phases.py        mapping phases_courses.json (qualification/demi-finale/finale)
  team_events.py   team_events.json (courses par équipe, non sauvegardées)
  referentiel.py   type_bateau / club
  bateaux.py       fiches bateaux (une seule requête API par bateau)
  courses.py       compétitions, courses, résultats, manches, pénalités
  correction_c2.py correction des noms d'équipage des C2 (--correction-noms-c2)
  revue_phases.py  revue interactive des phases (--revoir-phases)
  nettoyage_categories.py  suppression des résultats dont le type de bateau
                           n'est pas autorisé (post-traitement systématique)
  nettoyage_doublons.py    suppression des doublons (course_id, bateau_id) :
                           garde le meilleur score_scratch (post-traitement
                           systématique)

Source : API JSON du site https://slalom.ffck.org (application Vue.js).
Endpoints utilisés :
  GET /api/ffck/events?year=AAAA     -> compétitions d'une année (avec leurs courses)
  GET /api/ffck/race/{raceId}        -> résultats détaillés d'une course
  GET /api/ffck/boats/{boatId}       -> fiche du bateau : équipage, année de
                                        naissance, niveau, surclassement, club

Utilisation :
  python3 collecte_bdd.py                                  # collecte 2001 à l'année courante
  python3 collecte_bdd.py --debut 2010 --fin 2015
  python3 collecte_bdd.py --debut 2024 --db ma_base.db
  python3 collecte_bdd.py --no-interactif --correction-noms-c2 --revoir-phases
Relancez le même script après une nouvelle saison : les données déjà
présentes sont ignorées (INSERT OR IGNORE).

Pipeline : collecte -> nettoyage des catégories -> nettoyage des doublons
-> [--correction-noms-c2] -> [--revoir-phases].
--dry-run ne s'applique qu'aux post-traitements, nettoyage des catégories inclus
(pas à la collecte).

Aucune bibliothèque externe requise (sqlite3, urllib, json inclus).
Le schéma des tables est créé par schema_slalom.sql, exécuté
automatiquement si la base est vide, sinon importez-le avant :
  sqlite3 classement.db < schema_slalom.sql

------------------------------------------------------------
Phases des courses (qualification / demi-finale / finale) :
  La phase n'est PAS déduite automatiquement : elle est lue dans le mapping
  phases_courses.json (clé = nom de la course normalisé).
  Quand un nom de course inconnu apparaît, le script émet un bip et demande
  la phase interactivement (elle est alors enregistrée dans le JSON).
  --no-interactif : les noms inconnus passent à NULL et sont loggés dans
  phases_inconnues.log, à rejouer ensuite avec --revoir-phases.
  Stockage : course.phase_competition (NULL = pas de phase) et
  course.phase_ordre (0 = pas de phase, 0.k = "Course n°k", 1/2/3 =
  qualification/demi-finale/finale).

------------------------------------------------------------
Courses par équipe (NON sauvegardées) :
  team_events.json = {"team": [...], "non_team": [...]} (matching par nom
  normalisé sur race.name / ev.name). Une course est candidate "par équipe"
  si son nom (ou celui de son event) contient "equipe"/"patrouille".
  - nom connu dans le JSON -> décision appliquée directement ;
  - candidat inconnu -> bip + question interactive, réponse enregistrée
    dans le JSON ; en --no-interactif : la course est sautée et loggée dans
  team_events_inconnus.log.

------------------------------------------------------------
Correction des noms C2 (--correction-noms-c2) :
  Sur les vieilles courses, l'API ne renvoie parfois qu'un seul nom pour un
  bateau C2. La correction retrouve les deux noms dans les anciens CSV de la
  fédération (--csv-dir, défaut old_csv_database/) et met à jour bateau,
  competiteur et bateau_competiteur. Idempotent.
"""

import argparse
import datetime
import os
import sqlite3

from collecte import config, courses, phases, revue_phases, team_events
from collecte.correction_c2 import corriger_noms_c2
from collecte.nettoyage_categories import nettoyer_categories
from collecte.nettoyage_doublons import nettoyer_doublons


def main():
    ap = argparse.ArgumentParser(
        description="Collecte des résultats CNA Slalom (schéma v2) + post-traitements "
        "optionnels (correction noms C2, revue des phases)."
    )
    ap.add_argument("--debut", type=int, default=2001)
    ap.add_argument(
        "--fin",
        type=int,
        default=datetime.date.today().year,  # année courante à l'exécution
        help="Dernière année collectée (défaut : année courante)",
    )
    ap.add_argument("--db", default="../results.db")
    ap.add_argument(
        "--schema",
        default=config.SCHEMA_DEFAUT,
        help="Fichier schema_slalom.sql si la base doit être créée",
    )
    ap.add_argument(
        "--phases-json",
        default=config.PHASES_JSON_DEFAUT,
        help="Mapping nom de course -> phase (JSON)",
    )
    ap.add_argument(
        "--team-json",
        default=config.TEAM_JSON_DEFAUT,
        help="team_events.json : listes 'team' / 'non_team' des courses par équipe",
    )
    ap.add_argument(
        "--no-interactif",
        action="store_true",
        help="Ne bloque pas sur les noms de course inconnus : phase NULL + log dans phases_inconnues.log ; "
        "les potentielles courses par équipe inconnues sont sautées + loggées dans team_events_inconnus.log",
    )
    ap.add_argument(
        "--correction-noms-c2",
        action="store_true",
        help="Après la collecte : corrige les noms d'équipage des C2 incomplets "
        "depuis les anciens CSV (voir --csv-dir)",
    )
    ap.add_argument(
        "--csv-dir",
        default=config.CSV_DIR_DEFAUT,
        help="Dossier des anciens CSV FFCK pour --correction-noms-c2",
    )
    ap.add_argument(
        "--revoir-phases",
        action="store_true",
        help="Après la collecte : rejoue interactivement les phases des noms inconnus "
        "(phases_inconnues.log) et répercute le mapping dans la base",
    )
    ap.add_argument(
        "--revoir-phases-tout",
        action="store_true",
        help="Avec --revoir-phases : propose aussi tous les noms de courses de la base",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne s'applique qu'aux post-traitements (--correction-noms-c2, --revoir-phases) : "
        "n'écrit rien en base pour ces étapes",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    config.INTERACTIF = not args.no_interactif
    phases.init_phases(args.phases_json, config.LOG_INCONNUS_DEFAUT)
    team_events.init_team_events(args.team_json, config.LOG_TEAM_INCONNUS_DEFAUT)
    print(
        f"Mapping des phases : {len(phases.MAPPING_PHASES)} noms connus "
        f"({phases.CHEMIN_PHASES_JSON}){' [mode non-interactif]' if not config.INTERACTIF else ''}"
    )
    print(
        f"Courses par équipe : {len(team_events.TEAM_EVENTS['team'])} team, "
        f"{len(team_events.TEAM_EVENTS['non_team'])} non_team connues ({team_events.CHEMIN_TEAM_JSON})"
    )

    base_vide = not os.path.exists(args.db)
    conn = sqlite3.connect(args.db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")  # évite "database is locked"
    cur = conn.cursor()
    if base_vide:
        print(f"Création du schéma dans {args.db}...")
        with open(args.schema, encoding="utf-8") as f:
            cur.executescript(f.read())
        conn.commit()

    for annee in range(args.debut, args.fin + 1):
        courses.collecter_annee(cur, conn, annee)

    # petit contrôle final
    for table in (
        "competition",
        "course",
        "course_methode_ffck",
        "resultat",
        "resultat_methode_ffck",
        "bateau",
        "competiteur",
        "club",
    ):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {cur.fetchone()[0]} lignes")
    conn.close()

    # post-traitement systématique : nettoyage des catégories non autorisées
    print("\n=== Nettoyage des catégories ===")
    nettoyer_categories(db=args.db, dry_run=args.dry_run, verbose=args.verbose)

    # post-traitement systématique : suppression des doublons (course_id, bateau_id)
    print("\n=== Nettoyage des doublons ===")
    nettoyer_doublons(db=args.db, dry_run=args.dry_run, verbose=args.verbose)

    # post-traitements optionnels (chacun ouvre sa propre connexion à la base)
    if args.correction_noms_c2:
        print("\n=== Correction des noms C2 ===")
        corriger_noms_c2(
            db=args.db, csv_dir=args.csv_dir, dry_run=args.dry_run, verbose=args.verbose
        )

    if args.revoir_phases:
        print("\n=== Revue des phases ===")
        revue_phases.revoir_phases(
            db=args.db,
            phases_json=phases.CHEMIN_PHASES_JSON,
            log=phases.CHEMIN_LOG_INCONNUS,
            tout=args.revoir_phases_tout,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

    print("\nTerminé.")


if __name__ == "__main__":
    main()
