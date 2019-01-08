from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QLocale
import sys

from pymodaq.daq_utils.plotting.viewer0D.viewer0D_GUI import Ui_Form

import numpy as np
from easydict import EasyDict as edict
from collections import OrderedDict

class Viewer0D(QtWidgets.QWidget,QObject):
    data_to_export_signal=pyqtSignal(OrderedDict) #edict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)

    def __init__(self,parent=None,dock=None):
        """

        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Viewer0D,self).__init__()
        if parent is None:
            parent=QtWidgets.QWidget()
        self.ui=Ui_Form()
        self.ui.setupUi(parent)
        #self.dockarea=parent
        #if dock is not None:
        #    self.ui.viewer_dock = dock
        #    self.ui.viewer_dock.setTitle("0DViewer")
        #else:
        #    self.ui.viewer_dock = Dock("0DViewer", size=(1, 1))     ## give this dock the minimum possible size
        #    self.dockarea.addDock(self.ui.viewer_dock)

        #self.ui.viewer_dock.addWidget(widget_viewer)
        

        self.ui.statusbar=QtWidgets.QStatusBar(parent)
        self.ui.statusbar.setMaximumHeight(15)
        self.ui.StatusBarLayout.addWidget(self.ui.statusbar)
        self.ui.status_message=QtWidgets.QLabel()
        self.ui.status_message.setMaximumHeight(15)
        self.ui.statusbar.addWidget(self.ui.status_message)
        

        self.ui.xaxis_item=self.ui.Graph1D.plotItem.getAxis('bottom')
        
        self.viewer_type='Data0D'
        self.wait_time=1000

        self.plot_channels=None
        self.plot_colors=['r', 'g','b',  'c', 'm', 'y', 'k',' w']

        self.Nsamples=self.ui.Nhistory_sb.value()

        self.x_axis=np.linspace(0,self.Nsamples-1,self.Nsamples)
        self.datas=[] #datas on each channel. list of 1D arrays 
        self.legend=self.ui.Graph1D.plotItem.addLegend()
        self.data_to_export=OrderedDict(data0D=OrderedDict(),data1D=None,data2D=None)
        self.list_items=None

        ##Connecting buttons:
        self.ui.clear_pb.clicked.connect(self.clear_data)
        self.ui.Nhistory_sb.valueChanged.connect(self.update_x_axis)
        self.ui.show_datalist_pb.clicked.connect(self.show_data_list)

        self.show_data_list(False)


    def show_data_list(self,state=None):
        if state is None:
            state=self.ui.show_datalist_pb.isChecked()
        self.ui.values_list.setVisible(state)

    def update_x_axis(self,Nhistory):
        self.Nsamples=Nhistory
        self.x_axis=np.linspace(0,self.Nsamples-1,self.Nsamples)

    def update_channels(self):
        if self.plot_channels!=None:
            for ind,item in enumerate(self.plot_channels):
                self.legend.removeItem(item.name())
                self.ui.Graph1D.removeItem(item)
            self.plot_channels=None

    def clear_data(self):
        N=len(self.datas)
        self.datas=[]
        for ind in range(N):
            self.datas.append(np.array([]))
        self.x_axis=np.array([])
        for ind_plot,data in enumerate(self.datas):
            self.plot_channels[ind_plot].setData(x=self.x_axis,y=data)

    def update_status(self,txt,wait_time=0):
        self.ui.statusbar.showMessage(txt,wait_time)

    @pyqtSlot(list)
    def show_data_temp(self,datas):
        """
        to plot temporary data, for instance when all pixels are not yet populated...
        """
        pass
        
    @pyqtSlot(list)
    def show_data(self,datas):
         try:
            self.data_to_export=OrderedDict(data0D=OrderedDict(),data1D=None,data2D=None)
            if self.plot_channels==None or len(self.plot_channels)!=len(datas):
                if self.plot_channels!=None:
                    if len(self.plot_channels)!=len(datas):
                        for channel in self.plot_channels:
                            self.ui.Graph1D.removeItem(channel)

                self.plot_channels=[]
                self.datas=[]
                self.ui.values_list.clear()
                self.ui.values_list.addItems(['{:.06e}'.format(data[0]) for data in datas])
                self.list_items=[self.ui.values_list.item(ind) for ind in range(self.ui.values_list.count())]
                for ind in range(len(datas)):
                    self.datas.append(np.array([]))
                    #channel=self.ui.Graph1D.plot(np.array([]))
                    channel=self.ui.Graph1D.plot(y=np.array([]),name="CH{}".format(ind))
                    channel.setPen(self.plot_colors[ind])
                    #self.legend.addItem(channel,"CH{}".format(ind))
                    self.plot_channels.append(channel)

            for ind,data in enumerate(datas):
                self.list_items[ind].setText('{:.06e}'.format(data[0]))
       
            self.update_Graph1D(datas)
         except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def update_Graph1D(self,datas):
        try:
            data_tot=[]
            L=len(self.datas[0])+1
            if L>self.Nsamples:
                self.x_axis+=1
            else:
                self.x_axis=np.linspace(0,L-1,L)
            for ind_plot,data in enumerate(datas):
                data_tmp=self.datas[ind_plot]
                data_tmp=np.append(data_tmp,data)
                
                if len(data_tmp)>self.Nsamples:
                    data_tmp=data_tmp[L-self.Nsamples:]
                   
                data_tot.append(data_tmp)
                
                self.plot_channels[ind_plot].setData(x=self.x_axis,y=data_tmp)
                self.data_to_export['data0D']['CH{:03d}'.format(ind_plot)]=data[0]
            self.datas=data_tot  
                                 
             #
            self.data_to_export_signal.emit(self.data_to_export)


        except Exception as e:
            self.update_status(str(e),self.wait_time)



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Form=QtWidgets.QWidget();
    prog = Viewer0D(Form)
    from pymodaq.daq_utils.daq_utils import gauss1D
    x=np.linspace(0,200,201);y1=gauss1D(x,75,25);y2=gauss1D(x,120,50,2);Form.show()
    for ind,data in enumerate(y1):prog.show_data([data,y2[ind]]);QtWidgets.QApplication.processEvents()

    sys.exit(app.exec_())

