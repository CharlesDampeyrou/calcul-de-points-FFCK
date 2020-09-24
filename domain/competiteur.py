#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  4 19:36:38 2020

@author: charles
"""

from datetime import date, timedelta
from copy import deepcopy

import numpy as np

class Competiteur :
	"""
	Chaque compétiteur comporte son nom, son embarcation et la liste de ses courses. Chaque course est représentée sous la forme d'un tuple (nom_course, niv, date, points) où la date est une instance de la classe "date".
	"""
	def __init__(self, nom, emb) :
		self.nom = nom
		self.emb = emb
		self.L_courses = list()
	
	def add_course(self, nom_course, niv, date, points) :
		course = (nom_course, niv, date, points)
		self.L_courses.append(course)
	
	def get_val(self, date_calcul, nb_comp_min = 4, nb_nat_min = 3) :
		date_lim = date_calcul - timedelta(days=365)
		L_courses_calcul =list()
		for course in self.L_courses :
			if course[2] > date_lim and course[2] <= date_calcul :
				# La course a eu lieu entre 1 an avant le calul et la date du calcul
				L_courses_calcul.append(course)
		return Valeur.compute_val(L_courses_calcul, nb_comp_min=nb_comp_min, nb_nat_min=nb_nat_min)
	
	def is_ranked(self, date_calcul, nb_comp_min = 4, nb_nat_min = 3):
		date_lim = date_calcul - timedelta(days=365)
		L_courses_calcul =list()
		for course in self.L_courses :
			if course[2] > date_lim and course[2] <= date_calcul :
				# La course a eu lieu entre 1 an avant le calul et la date du calcul
				L_courses_calcul.append(course)
		nb_nat = 0
		nb_comp = len(L_courses_calcul)
		for course in L_courses_calcul:
			if course[1] != 'Régional':
				nb_nat +=1
		return nb_nat >= nb_nat_min and nb_comp >= nb_comp_min
	
	def copy(self):
		comp = Competiteur(self.nom, self.emb)
		comp.L_courses = deepcopy(self.L_courses)
		return comp


class Valeur :
	def __init__(self, moyenne, nb_nat, nb_comp) :
		self.moyenne = moyenne
		self.nb_nat = nb_nat # nombre de compétitions nationnales dans la moyenne
		self.nb_comp = nb_comp # nombre de compétitions dans la moyenne
	
	def __str__(self) :
		return "Moyenne : " + str(self.moyenne) + " (" + str(self.nb_comp) + " courses dont " + str(self.nb_nat) + " courses nationales)"
	
	def __lt__(self, autre_val) :
		if self.nb_comp == autre_val.nb_comp:
			if self.nb_nat == autre_val.nb_nat :
				return self.moyenne < autre_val.moyenne
			else :
				return self.nb_nat > autre_val.nb_nat
		else :
			return self.nb_comp > autre_val.nb_comp
	
	def __le__(self, autre_val):
		if self.nb_comp == autre_val.nb_comp:
			if self.nb_nat == autre_val.nb_nat:
				return self.moyenne <= autre_val.moyenne
			else:
				return self.nb_nat > autre_val.nb_nat
		else:
			return self.nb_comp > autre_val.nb_comp
	
	def __eq__(self, autre_val) :
		return self.moyenne == autre_val.moyenne and self.nb_nat == autre_val.nb_nat and self.nb_comp == autre_val.nb_comp
	
	def __ne__(self, autre_val) :
		return not self == autre_val
	
	def __ge__(self, autre_val) :
		return not self < autre_val
	
	def __gt__(self, autre_val) :
		return not self <= autre_val
	
	def compute_val(cls, comp_list, nb_comp_min = 4, nb_nat_min = 3) :
		"""
		Cette fonction permet d'obtenir un objet de type Valeur à partir d'une liste de compétitions. Chaque course est représentée sous la forme d'un tuple (nom_course, niv, date, points). nb_comp_min est le nombre de courses à avoir dans le classement et nb_nat_min le nombre de courses nationales à avoir au minimum.
		"""
		if len(comp_list) == 0 :
			return cls(1000, 0, 0) #convention si le compétiteur n'a pas de course
		comp_reg_list = list()
		comp_nat_list = list()
		for comp in comp_list :
			if comp[1] == "Régional" :
				comp_reg_list.append(comp)
			else :
				comp_nat_list.append(comp)
		nb_comp = min(len(comp_list), nb_comp_min)
		nb_nat = min(len(comp_nat_list), nb_nat_min)
		comp_reg_list.sort(key = lambda x:x[3])
		comp_nat_list.sort(key = lambda x:x[3])
		points_moy = list()
		for i in range(nb_nat):
			points_moy.append(comp_nat_list[0][3])
			comp_nat_list.pop(0)
		comp_list = comp_nat_list + comp_reg_list
		comp_list.sort(key = lambda x:x[3])
		for i in range(nb_comp - nb_nat) :
			points_moy.append(comp_list[i][3])
		moyenne = np.array(points_moy).mean()
		return cls(moyenne, nb_nat, nb_comp)
	compute_val = classmethod(compute_val)



def test_add_course() :
	competiteur1 = Competiteur("charles", "C1H")
	competiteur1.add_course("chelles", "reg", date(2020, 4, 5), 400.0)
	print(competiteur1.L_courses)

def test_get_val():
	competiteur1 = Competiteur("charles", "C1H")
	competiteur1.add_course("chelles", "reg", date(2020, 4, 5), 400.0)
	competiteur1.get_val(date(2020, 4, 5))

if __name__ == "__main__" :
	test_get_val()