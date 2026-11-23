# -*- coding: utf-8 -*-
"""
Courses par équipe (NON sauvegardées en base).

team_events.json = {"team": [...], "non_team": [...]} (noms de l'ancien
scrapper ; matching strict par nom normalisé sur race.name / ev.name).
Une course est considérée "par équipe" si son nom (ou celui de son event)
contient "equipe"/"patrouille" (normalisé = équivalent de unidecode+lower).
- nom connu dans le JSON -> décision appliquée directement ;
- candidat inconnu -> bip + question interactive, réponse enregistrée
  dans le JSON ; en non-interactif (config.INTERACTIF = False) : la course
  est sautée et loggée dans team_events_inconnus.log.

État du module (rempli par init_team_events, appelé depuis collecte_bdd.py) :
  TEAM_EVENTS, CHEMIN_TEAM_JSON, CHEMIN_LOG_TEAM
"""

import json
import os

from . import config
from .utils import date_courte, normaliser

TEAM_EVENTS = {"team": [], "non_team": []}  # noms bruts (rempli par init_team_events)
CHEMIN_TEAM_JSON = config.TEAM_JSON_DEFAUT
CHEMIN_LOG_TEAM = config.LOG_TEAM_INCONNUS_DEFAUT


def init_team_events(chemin_json, chemin_log=None):
    """Initialise l'état du module depuis les chemins passés en CLI."""
    global TEAM_EVENTS, CHEMIN_TEAM_JSON, CHEMIN_LOG_TEAM
    CHEMIN_TEAM_JSON = os.path.abspath(chemin_json)
    CHEMIN_LOG_TEAM = os.path.abspath(chemin_log or config.LOG_TEAM_INCONNUS_DEFAUT)
    TEAM_EVENTS = charger_team_events(CHEMIN_TEAM_JSON)


def charger_team_events(chemin_json):
    """Charge team_events.json ; le crée vide s'il n'existe pas."""
    if not os.path.exists(chemin_json):
        sauvegarder_team_events(chemin_json, {"team": [], "non_team": []})
    with open(chemin_json, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("team", [])
    data.setdefault("non_team", [])
    return data


def sauvegarder_team_events(chemin_json, data):
    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)


def possible_team_event(nom):
    """Candidat 'course par équipe' : 'equipe' ou 'patrouille' dans le nom
    (normalisé = équivalent de unidecode(nom).lower())."""
    n = normaliser(nom)
    return "equipe" in n or "patrouille" in n


def _dans_liste(nom, liste_bruts):
    """Matching STRICT"""
    n = normaliser(nom)
    if not n:
        return False
    for t in liste_bruts:
        tn = normaliser(t)
        if not tn:
            continue
        if n == tn:
            return True
    return False


def est_course_equipe(race, ev):
    """
    True si la course est une course par équipe (à ne PAS sauvegarder).
    - nom connu dans team_events.json (team / non_team) -> décision connue
    - sinon, candidat 'equipe'/'patrouille' (dans race.name ou ev.name) :
      mode interactif -> bip + question, réponse enregistrée dans le JSON ;
      non-interactif -> on saute la course + log dans team_events_inconnus.log
    """
    nom_course = str(race.get("name") or "")
    nom_event = str(ev.get("name") or "")
    combine = f"{nom_event} | {nom_course}".strip(
        " |"
    )  # forme des entrées enregistrées par le script
    # non_team prioritaire (faux positifs connus), puis team
    for texte in (combine, nom_course):
        if _dans_liste(texte, TEAM_EVENTS["non_team"]):
            return False
    for texte in (combine, nom_course):
        if _dans_liste(texte, TEAM_EVENTS["team"]):
            return True
    if not (possible_team_event(nom_course) or possible_team_event(nom_event)):
        return False
    # candidat inconnu
    contexte = (
        f"course {race.get('id')} ({nom_course!r}), event {ev.get('id')} "
        f"{nom_event!r} - {ev.get('place')}, {date_courte(ev.get('startDate') or ev.get('date'))}"
    )
    if not config.INTERACTIF:
        with open(CHEMIN_LOG_TEAM, "a", encoding="utf-8") as f:
            f.write(f"{contexte}\n")
        print(
            f"  [team? inconnu, course sautée] {contexte} -> loggé dans {CHEMIN_LOG_TEAM}"
        )
        return True
    for _ in range(3):
        print("\a", end="", flush=True)
    print(f"\n=== POTENTIELLE COURSE PAR ÉQUIPE ===")
    print(f"    {contexte}")
    while True:
        try:
            rep = input("Course par équipe à ne PAS sauvegarder ? [o/n] : ")
        except EOFError:
            with open(CHEMIN_LOG_TEAM, "a", encoding="utf-8") as f:
                f.write(f"{contexte} [EOF]\n")
            print("  [stdin fermé] course sautée, loggée.")
            return True
        rep = rep.strip().lower()
        if rep in ("o", "oui", "y", "yes", "team"):
            equipe = True
            break
        if rep in ("n", "non", "no"):
            equipe = False
            break
        print("  Réponse non reconnue (o/n).")
    brut = f"{nom_event} | {nom_course}".strip(" |")
    TEAM_EVENTS["team" if equipe else "non_team"].append(brut)
    sauvegarder_team_events(CHEMIN_TEAM_JSON, TEAM_EVENTS)
    print(
        f"  -> enregistré dans {CHEMIN_TEAM_JSON} ({'team' if equipe else 'non_team'}): {brut!r}"
    )
    return equipe
