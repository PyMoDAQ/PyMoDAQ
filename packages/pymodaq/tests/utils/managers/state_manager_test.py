# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
import pytest
from pathlib import Path
from qtpy import QtWidgets
from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq.utils.managers.state.subentries import (
    SubEntryHandlerFactory, SubEntryHandlerTypes)


factory = SubEntryHandlerFactory()


@pytest.fixture
def init_qt(qtbot):
    return qtbot


@pytest.fixture
def ini_state_manager(init_qt):

    qtbot = init_qt

    external_ui = QtWidgets.QMainWindow()

    state_manager = StateManager()
    state_manager.settings = Path(__file__).parent.joinpath('settings.xml')

    state_manager.update_entry()
    qtbot.addWidget(state_manager.mainwindow)
    state_manager.mainwindow.show()
    qtbot.addWidget(external_ui)

    yield state_manager, qtbot

    state_manager.mainwindow.close()
    external_ui.close()


class TestStateManager:

    def test_ini(self, ini_state_manager):
        """
        """
        state_manager, qtbot = ini_state_manager

        assert state_manager.entry_type == 'state'
        assert state_manager.entry_extension == '.state'


class TestSpecialEntryFactory:

    def test_registered_entries(self):
        for entry in SubEntryHandlerTypes.values():
            assert entry in factory.entries