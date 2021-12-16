# -*- coding: utf-8 -*-
"""
Created on Wed Dec 15 13:55:09 2021

@author: charl
"""

# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 17:18:15 2021

@author: charl
"""
import time
from pathlib import Path
import requests
import logging
from datetime import datetime

from bs4 import BeautifulSoup
import pickle

from data_handling.csv_data_service import CsvDataService

class Scrappeur(object) :
    def __init__(self) :
        self.domain = "http://www.ffcanoe.asso.fr"
        self.url = self.domain + "/eau_vive/slalom/classement/evenements/index"
        #self.years_url = [self.url + "/annee:" + str(i) for i in range(2000, 2022)]
        self.years_url = [self.url + "/annee:" + str(i) for i in [2001, 2021]] #for testing purpose
        self.competitions_url = list()
        self.niveaux = list()
        self.event_names = list()
        self.phases = list()
        self.logger = logging.getLogger("Scrapper")
        self.csv_data_service = CsvDataService(database_service=None)
        self.phase_simplifier = PhaseSimplifier()
        self.final_type_simplifier = FinalTypeSimplifier()

    def get_years_competitions_url(self, year_url) :
        content = requests.get(year_url).content
        soup = BeautifulSoup(content, "lxml")
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
            self.logger.info("Nombre de manches pour l'année " + year_url[-4:] + " : "+ str(len(niv_list)))
            self.competitions_url += url_list
            self.niveaux += niv_list
            self.event_names += names_list
            self.phases += phases_list
        self.logger.info("Au total, " + str(len(self.phases)) + " manches.")
        return

    def save_all_competitions(self, first_saving=False):
        self.logger.info("récupération et sauvegarde de toutes les infos de competition...")
        for i in range(0, len(self.competitions_url)):
            if i%20 == 0:
                msg = "Récupération et sauvegarde de la compétition %s sur %s"
                self.logger.info(msg % (i, len(self.competitions_url)))
            competition_infos = get_competition_infos(self.competitions_url[i])
            niv = self.niveaux[i]
            phase = self.phases[i]
            event = self.event_names[i]
            title, names_list, emb_list, score_list, val_list, points_list, final_type_list = competition_infos
            self.save_competition(title, event, niv, phase, names_list, emb_list,
                                    score_list, val_list, points_list, final_type_list, first_saving=first_saving)
        self.phase_simplifier.save_phases()
        self.final_type_simplifier.save_final_types()


    def get_row_infos(row) :
        cases = row.find_all("td")
        for case in cases :
            case_class = case.get("class")
            if case_class is None :
                if case.find("a") is not None :
                    nom = case.text.strip()
                    nom = nom.replace("\n", "-")
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
                    if categorie != "INV" and is_float_as_str(score) and is_float_as_str(points):
                        names_list.append(nom)
                        emb_list.append(categorie)
                        score_list.append(float(score))
                        if is_float_as_str(valeur):
                            val_list.append(float(valeur))
                        else:
                            val_list.append(valeur)
                        points_list.append(float(points))
                        final_type_list.append(final_type)
        return names_list, emb_list, score_list, val_list, points_list, final_type_list



    def save_competition(self, competition_name, simplified_competition_name, niveau, phase, names_list, emb_list,
                      score_list, val_list, points_list, final_type_list, first_saving=False) :
        if len(names_list) == 0:
            return #Ne pas sauvegarder les courses sans compétiteur
        date = Scrappeur.get_date(competition_name)
        simplified_phase = self.phase_simplifier.simplify(phase)
        simplified_final_type_list = self.final_type_simplifier.simplify_list(final_type_list)
        self.csv_data_service.save_competition_as_csv(names_list,
                                                      emb_list,
                                                      competition_name,
                                                      simplified_competition_name,
                                                      phase,
                                                      simplified_phase,
                                                      date,
                                                      niveau,
                                                      simplified_final_type_list,
                                                      score_list,
                                                      original_points=points_list,
                                                      original_values=val_list,
                                                      first_saving=first_saving)




    def get_date(title) :
        date_str = title[-10:]
        year = int(date_str[:4])
        month = int(date_str[5:7])
        day = int(date_str[8:])
        return datetime(year, month, day)

    def update_csv_database(self):
        self.logger.info("Mise à jour de la base de données CSV")
        last_year = self.csv_data_service.get_last_competition_year()
        first_saving =  (last_year == 2001)
        self.years_url = [self.url + "/annee:" + str(i) for i in range(last_year, time.localtime().tm_year+1)]
        #self.years_url = [self.url + "/annee:" + str(i) for i in [2001, 2014, 2021]] #for testing purpose
        self.logger.info("dernière année de compétition : %i" % last_year)
        self.get_all_competitions_url()
        self.save_all_competitions(first_saving=first_saving)


def get_competition_infos(comp_url):
    content = requests.get(comp_url).content
    soup = BeautifulSoup(content, 'lxml')
    title = soup.find("h1", {"class": "pagetitle"}).text.strip()
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

class FinalTypeSimplifier:
    def __init__(self, saving_file_path=Path(Path.cwd(),"data_handling" , "final_type_simplification.pkl")):
        self.saving_file_path = saving_file_path
        self.logger = logging.getLogger("FinalTypeSimplifier")
        (self.no_type_list,
         self.final_a_list,
         self.final_b_list) = self.read_final_types_file()

    def save_final_types(self):
        with open(self.saving_file_path, 'wb') as file:
            to_save = (self.no_type_list,
                       self.final_a_list,
                       self.final_b_list)
            pickle.dump(to_save, file)

    def read_final_types_file(self):
        try:
            with open(self.saving_file_path, 'rb') as file:
                (no_type_list,
                 final_a_list,
                 final_b_list) = pickle.load(file)
        except FileNotFoundError:
            msg = "Attention : pas de fichier trouvé pour la simplification des types de finales."
            msg += " ('%s')" % str(self.saving_file_path)
            self.logger.warning(msg)
            no_type_list = list()
            final_a_list = list()
            final_b_list = list()
        return (no_type_list, final_a_list, final_b_list)

    def simplify_list(self, final_type_list):
        simplified_types_list = list()
        for final_type in final_type_list:
            simplified_types_list.append(self.simplify(final_type))
        return simplified_types_list

    def simplify(self, final_type):
        if final_type is None or final_type in self.no_type_list:
            return None
        elif "finale a" in final_type.lower() or final_type in self.final_a_list:
            return "finale a"
        elif "finale b" in final_type.lower() or final_type in self.final_b_list:
            return "finale b"
        else:
            simplified_final_type = self.ask_for_final_type(final_type)
            self.add_final_type(final_type, simplified_final_type)

    def ask_for_final_type(self, final_type):
        response = None
        while response not in ["n", "a", "b"]:
            msg = "Type de finale non reconnu : %s. Entrez a pour finale a, b pour finale b, n sinon : "
            response = input(msg % final_type)
        if response == "a":
            return "finale a"
        elif response == "b":
            return "finale b"
        else:
            return None

    def add_final_type(self, final_type, simplified_final_type):
        if simplified_final_type is None:
            self.no_type_list.append(final_type)
        elif simplified_final_type == "finale a":
            self.final_a_list.append(final_type)
        else:
            self.final_b_list.append(final_type)

class PhaseSimplifier:
    def __init__(self, saving_file_path=Path(Path.cwd(),"data_handling" , "phase_simplification.pkl")):
        self.logger = logging.getLogger("PhaseSimplifier")
        self.saving_file_path = saving_file_path
        (self.no_phase_list,
         self.qualif_list,
         self.demi_list,
         self.final_list) = self.read_phases_file()

    def save_phases(self):
        with open(self.saving_file_path, 'wb') as file:
            to_save = (self.no_phase_list,
                       self.qualif_list,
                       self.demi_list,
                       self.final_list)
            pickle.dump(to_save, file)

    def read_phases_file(self):
        try:
            with open(self.saving_file_path, 'rb') as file:
                (no_phase_list,
                 qualif_list,
                 demi_list,
                 final_list) = pickle.load(file)
        except FileNotFoundError:
            msg = "Attention : pas de fichier trouvé pour la simplification des phases."
            msg += " ('%s')" % str(self.saving_file_path)
            self.logger.warning(msg)
            no_phase_list = list()
            qualif_list = list()
            demi_list = list()
            final_list = list()
        return (no_phase_list, qualif_list, demi_list, final_list)

    def simplify(self, phase):
        if phase in self.no_phase_list:
            return ""
        elif phase in self.qualif_list:
            return "qualif"
        elif phase in self.demi_list:
            return "demi"
        elif phase in self.final_list:
            return "finale"
        else :
            simplified_phase = self.ask_for_phase(phase)
            self.add_phase_to_list(phase, simplified_phase)
            return simplified_phase

    def ask_for_phase(self, phase):
        response = None
        while response not in ["n", "q", "d", "f"]:
            msg = "La phase '%s' n'est pas reconnue, tapez n si elle ne correspond"
            msg += " à aucune phase, q pour une qualification, d pour une demi-"
            msg += "finale ou f pour une  finale : "
            response = input(msg % phase)
        if response == "n":
            return ""
        elif response == "q":
            return "qualif"
        elif response == "d":
            return "demi"
        elif response == "f":
            return "finale"

    def add_phase_to_list(self, phase, simplified_phase):
        if simplified_phase == "":
            self.no_phase_list.append(phase)
        elif simplified_phase == "qualif":
            self.qualif_list.append(phase)
        elif simplified_phase == "demi":
            self.demi_list.append(phase)
        elif simplified_phase == "finale":
            self.final_list.append(phase)

    def show_all_phases(self):
        print("Voici les différentes phases :")
        print("Pas de phase :")
        print(self.no_phase_list, end="\n\n")
        print("Qualification :")
        print(self.qualif_list, end="\n\n")
        print("Demi-finale : ")
        print(self.demi_list, end="\n\n")
        print("Finale : ")
        print(self.final_list)

def is_float_as_str(float_as_str):
    try:
        float(float_as_str)
        return True
    except ValueError:
        return False


if __name__ =="__main__" :
    """
    nest_asyncio.apply()
    logging.basicConfig(level=logging.INFO)
    scrappeur = Scrappeur()
    scrappeur.get_all_competitions_url()
    loop = asyncio.get_event_loop()
    classe_test = ClasseTest()
    loop.run_until_complete(classe_test.get_all_pages())
    print("Done")"""
    logging.basicConfig(level=logging.INFO)
    scrappeur = Scrappeur()
    scrappeur.update_csv_database()
