# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 17:50:42 2021

@author: charl
"""

import logging
from datetime import timedelta

import pandas as pd

from points_methods.exceptions import ImpossiblePointsComputingException, NoCompetitorException
from points_methods.tensorial_product_estimator import estimate_tensorial_product
from points_methods.utils import calcul_pen_tps_course, add_penalties, calcul_malus_phase_and_div
from points_methods.utils import add_A_B_penality, calcul_points, calcul_tps_scratch, extract_points

class PointsComputer:
    def __init__(self,
                 point_type,
                 value_accessor,
                 database_service,
                 table_competition_validity_period=timedelta(days=365)):
        self.coef_inter_cat = {"K1H":1,
                               "C1H":1.05,
                               "C1D":1.2,
                               "K1D":1.13,
                               "C2H":1.1,
                               "C2D":1.3,
                               "C2M":1.2}
        self.table_competition_validity_period = table_competition_validity_period
        self.point_type = point_type
        self.value_accessor = value_accessor
        self.database_service = database_service
        self.logger = logging.getLogger("points_methods.skill_based_method")
    
    def initialize(self, **kwargs):
        pass # Pas d'initialisation nécessaire
    
    def compute_and_save_points(self, **kwargs):
        competition_names = kwargs["competition_names"]
        competition_date = kwargs["competition_date"]
        phase = kwargs["phase"]
        force_value_computing = kwargs.get("force_value_computing")
        scores_df, participations_df = self.create_dataframes(competition_date, phase)
        (competitions_vector,
         skills_vector) = estimate_tensorial_product(scores_df,
                                                     participations_df)
        if force_value_computing:
            for competition_name in competition_names:
                self.value_accessor.compute_and_save_competition_values(competition_name, phase)
        for competition_name in competition_names:
            participations = self.database_service.get_competition_participations(competition_name)
            try:
                result, point_computing_details = self.compute_points(participations,
                                                                      competitions_vector,
                                                                      skills_vector)
            except ImpossiblePointsComputingException as e:
                msg = "Impossible de calculer les points de la competition %s, raison : %s, erreur : %s"
                self.logger.error(msg % (competition_name, str(e), str(type(e))))
            else:
                self.database_service.save_competition_points(competition_name,
                                                              self.point_type,
                                                              result)
                self.database_service.save_point_computing_details(point_computing_details) 
    
    def compute_points(self,
                       participations,
                       competitions_vector,
                       skills_vector): 
        participations = list(participations)
        # Levée d'une Exception s'il n'y a aucun compétiteur
        if len(participations) == 0:
            raise NoCompetitorException("Pas de compétiteurs sur la course")
        competition_name = participations[0]["competitionName"]
        self.logger.info("Calcul des points de la course : " + participations[0]["competitionName"])
        
        
        ######## Calcul du temps scratch
        calcul_tps_scratch(participations, self.coef_inter_cat)

        ######## Calcul du temps de base
        tps_base = self.calcul_tps_base(competition_name,
                                        competitions_vector,
                                        skills_vector)

        ####### Calcul du nombre de points
        calcul_points(participations, tps_base)

        ####### Calcul des pénalités de course pour les temps scratch trop faibles ou trop élevés
        pen_tps_course = calcul_pen_tps_course(participations) 
        add_penalties(participations, pen_tps_course) 

        ####### Ajout du malus de phase et de division
        penalite_phase_division = calcul_malus_phase_and_div(participations)
        add_penalties(participations, penalite_phase_division)
        
        ####### Ajout du malus de finale A/B
        add_A_B_penality(participations)
        
        ######## Création des métadonnées
        metadata = {"competitionName":participations[0]["competitionName"],
                    "date":participations[0]["date"],
                    "simplifiedCompetitionPhase":participations[0]["simplifiedCompetitionPhase"],
                    "level":participations[0]["level"],
                    "pointType":self.point_type,
                    "tpsBase":tps_base,
                    "coefficientCourse":competitions_vector[competition_name],
                    "bestCompetitorSkill":skills_vector.min(),
                    "penTpsCourse":pen_tps_course,
                    "penalitePhasedivision":penalite_phase_division}
        points = extract_points(participations)
        return points, metadata
    
    def calcul_tps_scratch(self, participations):
        for participation in participations:
            coef = self.coef_inter_cat[participation["competitorCategory"]]
            participation["tpsScratch"] = participation["score"]/coef
    
    def calcul_tps_base(self,
                        competition_name,
                        competitions_vector,
                        skills_vector):
        return competitions_vector[competition_name]*skills_vector.min()
    
    def create_dataframes(self, competition_date, phase):
        starting_date = competition_date - self.table_competition_validity_period
        competitors_cursor = self.database_service.get_competitors_on_period(starting_date,
                                                                             competition_date,
                                                                             phase=phase)
        competitors, nb_participations = get_competitors_from_cursor(competitors_cursor)
        competitions = list(self.database_service.get_competitions_on_period(starting_date,
                                                                             competition_date,
                                                                             phase=phase))
        scores_df = pd.DataFrame(0, columns=competitors, index=competitions, dtype=float)
        participations_df = pd.DataFrame(0, columns=competitors, index=competitions)
        participations = self.database_service.get_participations_on_period(starting_date,
                                                                            competition_date,
                                                                            phase=phase)
        for participation in participations:
            competitor = (participation["competitorName"], participation["competitorCategory"])
            competition_name = participation["competitionName"]
            score = participation["score"]
            category = participation["competitorCategory"]
            scores_df.at[competition_name, competitor] = score/self.coef_inter_cat[category]
            participations_df.at[competition_name, competitor] = 1
        return scores_df, participations_df

def get_competitors_from_cursor(cursor):
    competitors = list()
    nb_participations = list()
    for elt in cursor:
        competitors.append((elt["_id"]["competitorName"], elt["_id"]["competitorCategory"]))
        nb_participations.append(elt["count"])
    return competitors, nb_participations

if __name__ == "__main__":
    from data_handling.database_service import DatabaseService
    db_service = DatabaseService()
    point_type = "to_remove"
    point_computer = PointsComputer(point_type, db_service)
