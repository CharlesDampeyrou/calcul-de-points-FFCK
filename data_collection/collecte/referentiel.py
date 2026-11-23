# -*- coding: utf-8 -*-
"""Tables référentielles : type_bateau, club."""


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


def ref_club(cur, club):
    """club : {'clubId': ..., 'clubName': ...} -> id interne."""
    club_id_api = club.get("clubId") or "?"
    cur.execute("SELECT id FROM club WHERE id_api = ?", (club_id_api,))
    row = cur.fetchone()
    if row:
        nom = club.get("clubName")
        # complète un nom resté vide lors d'une rencontre précédente
        if nom:
            cur.execute(
                "UPDATE club SET nom = ? WHERE id = ? AND (nom IS NULL OR nom = '')",
                (nom, row[0]),
            )
        return row[0]
    cur.execute(
        "INSERT INTO club (id_api, nom) VALUES (?, ?)",
        (club_id_api, club.get("clubName")),
    )
    return cur.lastrowid
