# -*- coding: utf-8 -*-
"""
Created on Fri Feb 12 15:10:48 2021

@author: charl
"""
import logging

from points_methods.exceptions import ImpossiblePointsComputingException

class CompetitionProcessor:
    def __init__(self,
                 point_type,
                 value_accessor,
                 database_service,
                 competition_validity_period,
                 point_computer):
        self.point_type = point_type
        self.competition_validity_period = competition_validity_period
        self.database_service = database_service
        self.value_accessor = value_accessor
        self.logger = logging.getLogger("CompetitionProcessor")
        self.point_computer = point_computer
    
    def initialize_point_type(self, date, origin_points="scrapping"):
        self.logger.info("Starting the initialisation of the point type %s..." % self.point_type)
        starting_date = date-self.competition_validity_period
        self.database_service.copy_points(starting_date, date, self.point_type, origin_points)
        self.logger.info("Initialisation of the point type %s finished" % self.point_type)
    
    def compute_point_type(self, starting_date):
        self.logger.info("Starting to cumpute the %s points..." % self.point_type)
        competition_dates = self.database_service.get_competition_dates(starting_date)
        msg = "%i dates de compétitions sur lesquelles calculer les points, du %s au %s"
        self.logger.info(msg % (len(competition_dates),str(min(competition_dates)), str(max(competition_dates))))
        phases = ["qualif", "demi", "finale", ""]
        for competition_date in competition_dates:
            competition_names = list(self.database_service.get_competition_list(competition_date))
            self.logger.info("Calcul des points pour les %i compétitions du %s." % (len(competition_names),
                                                                                    str(competition_date)))
            for phase in phases:
                for competition_name in competition_names:
                    if self.database_service.is_phase(competition_name, phase):
                        self.value_accessor.compute_and_save_competition_values(competition_name,
                                                                                phase)
                for competition_name in competition_names:
                    if self.database_service.is_phase(competition_name, phase):
                        self._compute_and_save_points(competition_name)
            
    
    def _compute_and_save_points(self, competition_name):
        self.logger.debug("Calcul et sauvegarde des points de la course %s", competition_name)
        participations = self.database_service.get_competition_participations(competition_name)
        try :
            result, point_computing_details = self.point_computer.compute_points(participations)
        except ImpossiblePointsComputingException as e:
            msg = "Impossible de calculer les points de la competition %s, raison : %s, erreur : %s"
            self.logger.error(msg % (competition_name, str(e), str(type(e))))
        else:
            self.database_service.save_competition_points(competition_name,
                                                          self.point_type,
                                                          result)
            self.database_service.save_point_computing_details(point_computing_details)
            