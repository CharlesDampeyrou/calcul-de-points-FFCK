# -*- coding: utf-8 -*-
"""
Created on Tue Feb 23 18:05:23 2021

@author: charl
"""
import logging
import unidecode

import pymongo

from data_handling.database_service import DatabaseService

class DatabaseManagementService:
    def __init__(self):
        self.logger = logging.getLogger("DatabaseService")
        self.client = pymongo.MongoClient()
        self.db = self.client["ck_db"]
        self.db_service = DatabaseService()
    
    def reset_db(self):
        response = input("Delete the complete database ? (y/n)\n")
        if response == "y":
            self.db["participations"].drop()
            self.db["values"].drop()
            self.db["pointComputingDetails"].drop()
    
    def create_indexes(self):
        self.db["participations"].create_index([("competitorCategory",1),
                                                ("competitorName",1),
                                                ("competition_name",1)])
        self.db["participations"].create_index([("competitorCategory",1),
                                                ("competitorName",1),
                                                ("date",1)])
        self.db["participations"].create_index("competitionName")
        self.db["participations"].create_index("date")
        self.db["values"].create_index("date")
        self.db["values"].create_index([("valueType",1),
                                        ("date",1),
                                        ("competitorCategory",1),
                                        ("competitorName",1)])
    
    def create_backup(self, backup_name):
        backup_db = self.client[backup_name]
        participations = self.db["participations"].find({})
        point_computing_details = list(self.db["pointComputingDetails"].find({}))
        values = list(self.db["values"].find({}))
        backup_db["participations"].insert_many(list(participations))
        if len(point_computing_details) != 0:
            backup_db["pointComputingDetails"].insert_many(point_computing_details)
        if len(values) != 0:
            backup_db["values"].insert_many(values)
    
    def restore_db(self, backup_name):
        self.db["participations"].drop()
        self.db["values"].drop()
        self.db["pointComputingDetails"].drop()
        backup_db = self.client[backup_name]
        participations = backup_db["participations"].find({})
        values = list(backup_db["values"].find({}))
        point_computing_details = list(backup_db["pointComputingDetails"].find({}))
        self.db["participations"].insert_many(list(participations))
        if len(values) != 0:
            self.db["values"].insert_many(values)
        if len(point_computing_details) != 0:
            self.db["pointComputingDetails"].insert_many(point_computing_details)
        self.create_indexes()
    
    def delete_point_type(self, point_type): 
        self.db["participations"].update_many({},
                                              {"$pull":{"pointTypes":point_type},
                                               "$unset":{"points."+point_type:""}})
        self.db["values"].delete_many({"pointType":point_type})
        self.db["pointComputingDetails"].delete_many({"pointType":point_type})
    
    def delete_value_type(self, value_type): 
        self.db["participations"].update_many({},
                                              {"$pull":{"valueTypes":value_type},
                                               "$unset":{"values."+value_type:""}})
        self.db["values"].delete_many({"valueType":value_type})
        self.db["pointComputingDetails"].delete_many({"pointType":value_type})
    
    def get_point_types(self):
        return self.db["participations"].distinct("pointTypes")
    
    def get_value_types(self):
        values = self.db["participations"].distinct("valueTypes")
        for value in self.db["values"].distinct("valueTypes"):
            if value not in values:
                values.append(value)
        return values
        
    def delete_event(self, event_name):
        self.db["participations"].delete_many({"competitionName":event_name})
    
    def delete_team_events(self):
        event_name_list = self.db_service.get_all_competition_names()
        for event_name in event_name_list:
            if is_team_event(event_name):
                response = input("supprimer l'évènement %s ? (o/n)\n" % event_name)
                if response == "o":
                    self.delete_event(event_name)
    
    def replace_and_delete_unwanted_categories(self):
        authorized_categories = ["C1D", "C1H", "C2D", "C2H", "C2M", "K1D", "K1H"]
        for cat in authorized_categories:
            catM = cat + "M"
            self.db["participations"].update_many({"competitorCategory":catM},
                                                  {"$set":{"competitorCategory":cat}})
            self.db["values"].update_many({"competitorCategory":catM},
                                          {"$set":{"competitorCategory":cat}})
        self.db["participations"].delete_many({"competitorCategory":{"$nin":authorized_categories}})
        self.db["values"].delete_many({"competitorCategory":{"$nin":authorized_categories}})
    
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
        self.delete_team_events()
        self.replace_and_delete_unwanted_categories()
        self.delete_duplicated_participations()
        self.create_indexes()
    
    def get_duplicated_participations(self):
        pipeline = [{"$group":{"_id":{"competitorName":"$competitorName",
                                       "competitorCategory":"$competitorCategory",
                                       "competitionName":"$competitionName"},
                                "count":{"$sum":1},
                                "points":{"$addToSet":"$points.scrapping"}}}]
        return self.db["participations"].aggregate(pipeline, allowDiskUse=True)


def is_team_event(event_name):
    event_name_simplified = unidecode.unidecode(event_name).lower()
    return "equipe" in event_name_simplified or "patrouille" in event_name_simplified

if __name__ == "__main__":
    db_management_service = DatabaseManagementService()