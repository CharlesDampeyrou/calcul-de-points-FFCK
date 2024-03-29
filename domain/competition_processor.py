# -*- coding: utf-8 -*-
"""
Created on Fri Feb 12 15:10:48 2021

@author: charl
"""
import logging
from datetime import datetime


class CompetitionProcessor:
    def __init__(self,
                 database_service,
                 point_computer):
        self.db_service = database_service
        self.point_computer = point_computer
        self.logger = logging.getLogger("CompetitionProcessor")

    def initialize_point_type(self, date, origin_points="scrapping"):
        self.logger.info("Starting the initialisation of the point type %s..." %
                         self.point_computer.point_type)
        self.point_computer.initialize(date=date, origin_points=origin_points)
        self.logger.info("Initialisation of the point type %s finished" %
                         self.point_computer.point_type)

    def compute_point_type(self, starting_date):
        self.logger.info("Starting to cumpute the %s points..." %
                         self.point_computer.point_type)
        competition_dates = self.db_service.get_competition_dates(
            starting_date)
        if len(competition_dates) == 0:
            self.logger.info(
                "Pas de nouvelles compétitions pour lesquelles calculer des points")
            return
        msg = "%i dates de compétitions sur lesquelles calculer les points, du %s au %s"
        self.logger.info(msg % (len(competition_dates), str(
            min(competition_dates)), str(max(competition_dates))))
        phases = ["qualif", "demi", "finale", ""]
        for competition_date in competition_dates:
            self.logger.info(
                "Calcul des points pour les compétitions du %s." % str(competition_date))
            for phase in phases:
                competition_names = list(self.db_service.get_competition_list(competition_date,
                                                                              phase=phase))
                if competition_names:  # La méthode n'est pas appelée si la liste est vide
                    self.point_computer.compute_and_save_points(competition_names=competition_names,
                                                                phase=phase,
                                                                competition_date=competition_date,
                                                                force_value_computing=True)

    def update_point_type(self, default_starting_date=datetime(2012, 1, 1)):
        self.logger.info("Mise à jour des points %s" %
                         self.point_computer.point_type)
        update_starting_date = self.db_service.get_last_points_date(
            self.point_computer.point_type)
        if update_starting_date is None:
            update_starting_date = default_starting_date
            self.initialize_point_type(update_starting_date)
        self.compute_point_type(update_starting_date)
