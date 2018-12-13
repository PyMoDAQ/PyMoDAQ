from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal
import sys
from PyMoDAQ.DAQ_Utils.plotting.trace1D_selection_GUI import Ui_Dialog
import python_lib as mylib
import pyqtgraph
import numpy as np


class Trace1D_selection(Ui_Dialog):
    def __init__(self,parent,file_path):
        super(Ui_Dialog,self).__init__()
        self.ui=Ui_Dialog()
        self.ui.setupUi(parent)
        self.wait_time=2000

        self.ui.statusbar=QtWidgets.QStatusBar(parent)
        self.ui.verticalLayout_2.addWidget(self.ui.statusbar)

        self.ui.plot_area=self.ui.graphicsView.plotItem
        self.ui.plot_area.enableAutoRange('xy', True)
        self.ui.curve_1D=self.ui.plot_area.plot(pen='w')
        
        self.file_path=file_path
        self.selected_data=Selection_data(file_path)

        #connect signals
        self.ui.buttonBox.accepted.connect(self.selected_data.accept)
        self.ui.buttonBox.rejected.connect(self.selected_data.reject)
        self.ui.retry_pb.clicked.connect(self.import_data)
        self.ui.data_name_edit.editingFinished.connect(self.update_data_name)


        if self.file_path!=None:
            self.import_data()
    
    def update_data_name(self):
        self.selected_data.data_name=self.ui.data_name_edit.text()
                    
    def update_status(self,status,wait_time=0):
        self.ui.statusbar.showMessage(status,wait_time)

    def import_data(self):
        try:
            delimiter_text=self.ui.delimiter_combo.currentText()
            header_lines=self.ui.header_sb.value()
            xcol=self.ui.col_x_sb.value()
            ycol=self.ui.col_y_sb.value()

            if delimiter_text=="tab":
                delimiter='\t'
            elif delimiter_text=="comma":
                delimiter=','
            elif delimiter_text=="space":
                delimiter=" "

            data = np.loadtxt(self.file_path, delimiter=delimiter, skiprows=header_lines)
            shape=data.shape
            if len(shape)<=2:
                if shape[0]>shape[1]:
                    self.xdata=data[:,xcol]
                    self.ydata=data[:,ycol]
                else:
                    self.xdata=data[xcol,:]
                    self.ydata=data[ycol,:]
                self.ui.curve_1D.setData(self.xdata,self.ydata)
                self.selected_data.xdata=self.xdata
                self.selected_data.ydata=self.ydata
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)



class Selection_data(QObject):
    accept_reject=pyqtSignal(list)
    def __init__(self,file_path,xdata=None,ydata=None,data_name=None):
        super(QObject,self).__init__()
        self.xdata=xdata
        self.ydata=ydata
        self.data_name=data_name

    def accept(self):
        self.accept_reject.emit([True,self.data_name,self.xdata,self.ydata])
        
    def reject(self):
        self.accept_reject.emit([False,self.data_name,self.xdata,self.ydata])


if __name__ == '__main__':
	
    app = QtWidgets.QApplication(sys.argv);
    Dialog = QtWidgets.QDialog();
    file_path="D:\\Data\\2016\\Vincent\\trace_1D_test.dat";
    prog = Trace1D_selection(Dialog,file_path);
    Dialog.show();
    sys.exit(app.exec_())







