# -*- coding: utf-8 -*-
"""
Created the 29/07/2022

@author: Sebastien Weber
"""

from qtpy import QtWidgets, QtCore, QtGui
from pymodaq_gui.utils.styling import create_font


class LabelWithFont(QtWidgets.QLabel):

    def __init__(self, text: str = '', *args,
                 font_name='Tahoma', font_size=14, isbold=True,
                 isitalic=True, **kwargs):
        super().__init__(text, *args, **kwargs)

        font = create_font(font_name, font_size, isbold, isitalic)
        self.setFont(font)
