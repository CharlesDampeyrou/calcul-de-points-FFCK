# -*- coding: utf-8 -*-
"""
Nettoyage des courses sans résultats.

Après les suppressions de résultats (nettoyage des catégories, des doublons),
une course peut se retrouver sans aucun résultat : elle est supprimée ici,
ainsi que ses éventuelles lignes dans course_methode_* (cascade
PRAGMA foreign_keys = ON).

Appelée depuis collecte_bdd.py en post-traitement (toujours exécutée,
respecte --dry-run).
"""

import sqlite3

# condition "aucun résultat" pour une course (corrélée sur course.id)
CONDITION_SANS_RESULTAT = (
    "NOT EXISTS (SELECT 1 FROM resultat r WHERE r.course_id = course.id)"
)


def nettoyer_courses_sans_resultats(db, dry_run=False, verbose=False):
    """Supprime les courses qui n'ont aucun résultat.

    Parameters
    ----------
    db : str
        Chemin de la base SQLite.
    dry_run : bool
        Si True, compte seulement les courses concernées sans rien supprimer.
    verbose : bool
        Si True, liste les courses concernées.

    Returns
    -------
    int
        Nombre de courses supprimées (ou à supprimer en dry-run).
    """
    conn = sqlite3.connect(db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")  # évite "database is locked"
    conn.execute("PRAGMA foreign_keys = ON")  # cascade : course_methode_*
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM course WHERE {CONDITION_SANS_RESULTAT}")
    nb = cur.fetchone()[0]
    print(f"Nettoyage des courses sans résultats : {nb} course(s) concernée(s)")

    if verbose and nb:
        cur.execute(
            f"SELECT id, id_api, nom, date FROM course WHERE {CONDITION_SANS_RESULTAT} "
            f"ORDER BY id"
        )
        for course_id, id_api, nom, date_course in cur.fetchall():
            print(f"  course_id={course_id} id_api={id_api} nom={nom!r} date={date_course}")

    if dry_run:
        print("(dry-run) aucune suppression effectuée.")
    else:
        cur.execute(f"DELETE FROM course WHERE {CONDITION_SANS_RESULTAT}")
        conn.commit()
        print(f"{cur.rowcount} course(s) supprimée(s) (cascade course_methode_*).")
    conn.close()
    return nb


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Suppression des courses sans aucun résultat.")
    ap.add_argument("--db", default="../results.db", help="Chemin de la base SQLite")
    ap.add_argument("--dry-run", action="store_true", help="Compte sans supprimer")
    ap.add_argument("-v", "--verbose", action="store_true", help="Liste les courses supprimées")
    args = ap.parse_args()
    nettoyer_courses_sans_resultats(args.db, dry_run=args.dry_run, verbose=args.verbose)
