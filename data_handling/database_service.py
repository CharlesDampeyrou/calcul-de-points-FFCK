# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 12:42:04 2021

@author: charl
"""
import logging
from datetime import timedelta, datetime
import time
from bson.son import SON

import pymongo
from pymongo import UpdateOne


class DatabaseService:
    def __init__(self, prod=False):
        self.logger = logging.getLogger("DatabaseService")
        self.client = pymongo.MongoClient(connect=False)
        self.db = self.client["ck_db_prod"] if prod else self.client["ck_db"]

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
        if len(participation_list) != 0:
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

    def get_ranking(self,
                    date,
                    point_type,
                    category,
                    nb_nat_min,
                    nb_comp_min,
                    value_period=timedelta(days=365)):
        """
        Fonction renvoyant la liste classée des athlètes à la date souhaitée, avec la moyenne,
        le nombre de courses dans la moyenne et le nombre de courses nationnales dans la
        moyenne

        Parameters
        ----------
        date : datetime.datetime
            date de calcul du classement
        point_type : STR
            type de points pris en comptes dans la valeur
        category : "all", "K1D", "K1H", etc. optionnal
        nb_nat_min : INT, optional
            nombre de courses nationales minimum dans la valeur. The default is 3.
        nb_comp_min : INT, optional
            nombre de courses dans la valeur. The default is 4.
        value_period : datetime.timedelta, optional
            durée de prise en compte des compétitions pour la valeur. The default is timedelta(days=365).

        Returns
        -------
        pymongo.command_cursor.CommandCursor
             Itérateur sur des dictionnaires de la forme {"_id":{"competitionName":"...",
                                                                 "competitionCategory":"..."},
                                                          "nbNat":nombre de compétitions nationales
                                                              dans la moyenne,
                                                          "nbComp":nombre de compétitions dans la
                                                              moyenne,
                                                          "moy":moyenne}
        """
        query = dict()
        if category != "all":
            query["competitorCategory"] = category
        pipeline = create_value_pipeline(query, date, value_period, point_type, nb_nat_min, nb_comp_min)
        # Classement des compétiteurs
        pipeline.append({"$sort":SON([("nbComp", -1), ("nbNat", -1), ("moy", 1)])})
        return self.db["participations"].aggregate(pipeline)


    def get_value(self,
                  competitor_name,
                  competitor_category,
                  date,
                  point_type,
                  nb_nat_min,
                  nb_comp_min,
                  value_period=timedelta(days=365)):
        query = {"competitorName":competitor_name,
                 "competitorCategory":competitor_category}
        pipeline = create_value_pipeline(query, date, value_period, point_type, nb_nat_min, nb_comp_min)
        res = list(self.db["participations"].aggregate(pipeline))
        if len(res) != 0:
            return res[0]
        return {"_id":{"competitorName":competitor_name,
                       "competitorCategory":competitor_category},
                "nbNat":0,
                "nbComp":0,
                "moy":1000}


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

    def get_competitors_on_period(self, starting_date, ending_date, phase=None, category="all"):
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
        category : str ("K1D", "K1H", ... ou "all"), optionnal

        Returns
        -------
        pymongo.command_cursor.CommandCursor
             Itérateur sur des dictionnaires de la forme {"_id":{"competitionName":"blabla",
                                                                 "competitionCategory":"K1H"},
                                                          "count":nb_participations_on_period}

        """

        query = get_participations_period_query(starting_date, ending_date, phase=phase)
        if category != "all":
            query["competitorCategory"] = category
        pipeline = [
            {"$match":query},
            {"$group":{"_id":{"competitorName":"$competitorName",
                              "competitorCategory":"$competitorCategory"},
                      "count":{"$sum":1}}}]
        return self.db["participations"].aggregate(pipeline)

    def delete_event(self, event_name):
        self.db["participations"].delete_many({"competitionName":event_name})

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

    def get_last_points_date(self, point_type):
        query = {"pointTypes":point_type}
        return self.db["participations"].find_one(query, sort=[("date",-1)])["date"]

    def get_competition_dates(self, starting_date):
        return self.db["participations"].distinct("date",
                                                  filter={"date":{"$gt":starting_date}})

    def get_competition_date(self, competition_name):
        return self.db["participations"].find_one({"competitionName":competition_name})["date"]

    def is_phase(self, competition_name, simplified_phase):
        participation = self.db["participations"].find_one({"competitionName":competition_name})
        return participation["simplifiedCompetitionPhase"] == simplified_phase


    def get_all_competition_names(self):
        all_participations = self.db["participations"].find({})
        event_name_list = list()
        for participation in all_participations:
            if participation["competitionName"] not in event_name_list:
                event_name_list.append(participation["competitionName"])
        return event_name_list

def create_value_pipeline(query,
                          date,
                          value_period,
                          point_type,
                          nb_nat_min,
                          nb_comp_min):
    query["date"] = {"$gt":date-value_period,
                     "$lte":date}
    pipeline = list()
    # Séléction des participations aux dates souhaitéeset dans la bonne catégorie
    pipeline.append({"$match":query})
    # Tri des participations selon le points
    pipeline.append({"$sort":{"points."+point_type:1}})
    # Création de la liste des compétitions nationales et régionales pour les athlètes
    pipeline.append({'$group':{
        '_id':{
            'competitorName': '$competitorName',
            'competitorCategory': '$competitorCategory'},
        'natPoints': {'$push': {'$cond': [
                    {'$in':['$level',['Nationale 3', 'Nationale 2', 'Nationale 1', 'Championnats de France']]},
                    '$points.'+point_type,
                    '$$REMOVE']}},
        'regPoints': {'$push': {'$cond': [
                    {'$eq': ['$level', 'Régional']},
                    '$points.'+point_type,
                    '$$REMOVE']}}}})
    # Separation des 3 meilleures compétitions nat et des autre compétitions
    pipeline.append({'$set': {
        'natList': {'$slice': ['$natPoints', nb_nat_min]},
        'compList': {'$concatArrays': [
                {'$slice': ['$natPoints', nb_nat_min, nb_comp_min]},
                '$regPoints']}}})
    # Tri des autres compétitions sur les 3 stages suivants
    pipeline.append({'$unwind': {
        'path': '$compList',
        'preserveNullAndEmptyArrays': True}})
    pipeline.append({"$sort":{"compList":1}})
    pipeline.append({'$group': {
        '_id': '$_id',
        'natList': {'$first': '$natList'},
        'compList': {'$push': '$compList'}}})
    # Comptage du nombre de nationales et création de la liste des courses comptants dans la moyenne
    pipeline.append({'$set': {
        'nbNat': {'$size': '$natList'},
        'moyList': {'$slice': [{'$concatArrays': ['$natList', '$compList']}, nb_comp_min]}}})
    # Création de la moyenne et comptage du nonmbre de courses dans la moyenne
    pipeline.append({'$set': {
        'nbComp': {'$size': '$moyList'},
        'moy': {'$avg': '$moyList'}}})
    pipeline.append({'$project':{
        'nbComp':1,
        'nbNat':1,
        'moy':1}})
    return pipeline

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
    db_service = DatabaseService()

    #for event_name in database_service.get_all_competition_names():
    #    (event_name)
    #database_service.reset_db()
    t0 = time.time()
    res = list(db_service.get_ranking(datetime(2021,12,18),
                                      "scrapping",
                                      "all",
                                      3,
                                      4))

    # res = db_service.get_value("Charles Dampeyrou",
    #                            "C1H",
    #                            datetime(2021,12,18),
    #                            "scrapping",
    #                            3,
    #                            4)
    print(time.time()-t0)
