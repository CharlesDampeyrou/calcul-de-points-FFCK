from typing import Tuple, List
from pathlib import Path
import logging
from datetime import datetime, timedelta
from tqdm import tqdm
import pickle
from hashlib import md5

import h5py
import pandas as pd
import numpy as np
import torch
from sklearn.preprocessing import OneHotEncoder
from pymongo.command_cursor import CommandCursor

from .database_service import DatabaseService


class ConvMethodDataPreparator:
    def __init__(
        self,
        db_service: DatabaseService,
        competition_table_period: timedelta = timedelta(days=365),
    ):
        self.db_service = db_service
        self.logger = logging.getLogger("data_handling.conv_method_data_prep")
        self.competition_table_period = competition_table_period

    def save_competition_data_over_period(
        self,
        starting_date: datetime,
        ending_date: datetime,
        saving_path: Path,
        normalize_scores: bool = True,
        seed: int = 0,
    ) -> None:
        """Saves the data representing the scores and participations for the given period in HDF5 format.

        Args:
            starting_datetime (datetime.datetime)
            ending_datetime (datetime.datetime)
            saving_path (pathlib.Path) : path of the directory where to store the files
            normalize_score (bool) [OPTIONNAL] : True to normalize the scores by dividing them by 90s
            seed [OPTIONNAL] : for generating the hash of the competitor and competition

        The created files have the following keys :
            - "scores" (f32 tensor of shape (nb_competitions, nb_competitors)) : the scores, normalized by a 90s division
            - "categories" (bool tensor of shape (nb_competitors, 5)) : the categories encodings
            - "mask" (bool tensor of shape (nb_competitions, nb_competitors)) : the mask of participations
            - "hash" (float tensor of shape (nb_competitions, nb_competitors)) : a int32 hash of the tuple (competitor, competition), to hide the same participations from different tables to the model
        """
        table_end_dates = self.db_service.get_competition_dates(
            starting_date + self.competition_table_period, ending_date
        )
        phases = ["qualif", "demi", "finale", ""]
        self.logger.info(
            "Transformation des données de competitions en matrices par période..."
        )
        i = 0
        for table_end_date in tqdm(list(table_end_dates)):
            for phase in phases:
                competition_names = list(
                    self.db_service.get_competition_list(table_end_date, phase=phase)
                )
                if (
                    competition_names
                ):  # La méthode n'est pas appelée si la liste est vide
                    scores_df, participations_df = (
                        self.get_comp_dataframes_at_specific_date_phase(
                            table_end_date, phase
                        )
                    )
                    scores, categories, mask = (
                        convert_competitions_dataframes_to_tensors(
                            scores_df,
                            participations_df,
                            normalize_scores=normalize_scores,
                        )
                    )
                    hash_t = compute_df_int_hash(participations_df, seed=seed)
                    phase_name = phase if phase != "" else "no_phase"
                    file_path = (
                        saving_path / f"{table_end_date:%Y-%m-%d}__{phase_name}.hdf5"
                    )
                    with h5py.File(file_path, "w") as f:
                        f.create_dataset(
                            "scores", data=scores.numpy(), dtype=np.float32
                        )
                        f.create_dataset(
                            "categories",
                            data=categories.numpy(),
                            dtype=np.bool,
                        )
                        f.create_dataset("mask", data=mask.numpy(), dtype=np.bool)
                        f.create_dataset("hash", data=hash_t, dtype=np.int32)
                    i += 1

    def get_comp_dataframes_at_specific_date_phase(
        self, table_end_date: datetime, phase: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Returns the dataframes representing the scores and participation masks for a specified end date and phase

        Args:
            table_end_date : ending date od the wanted data
            phase : phase for the last day

        Returns:
            scores_df : dataframe of the score obtained. Index : competition names, columns : competitors as (competitor_name, category)
            participation_df : mask of the participations, same indexing
        """
        competitors_cursor = self.db_service.get_competitors_on_period(
            table_end_date - self.competition_table_period,
            table_end_date,
            phase=phase,
        )
        competitors, nb_participations = get_competitors_from_cursor(competitors_cursor)
        competitions = list(
            self.db_service.get_competitions_on_period(
                table_end_date - self.competition_table_period,
                table_end_date,
                phase=phase,
            )
        )
        scores_df = pd.DataFrame(
            0, columns=competitors, index=competitions, dtype=float
        )
        participations_df = pd.DataFrame(0, columns=competitors, index=competitions)
        participations = self.db_service.get_participations_on_period(
            table_end_date - self.competition_table_period,
            table_end_date,
            phase=phase,
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
        return scores_df, participations_df


def get_competitors_from_cursor(
    cursor: CommandCursor,
) -> Tuple[List[Tuple[str, str]], List[int]]:
    """Returns the list of competitors and number of participations from a pymongo cursor

    Args:
        cursor : pymongo cursor returned by db_service.get_competitors_on_period

    Returns:
        competitors : list of competitors as tuples (name, category)
        nb_participations : number of competitions the given competitor has taken part in.
    """
    competitors = list()
    nb_participations = list()
    for elt in cursor:
        competitors.append(
            (elt["_id"]["competitorName"], elt["_id"]["competitorCategory"])
        )
        nb_participations.append(elt["count"])
    return competitors, nb_participations


def convert_competitions_dataframes_to_tensors(
    scores_df: pd.DataFrame,
    participation_df: pd.DataFrame,
    normalize_scores: bool = True,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Function transforming scores and participations DataFrames into tensors.

    Args:
        scores_df (pd.DataFrame): DataFrame containing the scores of competitors.
        participation_df (pd.DataFrame): DataFrame containing the participation status of competitors.
        normalize_scores (bool, optional): If True, scores are divided by 90. Defaults to True.

    Returns:
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            - scores (torch.Tensor): f32 tensor of shape (nb_competitions, nb_competitors), with the scores of each competitor at each competition.
            - categories (torch.Tensor): bool tensor of shape (nb_competitors, 5), representing the encoding of the category of each competitor.
            - mask (torch.Tensor): bool tensor of shape (nb_competitions, nb_competitors), where True means the competitor participated in the given competition.
    """
    scores = torch.tensor(scores_df.to_numpy(), dtype=torch.float32)
    if normalize_scores:
        scores = scores / 90
    categories_str = np.array([elt[1] for elt in scores_df.columns])
    categories = torch.tensor(cat_encoder(categories_str), dtype=torch.bool)
    mask = torch.tensor(participation_df.to_numpy(), dtype=torch.bool)
    return scores, categories, mask


def cat_encoder(cats: np.ndarray) -> np.ndarray:
    """Creates an encoding of the categories. Instead of a one hot encoding, the categories are encoded into 5 features : "K1", "C1", "C2", "H", "D". "C2M" is encoded by (0,0,1,0,0).

    Args :
        - cats : str np.array of shape (nb_competitors,), with the category as "K1H", "K1D", "C1H", "C1D", "C2H", "C2D" or "C2M"

    Returns :
        - res : bool np.array of shape (nb_competitors, 5). The second dimension is the encoding of the category. Instead of a one hot encoding, the categories are encoded into 5 features : "K1", "C1", "C2", "H", "D". "C2M" is encoded by (0,0,1,0,0).
    """
    res = np.zeros((cats.shape[0], 5), dtype=bool)
    res[:, 0] = np.isin(cats, ["K1H", "K1D"])
    res[:, 1] = np.isin(cats, ["C1H", "C1D"])
    res[:, 2] = np.isin(cats, ["C2H", "C2D", "C2M"])
    res[:, 3] = np.isin(cats, ["K1H", "C1H", "C2H"])
    res[:, 4] = np.isin(cats, ["K1D", "C1D", "C2D"])
    return res


def compute_df_int_hash(
    df: pd.DataFrame,
    seed: int = 0,
) -> torch.Tensor:
    """returns a tensor of a hash int of the row and column names of a dataframe

    Args:
        df (pd.DataFrame) : Dataframe containing the rows and columns that we want the hash from
        seed [OPTIONNAL] (int)


    Returns:
        hash_t (torch.Tensor of same shape than df) : each element is a a normalization of the normalization_digits last digits of the name of the row and the name of the column, between 0 and 1
    """
    cols = list(df.columns)
    rows = list(df.index)

    hash_array = np.array(
        [
            [
                int.from_bytes(
                    md5(pickle.dumps((c, r, seed))).digest()[:4],
                    byteorder="little",
                    signed=True,
                )
                for c in cols
            ]
            for r in rows
        ],
        dtype=np.int32,  # 👈 NumPy gère automatiquement l'overflow
    )
    hash_t = torch.from_numpy(hash_array)
    return hash_t
