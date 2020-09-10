#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 12:09:02 2020

@author: charles
"""

from datetime import date
import csv
import os

import numpy as np
import random as rd

from competition import Competition

def is_competition_file(file) :
	try :
		date_from_iso(file[:10])
		if file[-4:] == ".csv":
			return True
		else :
			return False
	except ValueError :
		return False

def is_number(s) :
	try :
		float(s)
		return True
	except ValueError :
		return False

def date_from_iso(iso) :
	year = int(iso[:4])
	month = int(iso[5:7])
	day = int(iso[8:])
	return date(year, month, day)

def get_competition_files(date_debut = None, date_fin = None) :
	rep = "/home/charles/database_courses_ffck"
	files_list = os.listdir(rep)
	files_list.sort()
	for i in range(len(files_list)).__reversed__() :
		if is_competition_file(files_list[i]) :
			date_competition = date_from_iso(files_list[i][:10])
			if date_debut is not None :
				if date_debut > date_competition :
					files_list.pop(i)
					continue
			if date_fin is not None :
				if date_fin < date_competition :
					files_list.pop(i)
					continue
			files_list[i] = rep + "/" + files_list[i]
		else :
			files_list.pop(i)
	return files_list

def get_competition(file_path) :
	with open(file_path, 'r') as file :
		reader = csv.reader(file)
		first_line = reader.__next__()
		nom_course = first_line[0]
		phase = simplify_phase(first_line[1])
		date_course = date_from_iso(first_line[2])
		niveau = first_line[3]
		
		reader.__next__() # Deuxième ligne inutile
		
		noms = list()
		embs = list()
		scores = list()
		valeurs = list()
		points = list()
		finale_a_b = list()
		valid_categories = ["K1H", "K1D", "C1H", "C1D", "C2H", "C2D", "C2M"]
		for line in reader :
			if is_number(line[2]) and is_number(line[4]) and line[1] in valid_categories : # On prend uniquement en compte les embarcations individuelles ayant un temps et des points
				noms.append(line[0])
				embs.append(line[1])
				scores.append(line[2])
				if is_number(line[3]) : # Si le competiteur a une valaur
					valeurs.append(float(line[3]))
				else :
					valeurs.append(np.nan)
				points.append(float(line[4]))
				if len(line) == 6 :
					finale_a_b.append(simplify_final_type(line[5]))
				else :
					finale_a_b.append("")
	noms = np.array(noms)
	embs = np.array(embs)
	scores = np.array(scores, dtype=float)
	points = np.array(points, dtype=float)
	finale_a_b = np.array(finale_a_b)
	return Competition(nom_course, phase, date_course, niveau, noms, embs, scores, valeurs, points, finale_a_b)

def simplify_phase(phase) :
	no_phase_list = ["Course 1", "Course 2", "Course 3", "3ème Manche", "Championnats de France Cadets, Juniors, Vétérans, Finale N2 Sénior et Qualification Finale N1", "Course par équipe | Finale", "7ème Manche", "Finale N2 Séniors", "Challenge Matthieu Perriguey", "Cadets", "Championnats de France Cadets", "Championnat Rhône Alpes Slalom - Vénéon", "Course N°1 | Qualification", "Course N°1", "Course n°4 - Pau", "2ème Manche", "Course N°3", "Challenge Jean-François Dugast", "1ère Manche", "Course 4", "5ème Manche", "6ème Manche", "8ème Manche", "Cadets, Juniors, Vétérans, Finale N2 Sénior et Qualification Finale N1", "4ème Manche", "Demi-finale N1", "Championnats d'Alsace", "Championnat de Normandie", "Course par équipe | Qualification", "Championnat de France par équipe de clubs", "Course n°3 - Pau", "Challenge Bertrand", "Course unique", "Open Val de Sarre", "Championnats de France Vétérans et Finale N2 Sénior", "Courses par équipe", "Championnats de France slalom par équipe", "Course par équipe", "Championnat régional", "Championnat de France Slalom par Equipe de Clubs", "Juniors et Vétérans", "Championnats de France Juniors", "Course n°2 - La Seu d'Urgell", "Championnat de France par Equipe de Clubs", " Cadets, Juniors, Vétérans, et Finale N2 Sénior", "Course N°2", "Vétérans", "Course n°1 - La Seu d'Urgell", "Championnat de France par équipe", "FestiKayaK", "7ème manche, course unique", "Course patrouille | Qualification", "Course patrouille | Finale", "Championnats de France Juniors, Vétérans, Finale N2 Sénior"]
	qualif_list = ["Qualification", "Course n°1 | Qualification", "Qualification - Manche 1", "Course n°2 | Qualification", "Course de qualification", "Course 2 | Qualification", "Qualifications", "Qualification - Manche 2", "Course individuelle | Qualification", "Course 1 | Qualification", "Course N°2 | Qualification", "Course 1 - Qualification", "Qualification K1D-C2H", "Qualification - Manche unique", "Course 2 - Qualification", "Qualification C1H-C1D-K1H"]
	demi_list = ["Demi finale", "Demi-finale", "Course n°1 | demi Finale", "Course n°2 | Demi-finale", "Course de demi-finale", "Demi-Finale", "demi finale", "Course n°2 | demi Finale", "Course n°3 | demi Finale", "Demi", "Course n°3 | Demi-finale", "Course 2 - Demi-finale", "Course 3 - Demi-finale", "Demi-finale (haut du bassin)", "Course 1 - Demi-finale", "Course n°3 | demi finale", "Course n°1 | Demi-finale", "Course n°1 | demi finale", "Demi-finale (bas du bassin)", "Course n°4 | Demi-finale", "Course n°2 | demi finale"]
	finale_list = ["Finale", "Course n°1 | Finale", "Course n°2 | Finale", "Course 1 | Finale", "Course de finale", "Course N°2 | Finale", "Course de Finale", "Course 2 - Finale", "Course 2 | Finale", "Finale N1", "Course n°4 | Finale", "Course N°1 | Finale", "Course n°3 | Finale", "Course 1 - Finale", "Course 1 | Finale ", "Course N°4", "Course individuelle | Finale", "Finales", "FINALE ", "Finale (haut du bassin)", "Finale C1H-C1D-K1H", "Course 3 - Finale", "Finale (bas du bassin)", "Finale de la coupe de Lorraine", "Finale K1D-C2H"]
	if phase in no_phase_list :
		return ""
	elif phase in qualif_list :
		return "qualif"
	elif phase in demi_list :
		return "demi"
	elif phase in finale_list :
		return "finale"
	else :
		print("Phase non reconnue : " + phase)
		return ""

def simplify_final_type(finale_a_b) :
	demi_a_list = ["Demi-finale A", "Demi-Finale A", "Demi finale A", "Demi A"]
	demi_b_list = ["Demi-finale B", "Demi-Finale B", "Demi finale B", "Demi B"]
	finale_a_list = ["Course n°1 | Finale A", "Course n°2 | Finale A", "Finale A", "Course 1 | Finale A", "Course N°2 | Finale A", "Course 2 - Finale A", "Course 2 | Finale A", "Course n°4 | Finale A", "Course N°1 | Finale A", "Course 1 - Finale A", "Course 1 | Finale  A", "Finales A", "FINALE  A", "Course n°3 | Finale A"]
	finale_b_list = ["Course n°1 | Finale B", "Course n°2 | Finale B", "Finale B", "Course 1 | Finale B", "Course N°2 | Finale B", "Course 2 - Finale B", "Course 2 | Finale B", "Course n°4 | Finale B", "Course N°1 | Finale B", "Course 1 - Finale B", "Course 1 | Finale  B", "Finales B", "FINALE  B", "Course n°3 | Finale B"]
	if finale_a_b == "" :
		return ""
	elif finale_a_b in demi_a_list :
		return "demi a"
	elif finale_a_b in demi_b_list :
		return "demi b"
	elif finale_a_b in finale_a_list :
		return "finale a"
	elif finale_a_b in finale_b_list :
		return "finale b"
	else :
		print("Type de finale non reconnu : " + finale_a_b)
		return ""

def test_simplify() :
	rep = "/home/charles/database_courses_ffck"
	files_list = os.listdir(rep)
	for i in range(len(files_list)).__reversed__() :
		if not is_competition_file(files_list[i]) :
			files_list.pop(i)
	file_paths = [rep + "/" + file for file in files_list]
	niv_list = list()
	phase_list = list()
	embs_list = list()
	finale_a_b_list = list()
	noms_list = list()
	for file_path in file_paths :
		nom_course, phase, date_course, niveau, noms, embs, scores, valeurs, points, finale_a_b = get_competition(file_path)
		if phase not in phase_list :
			phase_list.append(phase)
		if niveau not in niv_list :
			niv_list.append(niveau)
		for i in range(len(noms)) :
			if embs[i] not in embs_list :
				embs_list.append(embs[i])
			if noms[i] not in noms_list :
				noms_list.append(noms[i])
			if finale_a_b[i] not in finale_a_b_list :
				finale_a_b_list.append(finale_a_b[i])
	for phase in phase_list :
		simplify_phase(phase)
	for finale_a_b in finale_a_b_list :
		simplify_final_type(finale_a_b)
	return

def show_different_values() :
	rep = "/home/charles/database_courses_ffck"
	files_list = os.listdir(rep)
	for i in range(len(files_list)).__reversed__() :
		if not is_competition_file(files_list[i]) :
			files_list.pop(i)
	file_paths = [rep + "/" + file for file in files_list]
	niv_list = list()
	phase_list = list()
	embs_list = list()
	finale_a_b_list = list()
	noms_list = list()
	for file_path in file_paths :
		nom_course, phase, date_course, niveau, noms, embs, scores, valeurs, points, finale_a_b = get_competition(file_path)
		if phase not in phase_list :
			phase_list.append(phase)
		if niveau not in niv_list :
			niv_list.append(niveau)
		for i in range(len(noms)) :
			if embs[i] not in embs_list :
				embs_list.append(embs[i])
			if noms[i] not in noms_list :
				noms_list.append(noms[i])
			if finale_a_b[i] not in finale_a_b_list :
				finale_a_b_list.append(finale_a_b[i])
	print("Niveaux : " + str(niv_list))
	print("Phases : " + str(phase_list))
	print("Embarcations : " + str(embs_list))
	print("Types de finales : " + str(finale_a_b_list))
	return

def test_get_competition() :
	def show_competition(file_path) :
		nom_course, phase, date_course, niveau, noms, embs, scores, valeurs, points, finale_a_b = get_competition(file_path)
		print("Nom course : " + nom_course)
		print("Phase : " + phase)
		print("Date de la course : " + str(date_course))
		print("Niveau : " + niveau)
		print("format : nom, embarcation, score, valeur, points, finale_a_b")
		for i in range(len(noms)) :
			print(noms[i] + ", " + embs[i] + ", " + str(scores[i]) + ", " + str(valeurs[i]) + ", " + str(points[i]) + ", " + str(finale_a_b[i]))
		print("\n\n")
		return
	
	rep = "/home/charles/database_courses_ffck"
	files_list = os.listdir(rep)
	rd.shuffle(files_list)
	file_paths = [rep + "/" + file for file in files_list[:15]]
	
	for file_path in file_paths :
		show_competition(file_path)
	return


def test_get_competition_files() :
	date_debut = date(2018, 9, 1)
	date_fin = date(2019, 9, 1)
	fichiers = get_competition_files(date_debut = date_debut, date_fin = date_fin)
	print(fichiers)
	return

if __name__ == "__main__" :
	#test_get_competition()
	show_different_values()
	#test_simplify()
	#stest_get_competition_files()
