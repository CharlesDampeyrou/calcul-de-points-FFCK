#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  9 22:36:53 2020

@author: charles
"""
class ImpossiblePointsComputingException(Exception):
    pass

class NoCompetitorException(ImpossiblePointsComputingException):
	pass

class NotEnoughCompetitorException(ImpossiblePointsComputingException):
	pass