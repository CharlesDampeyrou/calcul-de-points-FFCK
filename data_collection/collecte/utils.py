# -*- coding: utf-8 -*-
"""Utilitaires texte : normalisation de noms, dates."""

import unicodedata


def normaliser(texte, separateurs_sup="", tout_non_alnum=True):
    """Minuscules, sans accents, espaces normalisés.

    - tout_non_alnum=True (défaut) : tout caractère non alphanumérique -> espace
      (version historique de la collecte) ;
    - separateurs_sup : caractères remplacés par des espaces en plus, AVANT la
      passe alphanum (ex "- '" pour les noms issus des anciens CSV, où la
      ponctuation restante comme "." est conservée : passer tout_non_alnum=False).
    """
    if not texte:
        return ""
    t = unicodedata.normalize("NFD", str(texte))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.lower()
    for sep in separateurs_sup:
        t = t.replace(sep, " ")
    if tout_non_alnum:
        t = "".join(ch if ch.isalnum() else " " for ch in t)
    return " ".join(t.split())


def date_courte(iso):
    """'2026-11-15T00:00:00.000Z' -> '2026-11-15' ; None sinon.

    Le placeholder '2030-01-01T00:00:00.000Z' renvoyé par l'API pour les vieux
    events sans startDate est traité comme une date absente (None).
    """
    d = (iso or "")[:10] or None
    return None if d == "2030-01-01" else d
