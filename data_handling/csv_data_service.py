# -*- coding: utf-8 -*-
"""
Created on Mon Dec  6 11:32:08 2021

@author: charl
"""

import os
import logging
from pathlib import Path
import csv
from datetime import datetime

from data_handling.database_service import DatabaseService

class CsvDataService:
    def __init__(self):
        self.logger = logging.getLogger("CsvDataService")
        self.csv_database_directory = Path(Path.cwd(), "csv_database")
        self.db_service = DatabaseService()
        
    def save_competition_as_csv(self,
                                competitor_names,
                                competitor_categories,
                                competition_name,
                                simplified_competition_name,
                                competition_phase,
                                simplified_competition_phase,
                                date,
                                level,
                                final_types,
                                scores,
                                original_points=None,
                                original_values=None,
                                first_saving=False):
        date_str = date.isoformat()[:10]
        file_name = date_str + "-"
        competition_name_without_date = competition_name[:-13] #retrait de la date
        if len(competition_name_without_date) > 100: #certains noms sont trop longs
            file_name += competition_name_without_date[:100]
        else:
            file_name += competition_name_without_date
        if competition_phase not in file_name: #Certains noms de compet ne comportent pas la manche et existent donc en double
            competition_name += " " + competition_phase
            file_name += " " + competition_phase[:min(40, len(competition_phase))]
        
        file_name += ".csv"
        file_name = replace_chars(file_name, ["/", "\"", "\\", "|", "?"], "-")
        file_path = Path(self.csv_database_directory, file_name)
        if os.path.exists(file_path) and first_saving:
            msg = "La competition '%s' est déjà enregistrée au format CSV"
            self.logger.error(msg % competition_name)
            raise ExistingItemException(msg % competition_name)
        elif os.path.exists(file_path):
            msg = "La competition '%s' est déjà enregistrée au format CSV"
            self.logger.warning(msg % competition_name)
            return
        with open(file_path, 'w', newline='') as csv_file :
            writer = csv.writer(csv_file, dialect="unix")
            writer.writerow([competition_name,
                             simplified_competition_name,
                             competition_phase,
                             simplified_competition_phase,
                             date_str,
                             level,
                             str(len(competitor_names))])
            writer.writerow(["Athlète", "Catégorie", "Score", "Valeur", "Points course",
                    "Finale A/B"])
            for i in range(len(competitor_names)) :
                writer.writerow([competitor_names[i],
                                 competitor_categories[i],
                                 scores[i],
                                 original_values[i] if original_values else "",
                                 original_points[i] if original_points else "",
                                 final_types[i]])
    
    def save_csv_files_in_database(self):
        competition_files_paths = self.get_competition_files_paths()
        for (i, file_path) in enumerate(competition_files_paths):
            if i%100==0:
                message = "Sauvegarde des compétitions dans la base de donnée : %i/%i"
                self.logger.info(message, i, len(competition_files_paths))
            competition_infos = self.get_competition(file_path)
            self.db_service.add_competition(*competition_infos)
    
    
    def get_competition_files_paths(self):
        files_paths = os.listdir(self.csv_database_directory)
        files_paths.sort()
        for i in reversed(range(len(files_paths))):
            if not is_competition_file(files_paths[i]):
                files_paths.pop(i)
                continue
        return [Path(self.csv_database_directory, fp) for fp in files_paths]
    
    def get_competition(self, file_path):
        with open(file_path, 'r') as file :
            reader = csv.reader(file, dialect="unix")
            first_line = next(reader)
            (competition_name,
             simplified_competition_name,
             competition_phase,
             simplified_competition_phase,
             date_str,
             level,
             nb_competitors) = first_line
            date = datetime.fromisoformat(date_str)

            next(reader) # Deuxième ligne inutile
            
            competitor_names = list()
            competitor_categories = list()
            scores = list()
            original_values = list()
            original_points = list()
            final_types = list()
            
            valid_categories = ["K1H", "K1D", "C1H", "C1D", "C2H", "C2D", "C2M"]
            for line in reader :
                if is_number(line[2]) and is_number(line[4]) and line[1] in valid_categories : # On prend uniquement en compte les embarcations individuelles ayant un temps et des points
                    competitor_names.append(line[0])
                    competitor_categories.append(line[1])
                    scores.append(line[2])
                    if is_number(line[3]) : # Si le competiteur a une valaur
                        original_values.append(float(line[3]))
                    else :
                        original_values.append(None)
                    original_points.append(float(line[4]))
                    if len(line) == 6 :
                        final_types.append(line[5])
                    else :
                        final_types.append("")
            return (competitor_names,
                    competitor_categories,
                    competition_name,
                    simplified_competition_name,
                    competition_phase,
                    simplified_competition_phase,
                    date,
                    level,
                    final_types,
                    scores,
                    original_points,
                    original_values)
    
    
    def get_last_competition_year(self):
        try:
            last_year = max([int(file_name[:4]) for file_name in os.listdir(self.csv_database_directory)])
        except ValueError:
            last_year = 2001
        return last_year


class ExistingItemException(Exception):
    pass

def replace_chars(string_var, char_list, replace_with):
    result = string_var
    for char in char_list:
        result = result.replace(char, replace_with)
    return result

def is_number(s) :
	try :
		float(s)
		return True
	except ValueError :
		return False
    
def is_competition_file(file) :
	try :
		datetime.fromisoformat(file[:10])
		if file[-4:] == ".csv":
			return True
		else :
			return False
	except ValueError :
		return False