# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
import pytest
from pathlib import Path
from qtpy import QtWidgets
from pymodaq.utils.managers import Configurator
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import ioxml

@pytest.fixture
def init_qt(qtbot):
    return qtbot


@pytest.fixture
def ini_configurator(init_qt):

    qtbot = init_qt

    external_ui = QtWidgets.QMainWindow()
    toolbar = QtWidgets.QToolBar()
    menu = QtWidgets.QMenu('Preset Manager Menu')
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    configurator = Configurator(menu=menu, toolbar=toolbar)
    configurator.settings = Path(__file__).parent.joinpath('settings.xml')

    configurator.update_entry_base()
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
