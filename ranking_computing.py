#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 15:48:11 2020

@author: charles
"""
from datetime import date, timedelta
import logging

from data_loader import get_competition_files, get_competition
from classement import Classement
from points_methods.original_points import PointsComputer as OriginalPointsComputer
from points_methods.classic_method import PointsComputer as ClassicPointsComputer
from points_methods.exceptions import NotEnoughCompetitorException


def initialize_ranking(ranking, start_date):
	logging.info("Starting ranking initialisation...")
	end_date = start_date + timedelta(days=365)
	while start_date < end_date:
		# Recuperation de toutes les courses de la journee
		comp_files = get_competition_files(date_debut=start_date, date_fin=start_date)
		comp_list = list()
		for comp_file in comp_files:
			comp_list.append(get_competition(comp_file))
		
		phases_list = [["", "qualif"], ["demi"], ["finale"]]
		# Traitement des courses de qualification ou sans phase, puis des demi et enfin des finales
		for phases in phases_list:
			for comp in comp_list:
				if comp.phase in phases:
					ranking.add_course(comp)
		
		start_date += timedelta(days=1)
	logging.info("Ranking initialisation finished")

def compute_ranking(start_date, end_date, points_computer):
	if start_date + timedelta(days=365) > end_date:
		raise Exception("Le classement doit se calculer sur plus d'un an.")
	ranking = Classement()
	initialize_ranking(ranking, start_date)
	start_date += timedelta(days=365)
	while start_date < end_date:
		# Recuperation de toutes les courses de la journee
		comp_files = get_competition_files(date_debut=start_date, date_fin=start_date)
		comp_list = list()
		for comp_file in comp_files:
			comp_list.append(get_competition(comp_file))
		
		phases_list = [["", "qualif"], ["demi"], ["finale"]]
		#traitement des qualif, puis demi, puis finales
		for phases in phases_list:
			for i in reversed(range(len(comp_list))):
				comp = comp_list[i]
				if comp.phase in phases:
					comp.update_val(ranking, comp.date_course)
					try:
						comp.update_points(ranking, points_computer)
					except NotEnoughCompetitorException:
						logging.error("La competition : " + comp.nom_course + " n'est pas prise en compte dans le classement")
						comp_list.pop(i)
			for comp in comp_list:
				if comp.phase in phases:
					ranking.add_course(comp)
		
		start_date += timedelta(days=1)
	return ranking



if __name__ == "__main__":
	#points_computer = OriginalPointsComputer()
	logging.basicConfig(level=logging.WARNING)
	points_computer = ClassicPointsComputer()
	ranking = compute_ranking(date(2018,1,1), date(2020, 7, 29), points_computer)