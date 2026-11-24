# -*- coding: utf-8 -*-
"""
Nettoyage des catégories de bateaux non souhaitées.

Supprime de la table resultat tous les résultats dont le type de bateau
(resultat.type_code) n'est pas dans CATEGORIES_AUTORISEES, ainsi que les
résultats sans type_code (NULL). La suppression est en cascade (manches,
pénalités et resultats_methode_*) grâce à PRAGMA foreign_keys = ON.

Appelée depuis collecte_bdd.py en post-traitement (toujours exécutée,
respecte --dry-run).
"""

import sqlite3

CATEGORIES_AUTORISEES = ("K1H", "K1D", "C1H", "C1D", "C2H", "C2D", "C2M")


def nettoyer_categories(db, categories=CATEGORIES_AUTORISEES, dry_run=False, verbose=False):
    """Supprime les résultats dont resultat.type_code n'est pas dans `categories`.

    Parameters
    ----------
    db : str
        Chemin de la base SQLite.
    categories : tuple de str
        Types de bateau autorisés (défaut CATEGORIES_AUTORISEES). Les
        résultats avec type_code NULL sont aussi supprimés.
    dry_run : bool
        Si True, compte seulement les résultats concernés sans rien supprimer.
    verbose : bool
        Si True, détaille le nombre de résultats supprimés par type_code.

    Returns
    -------
    int
        Nombre de résultats concernés (supprimés, ou à supprimer en dry-run).
    """
    conn = sqlite3.connect(db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")  # évite "database is locked"
    conn.execute("PRAGMA foreign_keys = ON")  # cascade : manche, penalite, resultat_methode_*
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in categories)
    condition = f"type_code IS NULL OR type_code NOT IN ({placeholders})"

    cur.execute(
        f"SELECT COUNT(*) FROM resultat WHERE {condition}", tuple(categories)
    )
    nb = cur.fetchone()[0]
    print(f"Nettoyage des catégories : {nb} résultat(s) hors {list(categories)}")
    if verbose:
        cur.execute(
            f"SELECT type_code, COUNT(*) FROM resultat WHERE {condition} "
            f"GROUP BY type_code ORDER BY 2 DESC",
            tuple(categories),
        )
        for type_code, n in cur.fetchall():
            print(f"  {type_code!r}: {n}")

    if dry_run:
        print("(dry-run) aucune suppression effectuée.")
    else:
        cur.execute(f"DELETE FROM resultat WHERE {condition}", tuple(categories))
        conn.commit()
        print(
            f"{cur.rowcount} résultat(s) supprimé(s) "
            f"(cascade manches / pénalités / résultats_methode_*)."
        )
    conn.close()
    return nb


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Nettoyage des catégories de bateaux non autorisées.")
    ap.add_argument("--db", default="../results.db", help="Chemin de la base SQLite")
    ap.add_argument("--dry-run", action="store_true", help="Compte sans supprimer")
    ap.add_argument("-v", "--verbose", action="store_true", help="Détail par type_code")
    args = ap.parse_args()
    nettoyer_categories(args.db, dry_run=args.dry_run, verbose=args.verbose)
