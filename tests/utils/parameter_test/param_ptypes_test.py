# -*- coding: utf-8 -*-
"""
Created the 23/11/2023

@author: Sebastien Weber
"""

import numpy as np
import pytest
import sys
from qtpy import QtWidgets, QtCore
from pymodaq.utils.parameter import Parameter,pymodaq_ptypes
from pymodaq.utils.parameter import utils as putils
from pymodaq.examples.parameter_ex import ParameterEx
from pymodaq.utils.managers.parameter_manager import ParameterManager


params_itemSelect = [{'title': 'Selectable items:', 'name': 'itemsSelect', 'type': 'group', 'children': [
    {'title': 'Selectable items', 'name': 'itemsSelect_base', 'type': 'itemselect',
        'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
        'tip': 'Press Ctrl+click  to select items in any order'},
    {'title': 'Selectable items', 'name': 'itemsSelect_pb', 'type': 'itemselect',
        'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
        'tip': 'If show_pb is True, user can add items to the list', 'show_pb': True,},
    {'title': 'Removable items', 'name': 'itemsSelect_mb', 'type': 'itemselect',
        'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
        'tip': 'If show_mb is True, user can remove selected items from the list', 'show_mb': True,},            
    {'title': 'Checkable items', 'name': 'itemsSelect_check', 'type': 'itemselect',
        'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
        'tip': 'If checkbox is True, user can select item by checking/unchecking items. Remove items is still used with standard selections',
        'show_pb': True, 'checkbox': True, 'show_mb': True,},                        
    {'title': 'Dragable items', 'name': 'itemsSelect_drag', 'type': 'itemselect',
        'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
        'tip': 'If dragdrop is True, user can drag or drop items inside the list', 'checkbox': True, 'dragdrop': True}, 
]}]

class ParameterTest(ParameterManager):
    def __init__(self,params):
        self.params =params
        super().__init__()
        
    def value_changed(self, param):
        """
        """
        print(f'The parameter {param.name()} changed its value to {param.value()}')        

def test_isSelected():
    app = QtWidgets.QApplication(sys.argv)
    ptree = ParameterTest(params_itemSelect)   
    ptree.settings_tree.show()
 
    ptree.settings.child('itemsSelect', 'itemsSelect_check').setValue(dict(all_items=['item1', 'item2', 'item3'],
                                                             selected=['item3']))    
    sys.exit(app.exec_())

    


