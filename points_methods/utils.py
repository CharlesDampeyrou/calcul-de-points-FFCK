# -*- coding: utf-8 -*-
"""
Created on Wed Feb 17 11:21:59 2021

@author: charl
"""

import numpy as np


def calcul_malus_phase_and_div(participations):
    """Calcul des malus de phase et de division. Ne prend pas en compte les finales N1/N2/N3 comme il faut, ni les qulifications 2eme manche"""
    p = participations[list(participations.keys())[0]]
    malus = 0
    phase = p["phase"]
    if phase == "qualif":
        malus += 10
    level = p["level"]
    if level == 1:
        malus += 40
    elif level in [2, 3, 4]:
        malus += 5
    return malus


def add_A_B_penality(participations):
    for boat_id in participations:
        if participations[boat_id]["finale_ab"] == "B":
            participations[boat_id]["points"] += 5


def calcul_pen_tps_course(participations):
    tps_scratch = sorted(
        [participations[b_id]["tpsScratch"] for b_id in participations]
    )
    best_times_mean = np.mean(tps_scratch[:5])
    pen = max(0, abs(95 - best_times_mean) - 10) ** 2 / 5
    return pen


def add_penalties(participations, pen_manque_competiteurs):
    for boat_id in participations:
        participations[boat_id]["points"] += pen_manque_competiteurs


def correct_negative_points(participations):
    min_points = min(participations, key=lambda x: x["points"])["points"]
    if min_points < 0:
        for participation in participations:
            participation["points"] -= min_points


def calcul_points(participations, tps_base):
    for bateau_id in participations:
        competitor_points = (
            1000 * (participations[bateau_id]["tpsScratch"] - tps_base) / tps_base
        )
        participations[bateau_id]["points"] = competitor_points


def calcul_tps_scratch(participations, coef_inter_cat):
    for bateau_id in participations:
        coef = coef_inter_cat[participations[bateau_id]["cat"]]
        participations[bateau_id]["tpsScratch"] = (
            participations[bateau_id]["score"] / coef
        )


def extract_points(participations):
    points = list()
    for participation in participations:
        points.append(
            {
                "competitorName": participation["competitorName"],
                "competitorCategory": participation["competitorCategory"],
                "points": participation["points"],
            }
        )
    return points
