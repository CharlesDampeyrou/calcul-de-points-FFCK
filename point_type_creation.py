# -*- coding: utf-8 -*-
"""
Created on Thu Feb 18 11:57:08 2021

@author: charl
"""
from datetime import datetime, timedelta
from pathlib import Path

from tools.init_logging import load_logging_configuration
from data_handling.database_service import DatabaseService
from domain.value import ValueMaker
from domain.competition_processor import CompetitionProcessor
from domain.value_accessor import ValueAccessor
#from points_methods.current_method import PointsComputer as CMPointsComputer
from points_methods.skill_based_method import PointsComputer as SBPointsComputer


if __name__ == "__main__":
    logging_file = Path(Path.cwd(),"tools", "logging.yml")
    load_logging_configuration(logging_file)
    point_type = "skill_based_calculation_initialized_2014_01_01"
    value_type = "3_4_skill_based_calculation_initialized_2014_01_01"
    # point_type = "skill_based_calculation_initialized_2002_01_03"
    # value_type = "1_4_skill_based_calculation_initialized_2002_01_03"
    PointsComputer = SBPointsComputer
    # point_type = "original_calculation_initialized_2014_01_01"
    # value_type = "3_4_original_calculation_initialized_2014_01_01"
    #PointsComputer = CMPointsComputer
    nb_nat_min = 3
    nb_comp_min = 4
    competition_validity_period = timedelta(days=365)
    starting_date = datetime(2014, 1, 1) 
    
    database_service = DatabaseService()
    Value = ValueMaker(nb_nat_min, nb_comp_min, point_type, value_type)
    value_accessor = ValueAccessor(database_service, Value, competition_validity_period=competition_validity_period)
    point_computer = PointsComputer(point_type, value_accessor, database_service)
    competition_processor = CompetitionProcessor(database_service,
                                                 point_computer)
    competition_processor.initialize_point_type(starting_date)
    competition_processor.compute_point_type(starting_date)