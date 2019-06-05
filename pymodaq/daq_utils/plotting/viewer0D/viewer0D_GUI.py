# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'viewer0D_GUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(598, 336)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter = QtWidgets.QSplitter(Form)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.Nhistory_sb = QtWidgets.QSpinBox(self.verticalLayoutWidget)
        self.Nhistory_sb.setReadOnly(False)
        self.Nhistory_sb.setMinimum(1)
        self.Nhistory_sb.setMaximum(1000000)
        self.Nhistory_sb.setSingleStep(100)
        self.Nhistory_sb.setProperty("value", 200)
        self.Nhistory_sb.setObjectName("Nhistory_sb")
        self.horizontalLayout_2.addWidget(self.Nhistory_sb)
        self.clear_pb = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.clear_pb.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/clear2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.clear_pb.setIcon(icon)
        self.clear_pb.setCheckable(False)
        self.clear_pb.setObjectName("clear_pb")
        self.horizontalLayout_2.addWidget(self.clear_pb)
        self.show_datalist_pb = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.show_datalist_pb.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/ChnNum.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.show_datalist_pb.setIcon(icon1)
        self.show_datalist_pb.setCheckable(True)
        self.show_datalist_pb.setObjectName("show_datalist_pb")
        self.horizontalLayout_2.addWidget(self.show_datalist_pb)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.Graph1D = PlotWidget(self.verticalLayoutWidget)
        self.Graph1D.setObjectName("Graph1D")
        self.verticalLayout.addWidget(self.Graph1D)
        self.values_list = QtWidgets.QListWidget(self.splitter)
        font = QtGui.QFont()
        font.setPointSize(20)
        self.values_list.setFont(font)
        self.values_list.setObjectName("values_list")
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)
        self.StatusBarLayout = QtWidgets.QHBoxLayout()
        self.StatusBarLayout.setObjectName("StatusBarLayout")
        self.gridLayout.addLayout(self.StatusBarLayout, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.Nhistory_sb.setToolTip(_translate("Form", "N samples in plot"))
        self.clear_pb.setToolTip(_translate("Form", "Clear plot"))
        self.show_datalist_pb.setToolTip(_translate("Form", "Show current data in a list"))

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

