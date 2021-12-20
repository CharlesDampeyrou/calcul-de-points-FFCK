# -*- coding: utf-8 -*-
"""
Created on Sun Dec 19 10:11:51 2021

@author: charl
"""

from flask_restplus import fields
from api.restplus import api

competitor = api.model("Competitor", {
    "competitorName": fields.String(description="Nom du compétiteur"),
    "competitorCategory": fields.String(description="Categorie du compétiteur")})

value = api.model('Value', {
    '_id': fields.Nested(competitor),
    'moy': fields.Float(description="Moyenne du compétiteur"),
    'nbNat': fields.Integer(description='Nombre de courses nationales dans la moyenne'),
    'nbComp': fields.Integer(description='Nnombre de courses dans la moyenne')
})