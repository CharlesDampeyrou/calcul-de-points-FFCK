# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 10:06:09 2021

@author: charl
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import matplotlib.pyplot as plt

from tools.init_logging import load_logging_configuration
from data_handling.database_service import DatabaseService
from domain.value_accessor import ValueAccessor
from domain.value import ValueMaker

class Analyst:
    def __init__(self, database_service, value_accessor):
        self.database_service = database_service
        self.value_accessor = value_accessor
        self.logger = logging.getLogger("Analyst")
    
    def show_value_and_ranking_evolution(self,
                                         starting_date,
                                         ending_date,
                                         timestep=timedelta(days=7),
                                         point_limits=[50, 150, 250],
                                         ranking_limits=[50, 250, 500]): #TODO
        current_date = starting_date
        ranking_for_points_limit = list()
        points_for_ranking_limit = list()
        dates = list()
        while current_date < ending_date:
            self.logger.info("Calcul des valeurs au %s", str(current_date))
            current_ranking_for_point_limit = list()
            current_points_for_ranking_limit = list()
            values = self.value_accessor.get_all_values(current_date)
            values.sort(key=lambda x:x["value"])
            for point_limit in point_limits:
                nb_nat = self.value_accessor.Value.NB_NAT_MIN
                nb_comp = self.value_accessor.Value.NB_COMP_MIN
                value_limit = self.value_accessor.Value(point_limit, nb_nat, nb_comp)
                ranking = find_ranking_for_point_limit(values, value_limit)
                current_ranking_for_point_limit.append(ranking)
            for ranking_limit in ranking_limits:
                points = find_points_for_ranking_limit(values, ranking_limit)
                current_points_for_ranking_limit.append(points)
            ranking_for_points_limit.append(current_ranking_for_point_limit)
            points_for_ranking_limit.append(current_points_for_ranking_limit)
            dates.append(current_date)
            current_date += timestep
        ranking_for_points_limit = np.array(ranking_for_points_limit)
        points_for_ranking_limit = np.array(points_for_ranking_limit)
        fig, axs = plt.subplots(2, 1)
        for i in range(ranking_for_points_limit.shape[1]):
            axs[0].plot(dates,
                        ranking_for_points_limit[:, i],
                        label="%i points" % point_limits[i])
        axs[0].set_ylabel("Nombre de personnes sous X points")
        axs[0].set_xlabel("Date")
        axs[0].legend(loc='best')
        for i in range(points_for_ranking_limit.shape[1]):
            axs[1].plot(dates,
                        points_for_ranking_limit[:, i],
                        label="%ième" % ranking_limits[i])
        axs[1].set_ylabel("Moyenne de la N ième personne")
        axs[1].set_xlabel("Date")
        fig.suptitle("Evolution de la moyenne au cours du temps")
        axs[1].legend(loc='best')
        plt.show()
    
    def show_improvement_rate_evolution(self, starting_date, ending_date, point_type, levels=["all"]):
        for level in levels:
            rates = list()
            dates = list()
            competition_list = self.database_service.get_competition_list_on_period(starting_date,
                                                                                    ending_date,
                                                                                    level=level)
            for competition_name in competition_list:
                participations = self.database_service.get_competition_participations(competition_name)
                rate = compute_improvement_rate(participations, point_type) 
                if not np.isnan(rate):
                    rates.append(rate)
                    dates.append(self.database_service.get_competition_date(competition_name))
            plt.plot(dates, rates, label=level, linestyle="None", marker='+', markersize=5)
        axes = plt.gca()
        axes.set_ylim([0,1])
        plt.legend()
        plt.title("Part des compétiteurs faisant une performance meilleure que leur moyenne")
        plt.show()
    
    def compute_improvement_rate_evolution(self, starting_date, ending_date, point_type, levels=["all"]):
        for level in levels:
            rates = list()
            competition_list = self.database_service.get_competition_list_on_period(starting_date,
                                                                                    ending_date,
                                                                                    level=level)
            for competition_name in competition_list:
                participations = self.database_service.get_competition_participations(competition_name)
                rate = compute_improvement_rate(participations, point_type) 
                if not np.isnan(rate):
                    rates.append(rate)
            rates = np.array(rates)
            msg = "En moyenne, sur une compétition %s, %f des compétiteurs marquent de meilleurs "
            msg += "points que leur moyenne, Avec un écart type de %f selon les compétitions.\n"
            print(msg % (level, 100*rates.mean(), 100*rates.std()))
            plt.figure()
            plt.hist(rates, label=level, range = (0, 1))
            plt.legend()
            plt.show()
        
            
        

def find_ranking_for_point_limit(values, limit):
    return len([0 for value in values if value["value"]<limit])

def find_points_for_ranking_limit(values, limit):
    return values[limit]["value"].moyenne

def compute_improvement_rate(participations, point_type):
    nb_ranked = 0
    nb_improving = 0
    for participation in participations:
        try:
            moyenne = participation["values"][point_type]["points"]
            points = participation["points"][point_type]
        except:
            pass
        else:
            if moyenne != 1000:
                nb_ranked += 1
                nb_improving += 1 if points<=moyenne else 0
    if nb_ranked != 0:
        return nb_improving/nb_ranked
    return np.nan

if __name__ == "__main__":
    load_logging_configuration()
    db_service = DatabaseService()
    Value = ValueMaker(3, 4, "scrapping_3_4")
    value_accessor = ValueAccessor(db_service, Value, use_scrapping_points=True)
    analyst = Analyst(db_service, value_accessor)
    #analyst.show_value_and_ranking_evolution(datetime(2002, 1, 3), datetime(2021, 1, 1))
    # analyst.show_improvement_rate_evolution(datetime(2002, 1, 3),
    #                                         datetime(2021, 1, 1),
    #                                         "scrapping",
    #                                         levels=['Championnats de France',
    #                                                 'Nationale 1',
    #                                                 'Nationale 2',
    #                                                 'Nationale 3'])
    analyst.compute_improvement_rate_evolution(datetime(2015, 1, 1),
                                               datetime(2021, 1, 1),
                                               "scrapping",
                                               levels=['all',
                                                       'Championnats de France',
                                                       'Nationale 1',
                                                       'Nationale 2',
                                                       'Nationale 3',
                                                        'Régional'])
                                            
"""
                                            levels=['Championnats de France',
                                                    'Nationale 1',
                                                    'Nationale 2',
                                                    'Nationale 3',
                                                    'Régional']"""
    