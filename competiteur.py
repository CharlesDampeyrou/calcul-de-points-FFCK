#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  4 19:36:38 2020

@author: charles
"""

from datetime import date

class Competiteur :
	dic_competiteurs = dict()
	def __init__(self, nom, emb) :
		Competiteur.dic_competiteurs[nom, emb] = self
		self.nom = nom
		self.emb = emb
		self.L_courses = list()
	
	def add_course_(self, nom_course, niv, date, points) :
		course = (nom_course, niv, date, points)
		self.L_courses.append(course)
	
	def get_moy_(self, date_calcul, calcul_moy) :
		date_lim = date_calcul.replace(year = date_calcul.year - 1)
		L_courses_calcul =list()
		for course in self.L_courses :
			if course[2] > date_lim and course[2] <= date_calcul :
				# La course a eu lieu entre 1 an avant le calul et la date du calcul
				L_courses_calcul.append(course)
		return calcul_moy(L_courses_calcul)
	
	def get_moy(cls, nom, emb, date_calcul, calcul_moy) :
		competiteur = cls.dic_competiteurs.get((nom, emb))
		if competiteur is not None :
			# le competiteur est dans le dico des competiteurs
			return competiteur.get_moy_(date_calcul, calcul_moy)
		else :
			return calcul_moy(list())
	get_moy = classmethod(get_moy)
	
	def add_course(cls, nom_course, date_course, niv, noms, embs, points) :
		for i in range(len(noms)):
			nom = noms[i]
			emb = embs[i]
			pts = points[i]
			competiteur = cls.dic_competiteurs.get((nom, emb))
			if competiteur is None :
				if emb in ['K1H', 'K1D', 'C1H', 'C1D', 'C2H', 'C2M', 'C2D'] :
					competiteur = cls(nom, emb)
				else :
					continue
			competiteur.add_course_(nom_course, niv, date_course, pts)
	add_course = classmethod(add_course)


def test_add_course_() :
	competiteur1 = Competiteur("charles", "C1H")
	competiteur1.add_course_("chelles", "reg", date(2020, 4, 5), 400)
	print(Competiteur.dic_competiteurs)
	print(competiteur1.L_courses)

def test_get_moy_():
	competiteur1 = Competiteur("charles", "C1H")
	competiteur1.add_course_("chelles", "reg", date(2020, 4, 5), 400)
	competiteur1.get_moy_(date(2020, 4, 5), print)

def test_get_moy() :
	competiteur1 = Competiteur("charles", "C1H")
	competiteur1.add_course_("chelles", "reg", date(2020, 4, 5), 400)
	Competiteur.get_moy("charles", "C1H", date(2020, 4, 5), print)
	Competiteur.get_moy("charles", "K1H", date(2020, 4, 5), print)

def test_add_course():
	niv = "reg"
	competiteur1 = Competiteur("charles", "C1H")
	competiteur1.add_course_("chelles", "reg", date(2020, 3, 5), 400)
	noms = ["charles", "yohan", "fanny"]
	embs = ["C1H", "K1H", "INV"]
	points = [350, 400, 450]
	Competiteur.add_course("corbeil", date(2020, 4, 5), niv, noms, embs, points)
	Competiteur.get_moy("charles", "C1H", date(2020, 4, 5), print)
	Competiteur.get_moy("yohan", "K1H", date(2020, 4, 5), print)
	Competiteur.get_moy("fanny", "INV", date(2020, 4, 5), print)

if __name__ == "__main__" :
	pass