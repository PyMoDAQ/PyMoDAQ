# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
import pytest
from qtpy import QtWidgets, QtCore
from pymodaq.utils.managers.parameter_manager import ParameterManager, Parameter, ParameterTree
from pymodaq.utils.scanner.scan_factory import ScannerFactory
from pymodaq.utils.parameter import utils as putils

scanner_factory = ScannerFactory()
config_scanner = dict(actuators=['act1', 'act2', 'act3'])


class TestSettings:
    def test_factory_interface(self, qtbot):
        for scan_type in scanner_factory.scan_types():
            for scan_sub_type in scanner_factory.scan_sub_types(scan_type):
                scanner = scanner_factory.get(scan_type, scan_sub_type, **config_scanner)
                scanner.evaluate_steps()
                scanner.set_scan()
                assert hasattr(scanner,  'axes_unique')
                assert hasattr(scanner,  'axes_indexes')
                assert hasattr(scanner,  'positions')
                assert hasattr(scanner, 'n_steps')
                assert hasattr(scanner, 'n_axes')

                if scan_type == 'Scan1D':
                    assert scanner.n_axes == 1
                elif scan_type == 'Scan2D':
                    assert scanner.n_axes == 2
                    if scan_sub_type == 'Spiral':
                        pass
                else:
                    assert scanner.n_axes == len(config_scanner['actuators'])

                if scan_type == 'Tabular':
                    assert scanner.n_steps == 1


