# -*- coding: utf-8 -*-
"""
Created on Wed Feb 17 11:21:59 2021

@author: charl
"""
import numpy as np

def calcul_malus_phase_and_div(participations):
    malus = 0
    phase = participations[0]["simplifiedCompetitionPhase"]
    if phase == "qualif":
        malus += 10
    level = participations[0]["level"]
    if level == "Régional":
        malus += 40
    elif level in ["Nationale 1", "Nationale 2", "Nationale 3"]:
        malus += 5
    elif level != "Championnats de France":
        msg = "niveau de competition %s non reconnu, competition %s"
        raise Exception(msg % (level, participations[0]["competitionName"]))
    return malus

def add_A_B_penality(participations):
    for participation in participations:
        if participation["finalType"] == "finale b":
            participation["points"] += 5

def calcul_pen_tps_course(participations):
    participations.sort(key=(lambda x:x["tpsScratch"]))
    tps_scratch = list()
    for i in range(5):
        tps_scratch.append(participations[i]["tpsScratch"])
    best_times_mean = np.mean(tps_scratch)
    PEN = max(0, abs(95-best_times_mean)-10)**2 /5
    return PEN

def add_penalties(participations, pen_manque_competiteurs):
    for participation in participations:
        participation["points"] += pen_manque_competiteurs

def correct_negative_points(participations):
    min_points = min(participations, key=lambda x:x["points"])["points"]
    if min_points<0:
        for participation in participations:
            participation["points"] -= min_points