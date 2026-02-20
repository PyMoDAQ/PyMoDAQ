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


class TestItemSelectContextMenu:

    BASE_PARAMS = dict(
        title='Test detectors', name='test_items', type='itemselect',
        value=dict(all_items=['det1', 'det2', 'det3'], selected=[]),
    )

    def _show_tree(self, tree, settings):
        tree.setParameters(settings, showTop=False)
        return tree.listAllItems()[0].widget.itemselect

    # ------------------------------------------------------------------
    # Registration timing
    # ------------------------------------------------------------------

    def test_action_before_show_stored_in_opts(self):
        settings = Parameter.create(**self.BASE_PARAMS)
        settings.addContextMenuAction('Probe', lambda cl, sel: None)
        assert len(settings.opts['context_actions']) == 1
        label, _, path = settings.opts['context_actions'][0]
        assert label == 'Probe'
        assert path == ()

    def test_action_before_show_applied_to_widget(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        settings.addContextMenuAction('Probe', lambda cl, sel: None)
        listwidget = self._show_tree(init_ParameterTree, settings)
        assert len(listwidget._context_actions) == 1
        assert listwidget._context_actions[0][0] == 'Probe'

    def test_action_after_show_applied_immediately(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        listwidget = self._show_tree(init_ParameterTree, settings)
        assert len(listwidget._context_actions) == 0
        settings.addContextMenuAction('Show viewer', lambda cl, sel: None)
        assert len(listwidget._context_actions) == 1
        assert listwidget._context_actions[0][0] == 'Show viewer'

    def test_multiple_actions_accumulate(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        settings.addContextMenuAction('Probe', lambda cl, sel: None)
        settings.addContextMenuAction('Show viewer', lambda cl, sel: None)
        listwidget = self._show_tree(init_ParameterTree, settings)
        assert len(listwidget._context_actions) == 2

    # ------------------------------------------------------------------
    # Separator
    # ------------------------------------------------------------------

    def test_separator_propagates_to_widget(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        settings.addContextMenuAction('A', lambda cl, sel: None)
        settings.addContextMenuAction(None)
        settings.addContextMenuAction('B', lambda cl, sel: None)
        listwidget = self._show_tree(init_ParameterTree, settings)
        labels = [label for label, _, _ in listwidget._context_actions]
        assert labels == ['A', None, 'B']

    # ------------------------------------------------------------------
    # Nested submenus
    # ------------------------------------------------------------------

    def test_nested_path_stored_correctly(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        settings.addContextMenuAction('Show', lambda cl, sel: None, path=('Viewers',))
        listwidget = self._show_tree(init_ParameterTree, settings)
        _, _, path = listwidget._context_actions[0]
        assert path == ('Viewers',)

    def test_nested_submenu_built_in_menu(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        settings.addContextMenuAction('Show', lambda cl, sel: None, path=('Viewers',))
        settings.addContextMenuAction('Hide', lambda cl, sel: None, path=('Viewers',))
        listwidget = self._show_tree(init_ParameterTree, settings)

        menu = listwidget._build_context_menu(QtCore.QPoint(0, 0))
        assert menu is not None
        submenus = [a.menu() for a in menu.actions() if a.menu() is not None]
        assert len(submenus) == 1
        assert submenus[0].title() == 'Viewers'
        assert len(submenus[0].actions()) == 2

    def test_deeply_nested_submenu(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        settings.addContextMenuAction('Export CSV', lambda cl, sel: None,
                                      path=('Data', 'Export'))
        listwidget = self._show_tree(init_ParameterTree, settings)

        root = listwidget._build_context_menu(QtCore.QPoint(0, 0))
        data_menu = next(a.menu() for a in root.actions()
                         if a.menu() and a.menu().title() == 'Data')
        export_menu = next(a.menu() for a in data_menu.actions()
                           if a.menu() and a.menu().title() == 'Export')
        assert len(export_menu.actions()) == 1
        assert export_menu.actions()[0].text() == 'Export CSV'

    # ------------------------------------------------------------------
    # Callback arguments
    # ------------------------------------------------------------------

    def test_callback_clicked_and_selected_checkbox_mode(self, init_ParameterTree):
        params = dict(self.BASE_PARAMS, checkbox=True)
        settings = Parameter.create(**params)
        received = []
        settings.addContextMenuAction('Go', lambda cl, sel: received.append((cl, sel)))
        listwidget = self._show_tree(init_ParameterTree, settings)

        listwidget.select_item(listwidget.item(1), True)   # check 'det2'

        pos = listwidget.visualItemRect(listwidget.item(0)).center()
        menu = listwidget._build_context_menu(pos)
        menu.actions()[0].trigger()

        assert len(received) == 1
        clicked, selected = received[0]
        assert clicked == 'det1'
        assert selected == ['det2']

    def test_callback_clicked_and_selected_no_checkbox(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        received = []
        settings.addContextMenuAction('Go', lambda cl, sel: received.append((cl, sel)))
        listwidget = self._show_tree(init_ParameterTree, settings)

        listwidget.select_item(listwidget.item(2), True)   # highlight 'det3'

        pos = listwidget.visualItemRect(listwidget.item(0)).center()
        menu = listwidget._build_context_menu(pos)
        menu.actions()[0].trigger()

        assert len(received) == 1
        clicked, selected = received[0]
        assert clicked == 'det1'
        assert 'det3' in selected

    def test_callback_receives_none_clicked_on_empty_space(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        received = []
        settings.addContextMenuAction('Go', lambda cl, sel: received.append((cl, sel)))
        listwidget = self._show_tree(init_ParameterTree, settings)

        # y=10_000 is well outside any rendered item
        menu = listwidget._build_context_menu(QtCore.QPoint(0, 10_000))
        menu.actions()[0].trigger()

        assert len(received) == 1
        assert received[0][0] is None

    def test_no_menu_returned_when_no_actions(self, init_ParameterTree):
        settings = Parameter.create(**self.BASE_PARAMS)
        listwidget = self._show_tree(init_ParameterTree, settings)

        assert listwidget._build_context_menu(QtCore.QPoint(0, 0)) is None