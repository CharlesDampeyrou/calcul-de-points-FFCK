import logging
from datetime import timedelta
from tqdm import tqdm

import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder


class ConvMethodDataPreparator:
    def __init__(self, db_service, competition_table_period=timedelta(days=365)):
        self.db_service = db_service
        self.logger = logging.getLogger("data_handling.conv_method_data_prep")
        self.competition_table_period = competition_table_period

    def get_competition_arrays_over_period(self, starting_date, ending_date, normalize_scores=True):
        """
        Returns the arrays representing the scores & categories and the mask for the given period. List of tuples (data, mask), data represents the scores concatenated with an encoding of the categories, in a np.array of shape (6, nb_competitions, nb_competitors). mask is an indicator dataframe of the presence of the competitors at the given competitions, np.array of shape (nb_competitions, nb_competitors).
        if normalize_scores, the scores are divided by 90.
        """
        dataframes_list = self.get_competition_dataframes_over_period(starting_date, ending_date)
        res = list()
        for (scores_df, participations_df) in dataframes_list:
            data, mask = convert_competitions_dataframes_to_arrays(scores_df, participations_df, normalize_scores=normalize_scores)
            res.append((data, mask))
        return res

    def get_competition_dataframes_over_period(self, starting_date, ending_date):
        """
        Returns the dataframes representing the scores and participations for the given period. List of tuples (df_scores, df_participations), df_scores represents the scores, in a pd.dataframe with competitions as row ids, and competitors as column ids. df_participation is an indicator dataframe of the presence of the competitors at the given competitions.
        """
        table_start_dates = self.db_service.get_competition_dates(
            starting_date, ending_date - self.competition_table_period
        )
        phases = ["qualif", "demi", "finale", ""]
        res_list = []
        self.logger.info("Transformation des competitions en DataFrames par période...")
        for table_start_date in tqdm(list(table_start_dates)):
            for phase in phases:
                competition_names = list(
                    self.db_service.get_competition_list(table_start_date, phase=phase)
                )
                if (
                    competition_names
                ):  # La méthode n'est pas appelée si la liste est vide
                    competitors_cursor = self.db_service.get_competitors_on_period(
                        table_start_date, table_start_date+self.competition_table_period, phase=phase
                    )
                    competitors, nb_participations = get_competitors_from_cursor(competitors_cursor)
                    competitions = list(
                        self.db_service.get_competitions_on_period(
                            table_start_date, table_start_date+self.competition_table_period, phase=phase
                        )
                    )
                    scores_df = pd.DataFrame(
                        0, columns=competitors, index=competitions, dtype=float
                    )
                    participations_df = pd.DataFrame(0, columns=competitors, index=competitions)
                    participations = self.db_service.get_participations_on_period(
                        table_start_date, table_start_date+self.competition_table_period, phase=phase
                    )
                    for participation in participations:
                        competitor = (
                            participation["competitorName"],
                            participation["competitorCategory"],
                        )
                        competition_name = participation["competitionName"]
                        score = participation["score"]
                        scores_df.at[competition_name, competitor] = score 
                        participations_df.at[competition_name, competitor] = 1
                    res_list.append((scores_df, participations_df))
        return res_list


def get_competitors_from_cursor(cursor):
    competitors = list()
    nb_participations = list()
    for elt in cursor:
        competitors.append(
            (elt["_id"]["competitorName"], elt["_id"]["competitorCategory"])
        )
        nb_participations.append(elt["count"])
    return competitors, nb_participations

def convert_competitions_dataframes_to_arrays(scores_df, participation_df, normalize_scores=True):
    """
    Function transforming scores and participations DataFrames into two arrays : one with the score and an encoding of the competitor category (dim=6,nb_competitions,nb_competitors), and another representing a mask of the participations of the competitors to the competitions (dim=nb_competitions,nb_competitors).
    """
    scores_array = scores_df.to_numpy()
    if normalize_scores:
        scores_array = scores_array/90
    categories = np.array([elt[1] for elt in scores_df.columns])
    categories_encoded = cat_encoder(categories)
    categories_array = np.repeat(categories_encoded[np.newaxis, ...], scores_array.shape[0], axis=0)
    data = np.concat([scores_array[:,:,np.newaxis], categories_array], axis=2).astype(np.float32)
    mask = participation_df.to_numpy()
    return data.transpose(2,0,1), mask

def cat_encoder(cats):
    """
    Creates an encoding of the categories. Instead of a one hot encoding, the categories are encoded into 5 features : "K1", "C1", "C2", "H", "D". "C2M" is encoded by (0,0,1,0,0). 
    """
    res = np.zeros((cats.shape[0], 5))
    res[:, 0] = np.isin(cats, ["K1H", "K1D"]).astype(np.float32)
    res[:, 1] = np.isin(cats, ["C1H", "C1D"]).astype(np.float32)
    res[:, 2] = np.isin(cats, ["C2H", "C2D", "C2M"]).astype(np.float32)
    res[:, 3] = np.isin(cats, ["K1H", "C1H", "C2H"]).astype(np.float32)
    res[:, 4] = np.isin(cats, ["K1D", "C1D", "C2D"]).astype(np.float32)
    return res