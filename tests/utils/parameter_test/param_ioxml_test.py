# -*- coding: utf-8 -*-
"""
Created the 29/08/2023

@author: Sebastien Weber
"""

import numpy as np
import pytest

from pymodaq.utils.parameter import Parameter
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter import ioxml
from unittest import mock


axes_names = {'Axis 1': 0, 'Axis 2': 1, 'Axis 3': 2}

params = [{'title': 'Axes', 'name': 'axes', 'type': 'list', 'limits': axes_names}]

settings = Parameter.create(name='settings', type='group', children=params)


string = ioxml.parameter_to_xml_string(settings.child('axes'))

ioxml.XML_string_to_pobject(string)
