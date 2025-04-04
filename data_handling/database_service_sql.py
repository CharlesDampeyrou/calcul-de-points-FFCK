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
        """
        Execute a query, commit the changes and return the last row id
        """
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")

    def fetch_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return []

    def add_complete_competition_infos(
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
        """
        Add complete competition infos to the database
        Parameters:
        - competitor_names: list of competitor names
        - competitor_categories: list of competitor categories
        - competition_name: name of the competition
        - simplified_competition_name: simplified name of the competition
        - competition_phase: phase of the competition
        - simplified_competition_phase: simplified phase of the competition
        - date: date of the competition
        - level: level of the competition
        - final_types: list of final types
        - scores: list of scores
        - (OPTIONAL) original_points: list of original points
        - (OPTIONAL) original_values: list of original values
        """
        # Add competition
        competition_id = self.add_competition(
            competition_name,
            simplified_competition_name,
            competition_phase,
            simplified_competition_phase,
            date,
            level,
        )
        for i in range(len(competitor_names)):
            # Add competitor
            competitor_id = self.add_competitor(
                competitor_names[i], competitor_categories[i], ignore_if_exists=True
            )
            # Add participation
            self.add_participation(
                competitor_id, competition_id, final_types[i], scores[i]
            )
            # Add points if they are provided
            if original_points is not None:
                self.add_points(
                    competitor_id,
                    competition_id,
                    "scrapping",
                    original_points[i],
                )
            # Add values if provided
            if original_values is not None:
                self.add_value(
                    competitor_id, competition_id, "scrapping", original_values[i]
                )

    def add_competition(
        self,
        competition_name,
        simplified_competition_name,
        competition_phase,
        simplified_competition_phase,
        date,
        level,
    ):
        """
        Add competition to the database and returns the competition id
        Parameters:
        - competition_name: name of the competition
        - simplified_competition_name: simplified name of the competition
        - competition_phase: phase of the competition
        - simplified_competition_phase: simplified phase of the competition
        - date: date of the competition
        - level: level of the competition
        """
        query = "INSERT INTO competitions VALUES (?, ?, ?, ?, ?, ?)"
        competition_id = self.execute_query(
            query,
            (
                competition_name,
                simplified_competition_name,
                competition_phase,
                simplified_competition_phase,
                date,
                level,
            ),
        )
        if competition_id is None:
            raise Exception(f"Error adding competition {competition_name}")
        return competition_id

    def add_competitor(
        self, competitor_name, competitor_category, ignore_if_exists=False
    ):
        """
        Add competitor to the database and returns the competitor id
        Parameters:
        - competitor_name: name of the competitor
        - competitor_category: category of the competitor
        - ignore_if_exists: if True, trying to add an existing competitor does not raise an error and the competitor id is still returned.
        """
        query = "INSERT INTO competitors VALUES (?, ?)"
        try:
            return self.execute_query(query, (competitor_name, competitor_category))
        except sqlite3.IntegrityError:
            if ignore_if_exists:
                query = (
                    "SELECT competitor_id FROM competitors WHERE competitor_name = ?"
                )
                return self.fetch_query(query, (competitor_name,))[0][0]
            else:
                raise Exception(
                    f"Error adding competitor {competitor_name} {competitor_category}"
                )

    def add_participation(self, competitor_id, competition_id, final_type, score):
        """
        Add participation to the database and returns the participation id
        Parameters:
        - competitor_id: id of the competitor
        - competition_id: id of the competition
        - final_type: final type of the participation
        - score: score of the participation
        """
        query = "INSERT INTO participations VALUES (?, ?, ?, ?)"
        return self.execute_query(
            query, (competitor_id, competition_id, final_type, score)
        )

    def add_points(self, competitor_id, competition_id, point_type, points):
        query = "Insert INTO points VALUES (?, ?, ?, ?)"
        return self.execute_query(
            query, (competitor_id, competition_id, point_type, points)
        )

    def add_value(self, competitor_id, competition_id, value_type, value):
        query = "Insert INTO points VALUES (?, ?, ?, ?)"
        return self.execute_query(
            query, (competitor_id, competition_id, value_type, value)
        )

    def competition_exists(self, competition_name):
        query = "SELECT * FROM competitions WHERE competition_name = ?"
        return len(self.fetch_query(query, (competition_name,))) > 0

    def competitor_exists(self, competitor_name):
        query = "SELECT * FROM competitors WHERE competitor_name = ?"
        return len(self.fetch_query(query, (competitor_name,))) > 0
