# -*- coding: utf-8 -*-
"""
Created the 06/01/2023

@author: Sebastien Weber
"""

import sys
from qtpy import QtWidgets, QtCore, QtSvg
from pyqtgraph.widgets.GraphicsView import GraphicsView


class SVGView:

    def __init__(self, parent: QtWidgets.QWidget = None):
        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent_widget = parent
        self.parent_widget.setLayout(QtWidgets.QHBoxLayout())
        self.graphicsView = GraphicsView()
        self.parent_widget.layout().addWidget(self.graphicsView)

        svg_item = QtSvg.QGraphicsSvgItem(r'C:\Users\weber\Labo\Projet-Dossier candidature\Technical project\GDSII\wafer.svg')

        self.graphicsView.sceneObj.addItem(svg_item)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    widget = QtWidgets.QWidget()
    prog = SVGView(widget)
    widget.show()

    sys.exit(app.exec_())
