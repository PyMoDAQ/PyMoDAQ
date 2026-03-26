# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
import pytest
from pathlib import Path
from qtpy import QtWidgets
from pymodaq.utils.managers.configurator.configurator import Configurator
from pymodaq.utils.managers.configurator.subentries import (
    SubEntryHandlerFactory, SubEntryHandlerTypes)


factory = SubEntryHandlerFactory()


@pytest.fixture
def init_qt(qtbot):
    return qtbot


@pytest.fixture
def ini_configurator(init_qt):

    qtbot = init_qt

    external_ui = QtWidgets.QMainWindow()

    configurator = Configurator()
    configurator.settings = Path(__file__).parent.joinpath('settings.xml')

    configurator.update_entry()
    qtbot.addWidget(configurator.mainwindow)
    configurator.mainwindow.show()
    qtbot.addWidget(external_ui)

    yield configurator, qtbot

    configurator.mainwindow.close()
    external_ui.close()


class TestConfigurator:

    def test_ini(self, ini_configurator):
        """
        """
        configurator, qtbot = ini_configurator

        assert configurator.entry_type == 'configurator'
        assert configurator.entry_extension == '.config'


class TestSpecialEntryFactory:

    def test_registered_entries(self):
        for entry in SubEntryHandlerTypes.values():
            assert entry in factory.entries