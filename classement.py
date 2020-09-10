#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 11 16:14:25 2020

@author: charles
"""
from competiteur import Competiteur

class Classement :
	def __init__(self) :
		self.dic_competiteurs = dict()
	
	def get_competitor(self, nom, emb) :
		if self.dic_competiteurs.get((nom, emb)) is None :
			comp = Competiteur(nom, emb)
			self.dic_competiteurs[nom, emb] = comp
		return self.dic_competiteurs[nom, emb]
	
	def get_val(self, nom, emb, date_calcul) :
		competiteur = self.get_competitor(nom, emb)
		return competiteur.get_val(date_calcul)
	
	def add_course(self, competition) :
		nom_course = competition.nom_course
		date_course = competition.date_course
		niv = competition.niveau
		noms = competition.noms
		embs = competition.embs
		points = competition.points
		for i in range(len(noms)):
			nom = noms[i]
			emb = embs[i]
			pts = points[i]
			if emb in ['K1H', 'K1D', 'C1H', 'C1D', 'C2H', 'C2M', 'C2D'] :
				competiteur = self.get_competitor(nom, emb)
				competiteur.add_course(nom_course, niv, date_course, pts)
		return
	
	def get_classement(self, date_calcul) :
		"""
		Retourne un dictionnaire dans lequel les tuples (nom, emb) sont les clés, et les valeurs sont le classement associé à chaque embarcation.
		"""
		dic_val = dict()
		for key in self.dic_competiteurs.keys() :
			dic_val[key] = self.dic_competiteurs[key].get_val(date_calcul)
		return dic_val