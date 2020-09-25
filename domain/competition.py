#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 16:18:00 2020

@author: charles
"""
import logging

import numpy as np

from points_methods.exceptions import NoCompetitorException, NotEnoughCompetitorException

class Competition:
	"""
	Objet Competition, contient les informations générales de la course ainsi que les liste des noms, embarcations, scores, moyenne (Valeur.moyenne si le nombre de courses est suffisant, np.nan sinon), points et finale_a_b
	"""
	def __init__(self, nom_course, phase, date_course, niveau, noms, embs, scores, moyennes, points, finale_a_b):
		self.nom_course = nom_course
		self.phase = phase
		self.date_course = date_course
		self.niveau = niveau
		self.noms = noms
		self.embs = embs
		self.scores = scores
		self.moyennes = moyennes
		self.points = points
		self.finale_a_b = finale_a_b
		self.logger = logging.getLogger("domain.Competition")

	def update_val(self, ranking, date_calcul):
		"""
		Méthode pour mettre à jour les valeurs des compétiteurs de la course à la date souhaitée, à l'aide du classement (objet Classement) valide à cette date.
		"""
		for num_competitor in range(len(self.noms)):
			nom = self.noms[num_competitor]
			emb = self.embs[num_competitor]
			competitor = ranking.get_competitor(nom, emb)
			if competitor.is_ranked(date_calcul):
				self.moyennes[num_competitor] = competitor.get_val(date_calcul).moyenne
			else:
				self.moyennes[num_competitor] = np.nan

	def update_points(self, ranking, point_computer):
		"""
		Méthode pour mettre à jour les points de la course avec l'objet point_computer fourni.
		"""
		try:
			new_points = point_computer.compute_points(self, ranking)
		except NoCompetitorException:
			self.logger.info("Les points de la course : "+self.nom_course+" n'ont pas pu etre mis a jour car la competition ne comporte pas d'embarquation individuelle.")
			new_points = np.array([])
		except NotEnoughCompetitorException as e:
			self.logger.info(repr(e))
			raise e
		self.points = new_points
