# -*- coding: utf-8 -*-
"""
Created the 04/11/2023

@author: Sebastien Weber
"""
from pymodaq.utils.scanner.utils import register_scanner, register_scanners


def test_register_scanner():

    scanner_modules = register_scanner('pymodaq.utils.scanner')
    assert len(scanner_modules) >= 4  # there are 4 base exporter modules





