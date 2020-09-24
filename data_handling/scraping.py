#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 28 20:42:06 2020

@author: charles
"""
from bs4 import BeautifulSoup
import requests
import csv
import time

class Scrappeur(object) :
	def __init__(self) :
		self.domain = "http://www.ffcanoe.asso.fr"
		self.url = self.domain + "/eau_vive/slalom/classement/evenements/index"
		self.years_url = [self.url + "/annee:" + str(i) for i in range(2001, 2021)]
		#self.years_url = [self.url + "/annee:" + str(i) for i in [2001, 2005, 2010, 2015, 2020]]
		self.competitions_url = list()
		self.niveaux = list()
		self.event_names = list()
		self.phases = list()
	
	def get_years_competitions_url(self, year_url) :
		content = requests.get(year_url).content
		soup = BeautifulSoup(content)
		niv_tags = soup.find_all("div", {"class": "niveaux"})
		url_list = list()
		niv_list = list()
		names_list = list()
		phases_list = list()
		for niv_tag in niv_tags :
			niveau = niv_tag.find("h3").text
			for event in niv_tag.find_all("li", {"class": "event"}) :
				event_name = event.find("a").text
				event_detail = event.find("ul", {"class": "eventDetails"})
				for manche in event_detail.find_all("a") :
					phase = manche.text
					url = self.domain + manche["href"]
					url_list.append(url)
					niv_list.append(niveau)
					names_list.append(event_name)
					phases_list.append(phase)
		return names_list, niv_list, phases_list, url_list
	
	def get_all_competitions_url(self) :
		self.competitions_url = list()
		self.niveaux = list()
		self.event_names = list()
		self.phases = list()
		for year_url in self.years_url :
			names_list, niv_list, phases_list, url_list = self.get_years_competitions_url(year_url)
			print("Nombre de manches pour l'année " + year_url[-4:] + " : "\
		 + str(len(niv_list)))
			self.competitions_url += url_list
			self.niveaux += niv_list
			self.event_names += names_list
			self.phases += phases_list
		print("Au total, " + str(len(self.phases)) + " manches.")
		return
	
	def show_all_competitions(self) :
		for i in range(len(self.competitions_url)) :
			url = self.competitions_url[i]
			event_name = self.event_names[i]
			niv = self.niveaux[i]
			phase = self.phases[i]
			title, names_list, emb_list, score_list, val_list, points_list,\
				final_type_list = 	Scrappeur.get_competition_infos(url)
			print(niv + " " + event_name + " " + phase + " : " + title +
				 " Nombre de compétiteurs : " + str(len(names_list)) +
				 " Premier compétiteur : " + str(names_list[0]) + ", embarquation : " +
				 str(emb_list[0]) + ", score : " + str(score_list[0]) + ", valeur : " +
				 str(val_list[0]) + ", points : " + str(points_list[0]) + "\n")
	
	def save_all_files(self, rep = "/home/charles/database_courses_ffck") :
		for i in range(len(self.competitions_url)) :
			url = self.competitions_url[i]
			niv = self.niveaux[i]
			phase = self.phases[i]
			event = self.event_names[i]
			title, names_list, emb_list, score_list, val_list, points_list, final_type_list\
				= Scrappeur.get_competition_infos(url)
			print("Sauvegarde de la course " + title + " (course " + str(i) + "/" +
												   str(len(self.competitions_url)) +
												   ")")
			Scrappeur.save_competition(rep, title, event, niv, phase, names_list, emb_list,
								score_list, val_list, points_list, final_type_list)
	
	def get_row_infos(row) :
		cases = row.find_all("td")
		for case in cases :
			case_class = case.get("class")
			if case_class is None :
				if case.find("a") is not None :
					nom = case.text.strip()
			elif "score" in case_class :
				score = case.text.strip()
			elif "valeur" in case_class :
				valeur = case.text.strip()
			elif "points" in case_class :
				points = case.text.strip()
		return nom, score, valeur, points
	
	def get_table_infos(table, final_type = None):
		categorie = "UNKNOWN"
		names_list = list()
		emb_list = list()
		score_list = list()
		val_list = list()
		points_list = list()
		final_type_list = list()
		
		for ligne in table.find_all("tr") :
			if len(ligne.find_all("td")) == 0 : #categorie ou première ligne
				if ligne.get("class") is None : #première ligne du tableau
					continue
				else :
					categorie = ligne.find("th").text
			else :
				if ligne.get("class") in [["paire"],["impaire"]] : #ligne de détail de pénalités
					nom, score, valeur, points = Scrappeur.get_row_infos(ligne)
					if categorie != "INV" :
						names_list.append(nom)
						emb_list.append(categorie)
						score_list.append(score)
						val_list.append(valeur)
						points_list.append(points)
						final_type_list.append(final_type)
		return names_list, emb_list, score_list, val_list, points_list, final_type_list
	
	def get_competition_infos(comp_url) :
		content = requests.get(comp_url).content
		soup = BeautifulSoup(content)
		title = soup.find("h1", {"class": "pagetitle"}).text.strip()
		title = title.replace('/', ' sur ') #problème avec les '/' lors de la sauvegarde des fichiers
		resultats = soup.find("div", {"class": "results view"})
		final_types = resultats.find_all("h1")
		if final_types is not None :
			for i in range(len(final_types)) :
				final_types[i] = final_types[i].text
		tables = soup.find_all("table", {"id": "tableResults"})
		if len(tables) == 1 :
			names_list, emb_list, score_list, val_list, points_list, final_type_list\
				= Scrappeur.get_table_infos(tables[0])
			return title, names_list, emb_list, score_list, val_list, points_list,\
				final_type_list
		else :
			assert len(final_types) == len(tables)
			names_list_glob = list()
			emb_list_glob = list()
			score_list_glob = list()
			val_list_glob = list()
			points_list_glob = list()
			final_type_list_glob = list()
			for  i in range(len(final_types)) :
				names_list, emb_list, score_list, val_list, points_list, final_type_list\
				= Scrappeur.get_table_infos(tables[i], final_type=final_types[i])
				names_list_glob += names_list
				emb_list_glob += emb_list
				score_list_glob += score_list
				val_list_glob += val_list
				points_list_glob += points_list
				final_type_list_glob += final_type_list
			return title, names_list_glob, emb_list_glob, score_list_glob,\
				val_list_glob, points_list_glob, final_type_list_glob
	
	def save_competition(rep, titre, event_name, niveau, phase, names_list, emb_list,
					  score_list, val_list, points_list, final_type_list) :
		date = Scrappeur.get_date(titre)
		event_name = event_name.replace('/', ' sur ')
		phase = phase.replace("1/2", "demi")
		file_path = rep + "/" + date + "-" + event_name + "-" + phase + ".csv"
		with open(file_path, 'w') as csv_file :
			writer = csv.writer(csv_file)
			writer.writerow([titre, phase, date, niveau, str(len(names_list))])
			writer.writerow(["Athlète", "Catégorie", "Score", "Valeur", "Points course",
					"Finale A/B"])
			for i in range(len(names_list)) :
				writer.writerow([names_list[i], emb_list[i], score_list[i], val_list[i],
					 points_list[i], final_type_list[i]])
	
	def get_date(titre) :
		return titre[-10:]


		
if __name__ =="__main__" :
	comp = Scrappeur()
	comp.get_all_competitions_url()
	comp.save_all_files()
	"""
	rep = "/home/charles/calcul_de_points/database"
	title, names_list, emb_list, score_list, val_list, points_list, final_type_list\
		= Scrappeur.get_competition_infos(comp.competitions_url[0])
	Scrappeur.save_competition(rep, title, comp.niveaux[0], comp.phases[0], names_list,
							  emb_list, score_list, val_list, points_list,
							  final_type_list)
	"""