# -*- coding: utf-8 -*-
"""
Created on Fri Dec 24 13:54:00 2021

@author: charl
"""

import sys
import logging
from datetime import datetime

from flask import request, current_app
from flask_restplus import Resource

from api.restplus import api
from api.serializer import participation
from data_handling.database_service import DatabaseService

ns = api.namespace('competitor_infos', description='Récupération des informations concernant un compétiteur')

@ns.route('/participations')
class Participations(Resource):

    @api.marshal_list_with(participation)
    def get(self):
        """
        Returns the list of all participations for the selected athlete.
        Order is date decreasing.
        """
        db_service = DatabaseService()
        data = request.args
        competitor_name = data.get("competitorName")
        competitor_category = data.get("competitorCategory")
        return (list(db_service.get_competitor_participations(competitor_name,
                                                              competitor_category)),
                200)

@ns.route('/value')
class Value(Resource):
    
    def get(self):
        """
        Returns the value of the selected athlete at the current date.
        """
        db_service = DatabaseService()
        data = request.args
        competitor_name = data.get("competitorName")
        competitor_category = data.get("competitorCategory")
        point_type = data.get("pointType")
        date = datetime.today()
        nb_nat_min = 3
        nb_comp_min = 4
        return (db_service.get_value(competitor_name,
                                     competitor_category,
                                     date,
                                     point_type,
                                     nb_nat_min,
                                     nb_comp_min,),
                200)


