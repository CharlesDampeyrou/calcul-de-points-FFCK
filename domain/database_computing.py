#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 15:48:11 2020

@author: charles
"""
from datetime import date, timedelta
import logging

from data_handling.data_loader import get_competition_files, get_competition
from domain.database import Database
from points_methods.original_points import PointsComputer as OriginalPointsComputer
from points_methods.classic_method import PointsComputer as ClassicPointsComputer
from points_methods.exceptions import NotEnoughCompetitorException


def initialize_database(database, start_date):
	logging.info("Starting database initialisation...")
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
					database.add_course(comp)

		start_date += timedelta(days=1)
	logging.info("database initialisation finished")

def compute_database(start_date, end_date, points_computer):
	if start_date + timedelta(days=365) > end_date:
		raise Exception("Le classement doit se calculer sur plus d'un an.")
	database = Database()
	initialize_database(database, start_date)
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
					comp.update_val(database, comp.date_course)
					try:
						comp.update_points(database, points_computer)
					except NotEnoughCompetitorException:
						logging.warning("La competition : " + comp.nom_course + " n'est pas prise en compte dans le classement")
						comp_list.pop(i)
			for comp in comp_list:
				if comp.phase in phases:
					database.add_course(comp)

		start_date += timedelta(days=1)
	return database
