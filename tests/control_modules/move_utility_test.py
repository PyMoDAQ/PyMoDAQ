# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""

from pymodaq.control_modules.move_utility_classes import check_units
from pymodaq.utils.data import DataActuator


def test_check_units():

    dwa = DataActuator('myact', data=24., units='km')

    assert check_units(dwa, 'm') == dwa

