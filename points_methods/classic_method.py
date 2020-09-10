#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 30 17:37:24 2020

@author: charles
"""
import logging

import numpy as np

from points_methods.utils import calcul_malus, calcul_pen_tps_course
from points_methods.exceptions import NoCompetitorException, NotEnoughCompetitorException

class PointsComputer:
	def __init__(self):
		self.coef_inter_cat = {"K1H":1, "C1H":1.05, "C1D":1.2, "K1D":1.13, "C2H":1.1, "C2D":1.3, "C2M":1.2}
		
	
	def compute_points(self, competition, ranking):
		logging.info("Calcul des points de la course : " + competition.nom_course)
		# Levée d'une Exception s'il n'y a aucun compétiteur
		if len(competition.noms) == 0:
			raise NoCompetitorException()
		######## Calcul du temps scratch
		tps_scratch = self.calcul_tps_scratch(competition)
		
		
		######## Calcul du temps de base
		tps_base, pen_manque_competiteurs = self.calcul_tps_base(competition, tps_scratch)
		
		
		####### Calcul du nombre de points
		points = 1000*(tps_scratch-tps_base)/tps_base
		points += pen_manque_competiteurs
		
		
		####### Calcul des pénalités de course
		PEN = calcul_pen_tps_course(tps_scratch)
		points += PEN
		
		
		####### Calcul du coefficient correcteur
		COEF = self.calcul_coef_correcteur(points, competition, ranking)
		points *=COEF
		
		
		####### Ajout du malus de phase et de division
		# TODO MALUS = calcul_malus(competition)
		MALUS = 0
		points += MALUS
		
		
		####### Verification que les points sont positifs
		points -= min(0, np.min(points))
		
		return points
	
	def calcul_tps_scratch(self, competition):
		tps_scratch = np.zeros((len(competition.noms),))
		for i in range(competition.noms.shape[0]):
			coef = self.coef_inter_cat[competition.embs[i]]
			tps_scratch[i] = competition.scores[i]/coef
		return tps_scratch
	
	def calcul_tps_base(self, competition, tps_scratch):
		# Recherche des 10 meilleurs scores
		valeur_max = self.get_valeur_max(competition)
		indices_meilleurs = self.get_indices_meilleurs(competition,
												 tps_scratch,
												 valeur_max)
		if indices_meilleurs.shape[0] < 5:
			raise NotEnoughCompetitorException("La course "+competition.nom_course+" comporte des points mais n'a pas assez de competiteurs pour avoir des points. " + str(indices_meilleurs.shape[0]) + " temps fictifs pour " + str(competition.noms.shape[0]) + " competiteurs")
		pen_manque_competiteurs = 0
		if indices_meilleurs.shape[0] < 10:
			pen_manque_competiteurs = 20*(10-indices_meilleurs.shape[0])
		
		#calcul des temps fictifs
		tps_fictifs = self.calcul_tps_fictif(competition, indices_meilleurs)
		
		# Suppression des 2 temps les plus éloignés
		ecart_moyenne = np.absolute(tps_fictifs-np.mean(tps_fictifs))
		nb_comp_tps_base = min(8, indices_meilleurs.shape[0])
		indices_tps_base = np.argsort(ecart_moyenne)[:nb_comp_tps_base]
		tps_base = tps_fictifs[indices_tps_base].mean()
		return tps_base, pen_manque_competiteurs
	
	def get_valeur_max(self, competition):
		if competition.niveau == "Nationale 1":
			valeur_max = 150
		elif competition.niveau == "Nationale 2":
			valeur_max = 300
		else:
			valeur_max = 500
		return valeur_max
	
	def get_indices_meilleurs(self, competition, tps_scratch, valeur_max):
		indices_meilleurs = list()
		indices_ordonnes = np.argsort(tps_scratch)
		for indice in indices_ordonnes:
			if competition.moyennes[indice] < valeur_max:
				indices_meilleurs.append(indice)
				if len(indices_meilleurs) == 10:
					break
		return np.array(indices_meilleurs)
	
	def calcul_tps_fictif(self, competition, indices_meilleurs):
		temps_fictifs = list()
		for i in indices_meilleurs:
			temps_fictifs.append(1000*competition.scores[i]/(competition.moyennes[i]+1000))
		temps_fictifs = np.array(temps_fictifs)
		return temps_fictifs
	
	def calcul_coef_correcteur(self, points, competition, ranking):
		nb_competiteurs = points.shape[0]
		pts_initiaux = 0
		pts_apres_course = 0
		for i in range(nb_competiteurs):
			nom = competition.noms[i]
			emb = competition.embs[i]
			competiteur = ranking.get_competitor(nom, emb)
			val_competiteur = competiteur.get_val(competition.date_course)
			if competiteur.is_ranked(competition.date_course) and abs(val_competiteur.moyenne-points[i])>50:
				pts_initiaux += val_competiteur.moyenne
				competiteur_apres_course = competiteur.copy()
				competiteur_apres_course.add_course("should not be viewable", competition.niveau, competition.date_course, points[i])
				val_apres_course = competiteur_apres_course.get_val(competition.date_course)
				pts_apres_course += val_apres_course.moyenne
		if pts_apres_course == 0:
			return 1
		return pts_initiaux/pts_apres_course






