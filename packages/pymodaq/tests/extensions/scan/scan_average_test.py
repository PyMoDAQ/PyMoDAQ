# -*- coding: utf-8 -*-
"""Averaging of the scans is only available for the scans with uniform data"""
import pytest

from pymodaq.utils.scanner.scanner import scanner_factory


class MoveMock:
    def __init__(self, title: str, units: str):
        self.title = title
        self.units = units


ACTUATORS = [MoveMock('act_0', 'nm'), MoveMock('act_1', 'ms')]
UNIFORM_SCANS = [('Scan1D', 'Linear'), ('Scan2D', 'Linear')]
SPREAD_SCANS = [('Scan2D', 'RandomSpread'), ('Tabular', 'Linear')]


def set_scan(scan, scan_type, scan_subtype):
    scan.scanner.actuators = ACTUATORS
    scan.scanner.set_scan_type_and_subtypes(scan_type, scan_subtype)
    assert scan.scanner.scan_type == scan_type
    assert scan.scanner.scan_sub_type == scan_subtype


def average_param(scan):
    return scan.settings.child('scan_options', 'scan_average')


@pytest.mark.parametrize('scan_type, scan_subtype', SPREAD_SCANS)
def test_spread_scans_are_not_averaged(scan, scan_type, scan_subtype):
    average_param(scan).setValue(3)
    set_scan(scan, 'Scan2D', 'Linear')
    assert average_param(scan).value() == 3

    set_scan(scan, scan_type, scan_subtype)

    assert scan.scanner.distribution.name == 'spread'
    assert average_param(scan).value() == 1
    assert average_param(scan).opts['readonly']


@pytest.mark.parametrize('scan_type, scan_subtype', SPREAD_SCANS)
def test_average_is_restored_with_uniform_scans(scan, scan_type, scan_subtype):
    average_param(scan).setValue(3)
    set_scan(scan, scan_type, scan_subtype)
    assert average_param(scan).value() == 1

    set_scan(scan, 'Scan2D', 'Linear')

    assert average_param(scan).value() == 3
    assert not average_param(scan).opts['readonly']


def test_average_cannot_be_set_for_a_spread_scan(scan):
    """For instance when the settings are loaded from a file (Scan Manager...)"""
    set_scan(scan, 'Scan2D', 'RandomSpread')

    average_param(scan).setValue(4)

    assert average_param(scan).value() == 1


@pytest.mark.parametrize('scan_type, scan_subtype', UNIFORM_SCANS)
def test_uniform_scans_can_be_averaged(scan, scan_type, scan_subtype):
    set_scan(scan, scan_type, scan_subtype)

    average_param(scan).setValue(4)

    assert average_param(scan).value() == 4
    assert not average_param(scan).opts['readonly']
