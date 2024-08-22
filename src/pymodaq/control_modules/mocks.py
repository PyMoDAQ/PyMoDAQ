# -*- coding: utf-8 -*-
"""
Created the 16/03/2023

@author: Sebastien Weber
"""
from pymodaq.utils.parameter import Parameter
from pymodaq_gui.h5modules import saving
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ActuatorSaver, ScanSaver


class MockDAQViewer:
    params = [{'title': 'mytitle', 'name': 'title', 'type': 'str', 'value': 'myviewervalue'}]

    def __init__(self, h5saver: saving.H5Saver = None, title='MyDet0D'):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)  # create a Parameter
        self.h5saver = h5saver
        self.title = title
        self.module_and_data_saver = DetectorSaver(self)
        self.ui = None


class MockDAQMove:
    params = [{'title': 'mytitle', 'name': 'title', 'type': 'str', 'value': 'myactuatorvalue'}]

    def __init__(self, h5saver: saving.H5Saver = None, title='MyAct'):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)  # create a Parameter
        self.h5saver = h5saver
        self.title = title
        self.module_and_data_saver = ActuatorSaver(self)
        self.ui = None


class ModulesManagerMock:
    def __init__(self, actuators, detectors):
        self.modules_all = actuators + detectors
        self.modules = actuators + detectors


class MockScan:
    params = [{'title': 'mytitle', 'name': 'title', 'type': 'str', 'value': 'myactuatorvalue'}]

    def __init__(self, h5saver: saving.H5Saver = None):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)  # create a Parameter
        self.h5saver = h5saver
        self.title = 'MyScan'
        actuators = [MockDAQMove(self.h5saver)]
        detectors = [MockDAQViewer(self.h5saver, 'Det0D'), MockDAQViewer(self.h5saver, 'Det1D')]
        self.modules_manager = ModulesManagerMock(actuators, detectors)
        self.module_and_data_saver = ScanSaver(self)
        self.ui = None