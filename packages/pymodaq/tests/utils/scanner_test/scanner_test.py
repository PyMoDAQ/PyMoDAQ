# -*- coding: utf-8 -*-
"""
Created the 08/12/2022

@author: Sebastien Weber
"""

import pytest
from qtpy import QtWidgets

from pymodaq.utils.scanner.scanner import Scanner, scanner_factory
from pymodaq_gui.parameter.utils import compareValuesParameter

units = ['nm', 'kW', 'ms', '°C', ]


class MoveMock:
    def __init__(self, ind: int = 0):
        self.title = f'act_{ind}_{units[ind]}'
        self.units = units[ind]

actuators = [MoveMock(ind) for ind in range(len(units))]


@pytest.fixture()
def scanner(qtbot) -> Scanner:
    widget_scanner = QtWidgets.QWidget()
    qtbot.addWidget(widget_scanner)
    scanner = Scanner(widget_scanner, actuators=actuators)
    return scanner


class TestScanner:
    def test_attributes(self, qtbot):
        """test if attributes needed by external objects are present"""
        scanner = Scanner()
        assert hasattr(scanner, 'scan_type')
        assert hasattr(scanner, 'scan_sub_type')
        assert hasattr(scanner, 'get_scan_info')
        assert hasattr(scanner, 'n_steps')
        assert hasattr(scanner, 'n_axes')
        assert hasattr(scanner, 'positions')
        assert hasattr(scanner, 'axes_indexes')
        assert hasattr(scanner, 'axes_unique')

    def test_instantiation(self, scanner):
        scanner = scanner

