# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 12:42:04 2021

@author: charl
"""
import logging

import pymongo
from pymongo import UpdateOne


class DatabaseService:
    def __init__(self):
        self.logger = logging.getLogger("DatabaseService")
        self.client = pymongo.MongoClient()
        self.db = self.client["ck_db"]
    
    def competition_exists(self,
                           competition_name):
        query = {"competitionName": competition_name}
        return self.db["participations"].find_one(query)

    def add_competition(self,
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
                        original_values=None):
        query = {"competitionName": competition_name}
        if self.db["participations"].find_one(query) is not None:
            msg = "La competition '%s' comporte déjà des entrées dans la BDD"
            raise ExistingItemException(msg % competition_name)
        participation_list = list()
        for i in range(len(competitor_names)):
            competitor_name = competitor_names[i]
            competitor_category = competitor_categories[i]
            final_type = final_types[i]
            score = scores[i]
            original_point = original_points[i] if original_points is not None else None
            if original_values is not None and type(original_values[i])==float:
               original_value = original_values[i]
            else:
                original_value = None
            participation_list.append(create_participation_dict(competitor_name,
                                                                competitor_category,
                                                                competition_name,
                                                                simplified_competition_name,
                                                                competition_phase,
                                                                simplified_competition_phase,
                                                                date,
                                                                level,
                                                                final_type,
                                                                score,
                                                                original_point,
                                                                original_value))
        self.db["participations"].insert_many(participation_list)
    
    def save_participation_value(self,
                                 competitor_name,
                                 competitor_category,
                                 competition_name,
                                 value_type,
                                 value_moyenne,
                                 value_nb_comp,
                                 value_nb_nat):
        query = {"competitorName":competitor_name,
                 "competitorCategory":competitor_category,
                 "competitionName":competition_name}
        value_dic = {"points":value_moyenne,
                     "nbCompetitions":value_nb_comp,
                     "nbNationals":value_nb_nat}
        instructions = {"$set":{"values."+value_type:value_dic},
                        "$push":{"valueTypes":value_type}}
        self.db["participations"].update_one(query, instructions)
    
    def save_competition_points(self, competition_name, point_type, points):
        instructions = list()
        for dic in points:
            instructions.append(UpdateOne({"competitorName":dic["competitorName"],
                                           "competitorCategory":dic["competitorCategory"],
                                           "competitionName":competition_name},
                                          {"$set":{"points."+point_type:dic["points"]},
                                           "$push":{"pointTypes":point_type}}))
        self.db["participations"].bulk_write(instructions, ordered=False)
    
    def save_point_computing_details(self, point_computing_details):
        assert("pointType" in point_computing_details)
        assert("competitionName" in point_computing_details)
        self.db["pointComputingDetails"].insert_one(point_computing_details)
    
    def get_last_participations(self,
                                competitor_name,
                                competitor_category,
                                date,
                                value_period):
        query = {"competitorName":competitor_name,
                 "competitorCategory":competitor_category,
                 "date":{"$gt":date-value_period,
                         "$lte":date}}
        return self.db["participations"].find(query)
    
    def get_competition_participations(self, competition_name, category="all"):
        query = {"competitionName":competition_name}
        if category != "all":
            query["competitorCategory"] = category
        return self.db["participations"].find(query)
    
    def get_participations_on_period(self, starting_date, ending_date, phase=None):
        """
        Cette fonction renvoit la liste des participations entre la starting_date (exlue)
        et ending_date (inclue). Le paramètre optionnel phase permet de spécifier la phase
        maximale des participations du dernier jour.
        
        Parameters
        ----------
        starting_date : datetime.datetime
        ending_date : datetime.datetime
        phase : str, optional

        Returns
        -------
        list de dict (participations)
        """
        query = get_participations_period_query(starting_date, ending_date, phase=phase)
        return self.db["participations"].find(query)
    
    
    def get_competition_list(self, competition_date, phase=None):
        query = {"date":competition_date}
        if phase is not None:
            query["simplifiedCompetitionPhase"] = phase
        return self.db["participations"].distinct("competitionName", filter=query)
    
    def get_competitions_on_period(self, starting_date, ending_date, level="all", phase=None):
        query = get_participations_period_query(starting_date, ending_date, phase=phase)
        if level != "all":
            query["level"] = level
        return self.db["participations"].distinct("competitionName", filter=query)
    
    def get_competitors_on_period(self, starting_date, ending_date, phase=None, category=None):
        """
        Renvoit la liste des competiteurs ayant eu au moins une participation entre
        starting_date (exclue) et ending_date (inclue). Le paramètre phase permet de
        spécifier la dernière phase à prendre en compte pour la journée ending_date.
        Le paramètre category permet de spécifier si l'on souhaite uniquement une catégorie.

        Parameters
        ----------
        starting_date : datetime.datetime
        ending_date : datetime.datetime
        phase : None ou str ("qualif, "demi", finale"), optional
        category : None ou str ("K1D", "K1H", ...), optionnal

        Returns
        -------
        pymongo.command_cursor.CommandCursor
             Itérateur sur des dictionnaires de la forme {"_id":{"competitionName":"blabla",
                                                                 "competitionCategory":"K1H"},
                                                          "count":nb_participations_on_period}

        """
        
        query = get_participations_period_query(starting_date, ending_date, phase=phase)
        if category is not None:
            query["competitorCategory"] = category
        pipeline = [
            {"$match":query},
            {"$group":{"_id":{"competitorName":"$competitorName",
                              "competitorCategory":"$competitorCategory"},
                      "count":{"$sum":1}}}]
        return self.db["participations"].aggregate(pipeline)
        
    
    def copy_points(self,
                    starting_date,
                    ending_date,
                    target_point_type,
                    origin_point_type):
        query = {"date":{"$gt":starting_date, "$lte":ending_date}}
        participations = self.db["participations"].find(query)
        instructions = list()
        for participation in participations:
            instructions.append(UpdateOne({"competitorName":participation["competitorName"],
                                           "competitorCategory":participation["competitorCategory"],
                                           "competitionName":participation["competitionName"]},
                                          {"$push":{"pointTypes":target_point_type},
                                           "$set":{"points."+target_point_type:participation["points"][origin_point_type]}}))
        self.db["participations"].bulk_write(instructions, ordered=False)
    
    def get_competition_dates(self, starting_date):
        return self.db["participations"].distinct("date",
                                                  filter={"date":{"$gt":starting_date}})
    
    def get_competition_date(self, competition_name):
        return self.db["participations"].find_one({"competitionName":competition_name})["date"]
    
    def is_phase(self, competition_name, simplified_phase):
        participation = self.db["participations"].find_one({"competitionName":competition_name})
        return participation["simplifiedCompetitionPhase"] == simplified_phase


    def get_value(self,
                  competitor_name,
                  competitor_category,
                  date,
                  value_type):
        query = {"competitorName":competitor_name,
                 "competitorCategory":competitor_category,
                 "date":date,
                 "valueType":value_type}
        return self.db["values"].find_one(query)
    
    def add_value(self,
                  competitor_name,
                  competitor_category,
                  date,
                  value_type,
                  value_points,
                  nb_competitions,
                  nb_nationals):
        value = self.get_value(competitor_name, competitor_category, date, value_type)
        if value is None:
            value_dic = create_value_dict(competitor_name,
                                          competitor_category,
                                          date,
                                          value_type,
                                          value_points,
                                          nb_competitions,
                                          nb_nationals)
            self.db["values"].insert_one(value_dic)
        else:
            msg = "La valeur de type %s de %s en %s au %s existe déja."
            raise ExistingItemException(msg % (value_type, competitor_name, competitor_category, str(date)))
    
    def get_all_competition_names(self):
        all_participations = self.db["participations"].find({})
        event_name_list = list()
        for participation in all_participations:
            if participation["competitionName"] not in event_name_list:
                event_name_list.append(participation["competitionName"])
        return event_name_list
    

def create_participation_dict(competitor_name,
                              competitor_category,
                              competition_name,
                              simplified_competition_name,
                              competition_phase,
                              simplified_competition_phase,
                              date,
                              level,
                              final_type,
                              score,
                              original_point=None,
                              original_value=None):
    participation = dict()
    participation["competitorName"] = competitor_name
    participation["competitorCategory"] = competitor_category
    participation["competitionName"] = competition_name
    participation["simplifiedCompetitionName"] = simplified_competition_name
    participation["competitionPhase"] = competition_phase
    participation["simplifiedCompetitionPhase"] = simplified_competition_phase
    participation["date"] = date
    participation["level"] = level
    participation["finalType"] = final_type
    participation["score"] = score
    participation["pointTypes"] = list() if original_point is None else ["scrapping"]
    participation["valueTypes"] = list() if original_value is None else ["scrapping"]
    participation["points"] = dict() if original_point is None else {"scrapping": original_point}
    if original_value is None:
        participation["values"] = dict()
    else:
        participation["values"] = {"scrapping":{"points":original_value,
                                                "nbCompetitions":-1,
                                                "nbNationals":-1}}
    return participation

def create_value_dict(competitor_name,
                      competitor_category,
                      date,
                      value_type,
                      value_points,
                      nb_competitions,
                      nb_nationals):
    value = dict()
    value["competitorName"] = competitor_name
    value["competitorCategory"] = competitor_category
    value["date"] = date
    value["valueType"] = value_type
    value["valuePoints"] = value_points
    value["nbCompetitions"] = nb_competitions
    value["nbNationals"] = nb_nationals
    return value

def get_participations_period_query(starting_date, ending_date, phase=None):
    if phase is None:
        query = {"date":{"$gt":starting_date, "$lte":ending_date}}
    else:
        if phase == "qualif":
            authorized_phases = ["", "qualif"]
        elif phase == "demi":
            authorized_phases = ["", "qualif", "demi"]
        else:
            authorized_phases = ["", "qualif", "demi", "finale"]
        query = {"$or":[{"date":{"$gt":starting_date,
                                 "$lt":ending_date}},
                        {"date":ending_date,
                         "simplifiedCompetitionPhase":{"$in":authorized_phases}}]}
    return query


class ExistingItemException(Exception):
    pass


class UnexistingParticipationException(Exception):
    pass

if __name__ == "__main__":
    database_service = DatabaseService()
    
    #for event_name in database_service.get_all_competition_names():
    #    (event_name)
    #database_service.reset_db()
    pass