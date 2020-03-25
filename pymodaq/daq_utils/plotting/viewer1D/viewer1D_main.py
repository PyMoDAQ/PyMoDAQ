from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize
import sys
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_GUI_dock import Ui_Form
from pymodaq.daq_measurement.daq_measurement_main import DAQ_Measurement
from collections import OrderedDict
from pymodaq.daq_utils.plotting.crosshair import Crosshair
import pyqtgraph as pg
import numpy as np
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as customparameter
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic import Viewer1DBasic
from pymodaq.daq_utils.plotting.roi_manager import ROIManager
import os
import pickle
import datetime

class Viewer1D(QtWidgets.QWidget,QObject):
    """this plots 1D data on a plotwidget. Math and measurement can be done on it. Datas and measurements are then exported with the signal
    data_to_export_signal
    """

    data_to_export_signal=pyqtSignal(OrderedDict) #self.data_to_export=edict(data0D=None,data1D=None,data2D=None)
    math_signal=pyqtSignal(OrderedDict) #OrderedDict:=[x_axis=...,data=...,ROI_bounds=...,operation=]
    ROI_changed=pyqtSignal()
    ROI_changed_finished=pyqtSignal()

    def __init__(self, parent=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Viewer1D, self).__init__()

        self.viewer_type='Data1D'

        if parent is None:
            parent=QtWidgets.QWidget()
        self.parent=parent

        self.roi_manager = ROIManager('1D')
        self.roi_manager.new_ROI_signal.connect(self.add_lineout)
        self.roi_manager.remove_ROI_signal.connect(self.remove_ROI)
        #self.roi_manager.ROI_changed_finished.connect(self.update_lineouts)

        self.setupUI()

        self.wait_time = 3000
        self.measurement_module = None

        self.math_module = Viewer1D_math()

        if DAQ_Measurement is None:
            self.ui.do_measurements_pb.setVisible(False)


        self._labels = []
        self.plot_channels = None
        self.plot_colors = utils.plot_colors
        self.color_list = ROIManager.color_list
        self.lo_items = OrderedDict([])
        self.lo_data = OrderedDict([])
        self.ROI_bounds = []

        self._x_axis = None

        self.datas = []  # datas on each channel. list of 1D arrays
        self.data_to_export = OrderedDict(data0D=OrderedDict(), data1D=OrderedDict(), data2D=None)
        self.measurement_dict = OrderedDict(x_axis=None, datas=[], ROI_bounds=[], operations=[], channels=[])
        # OrderedDict to be send to the daq_measurement module
        self.measure_data_dict = OrderedDict()
        # dictionnary with data to be put in the table on the form: key="Meas.{}:".format(ind)
        # and value is the result of a given lineout or measurement



    def setupUI(self):
        self.ui=Ui_Form()
        self.ui.setupUi(self.parent)


        widg = QtWidgets.QWidget()
        self.viewer = Viewer1DBasic(widg)
        self.ui.verticalLayout.addWidget(widg)
        self.ui.Graph1D = self.viewer #for backcompatibility

        self.roi_manager.viewer_widget = self.viewer.plotwidget

        self.legend = None
        self.axis_settings = dict(orientation='bottom', label='x axis', units='pxls')
        # creating the settings widget of the viewer (ROI...)

        self.ui.splitter_2.replaceWidget(1, self.roi_manager.roiwidget)
        self.ui.statusbar = QtWidgets.QStatusBar(self.parent)
        self.ui.statusbar.setMaximumHeight(15)
        self.ui.StatusBarLayout.addWidget(self.ui.statusbar)

        # create and set the zoom widget
        # self.ui.zoom_widget=Dock("1DViewer zoom", size=(300, 100), closable=True)
        self.ui.zoom_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()

        self.ui.Graph_zoom = pg.PlotWidget()
        layout.addWidget(self.ui.Graph_zoom)
        self.ui.zoom_widget.setLayout(layout)

        self.ui.zoom_region = pg.LinearRegionItem()
        self.ui.zoom_region.setZValue(-10)
        self.ui.zoom_region.setBrush('r')
        self.ui.zoom_region.setOpacity(0.2)
        self.ui.Graph_zoom.addItem(self.ui.zoom_region)
        self.zoom_plot = []
        # self.dockarea.addDock(self.ui.zoom_widget)
        self.ui.zoom_widget.setVisible(False)

        self.ui.xaxis_item = self.viewer.plotwidget.plotItem.getAxis('bottom')
        self.ui.Graph_Lineouts.hide()

        self.ui.aspect_ratio_pb.clicked.connect(self.lock_aspect_ratio)

        ##crosshair
        self.ui.crosshair = Crosshair(self.viewer.plotwidget.plotItem, orientation='vertical')
        self.ui.crosshair.crosshair_dragged.connect(self.update_crosshair_data)
        self.ui.crosshair_pb.clicked.connect(self.crosshairClicked)
        self.crosshairClicked()

        # self.ui.Measurement_widget=Dock("Measurement Module", size=(300, 100), closable=True)
        # self.dockarea.addDock(self.ui.Measurement_widget)
        self.ui.Measurement_widget = QtWidgets.QWidget()
        self.ui.Measurement_widget.setVisible(False)

        ##Connecting buttons:
        self.ui.Do_math_pb.clicked.connect(self.do_math_fun)
        self.ui.do_measurements_pb.clicked.connect(self.open_measurement_module)
        self.ui.zoom_pb.clicked.connect(self.enable_zoom)

    def update_lineouts(self):
        operations = []
        channels = []
        for ind, key in enumerate(self.roi_manager.ROIs):
            operations.append(self.roi_manager.settings.child('ROIs', key, 'math_function').value())
            channels.append(
                self.roi_manager.settings.child('ROIs', key,
                                'use_channel').opts['limits'].index(self.roi_manager.settings.child('ROIs',
                                        key, 'use_channel').value()))
            self.lo_items[key].setPen(self.roi_manager.settings.child('ROIs', key,
                                'Color').value())

        self.measurement_dict['datas'] = self.datas
        self.measurement_dict['ROI_bounds'] = [self.roi_manager.ROIs[item].getRegion() for item in
                                               self.roi_manager.ROIs]
        self.measurement_dict['channels'] = channels
        self.measurement_dict['operations'] = operations

        data_lo = self.math_module.update_math(self.measurement_dict)
        self.show_math(data_lo)

    @pyqtSlot(str)
    def remove_ROI(self, roi_name):

        item = self.lo_items.pop(roi_name)
        self.ui.Graph_Lineouts.plotItem.removeItem(item)
        self.measure_data_dict.pop("Lineout_{:s}:".format(roi_name))
        self.update_lineouts()

    @pyqtSlot(int, str)
    def add_lineout(self, index, roi_type=''):

        item=self.roi_manager.ROIs['ROI_{:02d}'.format(index)]
        item_param = self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(index))
        item_param.child(('use_channel')).setOpts(limits=self.labels)
        item_param.child(('use_channel')).setValue(self.labels[0])
        item.sigRegionChanged.connect(self.update_lineouts)
        item.sigRegionChangeFinished.connect(self.ROI_changed_finished.emit)
        for child in customparameter.iter_children_params(item_param, childlist=[]):
            if child.type() != 'group':
                child.sigValueChanged.connect(self.update_lineouts)


        item_lo=self.ui.Graph_Lineouts.plot()
        item_lo.setPen(item_param.child(('Color')).value())
        self.lo_items['ROI_{:02d}'.format(index)] = item_lo
        self.lo_data = OrderedDict([])
        for k in self.lo_items:
            self.lo_data[k] = np.zeros((1,))
        self.update_lineouts()


    def clear_lo(self):
        self.lo_data=[[] for ind in range(len(self.lo_data))]
        self.update_lineouts()

    def crosshairClicked(self):
        if self.ui.crosshair_pb.isChecked():
            self.ui.crosshair.setVisible(True)
            self.ui.x_label.setVisible(True)
            self.ui.y_label.setVisible(True)
            range=self.viewer.plotwidget.plotItem.vb.viewRange()
            self.ui.crosshair.set_crosshair_position(xpos=np.mean(np.array(range[0])))
        else:
            self.ui.crosshair.setVisible(False)
            self.ui.x_label.setVisible(False)
            self.ui.y_label.setVisible(False)


    def do_math_fun(self):
        try:
            if self.ui.Do_math_pb.isChecked():
                self.roi_manager.roiwidget.show()
                self.ui.Graph_Lineouts.show()


            else:
                self.ui.Graph_Lineouts.hide()
                self.roi_manager.roiwidget.hide()

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def do_zoom(self):
        bounds=self.ui.zoom_region.getRegion()
        self.viewer.plotwidget.setXRange(bounds[0],bounds[1])

    def enable_zoom(self):
        try:
            if not(self.ui.zoom_pb.isChecked()):
                if self.zoom_plot!=[]:
                    for plot in self.zoom_plot:
                        self.ui.Graph_zoom.removeItem(plot)
                self.ui.zoom_widget.hide()
                self.ui.zoom_region.sigRegionChanged.disconnect(self.do_zoom)

            else:
                self.zoom_plot=[]
                for ind,data in enumerate(self.datas):
                    channel=self.ui.Graph_zoom.plot()
                    channel.setPen(self.plot_colors[ind])
                    self.zoom_plot.append(channel)
                self.update_graph1D(self.datas)
                self.ui.zoom_region.setRegion([np.min(self._x_axis),np.max(self._x_axis)])

                self.ui.zoom_widget.show()
                self.ui.zoom_region.sigRegionChanged.connect(self.do_zoom)
        except Exception as e:
            self.update_status(str(e),self.wait_time)

    def ini_data_plots(self, Nplots):
        try:
            self.plot_channels=[]
            # if self.legend is not None:
            #     self.viewer.plotwidget.plotItem.removeItem(self.legend)
            self.legend = self.viewer.plotwidget.plotItem.legend
            flag = True
            while flag:
                items = [item[1].text for item in self.legend.items]
                if len(items) == 0:
                    flag = False
                else:
                    self.legend.removeItem(items[0])
            channels = []
            for ind in range(Nplots):
                channel=self.viewer.plotwidget.plot()
                channel.setPen(self.plot_colors[ind])
                self.legend.addItem(channel, self._labels[ind])
                channels.append(ind)
                self.plot_channels.append(channel)
        except Exception as e:
            self.update_status(str(e), wait_time=self.wait_time)

    def update_labels(self, labels=[]):
        try:
            labels_tmp = labels[:]
            if self.labels == labels:
                if self.labels == [] or len(self.labels) < len(self.datas):
                    self._labels = ["CH{}".format(ind) for ind in range(len(self.datas))]
            else:
                flag = True
                while flag:
                    items = [item[1].text for item in self.legend.items]
                    if len(items) == 0:
                        flag = False
                    else:
                        self.legend.removeItem(items[0])

                if len(labels) < len(self.plot_channels):
                     for ind in range(len(labels), len(self.plot_channels)):
                         labels_tmp.append('CH{:02d}'.format(ind))

                if len(labels_tmp) == len(self.plot_channels):
                    for ind, channel in enumerate(self.plot_channels):
                        self.legend.addItem(channel, labels_tmp[ind])

                self._labels = labels_tmp

            if self.labels != labels:
                for ind in range(len(self.roi_manager.ROIs)):
                    val = self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(ind), 'use_channel').value()
                    self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(ind), 'use_channel').setOpts(limits=self.labels)
                    if val not in self.labels:
                        self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(ind), 'use_channel').setValue(self.labels[0])

        except Exception as e:
            self.update_status(str(e), wait_time=self.wait_time)

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        self._labels = labels
        self.update_labels(labels)




    def lock_aspect_ratio(self):
        if self.ui.aspect_ratio_pb.isChecked():
            self.viewer.plotwidget.plotItem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.viewer.plotwidget.plotItem.vb.setAspectLocked(lock=False)

    def open_measurement_module(self):
        if not(self.ui.Do_math_pb.isChecked()):
            self.ui.Do_math_pb.setChecked(True)
            QtWidgets.QApplication.processEvents()
            self.ui.Do_math_pb.clicked.emit()
            QtWidgets.QApplication.processEvents()


        self.ui.Measurement_widget.setVisible(True)
        if self.ui.do_measurements_pb.isChecked():
            Form = self.ui.Measurement_widget
            self.measurement_module=DAQ_Measurement(Form)
            #self.ui.Measurement_widget.addWidget(Form)
            self.measurement_module.measurement_signal[list].connect(self.show_measurement)
            self.update_measurement_module()

        elif self.measurement_module is not None:
            self.measurement_module.Quit_fun()


    def remove_plots(self):
        if self.plot_channels is not None:
            for channel in self.plot_channels:
                self.viewer.plotwidget.removeItem(channel)
            self.plot_channels = None
        if self.legend is not None:
            self.viewer.plotwidget.removeItem(self.legend)


    def set_axis_label(self,axis_settings=dict(orientation='bottom',label='x axis',units='pxls')):
        axis=self.viewer.plotwidget.plotItem.getAxis(axis_settings['orientation'])
        axis.setLabel(text=axis_settings['label'], units=axis_settings['units'])
        self.axis_settings = axis_settings

    @pyqtSlot(list)
    def show_data(self, datas, labels=None, x_axis=None ):
        try:
            self.datas = datas
            self.update_labels(self.labels)

            self.data_to_export=OrderedDict(data0D=OrderedDict(), data1D=OrderedDict(), data2D=None)
            for ind,data in enumerate(datas):
                self.data_to_export['data1D']['CH{:03d}'.format(ind)] = OrderedDict()



            if self.plot_channels == [] or self.plot_channels is None: #initialize data and plots
                self.ini_data_plots(len(datas))

            elif len(self.plot_channels) != len(datas):
                self.remove_plots()
                self.ini_data_plots(len(datas))

            self.update_graph1D(datas)

            if x_axis is not None:
                self.x_axis = x_axis

            if labels is not None:
                self.update_labels(labels)

            if self.ui.do_measurements_pb.isChecked():
                self.update_measurement_module()

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)


    @pyqtSlot(list)
    def show_data_temp(self, datas):
        """f
        to plot temporary data, for instance when all pixels are not yet populated...
        """
        try:
            self.update_labels(self.labels)
            self.datas=datas

            if self.plot_channels==None: #initialize data and plots
                self.ini_data_plots(len(datas))
            elif len(self.plot_channels)!=len(datas):
                self.remove_plots()
                self.ini_data_plots(len(datas))

            for ind_plot, data in enumerate(datas):
                if self.x_axis is None:
                    self.x_axis = np.linspace(0, len(data), len(data), endpoint=False)
                    x_axis = self.x_axis
                elif len(self.x_axis) != len(data):
                    x_axis = np.linspace(0, len(data), len(data), endpoint=False)
                else:
                    x_axis = self.x_axis

                self.plot_channels[ind_plot].setData(x=x_axis, y=data)
        except Exception as e:
            self.update_status(str(e), wait_time=self.wait_time)

    @pyqtSlot(list)
    def show_math(self,data_lo):
        #self.data_to_export=OrderedDict(x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
        if len(data_lo) != 0:
            for ind, key in enumerate(self.lo_items):
                self.measure_data_dict["Lineout_{:s}:".format(key)] = data_lo[ind]
                self.data_to_export['data0D']['Measure_{:03d}'.format(ind)] = OrderedDict(data=data_lo[ind], type='roi')
            self.roi_manager.settings.child(('measurements')).setValue(self.measure_data_dict)


            for ind, key in enumerate(self.lo_items):
                self.lo_data[key] = np.append(self.lo_data[key],data_lo[ind])
                self.lo_items[key].setData(y=self.lo_data[key])

        if not (self.ui.do_measurements_pb.isChecked()):  # otherwise you export data from measurement
            self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
            self.data_to_export_signal.emit(self.data_to_export)

    @pyqtSlot(list)
    def show_measurement(self,data_meas):
        ind_offset=len(self.data_to_export['data0D'])
        for ind,res in enumerate(data_meas):
            self.measure_data_dict["Meas.{}:".format(ind)]=res
            self.data_to_export['data0D']['Measure_{:03d}'.format(ind+ind_offset)]=OrderedDict(data=res, type='roi')
        self.roi_manager.settings.child('measurements').setValue(self.measure_data_dict)
        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
        self.data_to_export_signal.emit(self.data_to_export)



    def update_crosshair_data(self,posx,posy,name=""):
        try:
            indx=utils.find_index(self._x_axis,posx)[0][0]

            string="y="
            for data in self.datas:
                string+="{:.6e} / ".format(data[indx])
            self.ui.y_label.setText(string)
            self.ui.x_label.setText("x={:.6e} ".format(posx))

        except Exception as e:
            pass

    def update_graph1D(self,datas):
        #self.data_to_export=OrderedDict(data0D=OrderedDict(),data1D=OrderedDict(),data2D=None)
        try:

            for ind_plot,data in enumerate(datas):
                if self.x_axis is None:
                    self._x_axis = np.linspace(0,len(data),len(data),endpoint=False)
                elif len(self.x_axis) != len(data):
                    self._x_axis = np.linspace(0,len(data),len(data),endpoint=False)

                self.plot_channels[ind_plot].setData(x=self.x_axis,y=data)

                if self.ui.zoom_pb.isChecked():
                    self.zoom_plot[ind_plot].setData(x=self.x_axis,y=data)
                x_axis = dict(data=self.x_axis, units=self.axis_settings['units'], label=self.axis_settings['label'])
                self.data_to_export['data1D']['CH{:03d}'.format(ind_plot)].update(OrderedDict(data=data,
                                                x_axis=x_axis, type='raw'))# to be saved or exported


            if not self.ui.Do_math_pb.isChecked(): #otherwise math is done and then data is exported
                self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
                self.data_to_export_signal.emit(self.data_to_export)
            else:
                self.measurement_dict['datas'] = datas

                data_lo = self.math_module.update_math(self.measurement_dict)
                self.show_math(data_lo)

        except Exception as e:
            self.update_status(str(e),self.wait_time)




    def update_measurement_module(self):
        xdata=self.measurement_dict['x_axis']
        ydata=self.measurement_dict['datas'][0]
        if xdata is None:
            self.measurement_module.update_data(ydata=ydata)
        else:
            self.measurement_module.update_data(xdata=xdata,ydata=ydata)

    def update_status(self,txt,wait_time=0):
        self.ui.statusbar.showMessage(txt,wait_time)

    @property
    def x_axis(self):
        return self._x_axis

    @x_axis.setter
    def x_axis(self, x_axis):
        label = 'Pxls'
        units = ''
        if isinstance(x_axis, dict):
            if 'data' in x_axis:
                xdata = x_axis['data']
            if 'label' in x_axis:
                label = x_axis['label']
            if 'units' in x_axis:
                units = x_axis['units']
        else:
            xdata=x_axis
        self._x_axis = xdata
        self.measurement_dict['x_axis'] = self._x_axis
        if self.datas != []:
            self.show_data_temp(self.datas)
        self.set_axis_label(dict(orientation='bottom', label=label, units=units))



