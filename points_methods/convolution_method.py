import logging
from datetime import timedelta

import pandas as pd

from points_methods.exceptions import (
    ImpossiblePointsComputingException,
    NoCompetitorException,
)
from points_methods.utils import (
    calcul_pen_tps_course,
    add_penalties,
    calcul_malus_phase_and_div,
)
from points_methods.utils import (
    add_A_B_penality,
    calcul_points,
    calcul_tps_scratch,
    extract_points,
)


class PointsComputer:
    def __init__(
        self,
        point_type,
        value_accessor,
        database_service,
        model_loading_path=None,
        table_competition_validity_period=timedelta(days=365),
    ):
        self.table_competition_validity_period = table_competition_validity_period
        self.point_type = point_type
        self.value_accessor = value_accessor
        self.database_service = database_service
        if model_loading_path is None:
            raise Exception(
                "Le modèle d'estimation des temps de compétition doit d'abord être entraîné et le chemin de chargement doit être fourni au PointComputer."
            )
        self.estimation_model = ...  # TODO : reprendre ici
        self.logger = logging.getLogger("points_methods.conv2D_based_method")

    def initialize(self, **kwargs):
        pass  # Pas d'initialisation nécessaire

    def compute_and_save_points(self, **kwargs):
        competition_names = kwargs["competition_names"]
        competition_date = kwargs["competition_date"]
        phase = kwargs["phase"]
        force_value_computing = kwargs.get("force_value_computing")
        scores_df, participations_df = self.create_dataframes(competition_date, phase)
        estimated_times = self.estimate_competition_times(scores_df, participations_df)
        if force_value_computing:
            for competition_name in competition_names:
                self.value_accessor.compute_and_save_competition_values(
                    competition_name, phase
                )
        for competition_name in competition_names:
            participations = self.database_service.get_competition_participations(
                competition_name
            )
            try:
                result, point_computing_details = self.compute_points(
                    participations, estimated_times
                )
            except ImpossiblePointsComputingException as e:
                msg = "Impossible de calculer les points de la competition %s, raison : %s, erreur : %s"
                self.logger.error(msg % (competition_name, str(e), str(type(e))))
            else:
                self.database_service.save_competition_points(
                    competition_name, self.point_type, result
                )
                self.database_service.save_point_computing_details(
                    point_computing_details
                )

    def estimate_competition_times(self, scores_df, participations_df):
        pass
        # TODO

    def compute_points(self, participations, estimated_times):
        participations = list(participations)
        # Levée d'une Exception s'il n'y a aucun compétiteur
        if len(participations) == 0:
            raise NoCompetitorException("Pas de compétiteurs sur la course")
        competition_name = participations[0]["competitionName"]
        self.logger.info(
            "Calcul des points de la course : " + participations[0]["competitionName"]
        )

        # TODO

    def create_dataframes(self, competition_date, phase):
        starting_date = competition_date - self.table_competition_validity_period
        competitors_cursor = self.database_service.get_competitors_on_period(
            starting_date, competition_date, phase=phase
        )
        competitors, nb_participations = get_competitors_from_cursor(competitors_cursor)
        competitions = list(
            self.database_service.get_competitions_on_period(
                starting_date, competition_date, phase=phase
            )
        )
        scores_df = pd.DataFrame(
            0, columns=competitors, index=competitions, dtype=float
        )
        participations_df = pd.DataFrame(0, columns=competitors, index=competitions)
        participations = self.database_service.get_participations_on_period(
            starting_date, competition_date, phase=phase
        )
        for participation in participations:
            competitor = (
                participation["competitorName"],
                participation["competitorCategory"],
            )
            competition_name = participation["competitionName"]
            score = participation["score"]
            category = participation["competitorCategory"]
            scores_df.at[competition_name, competitor] = (
                score / self.coef_inter_cat[category]
            )
            participations_df.at[competition_name, competitor] = 1
        return scores_df, participations_df


def get_competitors_from_cursor(cursor):
    competitors = list()
    nb_participations = list()
    for elt in cursor:
        competitors.append(
            (elt["_id"]["competitorName"], elt["_id"]["competitorCategory"])
        )
        nb_participations.append(elt["count"])
    return competitors, nb_participations


if __name__ == "__main__":
    from data_handling.database_service import DatabaseService

    db_service = DatabaseService()
    point_type = "to_remove"
    point_computer = PointsComputer(point_type, db_service)
