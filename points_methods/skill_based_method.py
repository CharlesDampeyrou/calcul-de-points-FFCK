# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 17:50:42 2021

@author: charl
"""

import logging
from datetime import date, timedelta

import pandas as pd

from points_methods.exceptions import (
    ImpossiblePointsComputingException,
    NoCompetitorException,
)
from points_methods.tensorial_product_estimator import estimate_tensorial_product
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
        db_service,
        table_competition_validity_period=timedelta(days=365),
    ):
        self.coef_inter_cat = {
            "K1H": 1,
            "C1H": 1.05,
            "C1D": 1.2,
            "K1D": 1.13,
            "C2H": 1.1,
            "C2D": 1.3,
            "C2M": 1.2,
        }
        self.table_competition_validity_period = table_competition_validity_period
        self.point_type = point_type
        self.value_accessor = value_accessor
        self.db_service = db_service
        self.logger = logging.getLogger("points_methods.skill_based_method")

    def initialize(self, **kwargs):
        pass  # Pas d'initialisation nécessaire

    def compute_and_save_points(
        self, course_ids, phase, competition_date, force_value_computing, **kwargs
    ):
        scores_df, participations_df = self.create_dataframes(competition_date, phase)
        competitions_vector, skills_vector = estimate_tensorial_product(
            scores_df, participations_df
        )
        for course_id in course_ids:
            participations = {
                boat_id: {
                    "cat": type_code,
                    "score": score_scratch,
                    "level": level,
                    "phase": phase,
                    "finale_ab": finale_ab,
                }
                for boat_id, type_code, score_scratch, level, phase, finale_ab in self.db_service.get_boat_infos_on_course(
                    course_id
                )
                if score_scratch is not None
            }
            self.logger.info(f"Calcul des points de la course id {course_id}")
            course_infos = self.compute_points(
                course_id, participations, competitions_vector, skills_vector
            )
            for boat_id in participations:
                if force_value_computing:
                    moyenne = self.value_accessor.get_value(
                        boat_id, competition_date, phase - 0.1
                    ).moyenne
                else:
                    moyenne = None
                self.db_service.save_resultat_methode(
                    boat_id,
                    course_id,
                    self.value_accessor.points_name,
                    participations[boat_id]["points"],
                    moyenne,
                )
            self.db_service.save_point_computing_details(
                course_id, self.value_accessor.points_name, course_infos
            )

    def compute_points(
        self, course_id, participations, competitions_vector, skills_vector
    ):
        # Levée d'une Exception s'il n'y a aucun compétiteur
        if len(participations) == 0:
            raise NoCompetitorException("Pas de compétiteurs sur la course")

        ######## Calcul du temps scratch
        calcul_tps_scratch(participations, self.coef_inter_cat)

        ######## Calcul du temps de base
        tps_base = self.calcul_tps_base(course_id, competitions_vector, skills_vector)

        ####### Calcul du nombre de points
        calcul_points(participations, tps_base)

        ####### Calcul des pénalités de course pour les temps scratch trop faibles ou trop élevés
        pen_tps_course = calcul_pen_tps_course(participations)
        add_penalties(participations, pen_tps_course)

        ####### Ajout du malus de phase et de division
        penalite_phase_division = calcul_malus_phase_and_div(participations)
        add_penalties(participations, penalite_phase_division)

        ####### Ajout du malus de finale A/B
        add_A_B_penality(participations)

        ######## Création des métadonnées
        course_infos = {
            "tpsBase": tps_base,
            "coefficientCourse": competitions_vector[course_id],
            "bestCompetitorSkill": skills_vector.min(),
            "penTpsCourse": pen_tps_course,
            "penalitePhasedivision": penalite_phase_division,
        }
        return course_infos

    def calcul_tps_scratch(self, participations):
        for participation in participations:
            coef = self.coef_inter_cat[participation["cat"]]
            participation["tpsScratch"] = participation["score"] / coef

    def calcul_tps_base(self, course_id, competitions_vector, skills_vector):
        return competitions_vector[course_id] * skills_vector.min()

    def create_dataframes(self, competition_date, phase):
        """Crée les dataframes de scores et de participations sur la période
        [competition_date - table_competition_validity_period, competition_date],
        à partir de db_service.get_scores_on_period.

        Pour le dernier jour (competition_date), seules les courses dont
        course.phase_ordre <= phase sont prises en compte (phase est passé tel
        quel comme last_day_max_phase).

        - scores_df : une ligne par course_id, une colonne par bateau_id,
          valeur = score_scratch du bateau sur la course ; les cases non
          remplies valent 0.
        - participations_df : mêmes lignes et colonnes, 1 si la cellule de
          scores_df est remplie, 0 sinon.

        Lignes et colonnes sont construites sans doublon (sorted(set(...))).
        Les résultats dont score_scratch est NULL sont ignorés : la cellule
        reste à 0 et le masque à 0 (un score de 0 fausserait l'estimation,
        0 signifiant "temps parfait").

        Parameters
        ----------
        competition_date : str, datetime.date ou datetime.datetime
            Date de fin de la période (dernier jour filtré par phase).
        phase : float
            phase_ordre maximal retenu pour les courses du dernier jour.

        Returns
        -------
        (pandas.DataFrame, pandas.DataFrame)
            (scores_df, participations_df)
        """
        if isinstance(competition_date, str):
            competition_date = date.fromisoformat(competition_date[:10])
        starting_date = competition_date - self.table_competition_validity_period
        scores = [
            (course_id, bateau_id, score_scratch)
            for course_id, bateau_id, score_scratch in self.db_service.get_scores_on_period(
                starting_date, competition_date, phase
            )
            if score_scratch is not None
        ]
        course_ids = sorted({course_id for course_id, _, _ in scores})
        bateau_ids = sorted({bateau_id for _, bateau_id, _ in scores})
        scores_df = pd.DataFrame(0.0, index=course_ids, columns=bateau_ids, dtype=float)
        participations_df = pd.DataFrame(
            0, index=course_ids, columns=bateau_ids, dtype=int
        )
        for course_id, bateau_id, score_scratch in scores:
            scores_df.at[course_id, bateau_id] = score_scratch
            participations_df.at[course_id, bateau_id] = 1
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
    pass
