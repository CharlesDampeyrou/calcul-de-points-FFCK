# -*- coding: utf-8 -*-
"""
Created on Tue Apr  6 22:08:51 2021

@author: charl
"""

import numpy as np
import pandas as pd

def estimate_tensorial_product(scores_df,
                               participations_df,
                               iterations_first_optimization=15,
                               removing_rate=0.2,
                               iterations_final_optimization=35):
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
    for i in range(iterations_final_optimization):
        (competition_vector, competitor_vector) = improve_vectors(scores_df,
                                                                  participations_df,
                                                                  competition_vector,
                                                                  competitor_vector)
    return competition_vector, competitor_vector

def improve_vectors(scores_df,
                    participations_df,
                    competition_vector,
                    competitor_vector):
    new_competition_vector = improve_competition_vector(scores_df,
                                                        participations_df,
                                                        competitor_vector)
    new_competition_vector *= new_competition_vector.shape[0]/new_competition_vector.sum()
    new_competitor_vector = improve_competitor_vector(scores_df,
                                                      participations_df,
                                                      new_competition_vector)
    return new_competition_vector, new_competitor_vector

def improve_competition_vector(scores_df,
                               participations_df,
                               competitor_vector):
    new_competition_vector = (scores_df*participations_df).sum(axis=1)
    new_competition_vector /= np.dot(participations_df, competitor_vector)
    return new_competition_vector

def improve_competitor_vector(scores_df,
                              participations_df,
                              competition_vector):
    new_competitor_vector = (scores_df*participations_df).sum(axis=0)
    new_competitor_vector /= np.dot(competition_vector, participations_df)
    return new_competitor_vector

def remove_underperformances(scores_df,
                             participations_df,
                             competition_vector,
                             competitor_vector,
                             nb_to_remove):
    deviation = np.array(scores_df)-np.tensordot(competition_vector, competitor_vector, axes=0)
    deviation *= np.array(participations_df)
    to_remove = deviation.argsort(axis=None)[-nb_to_remove:] if nb_to_remove != 0 else []
    nb_competitors = scores_df.shape[1]
    for index in to_remove:
        i = index // nb_competitors
        j = index % nb_competitors
        participations_df.iat[i, j] = 0

def distance_to_scores(scores_df,
                       participations_df,
                       competition_vector,
                       competitor_vector):
    deviation = np.array(scores_df)-np.tensordot(competition_vector, competitor_vector, axes=0)
    deviation *= np.array(participations_df)
    return np.linalg.norm(deviation)/np.sqrt(np.array(participations_df).sum())

if __name__ == "__main__":
    sc = np.array([[90, 94, 0], [88, 0, 94], [0, 94, 94], [0, 91, 91]])
    sc_df = pd.DataFrame(data=sc,
                         index=["competition1","competition2", "competition3","competition4"],
                         columns=["competitor1", "competitor2", "competitor3"])
    p = np.array([[1,1,0],[1,0,1],[0,1,1],[0,1,1]])
    p_df = pd.DataFrame(data=p,
                        index=["competition1","competition2", "competition3","competition4"],
                        columns=["competitor1", "competitor2", "competitor3"])
    ction, ctor = estimate_tensorial_product(sc_df, p_df, removing_rate=0.2)
    