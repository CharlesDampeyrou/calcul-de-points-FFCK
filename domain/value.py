# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 10:59:35 2021

@author: charl
"""
import logging

import numpy as np

class BasicValue :
    def __init__(self, moyenne, nb_nat, nb_comp) :
        self.moyenne = moyenne
        self.nb_nat = nb_nat # nombre de compétitions nationnales dans la moyenne
        self.nb_comp = nb_comp # nombre de compétitions dans la moyenne
    
    def __str__(self) :
        return "Moyenne : " + str(self.moyenne) + " (" + str(self.nb_comp) + " courses dont " + str(self.nb_nat) + " courses nationales)"
    
    def __lt__(self, autre_val) :
        if self.nb_comp == autre_val.nb_comp:
            if self.nb_nat == autre_val.nb_nat :
                return self.moyenne < autre_val.moyenne
            else :
                return self.nb_nat > autre_val.nb_nat
        else :
            return self.nb_comp > autre_val.nb_comp
    
    def __le__(self, autre_val):
        if self.nb_comp == autre_val.nb_comp:
            if self.nb_nat == autre_val.nb_nat:
                return self.moyenne <= autre_val.moyenne
            else:
                return self.nb_nat > autre_val.nb_nat
        else:
            return self.nb_comp > autre_val.nb_comp
    
    def __eq__(self, autre_val) :
        return self.moyenne == autre_val.moyenne and self.nb_nat == autre_val.nb_nat and self.nb_comp == autre_val.nb_comp
    
    def __ne__(self, autre_val) :
        return not self == autre_val
    
    def __ge__(self, autre_val) :
        return not self < autre_val
    
    def __gt__(self, autre_val) :
        return not self <= autre_val
    
    
def ValueMaker(nb_nat_min, nb_comp_min, point_type, value_type):
    class Value(BasicValue):
        NB_NAT_MIN = nb_nat_min
        NB_COMP_MIN = nb_comp_min
        POINT_TYPE = point_type
        VALUE_TYPE = value_type
        def __init__(self, moyenne, nb_nat, nb_comp):
            BasicValue.__init__(self, moyenne, nb_nat, nb_comp)
            self.nb_nat_min = nb_nat_min
            self.nb_comp_min = nb_comp_min
            self.logger = logging.getLogger("Value")
        
        def get_value_from_participations(participations):
            point_type = Value.POINT_TYPE
            if len(participations) == 0 :
                return Value(1000, 0, 0) #convention si le compétiteur n'a pas de course
            comp_reg_list = list()
            comp_nat_list = list()
            for participation in participations :
                if point_type not in participation["pointTypes"]:
                    continue
                if participation["level"] == "Régional" :
                    comp_reg_list.append(participation)
                else :
                    comp_nat_list.append(participation)
            nb_comp = min(len(comp_nat_list)+len(comp_reg_list), Value.NB_COMP_MIN)
            nb_nat = min(len(comp_nat_list), Value.NB_NAT_MIN)
            comp_nat_list.sort(key = lambda x:x["points"][point_type])
            points_val = list()
            for i in range(nb_nat):
                points_val.append(comp_nat_list[0]["points"][point_type])
                comp_nat_list.pop(0)
            comp_list = comp_nat_list + comp_reg_list
            comp_list.sort(key = lambda x:x["points"][point_type])
            for i in range(nb_comp - nb_nat) :
                points_val.append(comp_list[i]["points"][point_type])
            moyenne = np.array(points_val).mean()
            return Value(moyenne, nb_nat, nb_comp)
    return Value