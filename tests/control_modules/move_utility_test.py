# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""


import pytest
from pytest import fixture, approx


@fixture
def init_qt(qtbot):
    return qtbot

