# -*- coding: utf-8 -*-
"""
Created on Mon Jan 10 17:44:34 2022

@author: charl
"""
from datetime import datetime, timedelta
from random import randrange

import pandas as pd

from points_methods.skill_based_method import PointsComputer
from points_methods.tensorial_product_estimator import estimate_tensorial_product, improve_vectors, improve_competitor_vector, remove_underperformances
from data_handling.database_service import DatabaseService
from domain.value_accessor import ValueAccessor
from domain.value import ValueMaker

def random_date(start, end):
    """
    This function will return a random datetime between two datetime 
    objects.
    """
    delta = end - start
    return start + timedelta(days=randrange(delta.days))

def find_minimal_iteration_first_optim(scores_df,
                                       participations_df):
    ref_participations_df = participations_df.copy()
    _, _ = estimate_tensorial_product(scores_df, ref_participations_df)
    for first_iterations in range(5,51,5):
        participations_df_copy = participations_df.copy()
        _, _ = estimate_tensorial_product(scores_df,
                                          participations_df_copy,
                                          iterations_first_optimization=first_iterations,
                                          iterations_final_optimization=0)
        msg = "%s différences (soit %s %%) lors de la suppression des moins bonnes performances avec %s "
        msg += "iterations lors de la suppression"
        nb_differences = abs(participations_df_copy-ref_participations_df).sum().sum()
        print(msg % (nb_differences, nb_differences/participations_df_copy.sum().sum(), first_iterations))

def find_minimal_iterations(scores_df,
                            participations_df,
                            iterations_first_optimization=50,
                            removing_rate=0.2):
    participation_df_copy = participations_df.copy()
    target_competition_vector, target_competitor_vector = estimate_tensorial_product(scores_df,
                                                                                     participation_df_copy)
    target_base_time = target_competitor_vector.min()*target_competition_vector
    competition_vector = pd.Series(1.0, index=scores_df.index)
    competitor_vector = improve_competitor_vector(scores_df,
                                                  participations_df,
                                                  competition_vector)
    to_remove = int(removing_rate*participations_df.sum().sum())
    already_removed = 0
    for i in range(iterations_first_optimization):
        (competition_vector, competitor_vector) = improve_vectors(scores_df,
                                                                  participations_df,
                                                                  competition_vector,
                                                                  competitor_vector)
        to_remove_on_iteration = int((i+1)/iterations_first_optimization*to_remove) - already_removed
        remove_underperformances(scores_df,
                                 participations_df,
                                 competition_vector,
                                 competitor_vector,
                                 to_remove_on_iteration)
        already_removed += to_remove_on_iteration
    base_time = pd.Series(0.0, index=scores_df.index)
    nb_iterations = 0
    while abs(target_base_time-base_time).max()>0.01 and nb_iterations<80:
        (competition_vector, competitor_vector) = improve_vectors(scores_df,
                                                                  participations_df,
                                                                  competition_vector,
                                                                  competitor_vector)
        best_performer = competitor_vector.min()
        base_time = best_performer*competition_vector
        nb_iterations += 1
    return nb_iterations

if __name__ == "__main__":
    point_type = "skill_based"
    value_type = "skill_based_3_4"
    db_service = DatabaseService()
    Value = ValueMaker(3, 4, point_type, value_type)
    value_accessor = ValueAccessor(db_service,
                                   Value)
    
    pc = PointsComputer(point_type,
                       value_accessor,
                       db_service)
    nb_tests = 20
    start = datetime(2014,1,1)
    end = datetime(2021,12,31)
    phase = "finale"
    for i in range(nb_tests):
        competition_date = random_date(start, end)
        scores_df, participations_df = pc.create_dataframes(competition_date, phase)
        
        find_minimal_iteration_first_optim(scores_df, participations_df)
        
        # nb_iterations = find_minimal_iterations(scores_df, participations_df)
        # msg = "Nombre d'itérations avant d'obtenir le temps de base de chaque course au centième près : %s"
        # print(msg % nb_iterations)