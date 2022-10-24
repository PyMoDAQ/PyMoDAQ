# -*- coding: utf-8 -*-
"""
Created the 29/07/2022

@author: Sebastien Weber
"""

from qtpy import QtWidgets, QtCore, QtGui


class LabelWithFont(QtWidgets.QLabel):

    def __init__(self, text: str = '', *args, font_name=None, font_size=None, isbold=False, isitalic=False, **kwargs):
        super().__init__(text, *args, **kwargs)

        font = QtGui.QFont()
        if font_name is not None:
            font.setFamily(font_name)
        if font_size is not None:
            font.setPointSize(font_size)

        font.setBold(isbold)
        font.setItalic(isitalic)
        self.setFont(font)
