# -*- coding: utf-8 -*-
"""
Nettoyage des bateaux, compétiteurs et équipages (bateau_competiteur) orphelins.

Un bateau n'est « lié à une course » que s'il a au moins un résultat : après
les suppressions de résultats (catégories, doublons, courses vides) ou l'échec
de collecte d'une course, des bateaux, des membres d'équipage
(bateau_competiteur) et des compétiteurs peuvent se retrouver sans aucun
lien vers une course. Ils sont supprimés ici.

Ordre des suppressions : bateau_competiteur d'abord (clés étrangères vers
bateau / compétiteur), puis bateau, puis compétiteur.

Appelée depuis collecte_bdd.py en post-traitement (toujours exécutée,
respecte --dry-run).
"""

import sqlite3

# conditions "lié à aucune course" (aucun résultat), corrélées sur la table cible
CONDITION_BC_SANS_COURSE = (
    "NOT EXISTS (SELECT 1 FROM resultat r WHERE r.bateau_id = bateau_competiteur.bateau_id)"
)
CONDITION_BATEAU_SANS_COURSE = (
    "NOT EXISTS (SELECT 1 FROM resultat r WHERE r.bateau_id = bateau.id)"
)
CONDITION_COMP_SANS_COURSE = (
    "NOT EXISTS ("
    "  SELECT 1 FROM bateau_competiteur bc "
    "  JOIN resultat r ON r.bateau_id = bc.bateau_id "
    "  WHERE bc.competiteur_id = competiteur.id"
    ")"
)


def nettoyer_orphelins(db, dry_run=False, verbose=False):
    """Supprime les bateau_competiteur, bateaux et compétiteurs qui ne sont
    liés à aucune course (aucun résultat).

    Parameters
    ----------
    db : str
        Chemin de la base SQLite.
    dry_run : bool
        Si True, compte seulement les lignes concernées sans rien supprimer.
    verbose : bool
        Si True, liste les lignes concernées.

    Returns
    -------
    tuple (int, int, int)
        (nb bateau_competiteur, nb bateau, nb compétiteur) supprimés
        (ou à supprimer en dry-run).
    """
    conn = sqlite3.connect(db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")  # évite "database is locked"
    conn.execute("PRAGMA foreign_keys = ON")  # integridad des clés étrangères
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM bateau_competiteur WHERE {CONDITION_BC_SANS_COURSE}")
    nb_bc = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM bateau WHERE {CONDITION_BATEAU_SANS_COURSE}")
    nb_b = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM competiteur WHERE {CONDITION_COMP_SANS_COURSE}")
    nb_c = cur.fetchone()[0]
    print(
        f"Nettoyage des orphelins : {nb_bc} bateau_competiteur, "
        f"{nb_b} bateau(x), {nb_c} compétiteur(s) sans course"
    )

    if verbose and (nb_bc or nb_b or nb_c):
        cur.execute(
            f"SELECT bateau_id, competiteur_id FROM bateau_competiteur "
            f"WHERE {CONDITION_BC_SANS_COURSE} ORDER BY bateau_id, competiteur_id"
        )
        for bateau_id, competiteur_id in cur.fetchall():
            print(f"  bateau_competiteur bateau_id={bateau_id} competiteur_id={competiteur_id}")
        cur.execute(
            f"SELECT id, id_api, libelle FROM bateau "
            f"WHERE {CONDITION_BATEAU_SANS_COURSE} ORDER BY id"
        )
        for bateau_id, id_api, libelle in cur.fetchall():
            print(f"  bateau_id={bateau_id} id_api={id_api} libelle={libelle!r}")
        cur.execute(
            f"SELECT id, id_api, nom, prenom FROM competiteur "
            f"WHERE {CONDITION_COMP_SANS_COURSE} ORDER BY id"
        )
        for comp_id, id_api, nom, prenom in cur.fetchall():
            print(f"  competiteur_id={comp_id} id_api={id_api} nom={nom!r} prenom={prenom!r}")

    if dry_run:
        print("(dry-run) aucune suppression effectuée.")
    else:
        # bateau_competiteur d'abord (FK vers bateau / compétiteur), puis bateau, puis compétiteur
        cur.execute(f"DELETE FROM bateau_competiteur WHERE {CONDITION_BC_SANS_COURSE}")
        cur.execute(f"DELETE FROM bateau WHERE {CONDITION_BATEAU_SANS_COURSE}")
        cur.execute(f"DELETE FROM competiteur WHERE {CONDITION_COMP_SANS_COURSE}")
        conn.commit()
        print(
            f"Supprimé(s) : {nb_bc} bateau_competiteur, {nb_b} bateau(x), "
            f"{nb_c} compétiteur(s)."
        )
    conn.close()
    return nb_bc, nb_b, nb_c


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Suppression des bateaux/competiteurs/bateau_competiteur sans course."
    )
    ap.add_argument("--db", default="../results.db", help="Chemin de la base SQLite")
    ap.add_argument("--dry-run", action="store_true", help="Compte sans supprimer")
    ap.add_argument("-v", "--verbose", action="store_true", help="Liste les lignes supprimées")
    args = ap.parse_args()
    nettoyer_orphelins(args.db, dry_run=args.dry_run, verbose=args.verbose)
