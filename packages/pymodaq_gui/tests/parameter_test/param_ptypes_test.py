# -*- coding: utf-8 -*-
"""
Created the 23/11/2023

@author: Sebastien Weber
"""

import numpy as np
import pytest
import sys
from qtpy import QtWidgets, QtCore
from pymodaq_gui.parameter import Parameter, ParameterTree


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
                                 'checkbox': doCheckbox, 'dragdrop': True}
            tree = init_ParameterTree
            settings = Parameter.create(**params_itemSelect)
            tree.setParameters(settings, showTop=False)
            # Keeping selection order + erase non existing items
            settings.setValue(
                dict(all_items=['item1', 'item2', 'item3'], selected=['item1', 'item2']))
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item1', 'item2'])

            # Removing selection
            settings.setValue(dict(all_items=['item1', 'item2', 'item3'], selected=['item2']))
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item2'])

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
                                 'checkbox': doCheckbox, 'dragdrop': True}
            settings = Parameter.create(**params_itemSelect)

            tree = init_ParameterTree
            tree.setParameters(settings, showTop=False)
            listwidget = tree.listAllItems()[0].widget.itemselect

            # Selecting items

            listwidget.select_item(listwidget.item(2), True)
            listwidget.select_item(listwidget.item(0), True)
            settings.value()
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item3', 'item1'])

            # Unselecting item
            listwidget.select_item(listwidget.item(2), False)
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item1'])

            # Reselecting item
            listwidget.select_item(listwidget.item(2), True)
            assert settings.value() == dict(all_items=['item1', 'item2', 'item3'],
                                            selected=['item1', 'item3'])

    def test_stale_items_are_not_kept_in_selection(self, init_ParameterTree):
        """Changing all the items (e.g. the channels of a viewer) must not leave
        former items in the selection, whatever their number"""
        params_itemSelect = {'title': 'Channels', 'name': 'channels',
                             'type': 'itemselect',
                             'value': dict(all_items=['Mock1', 'Mock2'], selected=['Mock1', 'Mock2']),
                             'checkbox': True}
        tree = init_ParameterTree
        settings = Parameter.create(**params_itemSelect)
        tree.setParameters(settings, showTop=False)
        assert settings.value() == dict(all_items=['Mock1', 'Mock2'], selected=['Mock1', 'Mock2'])

        settings.setValue(dict(all_items=['CH00', 'CH01'], selected=['CH00', 'CH01']))
        assert settings.value() == dict(all_items=['CH00', 'CH01'], selected=['CH00', 'CH01'])

        listwidget = tree.listAllItems()[0].widget.itemselect
        value = listwidget.get_value()
        assert all(item in value['all_items'] for item in value['selected'])

    def test_selected_not_in_all_items_are_filtered(self, init_ParameterTree):
        params_itemSelect = {'title': 'Items', 'name': 'items', 'type': 'itemselect',
                             'value': dict(all_items=['item1', 'item2'], selected=[]),
                             'checkbox': True}
        tree = init_ParameterTree
        settings = Parameter.create(**params_itemSelect)
        tree.setParameters(settings, showTop=False)

        # several consecutive unknown items in 'selected' must all be filtered
        settings.setValue(dict(all_items=['item1', 'item2'],
                               selected=['unknown1', 'unknown2', 'unknown3', 'item2']))
        assert settings.value() == dict(all_items=['item1', 'item2'], selected=['item2'])
