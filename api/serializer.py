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
    'nbComp': fields.Integer(description='Nnombre de courses dans la moyenne')})

participation = api.model('Participation', {
    'competitorName': fields.String(description="Nom du compétiteur"),
    'competitorCategory': fields.String(description="Categorie du compétiteur"),
    'competitionName': fields.String(description="Nom de la compétition"),
    'simplifiedCompetitionName': fields.String(description="Version courte du nom de compétition"),
    'competitionPhase': fields.String(description="Phase de compétition"),
    'simplifiedCompetitionPhase': fields.String(description="Phase de compétition mise en forme"),
    'date': fields.String(description="Date de la compétition au format ISO"),
    'level': fields.String(description="Niveau de la compétition"),
    'finaleType': fields.String(description="Type de finale (A/B), si pertinant"),
    'pointTypes': fields.List(fields.String(description="Type de points"),
                              description="Types de points calculés pour la compétition"),
    'points': fields.Raw(description="Points obtenus sur la compétition"),
    'valueTypes': fields.List(fields.String(description="Type de valeur"),
                              description="Types de valeurs calculées sur la compétition"),
    'values': fields.Raw(description="valeurs obtenues sur la compétition"),
    'score': fields.Float(description="Score réalisé lors de la compétition")})

values_and_ranks = api.model('ValuesAndRanks', {
    'competitorName': fields.String(description="Nom du compétiteur"),
    'competitorCategory': fields.String(description="Catégorie du compétiteur"),
    'scrapping': fields.Raw(description="rang et valeur pour le scrapping"),
    'skill_based': fields.Raw(description="Ran et valeur pour la méthode proposée")})

competition = api.model('Competition', {
    'competitionName': fields.String(description="Nom de la competition"),
    'simplifiedCompetitionName': fields.String(description="Version courte du nom de compétition"),
    'competitionPhase': fields.String(description="Phase de compétition"),
    'simplifiedCompetitionPhase': fields.String(description="Phase de compétition mise en forme"),
    'date': fields.String(description="Date de la compétition au format ISO"),
    'level': fields.String(description="Niveau de la compétition")})