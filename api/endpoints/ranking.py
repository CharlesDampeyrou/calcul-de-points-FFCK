# -*- coding: utf-8 -*-
"""
Created on Sun Dec 19 10:09:12 2021

@author: charl
"""
import sys
import logging
from datetime import datetime

from flask import request, current_app
from flask_restx import Resource

from api.restx import api
from api.serializer import value
from data_handling.database_service import DatabaseService

ns = api.namespace('ranking', description='Classement des compétiteurs')

@ns.route('/test')
class Test(Resource):
    def get(self):
        return "Hello world !"

@ns.route('')
class Ranking(Resource):

    @api.marshal_list_with(value)
    def get(self):
        """
        Returns the list of all models.
        """
        db_service = DatabaseService()
        data = request.args
        date = datetime.fromisoformat(data.get("date")[:10])
        point_type = data.get("pointType")
        category = data.get("category")
        nb_nat_min = int(data.get("nbNatMin"))
        nb_comp_min = int(data.get("nbCompMin"))
        return (list(db_service.get_ranking(date,
                                        point_type,
                                        category,
                                        nb_nat_min,
                                        nb_comp_min,)),
                200)
