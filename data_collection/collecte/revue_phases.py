# -*- coding: utf-8 -*-
"""
Revoir les phases des courses après un run --no-interactif (ou après édition
manuelle de phases_courses.json).

Fonctionnement :
  1. lit phases_inconnues.log (lignes "nom\\tcontexte") et propose interactivement
     (bip + saisie) la phase de chaque nom qui n'est pas encore dans
     phases_courses.json ; la réponse est enregistrée dans le JSON ;
  2. avec tout=True, propose aussi tous les noms de courses distincts présents
     en base (pour corriger un nom déjà dans le JSON) ;
  3. répercute le mapping dans la base :
         UPDATE course SET phase_competition=?, phase_ordre=?
     pour toutes les courses dont le nom (normalisé) est dans le JSON ;
  4. archive phases_inconnues.log en phases_inconnues.log.old.

Appelée depuis collecte_bdd.py via --revoir-phases.

Saisie : Entrée = garder la valeur actuelle, q = qualification,
d = demi-finale, f = finale, 0 = pas de phase (ordre auto),
0.k = pas de phase mais ordre explicite 0.k (k = n° de course/manche, ex 0.3).
"""

import os
import re
import sqlite3
import time

from . import phases
from .utils import normaliser


def charger_log(chemin):
    """Renvoie [(nom, [contextes])] depuis phases_inconnues.log, dédoublonné."""
    noms = {}
    if not os.path.exists(chemin):
        return noms
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.rstrip("\n")
            if not ligne:
                continue
            parties = ligne.split("\t")
            nom = parties[0].strip("'\"")
            contexte = parties[1] if len(parties) > 1 else ""
            noms.setdefault(nom, [])
            if contexte and contexte not in noms[nom]:
                noms[nom].append(contexte)
    return noms


def contextes_base(cur, nom):
    """Quelques contextes (compétition, lieu, date, id course) pour un nom brut."""
    cur.execute("""
        SELECT c.id_api, co.nom, co.lieu, c.date FROM course c
        JOIN competition co ON co.id = c.competition_id
        WHERE c.nom = ? ORDER BY c.date LIMIT 3
    """, (nom,))
    return [f"course {r[0]}, {r[1]} - {r[2]}, {r[3]}" for r in cur.fetchall()]


def demander_phase(nom, phase_actuelle, contextes, mapping, chemin_json):
    """Interaction : bip + question. Entrée conserve la valeur actuelle.
    On peut saisir directement 0.k (k = n° de course/manche) : pas de phase,
    mais phase_ordre explicite = 0.k."""
    for _ in range(3):
        print("\a", end="", flush=True)
        time.sleep(0.2)
    print(f"\n=== NOM DE COURSE : {nom!r} ===")
    for ctx in contextes[:3]:
        print(f"    {ctx}")
    entree_actuelle = mapping.get(normaliser(nom), {})
    print(f"    phase actuelle dans le JSON : {phase_actuelle!r}"
          + (f", ordre actuel : {entree_actuelle.get('ordre')!r}" if "ordre" in entree_actuelle else ""))
    while True:
        try:
            rep = input("Phase ? [Entrée]=garder / [q]ualification / [d]emi-finale / [f]inale / "
                        "[0]=pas de phase / [0.k]=pas de phase, ordre 0.k (ex 0.3) : ")
        except EOFError:
            print("  [stdin fermé] valeur actuelle conservée.")
            return phase_actuelle
        rep = rep.strip().lower()
        if rep in ("", "garder", "oui", "ok"):
            return phase_actuelle
        ordre = None
        m0k = re.fullmatch(r"0\.([1-9])", rep)  # saisie "0.k" : k = n° de course/manche
        if m0k:
            phase = None
            ordre = int(m0k.group(1)) / 10.0
        elif rep in ("0", "rien", "non", "null", "none"):
            phase = None
        elif rep in ("q", "qualif", "qualification"):
            phase = "qualification"
        elif rep in ("d", "demi", "demi-finale", "demi finale", "1/2"):
            phase = "demi-finale"
        elif rep in ("f", "finale", "final"):
            phase = "finale"
        else:
            print("  Réponse non reconnue (Entrée/q/d/f/0/0.k).")
            continue
        break
    cle = normaliser(nom)
    entree = {"brut": str(nom), "phase": phase}
    if ordre is not None:
        entree["ordre"] = ordre
    mapping[cle] = entree
    phases.sauvegarder_phases(chemin_json, mapping)
    print(f"  -> enregistré : {cle!r} = {entree!r}")
    return phase


