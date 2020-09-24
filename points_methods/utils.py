#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 10 16:36:14 2020

@author: charles
"""
import logging

import numpy as np

def calcul_malus(competition):
	malus = np.zeros((competition.noms.shape[0],))
	if competition.phase == "qualif":
		malus += 10
	if competition.niveau == "Régional":
		malus += 40
	elif competition.niveau in ["Nationale 1", "Nationale 2", "Nationale 3"]:
		malus +=5
	elif competition.niveau != "Championnats de France":
		logging.warning("Attention course autre que nationnale ou régionnale : "+competition.niveau)
	malus[np.where(competition.finale_a_b=="Finale B")[0]] += 5
	return malus

def calcul_pen_tps_course(tps_scratch):
	best_times_mean = np.sort(tps_scratch)[:5].mean()
	PEN = max(0, abs(95-best_times_mean))**2 /5
	return PEN