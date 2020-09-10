#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 13 15:28:30 2020

@author: charles
"""
import numpy as np

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
	
	def get_val(cls, comp_list, nb_comp_min = 4, nb_nat_min = 3) :
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
			comp_nat_list.pop(i)
		comp_list = comp_nat_list + comp_reg_list
		comp_list.sort(key = lambda x:x[3])
		for i in range(nb_comp - nb_nat) :
			points_moy.append(comp_list[i][3])
		moyenne = np.array(points_moy).mean()
		return cls(moyenne, nb_nat, nb_comp)
	get_val = classmethod(get_val)


if __name__ == "__main__" :
	val1 = Valeur(100, 3, 4)
	val2 = Valeur(105, 3, 4)
	val3 = Valeur(101, 1, 1)
	val4 = Valeur(102, 0, 3)
	val_list = [val1, val2, val3, val4]
	for val in val_list :
		print(val)
	print("ordonnancement")
	val_list.sort()
	for val in val_list :
		print(val)