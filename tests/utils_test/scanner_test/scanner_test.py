# -*- coding: utf-8 -*-
"""
Created the 08/12/2022

@author: Sebastien Weber
"""

import pytest

from pymodaq.utils.scanner.scanner import Scanner, scanner_factory


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
