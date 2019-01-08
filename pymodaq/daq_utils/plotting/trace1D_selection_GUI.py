# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'trace1D_selection_GUI.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(397, 473)
        self.gridLayout_2 = QtWidgets.QGridLayout(Dialog)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.delimiter_combo = QtWidgets.QComboBox(Dialog)
        self.delimiter_combo.setObjectName("delimiter_combo")
        self.delimiter_combo.addItem("")
        self.delimiter_combo.addItem("")
        self.delimiter_combo.addItem("")
        self.gridLayout.addWidget(self.delimiter_combo, 4, 1, 1, 1)
        self.retry_pb = QtWidgets.QPushButton(Dialog)
        self.retry_pb.setObjectName("retry_pb")
        self.gridLayout.addWidget(self.retry_pb, 1, 1, 2, 1)
        self.label_5 = QtWidgets.QLabel(Dialog)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 6, 0, 1, 1)
        self.col_x_sb = QtWidgets.QSpinBox(Dialog)
        self.col_x_sb.setObjectName("col_x_sb")
        self.gridLayout.addWidget(self.col_x_sb, 5, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 2, 3, 1)
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 4, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(Dialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 5, 0, 1, 1)
        self.header_sb = QtWidgets.QSpinBox(Dialog)
        self.header_sb.setObjectName("header_sb")
        self.gridLayout.addWidget(self.header_sb, 3, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 1)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.col_y_sb = QtWidgets.QSpinBox(Dialog)
        self.col_y_sb.setProperty("value", 1)
        self.col_y_sb.setObjectName("col_y_sb")
        self.gridLayout.addWidget(self.col_y_sb, 6, 1, 1, 1)
        self.data_name_edit = QtWidgets.QLineEdit(Dialog)
        self.data_name_edit.setObjectName("data_name_edit")
        self.gridLayout.addWidget(self.data_name_edit, 2, 0, 1, 1)
        self.graphicsView = PlotWidget(Dialog)
        self.graphicsView.setObjectName("graphicsView")
        self.gridLayout.addWidget(self.graphicsView, 0, 0, 1, 3)
        self.verticalLayout_2.addLayout(self.gridLayout)
        self.gridLayout_2.addLayout(self.verticalLayout_2, 0, 0, 1, 1)
        self.graphicsView.raise_()

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.delimiter_combo.setItemText(0, _translate("Dialog", "tab"))
        self.delimiter_combo.setItemText(1, _translate("Dialog", "comma"))
        self.delimiter_combo.setItemText(2, _translate("Dialog", "space"))
        self.retry_pb.setText(_translate("Dialog", "Retry\n"
"Loading!"))
        self.label_5.setText(_translate("Dialog", "Col y:"))
        self.label_3.setText(_translate("Dialog", "Delimiter:"))
        self.label_4.setText(_translate("Dialog", "Col x:"))
        self.label_2.setText(_translate("Dialog", "Header lines:"))
        self.label.setText(_translate("Dialog", "Save 1D trace in tdms as:"))

from pyqtgraph import PlotWidget

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())

