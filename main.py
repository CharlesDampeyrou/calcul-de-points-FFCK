from datetime import date

from points_methods.classic_method import PointsComputer as ClassicPointsComputer
from domain.database_computing import compute_database

if __name__ == "__main__":
    points_computer = ClassicPointsComputer()
    database = compute_database(date(2010,1,1), date(2020, 7, 29), points_computer)
