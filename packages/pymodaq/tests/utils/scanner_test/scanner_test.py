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

    def test_repr_ser_deser(self, scanner):
        scanner = scanner

        repr = scanner.to_scan_repr()
        assert repr.actuators == [act.title for act in actuators]
        assert compareValuesParameter(repr.scanner_settings, scanner.settings, with_self=False)
        assert compareValuesParameter(repr.sub_scanner_settings, scanner.scanner.settings, with_self=False)
        repr_deser, _ = repr.deserialize(repr.serialize(repr))
        assert repr == repr_deser

    def test_repr_use(self, scanner: Scanner):
        scanner = scanner

        repr_ini = scanner.to_scan_repr()
        scan_types = scanner_factory.keys
        scanner.set_scan_type_and_subtypes(scan_types[1])

        assert repr_ini != scanner.to_scan_repr()

        scanner.from_scan_repr(repr_ini)
        assert scanner.to_scan_repr() == repr_ini

