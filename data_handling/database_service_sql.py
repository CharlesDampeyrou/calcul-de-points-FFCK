# -*- coding: utf-8 -*-

import sqlite3
import logging
import os


class DatabaseService:
    def __init__(self):
        self.logger = logging.getLogger("DatabaseService")

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
    
    def competition_exists(self, competition_name):
        query = "SELECT * FROM competitions WHERE competition_name = ?"
        return len(self.fetch_query(query, (competition_name,))) > 0
    
    def competitor_exists(self, competitor_name):
        query = "SELECT * FROM competitors WHERE competitor_name = ?"
        return len(self.fetch_query(query, (competitor_name,))) > 0
    
    def add_competition(
        self,
        competitor_names,
        competitor_categories,
        competition_name,
        simplified_competition_name,
        competition_phase,
        simplified_competition_phase,
        date,
        level,
        final_types,
        scores,
        original_points=None,
        original_values=None,
    ):
        pass
