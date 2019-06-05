# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'viewer1D_GUI_dock.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(929, 769)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter_2 = QtWidgets.QSplitter(Form)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.splitter = QtWidgets.QSplitter(self.splitter_2)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName("splitter")
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout_settings = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout_settings.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_settings.setObjectName("horizontalLayout_settings")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.zoom_pb = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.zoom_pb.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Zoom_to_Selection.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.zoom_pb.setIcon(icon)
        self.zoom_pb.setCheckable(True)
        self.zoom_pb.setObjectName("zoom_pb")
        self.horizontalLayout.addWidget(self.zoom_pb)
        self.Do_math_pb = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.Do_math_pb.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Calculator.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.Do_math_pb.setIcon(icon1)
        self.Do_math_pb.setCheckable(True)
        self.Do_math_pb.setObjectName("Do_math_pb")
        self.horizontalLayout.addWidget(self.Do_math_pb)
        self.do_measurements_pb = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.do_measurements_pb.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/MeasurementStudio_32.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.do_measurements_pb.setIcon(icon2)
        self.do_measurements_pb.setCheckable(True)
        self.do_measurements_pb.setObjectName("do_measurements_pb")
        self.horizontalLayout.addWidget(self.do_measurements_pb)
        self.crosshair_pb = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.crosshair_pb.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/reset.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.crosshair_pb.setIcon(icon3)
        self.crosshair_pb.setCheckable(True)
        self.crosshair_pb.setObjectName("crosshair_pb")
        self.horizontalLayout.addWidget(self.crosshair_pb)
        self.aspect_ratio_pb = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.aspect_ratio_pb.setText("")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/zoomReset.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.aspect_ratio_pb.setIcon(icon4)
        self.aspect_ratio_pb.setCheckable(True)
        self.aspect_ratio_pb.setObjectName("aspect_ratio_pb")
        self.horizontalLayout.addWidget(self.aspect_ratio_pb)
        self.x_label = QtWidgets.QLabel(self.horizontalLayoutWidget)
        self.x_label.setObjectName("x_label")
        self.horizontalLayout.addWidget(self.x_label)
        self.y_label = QtWidgets.QLabel(self.horizontalLayoutWidget)
        self.y_label.setObjectName("y_label")
        self.horizontalLayout.addWidget(self.y_label)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_settings.addLayout(self.verticalLayout)
        self.Graph_Lineouts = PlotWidget(self.splitter)
        self.Graph_Lineouts.setObjectName("Graph_Lineouts")
        self.ROIs_widget = QtWidgets.QWidget(self.splitter_2)
        self.ROIs_widget.setMaximumSize(QtCore.QSize(300, 16777215))
        self.ROIs_widget.setObjectName("ROIs_widget")
        self.gridLayout.addWidget(self.splitter_2, 0, 0, 1, 1)
        self.StatusBarLayout = QtWidgets.QHBoxLayout()
        self.StatusBarLayout.setObjectName("StatusBarLayout")
        self.gridLayout.addLayout(self.StatusBarLayout, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.zoom_pb.setToolTip(_translate("Form", "Zoom View"))
        self.Do_math_pb.setToolTip(_translate("Form", "Do Math"))
        self.do_measurements_pb.setToolTip(_translate("Form", "Do advanced measurrments"))
        self.crosshair_pb.setToolTip(_translate("Form", "Show/hide crosshair"))
        self.aspect_ratio_pb.setToolTip(_translate("Form", "Show/hide crosshair"))
        self.x_label.setText(_translate("Form", "x:"))
        self.y_label.setText(_translate("Form", "y:"))

from pyqtgraph import PlotWidget
from pymodaq.QtDesigner_Ressources import QtDesigner_ressources_rc

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

