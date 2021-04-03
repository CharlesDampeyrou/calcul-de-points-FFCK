# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:34:04 2021

@author: charl
"""

import logging

import numpy as np

from points_methods.utils import calcul_pen_tps_course, add_penalties, calcul_malus_phase_and_div
from points_methods.utils import add_A_B_penality, correct_negative_points
from points_methods.exceptions import NoCompetitorException, NotEnoughCompetitorException
from points_methods.exceptions import ImpossiblePointsComputingException

class PointsComputer:
    def __init__(self, point_type, value_accessor, database_service):
        self.coef_inter_cat = {"K1H":1, "C1H":1.05, "C1D":1.2, "K1D":1.13, "C2H":1.1, "C2D":1.3, "C2M":1.2}
        self.point_type = point_type
        self.value_type = value_accessor.value_type
        self.value_accessor = value_accessor
        self.database_service = database_service
        self.logger = logging.getLogger("points_methods.classic_method")
    
    def compute_and_save_points(self, competition_names, phase):
        for competition_name in competition_names:
            self.value_accessor.compute_and_save_competition_values(competition_name, phase)

        for competition_name in competition_names:
            self.logger.debug("Calcul et sauvegarde des points de la course %s", competition_name)
            participations = self.database_service.get_competition_participations(competition_name)
            try :
                result, point_computing_details = self.compute_points(participations)
            except ImpossiblePointsComputingException as e:
                msg = "Impossible de calculer les points de la competition %s, raison : %s, erreur : %s"
                self.logger.error(msg % (competition_name, str(e), str(type(e))))
            else:
                self.database_service.save_competition_points(competition_name,
                                                              self.point_type,
                                                              result)
                self.database_service.save_point_computing_details(point_computing_details)
    
    def initialize(self, date, origin_points="scrapping"):
        starting_date = date-self.value_accessor.value_period
        self.database_service.copy_points(starting_date, date, self.point_type, origin_points)

    def compute_points(self, participations):
        participations = list(participations)
        # Levée d'une Exception s'il n'y a aucun compétiteur
        if len(participations) == 0:
            raise NoCompetitorException("Pas de compétiteurs sur la course")
        self.logger.info("Calcul des points de la course : " + participations[0]["competitionName"])
        
        
        
        ######## Calcul du temps scratch
        self.calcul_tps_scratch(participations)


        ######## Calcul du temps de base
        tps_base, pen_manque_competiteurs = self.calcul_tps_base(participations)


        ####### Calcul du nombre de points
        self.calcul_points(participations, tps_base)
        add_penalties(participations, pen_manque_competiteurs)


        ####### Calcul des pénalités de course pour les temps scratch trop faibles ou trop élevés
        pen_tps_course = calcul_pen_tps_course(participations) 
        add_penalties(participations, pen_tps_course) 


        ####### Calcul du coefficient correcteur
        coef_correcteur, ratio_points_verts = self.calcul_coef_correcteur(participations)
        multiply_by_coef(participations, coef_correcteur)


        ####### Ajout du malus de phase et de division
        penalite_phase_division = calcul_malus_phase_and_div(participations)
        add_penalties(participations, penalite_phase_division)
        
        
        ####### Ajout du malus de finale A/B
        add_A_B_penality(participations)
        

        ####### Verification que les points sont positifs
        correct_negative_points(participations)
        
        ######## Création des métadonnées
        metadata = {"competitionName":participations[0]["competitionName"],
                    "date":participations[0]["date"],
                    "simplifiedCompetitionPhase":participations[0]["simplifiedCompetitionPhase"],
                    "level":participations[0]["level"],
                    "pointType":self.point_type,
                    "valueType":self.value_type,
                    "tpsBase":tps_base,
                    "penManqueCompetiteur":pen_manque_competiteurs,
                    "penTpsCourse":pen_tps_course,
                    "coefCorrecteur":coef_correcteur,
                    "penalitePhasedivision":penalite_phase_division}
        points = extract_points(participations)
        return points, metadata

    def calcul_tps_scratch(self, participations):
        for participation in participations:
            coef = self.coef_inter_cat[participation["competitorCategory"]]
            participation["tpsScratch"] = participation["score"]/coef

    def calcul_tps_base(self, participations):
        # Recherche des 10 meilleurs scores
        valeur_max = self.get_valeur_max(participations)
        meilleurs_participations = self.get_meilleurs_participations(participations,
                                                                     valeur_max)
        if len(meilleurs_participations) < 5:
            msg = "La course %s comporte des points mais n'a pas assez de competiteurs pour avoir des "
            msg += "points. %i temps fictifs pour %i competiteurs"
            raise NotEnoughCompetitorException(msg % (participations[0]["competitionName"],
                                                      len(meilleurs_participations),
                                                      len(participations)))
        pen_manque_competiteurs = 0
        if len(meilleurs_participations) < 10:
            pen_manque_competiteurs = 20*(10-len(meilleurs_participations))

        #calcul des temps fictifs
        tps_fictifs = self.calcul_tps_fictif(meilleurs_participations)

        # Suppression des 2 temps les plus éloignés
        ecart_moyenne = np.absolute(tps_fictifs-np.mean(tps_fictifs))
        nb_comp_tps_base = min(8, len(meilleurs_participations))
        indices_tps_base = np.argsort(ecart_moyenne)[:nb_comp_tps_base]
        tps_base = tps_fictifs[indices_tps_base].mean()
        return tps_base, pen_manque_competiteurs

    def get_valeur_max(self, participations):
        level = participations[0]["level"]
        if level == "Nationale 1":
            valeur_max = 150
        elif level == "Nationale 2":
            valeur_max = 300
        else:
            valeur_max = 500
        return valeur_max

    def get_meilleurs_participations(self, participations, valeur_max):
        meilleurs = list()
        participations.sort(key=(lambda x:x["tpsScratch"]))
        for participation in participations:
            if participation["values"][self.value_type]["points"] < valeur_max: #TODO : vrai comparaison de valeurs ?
                meilleurs.append(participation)
                if len(meilleurs) == 10:
                    break
        return meilleurs

    def calcul_tps_fictif(self, meilleurs_participations):
        temps_fictifs = list()
        for participation in meilleurs_participations:
            tps_scratch = participation["tpsScratch"]
            moyenne = participation["values"][self.value_type]["points"]
            temps_fictifs.append(1000*tps_scratch/(moyenne+1000))
        return np.array(temps_fictifs)
    
    def calcul_points(self ,participations, tps_base):
        for participation in participations:
            competitor_points = 1000*(participation["tpsScratch"]-tps_base)/tps_base
            participation["points"] = competitor_points

    def calcul_coef_correcteur(self, participations):
        pts_initiaux = 0
        pts_course = 0
        pts_verts = 0
        for participation in participations:
            competitor_points = participation["points"]
            competitor_value = participation["values"][self.value_type]["points"]
            is_ranked = participation["values"][self.value_type]["nbCompetitions"]>0
            if is_ranked and abs(competitor_points - competitor_value)<50:
                pts_initiaux += competitor_value
                pts_course += competitor_points
            pts_verts += 1 if competitor_points<competitor_value else 0
        if pts_course == 0:
            return 1
        ratio_points_verts = pts_verts/len(participations)
        return pts_initiaux/pts_course, ratio_points_verts


def multiply_by_coef(participations, COEF):
    for participation in participations:
        participation["points"]*=COEF

def extract_points(participations):
    points = list()
    for participation in participations:
        points.append({"competitorName":participation["competitorName"],
                       "competitorCategory":participation["competitorCategory"],
                       "points":participation["points"]})
    return points