def appliquer_mapping_a_la_base(conn, cur, mapping, verbose=False):
    """UPDATE course pour tous les noms (normalisés) présents dans le mapping."""
    cur.execute("SELECT id, nom FROM course WHERE nom IS NOT NULL AND nom != ''")
    n = 0
    for cid, nom in cur.fetchall():
        cle = normaliser(nom)
        if cle not in mapping:
            continue
        phase = mapping[cle]["phase"]
        ordre = phases.calculer_phase_ordre(nom, phase, mapping[cle].get("ordre"))
        cur.execute("UPDATE course SET phase_competition = ?, phase_ordre = ? WHERE id = ?",
                    (phase, ordre, cid))
        n += 1
        if verbose:
            print(f"  course {cid} ({nom!r}) -> phase={phase!r}, ordre={ordre}")
    conn.commit()
    return n


def revoir_phases(db, phases_json, log, tout=False, dry_run=False, verbose=False):
    """Rejoue interactivement les phases des noms de courses inconnus (log)
    et répercute le mapping dans la base.

    db         : chemin de la base SQLite (si elle existe ; sinon JSON seul)
    phases_json: chemin de phases_courses.json
    log        : chemin de phases_inconnues.log (archivé en .old à la fin)
    tout       : propose aussi tous les noms de courses distincts de la base
    dry_run    : ne met pas à jour la base ni le log (le JSON est quand même sauvegardé)
    verbose    : affiche chaque course mise à jour
    """
    chemin_json = os.path.abspath(phases_json)
    mapping = phases.charger_phases(chemin_json)
    print(f"Mapping : {len(mapping)} noms dans {chemin_json}")

    # noms à proposer : ceux du log absents du mapping (+ tous ceux de la base si tout)
    log_noms = charger_log(log)
    a_proposer = {nom: ctxs for nom, ctxs in log_noms.items() if normaliser(nom) not in mapping}

    base_existe = os.path.exists(db)
    conn = cur = None
    if base_existe:
        conn = sqlite3.connect(db, timeout=60)
        conn.execute("PRAGMA busy_timeout = 60000")
        cur = conn.cursor()
        if tout:
            cur.execute("SELECT DISTINCT nom FROM course WHERE nom IS NOT NULL AND nom != ''")
            for (nom,) in cur.fetchall():
                if nom not in a_proposer:
                    a_proposer[nom] = contextes_base(cur, nom)
    else:
        print(f"Base {db} absente : on ne met à jour que le JSON.")

    if not a_proposer:
        print("Aucun nom à revoir.")
    else:
        print(f"{len(a_proposer)} nom(s) à revoir.")
        for nom, ctxs in a_proposer.items():
            if base_existe and not ctxs:
                ctxs = contextes_base(cur, nom)
            phase_actuelle = mapping.get(normaliser(nom), {}).get("phase")
            demander_phase(nom, phase_actuelle, ctxs, mapping, chemin_json)

    # répercuter le mapping dans la base
    if base_existe and not dry_run:
        n = appliquer_mapping_a_la_base(conn, cur, mapping, verbose=verbose)
        print(f"Base mise à jour : {n} course(s) réconciliées.")
    elif base_existe:
        print("Dry-run : base non modifiée.")

    # archiver le log
    if os.path.exists(log) and not dry_run:
        os.replace(log, log + ".old")
        print(f"Log archivé : {log} -> {log}.old")

    if conn:
        conn.close()
    print("Terminé.")
