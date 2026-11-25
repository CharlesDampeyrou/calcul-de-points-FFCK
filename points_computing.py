# -*- coding: utf-8 -*-
"""
Created on Tue Dec 14 23:11:02 2021

@author: charl
"""

from argparse import ArgumentParser
from datetime import timedelta, date
from pathlib import Path
import os

from tools.init_logging import load_logging_configuration
from data_handling.sql_database_service import DBService
from domain.value import ValueMaker
from domain.competition_processor import CompetitionProcessor
from domain.value_accessor import ValueAccessor
from points_methods.skill_based_method import PointsComputer


def main():
    ap = ArgumentParser(
        description="Lancement du calcul de point (création ou mise à jour)"
    )
    ap.add_argument("--reset-point-type", action="store_true")
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--db", default="results.db")
    logging_file = Path(Path.cwd(), "tools", "logging.yml")
    load_logging_configuration(logging_file)
    ap.add_argument("--point-type", default="skill_based")
    ap.add_argument("--nb-nat-min", type=int, default=3)
    ap.add_argument("--nb-comp-min", type=int, default=4)
    args = ap.parse_args()

    if args.start is not None:
        start = date(args.start, 1, 1)
    else:
        start = None
    nb_nat_min = args.nb_nat_min
    nb_comp_min = args.nb_comp_min
    point_type = args.point_type
    value_type = f"{point_type}_{nb_nat_min}_{nb_comp_min}"
    competition_validity_period = timedelta(days=365)

    db_service = DBService(db_path=args.db)

    # reset des points si demandé
    if args.reset_point_type:
        db_service.delete_point_type(point_type)

    # Création des tables RESULTAT_METHODE_{point_type} et COURSE_METHODE_{point_type}
    db_service.create_point_type(point_type)

    Value = ValueMaker(nb_nat_min, nb_comp_min, point_type, value_type)
    value_accessor = ValueAccessor(
        db_service, Value, competition_validity_period=competition_validity_period
    )
    point_computer = PointsComputer(point_type, value_accessor, db_service)
    competition_processor = CompetitionProcessor(db_service, point_computer)
    competition_processor.update_point_type(minimal_start_date=start)


if __name__ == "__main__":
    main()
