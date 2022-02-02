# -*- coding: utf-8 -*-
"""
Created on Sat Dec 18 19:57:28 2021

@author: charl
"""

import logging
import os

from flask import Flask, Blueprint

from api.restplus import api
from api.endpoints.ranking import ns as ranking_namespace
from api.endpoints.competitor_infos import ns as competitor_infos_namespace
from api.endpoints.competition_infos import ns as competition_infos_namespace


app = Flask("apiClassementCanoeKayak")


blueprint = Blueprint('api', __name__)
api.init_app(blueprint)
api.add_namespace(ranking_namespace)
api.add_namespace(competitor_infos_namespace)
api.add_namespace(competition_infos_namespace)
app.register_blueprint(blueprint)


if __name__ == "__main__":
    try:
        production = os.environ["PRODUCTION"]
    except:
        production = False
    app.run(debug=(not production), port=5001)
