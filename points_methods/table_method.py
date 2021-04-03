# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 17:50:42 2021

@author: charl
"""

import logging
from datetime import timedelta

class PointsComputer:
    def __init__(self, point_type,
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
        self.database_service = database_service
        self.logger = logging.getLogger("points_methods.table_method")
    
    def compute_and_save_points(self, **kwargs):
        ending_date = kwargs["date"]
        phase = kwargs["phase"]
        starting_date = ending_date - self.table_competition_validity_period
        table = self.create_table(starting_date, ending_date, phase) # TODO
        (competitions_vector,
         competitor_vector) = self.compute_competition_and_competitor_vectors(table) # TODO
        for competition_name in competition_names:
            participations = self.database_service.get_competition_participations(competition_name)
            try:
                result, point_computing_details = self.compute_points(participations,
                                                                      table,
                                                                      phase) # TODO
    
    def compute_points(self, competition_names):
        pass
