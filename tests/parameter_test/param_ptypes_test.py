# -*- coding: utf-8 -*-
"""
Created the 23/11/2023

@author: Sebastien Weber
"""

import numpy as np
import pytest
import sys
from qtpy import QtWidgets, QtCore
from pymodaq.utils.parameter import Parameter, pymodaq_ptypes, ParameterTree
from pymodaq.utils.parameter import utils as putils
from pymodaq.examples.parameter_ex import ParameterEx
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.daq_utils import find_objects_in_list_from_attr_name_val


@pytest.fixture
def init_ParameterTree(qtbot):
    form = QtWidgets.QWidget()
    prog = ParameterTree(form)
    form.show()
    qtbot.addWidget(form)
    yield prog
    form.close()


class TestItemSelect:

    def test_isSelected_setValue(self, init_ParameterTree):

        for doCheckbox in [True, False]:
            params_itemSelect = {'title': 'Dragable items', 'name': 'itemsSelect_drag',
                                 'type': 'itemselect',
                                 'value': dict(all_items=['item1', 'item2', 'item3'], selected=[]),
                                 'show_pb': True, 'show_mb': True,
                                 'checkbox': doCheckbox, 'dragdrop': True, }
            tree = init_ParameterTree
            settings = Parameter.create(**params_itemSelect)
            tree.setParameters(settings, showTop=False)
            # Keeping selection order + erase non existing items
            settings.setValue(
                dict(all_items=['item1', 'item2', 'item3'], selected=['item1', 'item2']))
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item1', 'item2'])

            # Removing selection
            settings.setValue(dict(all_items=['item1', 'item2', 'item3'], selected=['item2', ]))
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item2', ])

            # Adding selection (non matching order between all/selected)
            settings.setValue(
                dict(all_items=['item1', 'item2', 'item3'], selected=['item2', 'item1']))
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item2', 'item1'])

            # Adding selection (non matching order between all/selected)
            settings.setValue(dict(all_items=['item1', 'item2', 'item3', 'item4'],
                                   selected=['item2', 'item1', 'item3', 'item4']))
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3', 'item4'],
                                            selected=['item2', 'item1', 'item3', 'item4'])

    def test_isSelected_clicked(self, init_ParameterTree):
        for doCheckbox in [True, False]:
            params_itemSelect = {'title': 'Dragable items', 'name': 'itemsSelect_drag',
                                 'type': 'itemselect',
                                 'value': dict(all_items=['item1', 'item2', 'item3'], selected=[]),
                                 'show_pb': True, 'show_mb': True,
                                 'checkbox': doCheckbox, 'dragdrop': True, }
            settings = Parameter.create(**params_itemSelect)

            tree = init_ParameterTree
            tree.setParameters(settings, showTop=False)
            listwidget = tree.listAllItems()[0].widget.itemselect

            # Selecting items

            listwidget.select_item(listwidget.item(2), True)
            listwidget.select_item(listwidget.item(0), True)
            settings.value()
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3', ],
                                            selected=['item3', 'item1'])

            # Unselecting item
            listwidget.select_item(listwidget.item(2), False)
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3', ],
                                            selected=['item1'])

            # Reselecting item
            listwidget.select_item(listwidget.item(2), True)
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3', ],
                                            selected=['item1', 'item3'])