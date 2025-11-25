# -*- coding: utf-8 -*-
"""
Created the 06/01/2023

@author: Sebastien Weber
"""
import sys

from qtpy import QtSvg, QtWidgets
from qtpy.QtSvg import QSvgWidget


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    widget = QSvgWidget()
    widget.show()
    widget.load(r'C:\Users\weber\Labo\Projet-Dossier candidature\Technical project\GDSII\wafer.svg')

    sys.exit(app.exec_())
