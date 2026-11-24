# -*- coding: utf-8 -*-
"""Fiches bateaux : chaque fiche de l'API est interrogée une seule fois
(mémoire de session + table bateau), car le même bateau court plusieurs courses."""

import time

from . import api, config, referentiel


def enregistrer_bateau(cur, conn, boat_id_api, label, type_code):
    """Crée le bateau s'il est inconnu, et charge sa fiche une seule fois."""
    cur.execute("SELECT id FROM bateau WHERE id_api = ?", (boat_id_api,))
    row = cur.fetchone()
    if row:
        return row[0]

    fiche = api.get_json(f"{config.BASE}/ffck/boats/{boat_id_api}")
    time.sleep(config.DELAI_BATEAU)
    if not isinstance(fiche, dict):
        fiche = None

    annee, niveau, surclassement = None, None, None
    if type_code:
        referentiel.ref_type(cur, type_code)
    cur.execute(
        "INSERT OR IGNORE INTO bateau (id_api, libelle, type_code) VALUES (?, ?, ?)",
        (boat_id_api, label, type_code),
    )
    cur.execute("SELECT id FROM bateau WHERE id_api = ?", (boat_id_api,))
    bateau_id = cur.fetchone()[0]

    # Équipage : chaque personne avec son club (un C2 peut avoir deux clubs).
    # Repli : les très vieilles fiches (ids "_C1H...") et les bateaux sans fiche
    # (ex INV, 404) n'ont pas de "people" ; on retombe alors sur le libellé du
    # bateau ("Prénom Nom\\nPrénom Nom").
    membres = fiche.get("people") if fiche else None
    if not isinstance(membres, list):
        membres = []
    membres = [p for p in membres if isinstance(p, dict)]
    if not membres and label:
        # Repli : la fiche n'a pas de "people" (vieux ids legacy "_C1H..." avec
        # people vide). Le boatId est unique par bateau et quasiment jamais
        # absent dans les résultats : on l'utilise comme id du membre, avec un
        # suffixe #position pour un biplace (competiteur.id_api est UNIQUE),
        # pour ne pas créer un doublon de compétiteur à chaque occurrence.
        parts = [p.strip() for p in str(label).split("\n") if p.strip()]
        for pos, part in enumerate(parts, start=1):
            morceaux = part.split(" ", 1)
            membres.append(
                {
                    "id": boat_id_api if len(parts) == 1 else f"{boat_id_api}#{pos}",
                    "firstname": morceaux[0] if len(morceaux) > 1 else None,
                    "lastname": morceaux[1] if len(morceaux) > 1 else morceaux[0],
                    "clubId": None,
                }
            )

    if fiche:
        slalom = fiche.get("slalom")
        if not isinstance(slalom, dict):
            slalom = {}
        try:
            annee = int(slalom.get("year"))  # type: ignore
        except (TypeError, ValueError):
            annee = None
        niveau = slalom.get("level")
        surclassement = fiche.get("surclassement")
        cur.execute(
            "UPDATE bateau SET annee_naissance = ?, niveau = ?, surclassement = ? "
            "WHERE id = ?",
            (annee, niveau, surclassement, bateau_id),
        )

    for pos, pers in enumerate(membres, start=1):
        nom = (pers.get("lastname") or "").strip() or None
        prenom = (pers.get("firstname") or "").strip() or None
        if not nom and not prenom:
            continue
        # ref_competiteur évite les doublons quand l'API ne fournit pas d'id :
        # match par (nom, prenom) exact puis normalisé avant création.
        competiteur_id = referentiel.ref_competiteur(cur, pers.get("id"), nom, prenom)
        # Club du membre pour ce bateau : un C2 peut réunir deux membres de
        # clubs différents (équipages mixtes) -> club_id sur la ligne
        # bateau_competiteur, pas de table bateau_club.
        club_id = None
        if pers.get("clubId"):
            club_id = referentiel.ref_club(
                cur,
                {"clubId": pers.get("clubId"), "clubName": pers.get("clubName")},
            )
        cur.execute(
            "INSERT OR IGNORE INTO bateau_competiteur "
            "(bateau_id, competiteur_id, position, club_id) VALUES (?, ?, ?, ?)",
            (bateau_id, competiteur_id, pos, club_id),
        )
    # PAS de commit ici : la transaction est validée par enregistrer_course
    # (sinon une erreur en cours de course laisserait la course en base
    # sans ses résultats).
    return bateau_id
