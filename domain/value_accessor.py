# -*- coding: utf-8 -*-
"""
Created on Sun Jan 31 18:01:31 2021

@author: charl
"""
import logging

from datetime import timedelta

class ValueAccessor:
    def __init__(self,
                 database_service,
                 Value,
                 competition_validity_period=timedelta(days=365),
                 use_scrapping_points=False):
        self.logger = logging.getLogger("ValueAccessor")
        self.database_service = database_service
        self.Value = Value
        self.value_type = Value.VALUE_TYPE
        self.value_period = competition_validity_period
    
    def compute_and_save_competition_values(self, competition_name, phase):
        self.logger.debug("Calcul et sauvegarde des valeurs pour la course %s" % competition_name)
        participations = self.database_service.get_competition_participations(competition_name)
        for participation in participations:
            competitor_name = participation["competitorName"]
            competitor_category = participation["competitorCategory"]
            date = participation["date"]
            phase = participation["simplifiedCompetitionPhase"]
            self._compute_and_save_participation_value(competitor_name,
                                                       competitor_category,
                                                       date,
                                                       competition_name,
                                                       phase)
    
    def _compute_and_save_participation_value(self,
                                              competitor_name,
                                              competitor_category,
                                              date,
                                              competition_name,
                                              phase):
        participations = list(self.database_service.get_last_participations(competitor_name,
                                                                            competitor_category,
                                                                            date,
                                                                            self.value_period))
        participations = filter_last_day_phases(participations,
                                                date,
                                                phase)
        value = self.Value.get_value_from_participations(participations)
        if value.nb_comp == 0:
            return
        self.database_service.save_participation_value(competitor_name,
                                                       competitor_category,
                                                       competition_name,
                                                       self.value_type,
                                                       value.moyenne,
                                                       value.nb_comp,
                                                       value.nb_nat)
        
    def get_all_values(self, date, category="all"):
        """
        Cette fonction permet de récupérer les valeurs à la date souhaitée de tous les compétiteurs
        ayant eu au moins une course dans la période concernée par la valeur. Si les valeurs ne sont pas
        dans la base de données, elles sont calculées puis stockées.

        Parameters
        ----------
        date : datetime.datetime
        category : Nonetype or str, optional
            DESCRIPTION. The default is None. Si autre que None, les valeurs retournées sont uniquement
            celles de la catégorie souhaitée.

        Returns
        -------
        result : liste de dict
            Chaque dictionnaire comporte les champs "competitorName", "competitorCategory" et "value".
            l'objet stocké sous la clé "value" est de type Valeur.

        """
        ranking = self.database_service.get_ranking(date,
                                                        self.Value.POINT_TYPE,
                                                        category,
                                                        self.Value.NB_NAT_MIN,
                                                        self.Value.NB_COMP_MIN,
                                                        value_period = self.value_period)
        values = list()
        for d in ranking:
            values.append({"competitorName":d["_id"]["competitorName"],
                           "competitorCategory":d["_id"]["competitorCategory"],
                           "value":self.get_value_from_dic(d)})
        return values
        
        
    
    def get_value(self,
                  competitor_name,
                  competitor_category,
                  date):
        """
        Cette fonction calcule et renvoit la valeur à la date souhaitée. La
        valeur prend en compte toutes les compétitions entre date-value_period
        et date (inclue). Si last_day_phase is None, la valeur est sauvegardée
        lors de son calcul.
        

        Parameters
        ----------
        competitor_name : STR
        competitor_category : STR
        date : DATETIME.DATETIME

        Returns
        -------
        Value
            Valeur à la date souhaitée. La valeur prend en compte toutes les
            compétitions entre date- value_period et date (inclue).

        """
        value_as_dic = self.database_service.get_value(competitor_name,
                                                       competitor_category,
                                                       date,
                                                       self.Value.POINT_TYPE,
                                                       self.Value.NB_NAT_MIN,
                                                       self.Value.NB_COMP_MIN)
        return self.get_value_from_dic(value_as_dic)
    
    
    def get_value_from_dic(self, value_as_dic):
        moyenne = value_as_dic["moy"]
        nb_competitions = value_as_dic["nbComp"]
        nb_nationals = value_as_dic["nbNat"]
        return self.Value(moyenne, nb_nationals, nb_competitions)
    
    
def filter_last_day_phases(participations,
                           date,
                           last_day_phase):
    if last_day_phase in ["qualif", ""]:
        authorized_phases = []
    elif last_day_phase == "demi":
        authorized_phases = ["qualif"]
    elif last_day_phase == "finale":
        authorized_phases = ["qualif", "demi"]
    else:
        authorized_phases = ["qualif", "demi", "finale", ""]
    for i in reversed(range(len(participations))):
        if participations[i]["date"]==date and participations[i]["simplifiedCompetitionPhase"] not in authorized_phases:
            participations.pop(i)
    return participations