class Viewer1D_math(QObject):
    status_sig = pyqtSignal(list)

    def __init__(self):
        super(QObject,self).__init__()   
        self.datas = []
        self.ROI_bounds = []
        self.x_axis = None
        self.operations = []
        self.channels = []
    

    def update_math(self, measurement_dict):
        try:
            if 'datas' in measurement_dict:
                self.datas=measurement_dict['datas']
            if 'ROI_bounds' in measurement_dict:
                self.ROI_bounds=measurement_dict['ROI_bounds']
            if 'x_axis' in measurement_dict:
                self.x_axis=measurement_dict['x_axis']
            if 'operations' in measurement_dict:
                self.operations=measurement_dict['operations']
            if 'channels' in measurement_dict:
                self.channels = measurement_dict['channels']

            #self.status_sig.emit(["Update_Status","doing math"])
            data_lo=[]
            for ind_meas in range(len(self.operations)):
                indexes=utils.find_index(self.x_axis, self.ROI_bounds[ind_meas])
                ind1=indexes[0][0]
                ind2=indexes[1][0]
                sub_data = self.datas[self.channels[ind_meas]][ind1:ind2]
                sub_xaxis = self.x_axis[ind1:ind2]

                if self.operations[ind_meas]=="Mean":
                    data_lo.append(np.mean(sub_data))
                elif self.operations[ind_meas]=="Sum":
                    data_lo.append(np.sum(sub_data))
                elif self.operations[ind_meas] == 'half-life' or self.operations[ind_meas] == 'expotime':
                    ind_x0 = utils.find_index(sub_data, np.max(sub_data))[0][0]
                    x0 = sub_xaxis[ind_x0]
                    sub_xaxis = sub_xaxis[ind_x0:]
                    sub_data = sub_data[ind_x0:]
                    offset = sub_data[-1]
                    N0 = np.max(sub_data) - offset
                    if self.operations[ind_meas] == 'half-life':
                        time = sub_xaxis[utils.find_index(sub_data - offset, 0.5 * N0)[0][0]]-x0
                    elif self.operations[ind_meas] == 'expotime':
                        time = sub_xaxis[utils.find_index(sub_data - offset, 0.37 * N0)[0][0]] - x0
                    data_lo.append(time)

            return data_lo
        except:
            return []





if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Form=QtWidgets.QWidget()
    prog = Viewer1D(Form)

    from pymodaq.daq_utils.daq_utils import gauss1D
    x=np.linspace(0,200,201)
    y1=gauss1D(x,75,25)
    y2=gauss1D(x,120,50,2)
    tau_half = 27
    tau2=100
    x0=50
    dx=20
    ydata_expodec = np.zeros((len(x)))
    ydata_expodec[:50] = 1*gauss1D(x[:50],x0,dx,2)
    ydata_expodec[50:] = 1*np.exp(-(x[50:]-x0)/(tau_half/np.log(2)))#+1*np.exp(-(x[50:]-x0)/tau2)
    ydata_expodec += 0.1*np.random.rand(len(x))

    # x = np.sin(np.linspace(0,6*np.pi,201))
    # y = np.sin(np.linspace(0, 6*np.pi, 201)+np.pi/2)



    Form.show()
    prog.ui.Do_math_pb.click()
    QtWidgets.QApplication.processEvents()
    prog.x_axis = x
    #prog.show_data([y, y+2])
    prog.show_data([y1, y2, ydata_expodec])
    QtWidgets.QApplication.processEvents()
    prog.update_labels(['coucou', 'label2'])
    sys.exit(app.exec_())

