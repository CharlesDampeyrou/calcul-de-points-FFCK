# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 19:31:51 2022

@author: charl
"""

import sys
import logging
from datetime import datetime

from flask import request, current_app
from flask_restx import Resource

from api.restx import api
from api.serializer import participation, competition
from data_handling.database_service import DatabaseService

ns = api.namespace('competition_infos', description='Récupération des informations concernant une compétition')

@ns.route('/point_computing_details')
class PointComputingDetails(Resource):

    #@api.marshal_with(competition_metadata)
    def get(self):
        """
        Returns the computation details of the competition.
        """
        db_service = DatabaseService()
        data = request.args
        competition_name = data.get("competitionName")
        return (db_service.get_point_computing_details(competition_name),
                200)

@ns.route('/participations')
class ParticipationList(Resource):
    
    @api.marshal_list_with(participation)
    def get(self):
        """
        Returns the list of the participations for the given competition
        """
        db_service = DatabaseService()
        data = request.args
        competition_name = data.get("competitionName")
        return (list(db_service.get_competition_participations(competition_name,
                                                               sort_by_score=True)),
                200)

@ns.route('/competition_list')
class CompetitionList(Resource):
    
    @api.marshal_list_with(competition)
    def get(self):
        """
        Returns the list of the compétitions for the given year
        """
        db_service = DatabaseService()
        data = request.args
        year = int(data.get("year"))
        return (list(db_service.get_year_competitions(year)),
                200)