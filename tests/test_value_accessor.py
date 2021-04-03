# -*- coding: utf-8 -*-
"""
Created on Wed Feb 24 11:40:09 2021

@author: charl
"""
from datetime import datetime

from data_handling.database_service import DatabaseService
from domain.value_accessor import ValueAccessor
from domain.value import ValueMaker

def test_get_value():
    db_service = DatabaseService()
    Value = ValueMaker(3, 4, "scrapping_3_4")
    value_accessor = ValueAccessor(db_service, Value, use_scrapping_points=True)
    competitor_name = "Charles Dampeyrou"
    competitor_category = "C1H"
    date = datetime(2020, 1, 1)
    res = value_accessor.get_value(competitor_name, competitor_category, date)
    print("Valeur de %s en %s le %s : %s" % (competitor_name, competitor_category, str(date), res.moyenne))
    nb_values = db_service.db["values"].count_documents({})
    value_accessor.get_value(competitor_name, competitor_category, date)
    new_nb_values = db_service.db["values"].count_documents({})
    assert nb_values == new_nb_values

if __name__ == "__main__":
    test_get_value()