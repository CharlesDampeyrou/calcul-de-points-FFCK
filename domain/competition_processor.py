# -*- coding: utf-8 -*-
"""
Created on Fri Feb 12 15:10:48 2021

@author: charl
"""
import logging

class CompetitionProcessor:
    def __init__(self,
                 database_service,
                 point_computer):
        self.database_service = database_service
        self.point_computer = point_computer
        self.logger = logging.getLogger("CompetitionProcessor")
    
    def initialize_point_type(self, date, origin_points="scrapping"):
        self.logger.info("Starting the initialisation of the point type %s..." % self.point_computer.point_type)
        self.point_computer.initialize(date, origin_points=origin_points)
        self.logger.info("Initialisation of the point type %s finished" % self.point_computer.point_type)
    
    def compute_point_type(self, starting_date):
        self.initialize_point_type(starting_date)
        self.logger.info("Starting to cumpute the %s points..." % self.point_computer.point_type)
        competition_dates = self.database_service.get_competition_dates(starting_date)
        msg = "%i dates de compétitions sur lesquelles calculer les points, du %s au %s"
        self.logger.info(msg % (len(competition_dates),str(min(competition_dates)), str(max(competition_dates))))
        phases = ["qualif", "demi", "finale", ""]
        for competition_date in competition_dates:
            self.logger.info("Calcul des points pour les compétitions du %s." % str(competition_date))
            for phase in phases:
                competition_names = list(self.database_service.get_competition_list(competition_date,
                                                                                    phase=phase))
                
                self.point_computer.compute_and_save_points(competition_names, phase) if competition_names else None
                # La méthode n'est pas appelée si la liste est vide