# -*- coding: utf-8 -*-
"""
Phases des courses (qualification / demi-finale / finale).

La phase n'est PAS déduite automatiquement : elle est lue dans le mapping
phases_courses.json (clé = nom de la course normalisé). Quand un nom de course
inconnu apparaît, le script émet un bip et demande la phase interactivement
(elle est alors enregistrée dans le JSON). En mode non-interactif
(config.INTERACTIF = False, option --no-interactif) : les noms inconnus passent
à NULL et sont loggés dans phases_inconnues.log.

Stockage : course.phase_competition (NULL = pas de phase) et
course.phase_ordre (0 = pas de phase, 0.k = "Course n°k", 1/2/3 =
qualification/demi-finale/finale).

État du module (rempli par init_phases, appelé depuis collecte_bdd.py) :
  MAPPING_PHASES, CHEMIN_PHASES_JSON, CHEMIN_LOG_INCONNUS
"""

import json
import os
import re
import time

from . import config
from .utils import normaliser

# état du mapping nom de course -> phase (rempli par init_phases)
MAPPING_PHASES = {}  # clé = nom normalisé -> {"brut": nom, "phase": ...}
CHEMIN_PHASES_JSON = config.PHASES_JSON_DEFAUT
CHEMIN_LOG_INCONNUS = config.LOG_INCONNUS_DEFAUT


def init_phases(chemin_json, chemin_log=None):
    """Initialise l'état du module depuis les chemins passés en CLI."""
    global MAPPING_PHASES, CHEMIN_PHASES_JSON, CHEMIN_LOG_INCONNUS
    CHEMIN_PHASES_JSON = os.path.abspath(chemin_json)
    CHEMIN_LOG_INCONNUS = os.path.abspath(chemin_log or config.LOG_INCONNUS_DEFAUT)
    MAPPING_PHASES = charger_phases(CHEMIN_PHASES_JSON)


def charger_phases(chemin_json):
    """Charge phases_courses.json ou renvoit un dict vide s'il n'existe pas."""
    if not os.path.exists(chemin_json):
        return {}
    with open(chemin_json, encoding="utf-8") as f:
        return json.load(f)


def sauvegarder_phases(chemin_json, mapping):
    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=1, sort_keys=True)


def log_phase_inconnue(nom, contexte):
    with open(CHEMIN_LOG_INCONNUS, "a", encoding="utf-8") as f:
        f.write(f"{nom!r}\t{contexte}\n")


def determiner_phase(nom, contexte=""):
    """
    Phase d'une course d'après son NOM, via le mapping JSON.
    - nom vide -> None (pas de phase), sans interaction
    - nom déjà dans le mapping -> phase enregistrée
    - nom inconnu + mode interactif -> bip + question, réponse enregistrée
      dans le JSON pour les prochaines fois
    - nom inconnu + non-interactif (ou stdin fermé) -> None + log
    """
    if not nom or not str(nom).strip():
        return None
    cle = normaliser(nom)
    if cle in MAPPING_PHASES:
        return MAPPING_PHASES[cle]["phase"]
    if not config.INTERACTIF:
        log_phase_inconnue(nom, contexte)
        print(
            f"  [phase inconnue, ignorée] nom={nom!r} ({contexte}) -> loggé dans {CHEMIN_LOG_INCONNUS}"
        )
        return None
    # mode interactif : attirer l'attention (script potentiellement en arrière-plan)
    for _ in range(3):
        print("\a", end="", flush=True)
        time.sleep(0.3)
    print(f"\n=== NOUVEAU NOM DE COURSE : {nom!r} ===")
    print(f"    contexte : {contexte}")
    while True:
        try:
            rep = input(
                "Phase ? [q]ualification / [d]emi-finale / [f]inale / Entrée = pas de phase "
                "/ 0.k = pas de phase mais ordre 0.k (ex 0.3) : "
            )
        except EOFError:
            # stdin fermé (run en arrière-plan sans terminal) : pas de phase, on loggue
            log_phase_inconnue(nom, contexte + " [EOF]")
            print(f"  [stdin fermé] nom={nom!r} -> pas de phase, loggé.")
            return None
        rep = rep.strip().lower()
        ordre = None
        m0k = re.fullmatch(r"0\.([1-9])", rep)  # saisie "0.k" : k = n° de course/manche
        if m0k:
            phase = None
            ordre = int(m0k.group(1)) / 10.0
        elif rep in ("", "rien", "non", "pas de phase", "none", "null", "0"):
            phase = None
        elif rep in ("q", "qualif", "qualification"):
            phase = "qualification"
        elif rep in ("d", "demi", "demi-finale", "demi finale", "1/2"):
            phase = "demi-finale"
        elif rep in ("f", "finale", "final"):
            phase = "finale"
        else:
            print("  Réponse non reconnue (q/d/f, Entrée, 0 ou 0.k).")
            continue
        break
    entree = {"brut": str(nom), "phase": phase}
    if ordre is not None:
        entree["ordre"] = ordre
    MAPPING_PHASES[cle] = entree
    sauvegarder_phases(CHEMIN_PHASES_JSON, MAPPING_PHASES)
    print(f"  -> enregistré dans {CHEMIN_PHASES_JSON} : {cle!r} = {entree!r}")
    return phase


def calculer_phase_ordre(nom, phase, ordre_explicite=None):
    """0 = pas de phase, 0.k = 'Course n°k', 1/2/3 = qualification/demi-finale/finale.
    Un ordre_explicite (saisi manuellement, ex 0.3) est prioritaire sur le calcul auto.
    """
    if ordre_explicite is not None:
        return float(ordre_explicite)
    if phase:
        return config.PHASES[phase]
    m = re.search(r"course n (\d+)", normaliser(nom))
    if m:
        return int(m.group(1)) / 10.0
    return 0.0
