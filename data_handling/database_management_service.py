# -*- coding: utf-8 -*-
"""
Created on Tue Feb 23 18:05:23 2021

@author: charl
"""
import logging
import unidecode
from pathlib import Path

import pymongo
import pickle

from data_handling.database_service import DatabaseService

class DatabaseManagementService:
    def __init__(self):
        self.logger = logging.getLogger("DatabaseManagementService")
        self.client = pymongo.MongoClient()
        self.db = self.client["ck_db"]
        self.db_service = DatabaseService()
    
    def reset_db(self):
        response = input("Delete the complete database ? (y/n)\n")
        if response == "y":
            self.db["participations"].drop()
            self.db["pointComputingDetails"].drop()
    
    def create_indexes(self):
        self.logger.info("Mise à jour des indexes pour la base de données")
        self.db["participations"].create_index([("competitorCategory",1),
                                                ("competitorName",1),
                                                ("competition_name",1)])
        self.db["participations"].create_index([("competitorCategory",1),
                                                ("competitorName",1),
                                                ("date",1)])
        self.db["participations"].create_index("competitionName")
        self.db["participations"].create_index([("date",1),
                                                ("competitionName",1)])
        self.db["participations"].create_index([("date",1),
                                                ("competitorCategory",1),
                                                ("competitorName",1)])
    
    def create_backup(self, backup_name):
        backup_db = self.client[backup_name]
        participations = self.db["participations"].find({})
        point_computing_details = list(self.db["pointComputingDetails"].find({}))
        backup_db["participations"].insert_many(list(participations))
        if len(point_computing_details) != 0:
            backup_db["pointComputingDetails"].insert_many(point_computing_details)
            
    def restore_db(self, backup_name):
        self.db["participations"].drop()
        self.db["pointComputingDetails"].drop()
        backup_db = self.client[backup_name]
        participations = backup_db["participations"].find({})
        point_computing_details = list(backup_db["pointComputingDetails"].find({}))
        self.db["participations"].insert_many(list(participations))
        if len(point_computing_details) != 0:
            self.db["pointComputingDetails"].insert_many(point_computing_details)
        self.create_indexes()
    
    def delete_point_type(self, point_type): 
        self.db["participations"].update_many({},
                                              {"$pull":{"pointTypes":point_type},
                                               "$unset":{"points."+point_type:""}})
        self.db["pointComputingDetails"].delete_many({"pointType":point_type})
    
    def delete_value_type(self, value_type): 
        self.db["participations"].update_many({},
                                              {"$pull":{"valueTypes":value_type},
                                               "$unset":{"values."+value_type:""}})
        self.db["pointComputingDetails"].delete_many({"pointType":value_type})
    
    def get_point_types(self):
        return self.db["participations"].distinct("pointTypes")
    
    def get_value_types(self):
        values = self.db["participations"].distinct("valueTypes")
        return values
        
    def delete_event(self, event_name):
        self.db["participations"].delete_many({"competitionName":event_name})
    
    def delete_team_events(self):
        event_name_list = self.db_service.get_all_competition_names()
        team_event_classifier = TeamEventClassifier()
        for event_name in event_name_list:
            if possible_team_event(event_name):
                if team_event_classifier.is_team_event(event_name):
                    self.logger.info("Suppression de l'évènement %s", event_name)
                    self.delete_event(event_name)
        team_event_classifier.save()
    
    def replace_and_delete_unwanted_categories(self):
        authorized_categories = ["C1D", "C1H", "C2D", "C2H", "C2M", "K1D", "K1H"]
        for cat in authorized_categories:
            catM = cat + "M"
            self.db["participations"].update_many({"competitorCategory":catM},
                                                  {"$set":{"competitorCategory":cat}})
        self.db["participations"].delete_many({"competitorCategory":{"$nin":authorized_categories}})
    
    def delete_duplicated_participations(self):
        pipeline = [{"$group":{"_id":{"competitorName":"$competitorName",
                                       "competitorCategory":"$competitorCategory",
                                       "competitionName":"$competitionName"},
                                "count":{"$sum":1},
                                "points":{"$addToSet":"$points.scrapping"}}}]
        participations = self.db["participations"].aggregate(pipeline, allowDiskUse=True)
        for p in participations:
            if p["count"]>1:
                competitor_name = p["_id"]["competitorName"]
                competitor_category = p["_id"]["competitorCategory"]
                competition_name = p["_id"]["competitionName"]
                points = min(p["points"])
                query = {"competitorName":competitor_name,
                         "competitorCategory":competitor_category,
                         "competitionName":competition_name,
                         "points.scrapping":points}
                self.db["participations"].delete_one(query)
    
    def clean_database(self):
        self.logger.info("Suppression des catégories non souhaitées")
        self.replace_and_delete_unwanted_categories()
        self.logger.info("Suppression des courses par équipes")
        self.delete_team_events()
        self.logger.info("Suppression des participations enregistrées en double")
        self.delete_duplicated_participations()
        self.create_indexes()
    
    def get_duplicated_participations(self):
        pipeline = [{"$group":{"_id":{"competitorName":"$competitorName",
                                       "competitorCategory":"$competitorCategory",
                                       "competitionName":"$competitionName"},
                                "count":{"$sum":1},
                                "points":{"$addToSet":"$points.scrapping"}}}]
        return self.db["participations"].aggregate(pipeline, allowDiskUse=True)


def possible_team_event(event_name):
    event_name_simplified = unidecode.unidecode(event_name).lower()
    return "equipe" in event_name_simplified or "patrouille" in event_name_simplified

class TeamEventClassifier:
    def __init__(self):
        self.logger = logging.getLogger("TeamEventClassifier")
        self.pkl_file_path = Path(Path.cwd(), "data_handling", "team_event_classification.pkl")
        (self.team_events, self.not_team_events) = self.load_pickle_file()
    
    def load_pickle_file(self):
        try:
            with open(self.pkl_file_path, 'rb') as file:
                (team_events, not_team_events) = pickle.load(file)
        except FileNotFoundError:
            msg = "Attention : pas de fichier trouvé pour la suppression des courses par équipes."
            msg += " ('%s')" % str(self.pkl_file_path) 
            self.logger.warning(msg)
            team_events = list()
            not_team_events = list()
        return team_events, not_team_events
    
    def is_team_event(self, event_name):
        if event_name in self.team_events:
            return True
        elif event_name in self.not_team_events:
            return False
        response = input("supprimer l'évènement %s ? (o/n)\n" % event_name)
        if response == "o":
            self.team_events.append(event_name)
            return True
        elif response == "n":
            self.not_team_events.append(event_name)
            return False
        else :
            self.logger.error("Entrée non reconnue, veuillez recommencer")
            return self.is_team_event(event_name)
    
    def save(self):
        with open(self.pkl_file_path, 'wb') as file:
            to_save = (self.team_events,
                       self.not_team_events)
            pickle.dump(to_save, file)
    
    

if __name__ == "__main__":
    db_management_service = DatabaseManagementService()