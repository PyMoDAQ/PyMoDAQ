# -*- coding: utf-8 -*-
"""
Created the 28/03/2023

@author: Sebastien Weber
"""
from qtpy import QtWidgets
from pymodaq_gui.plotting.navigator import Navigator


def test_navigator(qtbot):
    widg = QtWidgets.QWidget()
    prog = Navigator(widg)

    widg.show()
    prog.list_2D_scans()


