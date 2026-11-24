# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 10:59:35 2021

@author: charl
"""

import logging

import numpy as np


class BasicValue:
    def __init__(self, moyenne, nb_nat, nb_comp):
        self.moyenne = moyenne
        self.nb_nat = nb_nat  # nombre de compétitions nationnales dans la moyenne
        self.nb_comp = nb_comp  # nombre de compétitions dans la moyenne

    def __str__(self):
        return (
            "Moyenne : "
            + str(self.moyenne)
            + " ("
            + str(self.nb_comp)
            + " courses dont "
            + str(self.nb_nat)
            + " courses nationales)"
        )

    def __lt__(self, autre_val):
        if self.nb_comp == autre_val.nb_comp:
            if self.nb_nat == autre_val.nb_nat:
                if self.moyenne is None or autre_val.moyenne is None:
                    return self.moyenne is not None
                else:
                    return self.moyenne < autre_val.moyenne
            else:
                return self.nb_nat > autre_val.nb_nat
        else:
            return self.nb_comp > autre_val.nb_comp

    def __le__(self, autre_val):
        if self.nb_comp == autre_val.nb_comp:
            if self.nb_nat == autre_val.nb_nat:
                if self.moyenne is None or autre_val.moyenne is None:
                    return autre_val.moyenne is None
                else:
                    return self.moyenne <= autre_val.moyenne
            else:
                return self.nb_nat > autre_val.nb_nat
        else:
            return self.nb_comp > autre_val.nb_comp

    def __eq__(self, autre_val):
        return (
            self.moyenne == autre_val.moyenne
            and self.nb_nat == autre_val.nb_nat
            and self.nb_comp == autre_val.nb_comp
        )

    def __ne__(self, autre_val):
        return not self == autre_val

    def __ge__(self, autre_val):
        return not self < autre_val

    def __gt__(self, autre_val):
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

        @staticmethod
        def get_value_from_participations(participations):
            """Renvoit une Valeur à partir d'une liste de participations sous la forme de tuples (points, niveau)"""
            participations = list(participations)
            points_reg = [p[0] for p in participations if p[1] == 1]
            points_nat = [p[0] for p in participations if p[1] != 1]
            if len(points_reg) + len(points_nat) == 0:
                return Value(None, 0, 0)
            nb_comp = min(len(points_nat) + len(points_reg), Value.NB_COMP_MIN)
            nb_nat = min(len(points_nat), Value.NB_NAT_MIN)
            points_nat.sort()
            points_retenus = (
                points_nat[:nb_nat]
                + sorted(points_nat[nb_nat:] + points_reg)[: nb_comp - nb_nat]
            )
            moyenne = np.array(points_retenus).mean()
            return Value(moyenne, nb_nat, nb_comp)

    return Value
