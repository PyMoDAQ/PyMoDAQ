# -*- coding: utf-8 -*-
"""Shared fixtures of the extensions tests"""
from pytest import fixture

from pymodaq.extensions.scan.daq_scan import DAQScan
from pymodaq.utils.plugin_testing import loaded_extension


@fixture
def scan():
    """A DAQScan extension created on an empty Dashboard"""
    with loaded_extension(DAQScan) as (dashboard, daq_scan):
        yield daq_scan
