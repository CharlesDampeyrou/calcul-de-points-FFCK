# -*- coding: utf-8 -*-
"""
Mise à jour du niveau national des bateaux (bateau.niveau).

Le niveau est lu sur la fiche API de chaque bateau
(GET /ffck/boats/{id_api}, champ slalom.level) — la même source que lors de
la collecte (voir bateaux.py). Utile quand le niveau des athlètes a évolué
depuis la collecte.

Appelée depuis collecte_bdd.py (option --update-niveau, respecte --dry-run).
"""

import sqlite3
import time

from . import api, config


def mettre_a_jour_niveaux(db, dry_run=False, verbose=False):
    """Met à jour bateau.niveau pour tous les bateaux de la base, depuis leur
    fiche API (champ slalom.level).

    Les bateaux dont la fiche est indisponible (404...) ou sans champ
    slalom.level sont laissés inchangés.

    Parameters
    ----------
    db : str
        Chemin de la base SQLite.
    dry_run : bool
        Si True, compte seulement les niveaux à modifier sans rien écrire.
    verbose : bool
        Si True, détaille chaque bateau modifié (id_api, ancien -> nouveau).

    Returns
    -------
    int
        Nombre de bateaux dont le niveau a été modifié (ou à modifier en
        dry-run).
    """
    conn = sqlite3.connect(db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")  # évite "database is locked"
    cur = conn.cursor()

    cur.execute("SELECT id, id_api, niveau FROM bateau ORDER BY id")
    bateaux = cur.fetchall()

    nb_maj = 0
    for bateau_id, id_api, niveau_actuel in bateaux:
        fiche = api.get_json(f"{config.BASE}/ffck/boats/{id_api}")
        time.sleep(config.DELAI_BATEAU)
        if not isinstance(fiche, dict):
            continue  # fiche indisponible : niveau inchangé
        slalom = fiche.get("slalom")
        if not isinstance(slalom, dict):
            continue
        nouveau_niveau = slalom.get("level")
        if nouveau_niveau == niveau_actuel:
            continue
        nb_maj += 1
        if verbose:
            print(f"  bateau {id_api} : niveau {niveau_actuel!r} -> {nouveau_niveau!r}")
        if not dry_run:
            cur.execute(
                "UPDATE bateau SET niveau = ? WHERE id = ?",
                (nouveau_niveau, bateau_id),
            )

    print(
        f"Mise à jour des niveaux : {nb_maj} bateau(x) sur {len(bateaux)} "
        f"{'à mettre à jour' if dry_run else 'mis à jour'}"
    )
    if dry_run:
        print("(dry-run) aucune mise à jour effectuée.")
    else:
        conn.commit()
    conn.close()
    return nb_maj


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Mise à jour de bateau.niveau depuis les fiches API.")
    ap.add_argument("--db", default="../results.db", help="Chemin de la base SQLite")
    ap.add_argument("--dry-run", action="store_true", help="Compte sans mettre à jour")
    ap.add_argument("-v", "--verbose", action="store_true", help="Détaille chaque mise à jour")
    args = ap.parse_args()
    mettre_a_jour_niveaux(args.db, dry_run=args.dry_run, verbose=args.verbose)
