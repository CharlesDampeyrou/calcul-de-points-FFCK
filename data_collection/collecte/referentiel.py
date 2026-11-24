# -*- coding: utf-8 -*-
"""Tables référentielles : type_bateau, club, competiteur."""

from .utils import normaliser


def get_or_create(cur, table, colonne, valeur, extra=None):
    """Renvoie l'identifiant interne de la ligne référentielle (valeur unique)."""
    cur.execute(f"SELECT id FROM {table} WHERE {colonne} = ?", (valeur,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table} ({colonne}, nom) VALUES (?, ?)", (valeur, extra))
    return cur.lastrowid


def ref_type(cur, code):
    cur.execute("SELECT id FROM type_bateau WHERE code = ?", (code,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT OR IGNORE INTO type_bateau (code) VALUES (?)", (code,))
        cur.execute("SELECT id FROM type_bateau WHERE code = ?", (code,))
        row = cur.fetchone()
    return row[0]


def _candidat_club_par_nom(cur, nom):
    """Id du club de même nom (comparaison exacte, puis normalisée), le plus
    ancien (id min) s'il y en a plusieurs ; None si aucun.

    Les clubs ont beaucoup moins d'homonymes que les compétiteurs ; ce
    matching sert surtout à regrouper les variantes de codes (zéros de tête,
    anciens/nouveaux codes) renvoyées par l'API pour un même club."""
    cur.execute("SELECT id FROM club WHERE nom = ? ORDER BY id LIMIT 1", (nom,))
    row = cur.fetchone()
    if row:
        return row[0]
    cible = normaliser(nom)
    cur.execute("SELECT id, nom FROM club WHERE nom IS NOT NULL AND nom != '' ORDER BY id")
    for rid, rnom in cur.fetchall():
        if normaliser(rnom) == cible:
            return rid
    return None


def ref_club(cur, club):
    """club : {'clubId': ..., 'clubName': ...} -> id interne.

    Matching par id_api (code club). Pour une NOUVELLE entrée (id_api
    inconnu), matching par nom avant création, pour ne pas recréer un club
    déjà connu sous une variante de code (zéros de tête, ancien/nouveau code).
    """
    club_id_api = club.get("clubId") or "?"
    nom = (club.get("clubName") or "").strip() or None
    cur.execute("SELECT id FROM club WHERE id_api = ?", (club_id_api,))
    row = cur.fetchone()
    if row:
        # complète un nom resté vide lors d'une rencontre précédente
        if nom:
            cur.execute(
                "UPDATE club SET nom = ? WHERE id = ? AND (nom IS NULL OR nom = '')",
                (nom, row[0]),
            )
        return row[0]
    # nouvelle entrée : matching par nom (uniquement ici, jamais sur les
    # entrées existantes matchées par id_api)
    if nom:
        candidat = _candidat_club_par_nom(cur, nom)
        if candidat is not None:
            # si le club matché n'avait pas de vrai code ("?"/NULL), on le renseigne
            if club_id_api != "?":
                cur.execute(
                    "UPDATE club SET id_api = ? WHERE id = ? AND (id_api IS NULL OR id_api = '?')",
                    (club_id_api, candidat),
                )
            return candidat
    cur.execute(
        "INSERT INTO club (id_api, nom) VALUES (?, ?)",
        (club_id_api, nom),
    )
    return cur.lastrowid


def _candidats_par_nom(cur, nom, prenom, normalise=False):
    """Ids des compétiteurs dont (nom, prenom) correspond.

    normalise=False : comparaison exacte. normalise=True : comparaison
    normalisée (casse, accents, ponctuation), via un scan complet en Python
    (la création étant rare, le coût reste faible).
    """
    if not nom:
        return []
    if not normalise:
        cur.execute(
            "SELECT id FROM competiteur WHERE nom = ? AND prenom IS ?", (nom, prenom)
        )
        return [r[0] for r in cur.fetchall()]
    cible_nom = normaliser(nom)
    cible_prenom = normaliser(prenom or "")
    return [
        rid
        for rid, rnom, rprenom in cur.execute("SELECT id, nom, prenom FROM competiteur")
        if normaliser(rnom or "") == cible_nom
        and normaliser(rprenom or "") == cible_prenom
    ]


def ref_competiteur(cur, id_api, nom, prenom):
    """Renvoie l'id interne du compétiteur, en le créant si besoin.

    Anti-doublons, sans jamais fusionner deux homonymes :
    - id_api renseigné (people[].id de la fiche, ou boatId en repli) : match
      par id_api uniquement. Jamais de rattachement par nom : si une ligne
      sans id_api porte le même nom, c'est peut-être un homonyme, on préfère
      créer un doublon plutôt que de coller le mauvais id_api dessus.
    - id_api inconnu (ex CSV de la correction C2) : on ne réutilise un nom
      existant que s'il y a UN SEUL candidat (d'abord exact, puis normalisé) ;
      0 candidat -> création ; plusieurs candidats -> création aussi (on ne
      choisit pas entre homonymes : doublon préférable à une mauvaise fusion).
    """
    if id_api is not None:
        cur.execute("SELECT id FROM competiteur WHERE id_api = ?", (id_api,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT OR IGNORE INTO competiteur (id_api, nom, prenom) VALUES (?, ?, ?)",
            (id_api, nom, prenom),
        )
        cur.execute("SELECT id FROM competiteur WHERE id_api = ?", (id_api,))
        return cur.fetchone()[0]
    if nom:
        candidats = _candidats_par_nom(cur, nom, prenom)
        if len(candidats) == 1:
            return candidats[0]
        if not candidats:
            candidats = _candidats_par_nom(cur, nom, prenom, normalise=True)
            if len(candidats) == 1:
                return candidats[0]
        # 0 ou plusieurs candidats : on crée (pas de choix entre homonymes)
    cur.execute(
        "INSERT INTO competiteur (id_api, nom, prenom) VALUES (NULL, ?, ?)",
        (nom, prenom),
    )
    return cur.lastrowid
