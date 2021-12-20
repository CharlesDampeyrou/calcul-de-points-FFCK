# -*- coding: utf-8 -*-
"""
Created on Sat Dec 18 19:57:28 2021

@author: charl
"""

import logging
import os

from flask import Flask, Blueprint

from api.restplus import api
from data_handling.database_service import DatabaseService
from api.endpoints.ranking import ns as ranking_namespace


app = Flask("apiClassementCanoeKayak")

app.config["db_service"] = DatabaseService()
#app.config["db_service"] = None

blueprint = Blueprint('api', __name__)
api.init_app(blueprint)
api.add_namespace(ranking_namespace)
app.register_blueprint(blueprint)


if __name__ == "__main__":
    try:
        production = os.environ["PRODUCTION"]
    except:
        production = False
    app.run(debug=(not production), port=5001)
