# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
import pytest

from pymodaq.control_modules import utils
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq.control_modules.instruments import DAQTypesEnum


class TestDAQType:
    def test_daq_types_enum(self):
        for value in DAQTypesEnum.values():
            assert value in ViewersEnum.names()

    @pytest.mark.parametrize('daq_type_str, data_type_str, viewer_type_str', [('DAQ0D', 'Data0D', 'Viewer0D'),
                                                                              ('DAQ1D', 'Data1D', 'Viewer1D'),
                                                                              ('DAQ2D', 'Data2D', 'Viewer2D'),
                                                                              ('DAQND', 'DataND', 'ViewerND')])
    def test_to_data_type(self, daq_type_str, data_type_str, viewer_type_str):
        daq_type = DAQTypesEnum[daq_type_str]

        assert daq_type.to_daq_type() == daq_type_str
        assert daq_type.to_viewer_type() == viewer_type_str
        assert daq_type.to_data_type() == data_type_str
