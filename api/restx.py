# -*- coding: utf-8 -*-

from flask_restx import Api

api = Api(version='0.1', title='API de backend pour le classement FFCK',
          description='Une API pour gérer la communication en entre le front et la BDD des courses et points')