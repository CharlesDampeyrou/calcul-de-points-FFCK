# -*- coding: utf-8 -*-
"""
Created on Tue Dec 14 23:11:02 2021

@author: charl
"""

from datetime import timedelta
from pathlib import Path

from tools.init_logging import load_logging_configuration
from data_handling.database_service import DatabaseService
from data_handling.csv_data_service import CsvDataService
from domain.value import ValueMaker
from domain.competition_processor import CompetitionProcessor
from domain.value_accessor import ValueAccessor
from points_methods.skill_based_method import PointsComputer


if __name__ == "__main__":
    logging_file = Path(Path.cwd(),"tools", "logging.yml")
    load_logging_configuration(logging_file)
    # point_type = "skill_based"
    # value_type = "3_4_skill_based"
    
    point_type = "skill_based_calculation_initialized_2014_01_01"
    value_type = "3_4_skill_based_calculation_initialized_2014_01_01"

    nb_nat_min = 3
    nb_comp_min = 4
    competition_validity_period = timedelta(days=365)
    
    database_service = DatabaseService(prod=False)
    
    csv_data_service = CsvDataService(database_service)
    
    csv_data_service.update_database()

    Value = ValueMaker(nb_nat_min, nb_comp_min, point_type, value_type)
    value_accessor = ValueAccessor(database_service, Value, competition_validity_period=competition_validity_period)
    point_computer = PointsComputer(point_type, value_accessor, database_service)
    competition_processor = CompetitionProcessor(database_service,
                                                 point_computer)
    competition_processor.update_point_type()