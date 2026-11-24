# -*- coding: utf-8 -*-
"""
Nettoyage des doublons de résultats.

Un couple (course_id, bateau_id) ne devrait apparaître qu'une fois dans la
table resultat (les phases A/B de certaines époques peuvent créer des
doublons). Quand il y a plusieurs résultats pour un même couple, on garde
le MEILLEUR score_scratch (le plus petit) et on supprime les autres.

Gestion des scores manquants (score_scratch NULL) :
  - un résultat sans score ne bat jamais un résultat avec score ;
  - si tous les résultats du couple sont sans score, on garde le plus
    ancien (id le plus petit).

La suppression est en cascade (manches, pénalités, resultats_methode_*)
grâce à PRAGMA foreign_keys = ON.

Appelée depuis collecte_bdd.py en post-traitement (toujours exécutée,
respecte --dry-run).
"""

import sqlite3

# id des résultats à supprimer : tous sauf le rang 1 de chaque couple
# (rang 1 = meilleur score_scratch ; les NULL passent après ; départage par id)
REQUETE_ID_A_SUPPRIMER = """
SELECT id FROM (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY course_id, bateau_id
               ORDER BY (score_scratch IS NULL) ASC, score_scratch ASC, id ASC
           ) AS rang
    FROM resultat
) WHERE rang > 1
"""


def nettoyer_doublons(db, dry_run=False, verbose=False):
    """Supprime les résultats en double sur (course_id, bateau_id), en gardant
    à chaque fois le meilleur score_scratch.

    Parameters
    ----------
    db : str
        Chemin de la base SQLite.
    dry_run : bool
        Si True, compte seulement les résultats à supprimer sans rien faire.
    verbose : bool
        Si True, liste les couples en doublon avec leurs scores.

    Returns
    -------
    int
        Nombre de résultats supprimés (ou à supprimer en dry-run).
    """
    conn = sqlite3.connect(db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")  # évite "database is locked"
    conn.execute("PRAGMA foreign_keys = ON")  # cascade : manche, penalite, resultat_methode_*
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM ({REQUETE_ID_A_SUPPRIMER})")
    nb = cur.fetchone()[0]
    print(f"Nettoyage des doublons : {nb} résultat(s) en trop sur (course_id, bateau_id)")

    if verbose and nb:
        cur.execute(
            "SELECT course_id, bateau_id, COUNT(*) AS nb, "
            "GROUP_CONCAT(score_scratch) AS scores "
            "FROM resultat GROUP BY course_id, bateau_id HAVING nb > 1 "
            "ORDER BY nb DESC, course_id, bateau_id"
        )
        for course_id, bateau_id, n, scores in cur.fetchall():
            print(f"  course_id={course_id} bateau_id={bateau_id}: {n} résultats, scores={scores}")

    if dry_run:
        print("(dry-run) aucune suppression effectuée.")
    else:
        cur.execute(f"DELETE FROM resultat WHERE id IN ({REQUETE_ID_A_SUPPRIMER})")
        conn.commit()
        print(
            f"{cur.rowcount} résultat(s) supprimé(s) "
            f"(cascade manches / pénalités / résultats_methode_*)."
        )
    conn.close()
    return nb


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Suppression des résultats en double (course_id, bateau_id).")
    ap.add_argument("--db", default="../results.db", help="Chemin de la base SQLite")
    ap.add_argument("--dry-run", action="store_true", help="Compte sans supprimer")
    ap.add_argument("-v", "--verbose", action="store_true", help="Liste les couples en doublon")
    args = ap.parse_args()
    nettoyer_doublons(args.db, dry_run=args.dry_run, verbose=args.verbose)
