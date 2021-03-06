from datetime import date

from points_methods.classic_method import PointsComputer as ClassicPointsComputer
from domain.database_computing import compute_database
from tools.init_logging import load_logging_configuration

if __name__ == "__main__":
    load_logging_configuration("tools/logging.yml")
    points_computer = ClassicPointsComputer()
    database = compute_database(date(2010,1,1), date(2020, 7, 29), points_computer)
