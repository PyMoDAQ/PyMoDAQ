# -*- coding: utf-8 -*-
"""
Created the 20/10/2023

@author: Sebastien Weber
"""

from pymodaq_utils.utils import deprecation_msg

from pymodaq_utils.serialize.serializer_legacy import Serializer, DeSerializer, SocketString, Socket

deprecation_msg('Importing Serializer, DeSerializer from pymodaq is deprecated in PyMoDAQ >= 5,'
                'import them from pymodaq_data.serialize.serializer')
