# -*- coding: utf-8 -*-
"""Constantes et chemins par défaut de la collecte (dossier data_collection/)."""

import os

# data_collection/ (config.py est dans data_collection/collecte/)
DOSSIER_DATA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = "https://slalom.ffck.org/api"
DELAI = 0.1  # pause entre deux requêtes (events/races)
DELAI_BATEAU = 0.1  # pause entre deux fiches de bateau

SCHEMA_DEFAUT = os.path.join(DOSSIER_DATA, "schema_slalom.sql")
PHASES_JSON_DEFAUT = os.path.join(DOSSIER_DATA, "phases_courses.json")
LOG_INCONNUS_DEFAUT = os.path.join(DOSSIER_DATA, "phases_inconnues.log")
TEAM_JSON_DEFAUT = os.path.join(DOSSIER_DATA, "team_events.json")
LOG_TEAM_INCONNUS_DEFAUT = os.path.join(DOSSIER_DATA, "team_events_inconnus.log")
CSV_DIR_DEFAUT = os.path.join(DOSSIER_DATA, "old_csv_database")

PHASES = {"qualification": 1.0, "demi-finale": 2.0, "finale": 3.0}

INTERACTIF = True  # False avec --no-interactif (lu à l'exécution par phases/team_events)
