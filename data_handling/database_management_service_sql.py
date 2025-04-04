import logging
import os

import sqlite3


class DatabaseService:
    def __init__(self):
        self.logger = logging.getLogger("DatabaseManagementService")

        prod = True if os.environ.get("PRODUCTION") else False
        db_name = "ck_db_prod.sqlite" if prod else "ck_db.sqlite"

        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()

    def execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")

    def fetch_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return []

    def close(self):
        self.connection.close()

    def create_tables(self):
        create_competitions_q = """
            CREATE TABLE IF NOT EXISTS competitions (
                competition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_name TEXT NOT NULL,
                competition_simplified_name TEXT NOT NULL,
                competition_date TEXT NOT NULL,
                competition_phase TEXT NOT NULL,
                competition_simplified_phase TEXT NOT NULL,
                level TEXT NOT NULL
            )
        """
        create_competitors_q = """"
            CREATE TABLE IF NOT EXISTS competitors (
                competitor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_name TEXT NOT NULL,
                competitor_category TEXT NOT NULL,
                UNIQUE(competitor_name, competitor_category)
            )
        """
        create_participations_q = """
            CREATE TABLE IF NOT EXISTS participations (
                participation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER,
                competition_id INTEGER,
                final_type TEXT NOT NULL,
                score REAL NOT NULL,
                FOREIGN KEY (competitor_id) REFERENCES competitors(competitor_id),
                FOREIGN KEY (competition_id) REFERENCES competitions(competition_id)
            )"""
        create_points_q = """
            CREATE TABLE IF NOT EXISTS points (
                point_id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER,
                competition_id INTEGER,
                point_type TEXT NOT NULL,
                point_value REAL NOT NULL,
                FOREIGN KEY (competitor_id) REFERENCES competitors(competitor_id),
                FOREIGN KEY (competition_id) REFERENCES competitions(competition_id)
            )"""
        create_values_q = """
            CREATE TABLE IF NOT EXISTS values (
                value_id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER,
                competition_id INTEGER,
                value_type TEXT NOT NULL,
                value REAL NOT NULL,
                FOREIGN KEY (competitor_id) REFERENCES competitors(competitor_id),
                FOREIGN KEY (competition_id) REFERENCES competitions(competition_id)
            )"""
        self.execute_query(create_competitions_q)
        self.execute_query(create_competitors_q)
        self.execute_query(create_participations_q)
        self.execute_query(create_points_q)
        self.execute_query(create_values_q)
