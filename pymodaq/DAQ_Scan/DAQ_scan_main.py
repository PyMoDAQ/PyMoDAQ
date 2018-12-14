from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QTimer, QDateTime, QDate, QTime

import sys
import logging
logging.basicConfig(filename='daq_scan.log',level=logging.DEBUG)


from  pymodaq.daq_scan.gui.daq_scan_gui import Ui_Form
from pymodaq.daq_utils.h5browser import H5Browser
from collections import OrderedDict
import pymodaq.daq_utils.daq_utils as utils
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
import numpy as np

from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.manage_preset import PresetManager

import matplotlib.image as mpimg
from pymodaq.daq_move.daq_move_main import DAQ_Move
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer

from pymodaq.daq_utils.plotting.qled import QLED
from easydict import EasyDict as edict
from pymodaq.daq_utils import daq_utils
from pathlib import Path
import tables
import datetime
import pickle
import os
from pymodaq.daq_utils.daq_utils import make_enum

# DAQ_Move_Stage_type=make_enum('daq_move')
# DAQ_0DViewer_Det_type=make_enum('daq_0Dviewer')
# DAQ_1DViewer_Det_type=make_enum('daq_1Dviewer')
# DAQ_2DViewer_Det_type=make_enum('daq_2Dviewer')

class QSpinBox_ro(QtWidgets.QSpinBox):
    def __init__(self, **kwargs):
        super(QtWidgets.QSpinBox,self).__init__()
        self.setMaximum(100000)
        self.setReadOnly(True)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

def set_param_from_param(param_old,param_new):
    """
        Walk through parameters children and set values using new parameter values.
    """
    for child_old in param_old.children():
        try:
            path=param_old.childPath(child_old)
            child_new=param_new.child(*path)
            param_type=child_old.type()

            if 'group' not in param_type: #covers 'group', custom 'groupmove'...
                try:
                    if 'list' in param_type:#check if the value is in the limits of the old params (limits are usually set at initialization)
                        if child_new.value() not in child_old.opts['limits']:
                            child_old.opts['limits'].append(child_new.value())

                        child_old.setValue(child_new.value())
                    elif 'str' in param_type or 'browsepath' in param_type or 'text' in param_type:
                        if child_new.value()!="":#to make sure one doesnt overwrite something
                            child_old.setValue(child_new.value())
                    else:
                        child_old.setValue(child_new.value())
                except Exception as e:
                    print(str(e))
            else:
                set_param_from_param(child_old,child_new)
        except Exception as e:
            print(str(e))


class DAQ_Scan(QtWidgets.QWidget,QObject):
    """
              ======================= =====================================
              **Attributes**          **Type**
              *title*                 string
              *splash_sc*             instance of QtWidgets.QSplashScreen
              *init_prog*             boolean
              *widgetsettings*        instance of QtWidgets.QWidget
              *dockarea*              instance of pyqtgraph.DockArea
              *mainwindow*            instance of pyqtgraph.DockArea
              *dockarea*              instance of pyqtgraph.DockArea
              *plot_items*            list
              *plot_colors*           string list
              *wait_time*             int
              *settings_tree*         instance of pyqtgraph.parametertree
              *DAQscan_settings*      instance of pyqtgraph.parametertree
              *scan_parameters*       dictionnary
              *date*                  instance of QDateTime
              *params_dataset*        dictionnary list
              *params_scan*           dictionnary list
              *param*                 dictionnary list
              *params_move*           dictionnary list
              *params_det*            dictionnary list
              *dataset_attributes*    instance of pyqtgraph.parametertree
              *scan_attributes*       instance of pyqtgraph.parametertree
              *scan_x_axis*           float array
              *scan_y_axis*           float array
              *scan_data_1D*          double precision float array
              *scan_data_2D*          double precision float array
              *ind_scan*              int
              *scan_data_2D_to_save*  double precision float array
              *scan_data_1D_to_save*  double precision float array
              *save_parameters*       dictionnary
              *det_modules_scan*      Object list
              *move_modules_scan*     Object list
              *menubar*               instance of QMenuBar
              *log_signal*            instance of pyqtSignal
              ======================= =====================================
    """
    command_DAQ_signal=pyqtSignal(list)
    log_signal=pyqtSignal(str)

    def __init__(self,parent,fname="",move_modules=None,detector_modules=None):
        """
            | daq_scan(parent,fname="",move_modules=None,detector_modules=None) is a user interface that will enable scanning of motors controlled by the module daq_move and acquisition of signals using DAQ_0DViewer,DAQ_1DViewer or DAQ_2DViewer.
            |
            | Parent is the parent Widget ( a QWidget in general).
            |
            | Fname is a path pointing to a png image to be displayed at the beginning in the 2D viewer of the scan module.
            |
            | Move_modules is a dict of the type move_modules=dict(polarization=DAQ_Move_polarization) where DAQ_Move_polarization is an instance of the daq_move class.
            |
            | Detector_modules is a dict of the type detector_modules=dict(current=DAQ_0D_current) where DAQ_0D_current is an instance of the DAQ_0DViewer class.
            |
            | The detector module can be any instance in the list:  DAQ_0DViewer, DAQ_1DViewer, DAQ_2DViewer. These modules have in common a signal: export_data_signal exporting a dict of the type: dict:=[x_axis=...,data=list of vectors...,data_measurements=list of floats] to be connected to main gui
            |



            See Also
            --------
            move_to_crosshair, DAQscan_settings_changed, update_plot_det_items, update_scan_type, add_comments, add_log, set_scan, Quit_fun, start_scan, stop_scan, set_ini_positions
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Scan,self).__init__()
        self.title='daq_scan'
        splash=QtGui.QPixmap('..//documentation//splash.png')
        self.splash_sc=QtWidgets.QSplashScreen(splash,Qt.WindowStaysOnTopHint)
        self.init_prog=True

        self.ui=Ui_Form()
        widgetsettings=QtWidgets.QWidget()
        self.ui.setupUi(widgetsettings)


        self.dockarea=parent
        self.mainwindow=parent.parent()
        self.mainwindow.setVisible(False)


        #%% create scan dock and make it a floating window
        self.ui.scan_dock = Dock("Scan", size=(1, 1), autoOrientation=False)     ## give this dock the minimum possible size
        self.ui.scan_dock.setOrientation('vertical')

        self.ui.scan_dock.addWidget(widgetsettings)
        self.dockarea.addDock(self.ui.scan_dock,'left')
        

        #%% create logger dock
        self.ui.logger_dock=Dock("Logger")
        self.ui.logger_list=QtWidgets.QListWidget()
        self.ui.logger_list.setMinimumWidth(300)
        self.ui.logger_dock.addWidget(self.ui.logger_list)
        self.dockarea.addDock(self.ui.logger_dock,'top')
        self.ui.logger_dock.setVisible(False)

        #%% init the 2D viewer
        self.ui.scan2D_graph_widget=QtWidgets.QWidget()
        self.ui.scan2D_graph=Viewer2D(self.ui.scan2D_graph_widget)
        self.ui.scan2D_layout.addWidget(self.ui.scan2D_graph_widget)
        self.ui.scan2D_graph.ui.Show_histogram.setChecked(False)
        self.ui.scan2D_graph.ui.histogram_blue.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_green.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_red.setVisible(False)
        self.ui.move_to_crosshair_cb=QtWidgets.QCheckBox("Move at doubleClicked")
        self.ui.ROIselect=pg.RectROI([0,0],[10,10])
        self.ui.scan2D_graph.ui.plotitem.addItem(self.ui.ROIselect)
        self.ui.ROIselect.setVisible(False)
        self.overlays=[]#%list of imageItem items displaying 2D scans info

        self.ui.overlay2D_pb=QtWidgets.QPushButton("")
        self.ui.overlay2D_pb.setCheckable(True)
        self.ui.overlay2D_pb.setToolTip('Show/hide previsous 2D scans')
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/overlay.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.overlay2D_pb.setIcon(icon)

        self.ui.ROIselect_pb=QtWidgets.QPushButton("")
        self.ui.ROIselect_pb.setCheckable(True)
        self.ui.ROIselect_pb.setToolTip('Show/hide ROI scan area selection')
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/Region.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.ROIselect_pb.setIcon(icon2)

        self.ui.scan2D_graph.ui.horizontalLayout_2.addWidget(self.ui.ROIselect_pb)
        self.ui.scan2D_graph.ui.horizontalLayout_2.addWidget(self.ui.overlay2D_pb)
        self.ui.scan2D_graph.ui.horizontalLayout_2.addWidget(self.ui.move_to_crosshair_cb)

        self.ui.scan2D_graph.sig_double_clicked.connect(self.move_to_crosshair)
        self.ui.overlay2D_pb.clicked.connect(self.show_overlay)
        self.ui.ROIselect_pb.clicked.connect(self.show_ROIselect)
        #%% init and set the status bar
        self.ui.statusbar=QtWidgets.QStatusBar(parent)
        self.ui.statusbar.setMaximumHeight(25)
        self.ui.StatusBarLayout.addWidget(self.ui.statusbar)
        self.ui.log_message=QtWidgets.QLabel('Initializing')
        self.ui.statusbar.addPermanentWidget(self.ui.log_message)
        self.ui.N_scan_steps_sb=QSpinBox_ro()
        self.ui.N_scan_steps_sb.setToolTip('Total number of steps')
        self.ui.indice_scan_sb=QSpinBox_ro()
        self.ui.indice_scan_sb.setToolTip('Current step value')
        self.ui.scan_done_LED=QLED()
        self.ui.scan_done_LED.setToolTip('Scan done state')
        self.ui.statusbar.addPermanentWidget(self.ui.N_scan_steps_sb)
        self.ui.statusbar.addPermanentWidget(self.ui.indice_scan_sb)
        self.ui.statusbar.addPermanentWidget(self.ui.scan_done_LED)


        self.plot_items=[]
        self.plot_colors=['b', 'g', 'r', 'c', 'm', 'y', 'k',' w']

        self.ui.splitter.setSizes([500, 1200])
        if fname!="":
            image=mpimg.imread(fname)
            self.ui.scan2D_graph.setImage(np.flipud(image[:,:,2]),np.flipud(image[:,:,1]),np.flipud(image[:,:,0]))

        self.wait_time=1000


        self.ui.scan_done_LED.set_as_false()
        self.ui.scan_done_LED.clickable=False
        self.ui.start_scan_pb.setEnabled(False)
        self.ui.stop_scan_pb.setEnabled(False)


        #displaying the scan list tree
        self.scan_tree = ParameterTree()
        self.scan_tree.setMaximumWidth(300)
        self.scan_tree.setMinimumWidth(300)
        self.ui.verticalLayout.addWidget(self.scan_tree)
        self.scan_tree.setVisible(False)
        params_scan = [{'title': 'Scans', 'name': 'scans', 'type': 'group', 'children': []}]
        self.scan_list=Parameter.create(name='Scan_List', type='group', children=params_scan)
        self.scan_tree.setParameters(self.scan_list, showTop=False)
        self.scan_list.sigTreeStateChanged.connect(self.scan_list_changed)


        #displaying the settings Tree

        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(300)
        self.ui.settings_layout.addWidget(self.settings_tree)
        params = [
        {'title': 'Moves/Detectors', 'name': 'Move_Detectors', 'type': 'group', 'children': [
            {'name': 'Detectors', 'type': 'itemselect'},
            {'name': 'Moves', 'type': 'itemselect'}
            ]},
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'children': [
            {'title': 'Wait time (ms)','name': 'wait_time', 'type': 'int', 'value': 0},
            {'title': 'Timeout (ms)','name': 'timeout', 'type': 'int', 'value': 10000},
            ]},
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Scan type:','name': 'scan_type', 'type': 'list', 'values': ['Scan1D','Scan2D'],'value': 'Scan1D'},
            #{'title': 'Plot type:','name': 'plot_type', 'type': 'list', 'values': ['1D','2D'],'value': '1D'},
            {'title': 'Plot from:','name': 'plot_from', 'type': 'list'},
            {'title': 'Scan1D settings','name': 'scan1D_settings', 'type': 'group', 'children': [
                    {'title': 'Scan type:','name': 'scan1D_type', 'type': 'list', 'values': ['Linear','Linear back to start'],'value': 'Linear'},
                    {'title': 'Start:','name': 'start_1D', 'type': 'float', 'value': 0.},
                    {'title': 'Stop:','name': 'stop_1D', 'type': 'float', 'value': 10.},
                    {'title': 'Step:','name': 'step_1D', 'type': 'float', 'value': 1.}
                    ]},
            {'title': 'Scan2D settings', 'name': 'scan2D_settings', 'type': 'group','visible': False, 'children': [
                    {'title': 'Scan type:','name': 'scan2D_type', 'type': 'list', 'values': ['Spiral','Linear', 'back&forth'],'value': 'Spiral'},
                    {'title': 'Start Ax1:','name': 'start_2d_axis1', 'type': 'float', 'value': 0., 'visible':True},
                    {'title': 'Start Ax2:','name': 'start_2d_axis2', 'type': 'float', 'value': 10., 'visible':True},
                    {'title': 'Stop Ax1:','name': 'stop_2d_axis1', 'type': 'float', 'value': 10., 'visible':False},
                    {'title': 'Stop Ax2:','name': 'stop_2d_axis2', 'type': 'float', 'value': 40., 'visible':False},
                    {'title': 'Step Ax1:','name': 'step_2d_axis1', 'type': 'float', 'value': 1., 'visible':False},
                    {'title': 'Step Ax2:','name': 'step_2d_axis2', 'type': 'float', 'value': 5., 'visible':False},
                    {'title': 'Rstep:','name': 'Rstep_2d', 'type': 'float', 'value': 1., 'visible':True},
                    {'title': 'Rmax:','name': 'Rmax_2d', 'type': 'float', 'value': 10., 'visible':True}
                    ]},
            ]},
        {'title': 'Saving options:', 'name': 'saving_options', 'type': 'group', 'children': [
            {'title': 'Save 2D datas:','name': 'save_2D', 'type': 'bool', 'value': True},
            {'title': 'Base path:','name': 'base_path', 'type': 'browsepath', 'value': 'C:\Data', 'filetype': False},
            {'title': 'Base name:','name': 'base_name', 'type': 'str', 'value': 'Scan','readonly': True},
            {'title': 'Current path:','name': 'current_scan_path', 'type': 'text', 'value': 'C:\Data','readonly': True},
            {'title': 'Current file name:','name': 'current_filename', 'type': 'list', 'value': ''},
            {'title': 'Comments:','name': 'add_comments', 'type': 'text_pb', 'value': ''},
            {'title': 'h5file:','name': 'current_h5_file', 'type': 'text_pb', 'value': '','readonly': True},
            {'title': 'Compression options:', 'name': 'compression_options', 'type': 'group', 'children': [
                {'title': 'Compression library:','name': 'h5comp_library', 'type': 'list', 'value': 'zlib', 'values': ['zlib', 'lzo', 'bzip2', 'blosc']},
                {'title': 'Compression level:','name': 'h5comp_level', 'type': 'int', 'value': 5, 'min': 0 , 'max': 9},
                ]},
            ]}

        ]

        self.DAQscan_settings=Parameter.create(name='Settings', type='group', children=params)
        self.settings_tree.setParameters(self.DAQscan_settings, showTop=False)
        self.DAQscan_settings.sigTreeStateChanged.connect(self.DAQscan_settings_changed)
        self.DAQscan_settings.child('Move_Detectors','Detectors').sigValueChanged.connect(self.update_plot_det_items)
        self.DAQscan_settings.child('scan_options','scan2D_settings','scan2D_type').sigValueChanged.connect(self.update_scan_type)
        self.DAQscan_settings.child('saving_options','current_h5_file').sigActivated.connect(lambda : self.update_file_paths(update_h5=True))
        self.DAQscan_settings.child('saving_options','add_comments').sigActivated.connect(self.add_comments)
        self.scan_parameters=edict()#contains information about scan to be done, such as Nsteps, x_axis...


        #params about dataset attributes and scan attibutes
        date=QDateTime(QDate.currentDate(),QTime.currentTime())
        params_dataset=[{'title': 'Dataset information', 'name': 'dataset_info', 'type': 'group', 'children':[
                            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': 'Sebastien Weber'},
                            {'title': 'Date/time:', 'name': 'date_time', 'type': 'date_time', 'value': date},
                            {'title': 'Sample:', 'name': 'sample', 'type': 'str', 'value':''},
                            {'title': 'Experiment type:', 'name': 'experiment_type', 'type': 'str', 'value': ''},
                            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''}]}]

        params_scan=[{'title': 'Scan information', 'name': 'scan_info', 'type': 'group', 'children':[
                            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': 'Sebastien Weber'},
                            {'title': 'Date/time:', 'name': 'date_time', 'type': 'date_time', 'value': date},
                            {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'value':'Scan1D', 'values':['Scan1D','Scan2D']},
                            {'title': 'Scan name:', 'name': 'scan_name', 'type': 'str', 'value': '', 'readonly': True},
                            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''},
                            ]}]


        self.preset_manager=PresetManager()

        self.dataset_attributes=Parameter.create(name='Attributes', type='group', children=params_dataset)
        self.scan_attributes=Parameter.create(name='Attributes', type='group', children=params_scan)


        self.scan_x_axis=None
        self.scan_y_axis=None
        self.scan_data_1D=np.array([])
        self.scan_data_2D=[]
        self.ind_scan=None
        self.scan_data_2D_to_save=[]
        self.scan_data_1D_to_save=[]

        self.move_modules=[]
        self.detector_modules=[]

        self.save_parameters=edict()
        self.save_parameters.h5_file=None
        self.save_parameters.h5_file_path=None
        #self.update_file_paths()

        self.det_modules_scan=[]
        self.move_modules_scan=[]

        #creating the menubar
        self.menubar=self.mainwindow.menuBar()
        self.create_menu(self.menubar)

#        connecting
        self.log_signal[str].connect(self.add_log)
        self.ui.set_scan_pb.clicked.connect(self.set_scan)
        self.ui.quit_pb.clicked.connect(self.Quit_fun)

        self.ui.start_scan_pb.clicked.connect(self.start_scan)
        self.ui.stop_scan_pb.clicked.connect(self.stop_scan)
        self.ui.set_ini_positions_pb.clicked.connect(self.set_ini_positions)

        self.mainwindow.setVisible(True)
        self.ui.logger_dock.float()

    def show_ROIselect(self):
        if self.ui.ROIselect_pb.isChecked():
            self.ui.ROIselect.setVisible(False)
        else:
            self.ui.ROIselect.setVisible(True)

    def show_overlay(self):
        if self.ui.overlay2D_pb.isChecked():
            self.scan_tree.setVisible(True)
            self.list_2Dscans()
        else:
            self.scan_tree.setVisible(False)

    def scan_list_changed(self,param,changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, update the DAQscan_settings tree consequently.

            =============== ============================================ ==============================
            **Parameters**    **Type**                                     **Description**
            *param*           instance of pyqtgraph parameter              the parameter to be checked
            *changes*         (parameter,change,information) tuple list    the current changes state
            =============== ============================================ ==============================
        """
        for param, change, data in changes:
            path = self.scan_list.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':pass

            elif change == 'value':
                if data['checked']:
                    #check if 2D scan of 0D datas are presents:
                    scan_group=self.save_parameters.h5_file.get_node(data['path'])
                    for node in self.save_parameters.h5_file.walk_nodes(data['path']):
                        if 'data_type' in node._v_attrs and 'scan_type' in node._v_attrs:
                            if node._v_attrs['data_type']=='0D' and node._v_attrs['scan_type']=='Scan2D':
                                im=pg.ImageItem()
                                im.setOpacity(0.25)
                                im.setOpts(axisOrder='row-major')
                                self.ui.scan2D_graph.ui.plotitem.addItem(im)
                                im.setImage(node.read())
                                x_axis=self.save_parameters.h5_file.get_node(data['path']+'/scan_x_axis_unique').read()
                                y_axis=self.save_parameters.h5_file.get_node(data['path']+'/scan_y_axis_unique').read()
                                im.setRect(QtCore.QRectF(np.min(x_axis),np.min(y_axis),np.max(x_axis)-np.min(x_axis),np.max(y_axis)-np.min(y_axis)))
                                
                                self.overlays.append(dict(name=param.name(),image=im))
                                break #means it plots only the first 0D channel
                else:
                    for ind, im in enumerate(self.overlays):
                        if im['name']==param.name():
                            self.ui.scan2D_graph.ui.plotitem.removeItem(im['image'])
                            self.overlays.pop(ind)

            elif change == 'parent':pass


    def DAQscan_settings_changed(self,param,changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, update the DAQscan_settings tree consequently.

            =============== ============================================ ==============================
            **Parameters**    **Type**                                     **Description**
            *param*           instance of pyqtgraph parameter              the parameter to be checked
            *changes*         (parameter,change,information) tuple list    the current changes state
            =============== ============================================ ==============================
        """
        for param, change, data in changes:
            path = self.DAQscan_settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':pass

            elif change == 'value':
                if param.name()=='scan_type':
                    if data=='Scan1D':
                        self.DAQscan_settings.child('scan_options','scan1D_settings').show()
                        self.DAQscan_settings.child('scan_options','scan2D_settings').hide()
                    else:
                        self.DAQscan_settings.child('scan_options','scan1D_settings').hide()
                        self.DAQscan_settings.child('scan_options','scan2D_settings').show()
            elif change == 'parent':pass



    def save_layout_state(self):
        """
            Save the current layout state in the select_file obtained pathname file.
            Once done dump the pickle.

            See Also
            --------
            DAQ_utils.select_file
        """
        try:
            dockstate = self.dockarea.saveState()
            fname=daq_utils.select_file(start_path=None, save=True, ext='dock')
            if fname is not None:
                with open(str(fname), 'wb') as f:
                    pickle.dump(dockstate, f, pickle.HIGHEST_PROTOCOL)
        except: pass

    def load_layout_state(self):
        """
            Load and restore a layout state from the select_file obtained pathname file.

            See Also
            --------
            DAQ_utils.select_file
        """
        try:
            fname=daq_utils.select_file(save=False, ext='dock')
            if fname is not None:
                with open(str(fname), 'rb') as f:
                    dockstate = pickle.load(f)
                    self.dockarea.restoreState(dockstate)
        except: pass

    @pyqtSlot(str)
    def add_log(self,txt):
        """
            Add the QListWisgetItem initialized with txt informations to the User Interface logger_list and to the save_parameters.logger array.

            =============== =========== ======================
            **Parameters**    **Type**   **Description**
            *txt*             string     the log info to add.
            =============== =========== ======================
        """
        try:
            now=datetime.datetime.now()
            new_item=QtWidgets.QListWidgetItem(str(now)+": "+txt)
            self.ui.logger_list.addItem(new_item)

            self.save_parameters.logger_array.append(str(now)+": "+txt)
        except:
            pass

    def create_menu(self,menubar):
        """
            Create the menubar object looking like :
                * **Docked windows**
                    * Load Layout
                    * Save Layout
                    * Clear Moves/Detector
                    * Show/Hide Log Window
                * **Preset Modes**
                    * Create a preset
                * **Load Presets**
                    * Mock preset
                    * Canon preset

            | Connect each action to his referenced function.
            |
            | Finnaly store the directory list of xml files paths into the load_actions list.

            =============== ======================= =====================================
            **Parameters**   **Type**                 **Description**
            *menubar*         instance of QMenuBar    The generic menubar object of menu
            =============== ======================= =====================================

            See Also
            --------
            clear_move_det_controllers, load_layout_state, save_layout_state, show_file_attributes, set_preset_mode
        """
        menubar.clear()

        #%% create Settings menu
        file_menu=menubar.addMenu('File')
        load_action=file_menu.addAction('Load file')
        load_action.triggered.connect(self.load_file)
        save_action=file_menu.addAction('Save file')
        save_action.triggered.connect(self.save_file)
        show_action=file_menu.addAction('Show file content')
        show_action.triggered.connect(self.show_file_content)

        file_menu.addSeparator()
        quit_action=file_menu.addAction('Quit')
        quit_action.triggered.connect(self.Quit_fun)

        settings_menu=menubar.addMenu('Settings')
        docked_menu=settings_menu.addMenu('Docked windows')
        action_load=docked_menu.addAction('Load Layout')
        action_save=docked_menu.addAction('Save Layout')
        action_clear=settings_menu.addAction('Clear moves/Detectors')
        action_clear.triggered.connect(self.clear_move_det_controllers)

        action_load.triggered.connect(self.load_layout_state)
        action_save.triggered.connect(self.save_layout_state)

        docked_menu.addSeparator()
        action_show_log=docked_menu.addAction('Show/hide log window')
        action_show_log.setCheckable(True)
        action_show_log.toggled.connect(self.ui.logger_dock.setVisible)



        preset_menu=menubar.addMenu('Preset Modes')
        action_new_preset=preset_menu.addAction('New preset')
        #action.triggered.connect(lambda: self.show_file_attributes(type_info='preset'))
        action_new_preset.triggered.connect(self.create_preset)
        action_modify_preset=preset_menu.addAction('Modify preset')
        action_modify_preset.triggered.connect(self.modify_preset)
        preset_menu.addSeparator()
        load_preset=preset_menu.addMenu('Load presets')
        #load_mock=load_preset.addAction('Mock preset')
        #load_STEM=load_preset.addAction('STEM preset')
        #load_canon=load_preset.addAction('Canon Preset')
        #load_mock.triggered.connect(lambda: self.set_preset_mode('mock'))
        #load_STEM.triggered.connect(lambda: self.set_preset_mode('STEM'))
        #load_canon.triggered.connect(lambda: self.set_preset_mode('canon'))

        slots=dict([])
        start,end=os.path.split(os.path.realpath(__file__))
        for ind_file,file in enumerate(os.listdir(os.path.join(start,'preset_modes'))):
            if file.endswith(".xml"):
                (filesplited,ext)=os.path.splitext(file)
                slots[filesplited]=load_preset.addAction(filesplited)
                slots[filesplited].triggered.connect(self.create_menu_slot(os.path.join(start,'preset_modes',file)))
                


        #help menu
        help_menu=menubar.addMenu('?')
        action_about=help_menu.addAction('About')
        action_about.triggered.connect(self.show_about)
        action_help=help_menu.addAction('Help')
        action_help.triggered.connect(self.show_help)
        action_help.setShortcut(QtCore.Qt.Key_F1)

    def create_preset(self):
        try:
            self.preset_manager.set_new_preset()
            self.create_menu(self.menubar)
        except Exception as e:
            self.update_status(str(e),log_type='log')

    def modify_preset(self):
        try:
            path = utils.select_file(start_path='.\\preset_modes', save=False, ext='xml')
            if path != '':
                self.preset_manager.set_file_preset(str(path))

            else:  # cancel
                pass
        except Exception as e:
            self.update_status(str(e),log_type='log')

    def create_menu_slot(self,filename):
        return lambda: self.set_preset_mode(filename)



    def load_file(self):
        file=daq_utils.select_file(self.DAQscan_settings.child('saving_options', 'base_path').value(), save=False, ext='h5')
        self.save_parameters.h5_file_path=file
        self.update_file_settings()

    def save_file(self):
        filename=daq_utils.select_file(self.DAQscan_settings.child('saving_options', 'base_path').value(), save=True, ext='h5')
        file.copy_file(str(filename))

    def show_file_content(self):
        try:
            form = QtWidgets.QWidget();
            if not self.save_parameters.h5_file.isopen:
                if self.save_parameters.h5_file_path.exists():
                    self.analysis_prog = H5Browser(form,h5file=self.save_parameters.h5_file_path)
                else:
                    raise FileExistsError('no File presents')
            else:
                self.analysis_prog = H5Browser(form,h5file=self.save_parameters.h5_file)
            form.show()
        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def show_about(self):
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage("pymodaq version 1.0.0\nModular Acquisition with Python\nWritten by Sébastien Weber", QtCore.Qt.AlignRight, QtCore.Qt.white)


    def show_help(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("file:..//documentation//_build//html//index.html"))


    def clear_move_det_controllers(self):
        """
            Remove all docks containing Moves or Viewers.

            See Also
            --------
            Quit_fun, update_status
        """
        try:
        #remove all docks containing Moves or Viewers
            if hasattr(self,'move_modules'):
                if self.move_modules is not None:
                    for module in self.move_modules:
                        module.Quit_fun()
                self.move_modules=None

            if hasattr(self,'detector_modules'):
                if self.detector_modules is not None:
                    for module in self.detector_modules:
                        module.Quit_fun()
                self.detector_modules=None
        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def set_Mock_preset(self):
        """
            Set a Mock preset in 5 steps :
                * **Move Mock** : initialize docks and modules procedure. Append an instance of daq_move to the move_modules list.
                * **Move Mock** : initialize docks and modules procedure. Append an instance of daq_move to the move_modules list.
                * **DAQ0D** : initialize viewer's dock and modules procedure. Append an instance of daq_viewer to the detector_modules list.
                * **DAQ1D** : initialize viewer's dock and modules procedure. Append an instance of daq_viewer to the detector_modules list.
                * **DAQ2D** : initialize viewer's dock and modules procedure. Append an instance of daq_viewer to the detector_modules list.

            Returns
            -------
            (object list, object list) tuple
                The initialized Mock preset containing all the modules needed.

            See Also
            --------
            DAQ_Move_main.daq_move, stop_moves,  DAQ_viewer_main.daq_viewer
        """
        self.move_docks=[]
        move_forms=[]
        move_modules=[]
        move_types=[]
        try:
            move_name='Conex_U'
            move_type='Mock'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.ui.logger_dock)
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            move_modules[-1].ui.IniStage_pb.click()
            self.move_docks[-1].addWidget(move_forms[-1])
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass
        try:
            move_name='Conex_V'
            move_type='Mock'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].controller=move_modules[-2].controller #it uses the previous conex controller as a controller
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            move_modules[-1].ui.IniStage_pb.click()
            self.move_docks[-1].addWidget(move_forms[-1])
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass

        try:
            self.det_docks_settings=[]
            self.det_docks_viewer=[]
            detector_modules=[]
            det_name='Current'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.move_docks[-1])
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ0D'
            control_type='Mock'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)
            detector_modules[-1].ui.IniDet_pb.click()
            detector_modules[-1].settings.child('main_settings','overshoot').show()
            detector_modules[-1].settings.child('main_settings','wait_time').setValue(100)
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass

        try:
            det_name='Spectrum'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'bottom',self.ui.logger_dock)
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ1D'
            control_type='Mock'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)
            detector_modules[-1].ui.IniDet_pb.click()
            detector_modules[-1].settings.child('main_settings','overshoot').show()
            detector_modules[-1].settings.child('main_settings','wait_time').setValue(100)
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass
        try:

            det_name='image'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.det_docks_viewer[-2])
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ2D'
            control_type='Mock'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)
            detector_modules[-1].ui.IniDet_pb.click()
            detector_modules[-1].settings.child('main_settings','overshoot').show()
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass

        return move_modules, detector_modules


    def set_STEM_preset(self):
        """

        """
        self.move_docks=[]
        move_forms=[]
        move_modules=[]
        move_types=[]
        try:
            move_name='STEM X'
            move_type='STEM'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.ui.logger_dock)
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name,unique_ID=0))
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            move_modules[-1].ui.IniStage_pb.click()
            self.move_docks[-1].addWidget(move_forms[-1])
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass

        QtWidgets.QApplication.processEvents()
        QThread.msleep(2000)
        QtWidgets.QApplication.processEvents()

        try:
            move_name='STEM Y'
            move_type='STEM'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name,unique_ID=1))
            move_modules[-1].controller=move_modules[-2].controller #it uses the previous STEM controller as a controller
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            move_modules[-1].ui.IniStage_pb.click()
            self.move_docks[-1].addWidget(move_forms[-1])
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass


        try:

            det_name='STEM'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.det_docks_viewer[-2])
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ2D'
            control_type='OrsaySTEM'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type,unique_ID=2))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)
            detector_modules[-1].controller=move_modules[-2].controller
            detector_modules[-1].ui.IniDet_pb.click()
            detector_modules[-1].settings.child('main_settings','overshoot').show()
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass

        return move_modules, detector_modules

    def set_canon_preset(self):
        """
            Set a Canon preset in 6 steps :
                * **Connex_U** : initialize docks and modules procedure. Append an instance of daq_move to the move_modules list. Update settings tree with com_port child.
                * **Connex_V** : initialize docks and modules procedure. Append an instance of daq_move to the move_modules list. Update settings tree with com_port child.
                * **Loading Detector Modules** (Hardware parameter settings procedure):
                    * *Kinesis* Power : Append an instance of daq_move to the move_modules list. Update settings tree with serial number
                    * *Kinesis* Polarization : Append an instance of daq_move to the move_modules list. Update settings tree with serial number
                    * *Kinesis_Flipper* Flipper : Append an instance of daq_move to the move_modules list. Update settings tree with serial number
                    * *Kinesis_Flipper* Injection power : Append an instance of daq_move to the move_modules list. Update settings tree with serial number
                    * *Kinesis Injection* power : Append an instance of daq_move to the move_modules list. Update settings tree with serial number
                    * *PI* Delay : Append an instance of daq_move to the move_modules list.

                    Update settings tree with :
                        * *scaling*
                        * *offset*
                        * *use_scaling*
                        * *move_bounds*
                        * *limits*
                        * *devices*

                * **DAQ0d Keithley_Pico** : Initialize docks and modules procedure.

                Update settings tree with :
                    * *Visa_ressources limits option*
                    * *Visa_ressources*
                    * *overshoot*

                * **DAQ0D NIDAQ** : Initialize docks and modules procedure.

                Update settings tree with :
                    * *Analog_Input NIDAQ_type*
                    * *limits NIDAQ_devices*
                    * *NIDAQ_devices*
                    * *channels*
                    * *overshoot*

                * **DAQ2D OrsayCamera** : Initialize docks and modules procedure.

                Update settings tree with :
                    * *overshoot*

            See Also
            --------
            DAQ_Move_main.daq_move, stop_moves
        """
        self.move_docks=[]
        move_forms=[]
        move_modules=[]
        move_types=[]
        self.splash_sc.showMessage('Loading Move modules')
        try:
            move_name='Conex_U'
            move_type='Conex'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.ui.logger_dock)
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            move_modules[-1].settings.child('move_settings','axis_address').setValue('U')
            com_ports=move_modules[-1].settings.child('move_settings','com_port').opts['limits']
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            for com in com_ports:
                if 'COM5' in com:
                    move_modules[-1].settings.child('move_settings','com_port').setValue(com)
                    move_modules[-1].ui.IniStage_pb.click()
                    break
            self.move_docks[-1].addWidget(move_forms[-1])
        except Exception as e:
            pass

        QtWidgets.QApplication.processEvents()
        QThread.msleep(2000)
        QtWidgets.QApplication.processEvents()
        try:
            move_name='Conex_V'
            move_type='Conex'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].controller=move_modules[-2].controller #it uses the previous conex controller as a controller
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            move_modules[-1].settings.child('move_settings','axis_address').setValue('V')
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            com_ports=move_modules[-1].settings.child('move_settings','com_port').opts['limits']
            for com in com_ports:
                if 'COM5' in com:
                    move_modules[-1].settings.child('move_settings','com_port').setValue(com)
                    move_modules[-1].ui.IniStage_pb.click()
                    break
            self.move_docks[-1].addWidget(move_forms[-1])
        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(2000)
        QtWidgets.QApplication.processEvents()

        try:
            move_name='Power'
            move_type='Kinesis'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            serials=move_modules[-1].settings.child('move_settings','serial_number').opts['limits']
            for ser in serials:
                if '55000520' in ser:
                    move_modules[-1].settings.child('move_settings','serial_number').setValue(ser)
                    move_modules[-1].ui.IniStage_pb.click()
                    break
            self.move_docks[-1].addWidget(move_forms[-1])
        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(4000)
        QtWidgets.QApplication.processEvents()

        try:
            move_name='Polarization'
            move_type='Kinesis'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            serials=move_modules[-1].settings.child('move_settings','serial_number').opts['limits']
            for ser in serials:
                if '55000309' in ser:
                    move_modules[-1].settings.child('move_settings','serial_number').setValue(ser)
                    move_modules[-1].ui.IniStage_pb.click()
                    break
            self.move_docks[-1].addWidget(move_forms[-1])
        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(4000)
        QtWidgets.QApplication.processEvents()

        try:
            move_name='Flipper'
            move_type='Kinesis_Flipper'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            serials=move_modules[-1].settings.child('move_settings','serial_number').opts['limits']
            for ser in serials:
                if '37873712' in ser:
                    move_modules[-1].settings.child('move_settings','serial_number').setValue(ser)
                    move_modules[-1].ui.IniStage_pb.click()
                    break
            self.move_docks[-1].addWidget(move_forms[-1])

        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(4000)
        QtWidgets.QApplication.processEvents()

        try:
            move_name='Injection power'
            move_type='Kinesis'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            serials=move_modules[-1].settings.child('move_settings','serial_number').opts['limits']
            for ser in serials:
                if '55000902' in ser:
                    move_modules[-1].settings.child('move_settings','serial_number').setValue(ser)
                    move_modules[-1].ui.IniStage_pb.click()
                    break
            self.move_docks[-1].addWidget(move_forms[-1])
        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(4000)
        QtWidgets.QApplication.processEvents()

        try:
            move_name='Delay'
            move_type='PI'
            move_types.append(move_type)
            self.move_docks.append(Dock(move_name, size=(150,250)))
            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
            self.move_docks[-1].float()
            move_forms.append(QtWidgets.QWidget())
            move_modules.append(DAQ_Move(move_forms[-1],move_name))
            self.move_docks[-1].addWidget(move_forms[-1])
            move_modules[-1].ui.Stage_type_combo.setCurrentText(move_type)
            move_modules[-1].settings.child('move_settings','scaling','scaling').setValue(0.66666)
            move_modules[-1].settings.child('move_settings','scaling','offset').setValue(106.42)
            move_modules[-1].settings.child('move_settings','scaling','use_scaling').setValue(True)
            
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            devices=move_modules[-1].settings.child('move_settings','devices').opts['limits']
            for dev in devices:
                if 'PI' in dev:
                    move_modules[-1].settings.child('move_settings','devices').setValue(dev)
                    move_modules[-1].ui.IniStage_pb.click()
                    break

        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(4000)
        QtWidgets.QApplication.processEvents()
        self.splash_sc.showMessage('Loading Detector modules')
        try:
            self.det_docks_settings=[]
            self.det_docks_viewer=[]
            detector_modules=[]
            det_name='Current'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'bottom')
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ0D'
            control_type='Keithley_Pico'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)

            visas=detector_modules[-1].settings.child('detector_settings','VISA_ressources').opts['limits']
            for visa in visas:
                if 'ASRL8::INSTR' in visa:
                    detector_modules[-1].settings.child('detector_settings','VISA_ressources').setValue(visa)
                    detector_modules[-1].ui.IniDet_pb.click()
            detector_modules[-1].settings.child('main_settings','overshoot').show()
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(2000)
        QtWidgets.QApplication.processEvents()

        try:
            det_name='Power'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.det_docks_viewer[-2])
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ0D'
            control_type='NIDAQ'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)
            detector_modules[-1].ui.IniDet_pb.click()
            detector_modules[-1].settings.child('detector_settings','NIDAQ_type').setValue('Analog_Input')
            devices=detector_modules[-1].settings.child('detector_settings','NIDAQ_devices').opts['limits']
            for dev in devices:
                if 'Dev1' in devices:
                    detector_modules[-1].settings.child('detector_settings','NIDAQ_devices').setValue()
                    items=detector_modules[-1].settings.child('detector_settings','channels').value()
                    items['selected']=['ai0']
                    detector_modules[-1].settings.child('detector_settings','channels').setValue(items)
            detector_modules[-1].settings.child('main_settings','overshoot').show()
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)

        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(2000)
        QtWidgets.QApplication.processEvents()

        try:
            det_name='Pixis'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(550,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.move_docks[-1])
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ2D'
            control_type='OrsayCamera'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)
            detector_modules[-1].settings.child('main_settings','overshoot').show()
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
            #detector_modules[-1].ui.IniDet_pb.click()


        except Exception as e:
            pass
        QtWidgets.QApplication.processEvents()
        QThread.msleep(2000)
        QtWidgets.QApplication.processEvents()

        return move_modules,detector_modules

    def set_file_preset(self,filename):
        """
            Set a file preset from the converted xml file given by the filename parameter.


            =============== =========== ===================================================
            **Parameters**    **Type**    **Description**
            *filename*        string      the name of the xml file to be converted/treated
            =============== =========== ===================================================

            Returns
            -------
            (Object list, Object list) tuple
                The updated (Move modules list, Detector modules list).

            See Also
            --------
            custom_tree.XML_file_to_parameter, set_param_from_param, stop_moves, update_status,DAQ_Move_main.daq_move, DAQ_viewer_main.daq_viewer
        """

        if os.path.splitext(filename)[1]=='.xml':
            self.preset_manager.set_file_preset(filename,show=False)
            self.move_docks=[]
            self.det_docks_settings=[]
            self.det_docks_viewer=[]
            move_forms=[]
            move_modules=[]
            detector_modules=[]
            move_types=[]

            #################################################################
            ###### sort plugins by IDs and within the same IDs by Master and Slave status
            plugins=[{'type': 'move', 'value': child} for child in self.preset_manager.preset_params.child(('Moves')).children()]+[{'type': 'det', 'value': child} for child in self.preset_manager.preset_params.child(('Detectors')).children()]
            for plug in plugins:
                plug['ID']=plug['value'].child('params','main_settings','controller_ID').value()
                if plug["type"]=='det':
                    plug['status']=plug['value'].child('params','detector_settings','controller_status').value()
                else:
                    plug['status']=plug['value'].child('params','move_settings','multiaxes','multi_status').value()

            IDs=list(set([plug['ID'] for plug in plugins]))
            #%%
            plugins_sorted=[]
            for id in IDs:
                plug_Ids=[]
                for plug in plugins:
                    if plug['ID']==id:
                        plug_Ids.append(plug)
                plug_Ids.sort(key=lambda status: status['status'])      
                plugins_sorted.append(plug_Ids)
            #################################################################
            #######################

            ind_move=-1
            ind_det=-1
            for plug_IDs in plugins_sorted:
                for ind_plugin, plugin in enumerate(plug_IDs):
                

                    plug_name=plugin['value'].child(('name')).value()
                    plug_init=plugin['value'].child(('init')).value()
                    plug_settings=plugin['value'].child(('params'))
                    self.splash_sc.showMessage('Loading {:s} module: {:s}'.format(plugin['type'],plug_name),color = Qt.white)
                    if plugin['type'] == 'move':
                        ind_move+=1
                        plug_type=plug_settings.child('main_settings','move_type').value()
                        self.move_docks.append(Dock(plug_name, size=(150,250)))
                        if ind_move==0:
                            self.dockarea.addDock(self.move_docks[-1], 'right',self.ui.logger_dock)
                        else:
                            self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
                        move_forms.append(QtWidgets.QWidget())
                        mov_mod_tmp=DAQ_Move(move_forms[-1],plug_name)

                        mov_mod_tmp.ui.Stage_type_combo.setCurrentText(plug_type)
                        QtWidgets.QApplication.processEvents()

                        set_param_from_param(mov_mod_tmp.settings,plug_settings)
                        QtWidgets.QApplication.processEvents()

                        mov_mod_tmp.bounds_signal[bool].connect(self.stop_moves)
                        self.move_docks[-1].addWidget(move_forms[-1])
                        move_modules.append(mov_mod_tmp)

                        try:
                            if ind_plugin==0: #should be a master type plugin
                                if plugin['status']!="Master":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    move_modules[-1].ui.IniStage_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    QThread.msleep(4000)
                                    QtWidgets.QApplication.processEvents()
                                    master_controller=move_modules[-1].controller
                            else:
                                if plugin['status']!="Slave":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    move_modules[-1].controller=master_controller
                                    move_modules[-1].ui.IniStage_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    QThread.msleep(4000)
                                    QtWidgets.QApplication.processEvents()
                        except Exception as e:
                            self.update_status(str(e),'log')


                    else:
                        ind_det+=1
                        plug_type=plug_settings.child('main_settings','DAQ_type').value()
                        plug_subtype=plug_settings.child('main_settings','detector_type').value()

                        self.det_docks_settings.append(Dock(plug_name+" settings", size=(150,250)))
                        self.det_docks_viewer.append(Dock(plug_name+" viewer", size=(350,350)))

                        if ind_det==0:
                            self.ui.logger_dock.area.addDock(self.det_docks_settings[-1], 'bottom') #dockarea of the logger dock
                        else:
                            self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.det_docks_viewer[-2])
                        self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])

                        det_mod_tmp=DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                            dock_viewer=self.det_docks_viewer[-1],title=plug_name,DAQ_type=plug_type)
                        detector_modules.append(det_mod_tmp)
                        detector_modules[-1].ui.Detector_type_combo.setCurrentText(plug_subtype)

                        set_param_from_param(det_mod_tmp.settings,plug_settings)
                        QtWidgets.QApplication.processEvents()


                        try:
                            if ind_plugin==0: #should be a master type plugin
                                if plugin['status']!="Master":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    detector_modules[-1].ui.IniDet_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    QThread.msleep(4000)
                                    QtWidgets.QApplication.processEvents()
                                    master_controller=detector_modules[-1].controller
                            else:
                                if plugin['status']!="Slave":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    detector_modules[-1].controller=master_controller
                                    detector_modules[-1].ui.IniDet_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    QThread.msleep(4000)
                                    QtWidgets.QApplication.processEvents()
                        except Exception as e:
                            self.update_status(str(e),'log')

                        detector_modules[-1].settings.child('main_settings','overshoot').show()
                        detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)




     
            return move_modules,detector_modules
        else:
            raise Exception('Invalid file selected')

    def set_preset_mode(self,filename):
        """
            | Set the preset mode from the given filename.
            |
            | In case of "mock" or "canon" move, set the corresponding preset calling set_(*)_preset procedure.
            |
            | Else set the preset file using set_file_preset function.
            | Once done connect the move and detector modules to logger to recipe/transmit informations.

            Finally update DAQ_scan_settings tree with :
                * Detectors
                * Move
                * plot_form.

            =============== =========== =============================================
            **Parameters**    **Type**    **Description**
            *filename*        string      the name of the preset file to be treated
            =============== =========== =============================================

            See Also
            --------
            set_Mock_preset, set_canon_preset, set_file_preset, add_log, update_status
        """
        try:
            self.mainwindow.setVisible(False)
            for area in self.dockarea.tempAreas:
                area.window().setVisible(False)

            self.splash_sc.show()
            self.splash_sc.raise_()
            self.splash_sc.showMessage('Loading Modules, please wait',color = Qt.white)
            QtWidgets.QApplication.processEvents()
            self.clear_move_det_controllers()
            QtWidgets.QApplication.processEvents()

            if filename=='mock':
                move_modules,detector_modules= self.set_Mock_preset()
            elif filename=='canon':
                move_modules,detector_modules= self.set_canon_preset()
            elif filename=='STEM':
                move_modules,detector_modules= self.set_STEM_preset()
            else:
                move_modules,detector_modules= self.set_file_preset(filename)

            self.move_modules=move_modules
            self.detector_modules=detector_modules

            #connecting to logger
            for mov in move_modules:
                mov.log_signal[str].connect(self.add_log)
            for det in detector_modules:
                det.log_signal[str].connect(self.add_log)

            #setting moves and det in tree
            preset_items_det=[]
            preset_items_move=[]
            items_det=[module.title for module in detector_modules]
            if items_det!=[]:
                preset_items_det=[items_det[0]]

            items_move=[module.title for module in move_modules]
            if items_move!=[]:
                preset_items_move=[items_move[0]]

            self.DAQscan_settings.child('Move_Detectors','Detectors').setValue(dict(all_items=items_det,selected=preset_items_det))
            self.DAQscan_settings.child('Move_Detectors','Moves').setValue(dict(all_items=items_move,selected=preset_items_move))
            self.DAQscan_settings.child('scan_options','plot_from').setLimits(preset_items_det)
            if preset_items_det!=[]:
                self.DAQscan_settings.child('scan_options','plot_from').setValue(preset_items_det[0])


            self.splash_sc.close()
            self.mainwindow.setVisible(True)
            for area in self.dockarea.tempAreas:
                area.window().setVisible(True)
        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def stop_moves(self):
        """
            Foreach module of the move module object liost, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.daq_move.Stop_Motion
        """
        self.stop_scan()
        for mod in self.move_modules:
            mod.Stop_Motion()

    def update_scan_type(self,param):
        """
            Update the scan type from the given parameter.

            =============== ================================= ========================
            **Parameters**    **Type**                         **Description**
            *param*           instance of pyqtgraph parameter  the parameter to treat
            =============== ================================= ========================

            See Also
            --------
            update_status
        """
        try:
            state=param.value()=='Spiral'
            self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis1').setOpts(visible=not state,value=self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis1').value())
            self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis2').setOpts(visible=not state,value=self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis2').value())
            self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis1').setOpts(visible=not state,value=self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis1').value())
            self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis2').setOpts(visible=not state,value=self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis2').value())
            self.DAQscan_settings.child('scan_options','scan2D_settings','Rstep_2d').setOpts(visible=state,value=self.DAQscan_settings.child('scan_options','scan2D_settings','Rstep_2d').value())
            self.DAQscan_settings.child('scan_options','scan2D_settings','Rmax_2d').setOpts(visible=state,value=self.DAQscan_settings.child('scan_options','scan2D_settings','Rstep_2d').value())
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')

    def update_plot_det_items(self,param):
        """
            Add the scan_options-plot_form child to the DAQscan_settings tree from the selected value of the given parameter.

            =============== ================================= ========================
            **Parameters**    **Type**                         **Description**
            *param*           instance of pyqtgraph parameter  the parameter to treat
            =============== ================================= ========================
        """
        items=param.value()['selected']
        self.DAQscan_settings.child('scan_options','plot_from').setOpts(limits=items)


    @pyqtSlot(float,float)
    def move_to_crosshair(self,posx=None,posy=None):
        """
            Compute the scaled position from the given x/y position and send the command_DAQ signal with computed values as attributes.


            =============== =========== ==============================
            **Parameters**    **Type**   **Description**
            *posx*           float       the original x position
            *posy*           float       the original y position
            =============== =========== ==============================

            See Also
            --------
            update_status
        """
        if self.ui.move_to_crosshair_cb.isChecked():
            if "2D" in self.DAQscan_settings.child('scan_options','scan_type').value():
                if len(self.move_modules_scan)==2 and posx is not None and posy is not None:
                    posx_real=posx*self.ui.scan2D_graph.scaled_xaxis.scaling+self.ui.scan2D_graph.scaled_xaxis.offset
                    posy_real=posy*self.ui.scan2D_graph.scaled_yaxis.scaling+self.ui.scan2D_graph.scaled_yaxis.offset                    
                    self.command_DAQ_signal.emit(["move_stages",[posx_real,posy_real]])
                else:
                    self.update_status("not valid configuration, check number of stages and scan2D option",log_type='log')

    def set_ini_positions(self):
        """
            Send the command_DAQ signal with "set_ini_positions" list item as an attribute.
        """
        self.command_DAQ_signal.emit(["set_ini_positions"])

    def Quit_fun(self):
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            Quit_fun
        """
        try:
            try:
                if self.save_parameters.h5_file.isopen:
                    self.save_parameters.h5_file.close()
            except:
                pass

            for module in self.move_modules:
                try:
                    module.Quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
                except:
                    pass

            for module in self.detector_modules:
                try:
                    module.Quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
                except:
                    pass
            areas=self.dockarea.tempAreas[:]
            for area in areas:
                area.win.close()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(1000)
                QtWidgets.QApplication.processEvents()


            if hasattr(self,'mainwindow'):
                self.mainwindow.close()




        except Exception as e:
            pass

    def start_scan(self):
        """
            Start an acquisition calling the set_scan function.
            Emit the command_DAQ signal "start_acquisition".

            See Also
            --------
            set_scan
        """
        self.plot_3D_ini=False
        self.plot_2D_ini=False
        if self.plot_items!=[]:
            for plot_item in self.plot_items:
                self.ui.scan1D_graph.removeItem(plot_item)
            self.plot_items=[]
        self.set_scan()
        self.ui.scan_done_LED.set_as_false()
        self.ui.log_message.setText('Starting acquisition')
        self.command_DAQ_signal.emit(["start_acquisition"])

    def stop_scan(self):
        """
            Emit the command_DAQ signal "stop_acquisiion".

            See Also
            --------
            set_ini_positions
        """
        self.command_DAQ_signal.emit(["stop_acquisition"])
        self.set_ini_positions()

    def add_comments(self):
        """
            Add a scan info description child in the settings tree converting the xml concerned parameter to string and setting the child value consequently.

            See Also
            --------
            custom_tree.XML_string_to_parameter, custom_tree.parameter_to_xml_string
        """
        comments=self.DAQscan_settings.child('saving_options','add_comments').value()
        scangroup=self.save_parameters.h5_file.get_node('/Raw_datas/{:s}'.format(self.DAQscan_settings.child('saving_options','current_filename').value()))

        param=Parameter.create(name='Attributes', type='group', children= custom_tree.XML_string_to_parameter(scangroup._v_attrs.settings.decode()))
        comments_ini=param.child('scan_info','description').value()
        if comments_ini is None:
            comments_ini=""
        param.child('scan_info','description').setValue(comments_ini+'\n'+comments)
        scangroup._v_attrs.settings=custom_tree.parameter_to_xml_string(param)

    def update_file_paths(self,update_h5=False):
        """
            | Update the raw datas into the h5 file given by base_path child in DAQscan_setttings tree.
            |
            | Set metadata about dataset.
            | Check in the raw data group (in h5 file) and save metadata into.
            | Check if logger exist.
            | Set attributes to the current group, such as scan_type.

            =============== =========== ======================================
            **Parameters**    **Type**    **Description**
            *update_h5*       boolean    1/0 to update the associated h5 file
            =============== =========== ======================================

            See Also
            --------
            DAQ_utils.set_current_scan_path, set_metadata_about_dataset, save_metadata, update_status
        """
        try:
            # set the filename and path
            base_path=self.DAQscan_settings.child('saving_options','base_path').value()
            base_name=self.DAQscan_settings.child('saving_options','base_name').value()


            scan_path,current_filename,dataset_path=daq_utils.set_current_scan_path(base_path, base_name, update_h5)
            self.DAQscan_settings.child('saving_options','current_scan_path').setValue(str(scan_path))



            self.save_parameters.h5_file_path=dataset_path.joinpath(dataset_path.name+".h5")
            self.update_file_settings(current_filename)

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')

    def update_file_settings(self,current_filename='Scan000'):
        try:
            self.DAQscan_settings.child('saving_options','current_h5_file').setValue(str(self.save_parameters.h5_file_path))

            if 'h5_file' in self.save_parameters.keys():
                if  self.save_parameters.h5_file is not None:
                    if self.save_parameters.h5_file.isopen:
                        self.save_parameters.h5_file.close()
                    del(self.save_parameters.h5_file)

            if self.save_parameters.h5_file_path.exists():
                self.save_parameters.h5_file = tables.open_file(str(self.save_parameters.h5_file_path), mode = "a")
            else:
                self.save_parameters.h5_file = tables.open_file(str(self.save_parameters.h5_file_path), mode = "w")
                self.set_metadata_about_dataset()


            if not 'Raw_datas' in list(self.save_parameters.h5_file.root._v_children.keys()):
                raw_data_group = self.save_parameters.h5_file.create_group("/", 'Raw_datas', 'Data from daq_scan and detector modules')
                self.save_metadata(raw_data_group,'dataset_info')
                #selected_data_group = self.save_parameters.h5_file.create_group("/", 'Selected_datas', 'Data currently selected')
                #analysis_data_group= self.save_parameters.h5_file.create_group("/", 'Analysed_datas', 'Data analysed from raw data')



            raw_data_group=self.save_parameters.h5_file.root.Raw_datas
            if not(raw_data_group.__contains__(current_filename)):#check if Scan00i is a group
                self.save_parameters.current_group=self.save_parameters.h5_file.create_group(raw_data_group,current_filename) #if not it is created
                self.save_parameters.current_group._v_attrs['description']=""
            else:
                self.save_parameters.current_group=raw_data_group._f_get_child(current_filename)

            self.DAQscan_settings.child('saving_options','current_filename').setOpts(limits=[child for child in raw_data_group._v_children if 'Scan' in child])
            self.DAQscan_settings.child('saving_options','current_filename').setValue(str(current_filename))

            #check if logger node exist
            logger="logging"
            node_list=[node._v_name for node in self.save_parameters.h5_file.list_nodes(raw_data_group)]
            if logger not in node_list:
                text_atom = tables.atom.ObjectAtom()
                self.save_parameters.logger_array = self.save_parameters.h5_file.create_vlarray(raw_data_group, logger, atom=text_atom)
                self.save_parameters.logger_array._v_attrs['type']='list'
            else:
                self.save_parameters.logger_array=self.save_parameters.h5_file.get_node(raw_data_group, name=logger)


            #display list of actual saved 2Dscans
            if self.ui.overlay2D_pb.isChecked():
                self.list_2Dscans()

            #set attributes to the current group, such as scan_type....
            self.scan_attributes.child('scan_info','scan_type').setValue(self.DAQscan_settings.child('scan_options','scan_type').value())
            self.scan_attributes.child('scan_info','scan_name').setValue(current_filename)
            self.scan_attributes.child('scan_info','description').setValue(self.save_parameters.current_group._v_attrs['description'])
            self.set_metadata_about_current_scan()
            self.save_metadata(self.save_parameters.current_group,'scan_info')

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')

    def list_2Dscans(self):
        try:
            scan_list=utils.get_h5file_scans(self.save_parameters.h5_file)
            #scan_list=[dict(scan_name=node._v_name,path=node._v_pathname, pixmap=nparray2Qpixmap(node.read()))),...]
            params=[]
            self.scan_list.clearChildren()
            for scan in scan_list:
                params.append({'name': scan['scan_name'], 'type': 'pixmap_check', 'value':dict(data=scan['data'],checked=False,path=scan['path'])})
            self.scan_list.addChildren(params)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')

    def show_file_attributes(self,type_info='dataset'):
        """
            Switch the type_info value.

            In case of :
                * *scan* : Set parameters showing top false
                * *dataset* : Set parameters showing top false
                * *preset* : Set parameters showing top false. Add the save/cancel buttons to the accept/reject dialog (to save preset parameters in a xml file).

            Finally, in case of accepted preset type info, save the preset parameters in a xml file.

            =============== =========== ====================================
            **Parameters**    **Type**    **Description**
            *type_info*       string      The file type information between
                                            * scan
                                            * dataset
                                            * preset
            =============== =========== ====================================

            See Also
            --------
            custom_tree.parameter_to_xml_file, create_menu
        """
        dialog=QtWidgets.QDialog()
        vlayout=QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        if type_info=='scan':
            tree.setParameters(self.scan_attributes, showTop=False)
        elif type_info=='dataset':
            tree.setParameters(self.dataset_attributes, showTop=False)


        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog);
        # if type_info=='preset':
        #     buttonBox.addButton('Save',buttonBox.AcceptRole)
        #     buttonBox.accepted.connect(dialog.accept)
        #     buttonBox.addButton('Cancel',buttonBox.RejectRole)
        #     buttonBox.rejected.connect(dialog.reject)
        # else:
        #     buttonBox.addButton('Apply',buttonBox.AcceptRole)
        #     buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Apply', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this {}'.format(type_info))
        res=dialog.exec()


    def set_metadata_about_dataset(self):
        """
            Set the date value of the data_set_info-date_time child of the data_set_attributes tree.
            Show the 'dataset' file attributes.

            See Also
            --------
            show_file_attributes
        """
        date=QDateTime(QDate.currentDate(),QTime.currentTime())
        self.dataset_attributes.child('dataset_info','date_time').setValue(date)
        self.show_file_attributes('dataset')

        #self.save_parameters.h5_file._f_setattr('author','Sebastien Weber')

    def set_metadata_about_current_scan(self):
        """
            Set the date/time and author values of the scan_info child of the scan_attributes tree.
            Show the 'scan' file attributes.

            See Also
            --------
            show_file_attributes
        """
        date=QDateTime(QDate.currentDate(),QTime.currentTime())
        self.scan_attributes.child('scan_info','date_time').setValue(date)
        self.scan_attributes.child('scan_info','author').setValue(self.dataset_attributes.child('dataset_info','author').value())
        self.show_file_attributes('scan')

    def save_metadata(self,node,type_info='dataset_info'):
        """
            Switch the type_info value with :
                * *'dataset_info'* : Give the params attributes the dataset_attributes values
                * *'dataset'* : Give the params attributes the scan_attributes values

            |
            | Once done, course the params and add string casted date/time metadata as an element of attributes array.
            | Save the contents of given parameter object into a xml string unde the attributes settings.

            =============== =================== =========================================
            **Parameters**    **Type**           **Description**
            *node*            pytables h5 node   Root node to be treated
            *type_info*       string             File type info between :
                                                    * 'dataset_info'
                                                    * 'scan_info'
            =============== =================== =========================================

            See Also
            --------
            custom_tree.parameter_to_xml_string
        """

        attr=node._v_attrs
        if type_info=='dataset_info':
            attr['type']='dataset'
            params=self.dataset_attributes
        else:
            attr['type']='scan'
            params=self.scan_attributes
        for child in params.child((type_info)).children():
            if type(child.value()) is QDateTime:
                attr[child.name()]=child.value().toString('dd/mm/yyyy HH:MM:ss')
            else:
                attr[child.name()]=child.value()
        #save contents of given parameter object into an xml string under the attribute settings
        attr.settings=custom_tree.parameter_to_xml_string(params)
        if type_info=='scan_info':
            attr.scan_settings=custom_tree.parameter_to_xml_string(self.DAQscan_settings)

    def set_scan(self):
        """
            Set the scan in 8 steps :
                * **Set the filename and path**
                * **Set the moves positions according to data from user**
                * **Get the name and list of all move modules used for this scan**
                * **Get the name and list of all detector modules used for this scan**
                * Switch the 'scan_option-scan_type' child value of the DAQ_scan settings tree between
                    * *Scan1D* :
                        * Get the start/stop/step values from the tree
                        * Define a linscape distributions as an axis
                        * Set the scan_saves consequently.
                    * *Scan2D* :
                        * Check the number of modules.
                        * Get the start/stop/step values from the tree
                        * Define linscape distributions as two axis
                        * Set the corresponding scan (linear or spiral)
                        * Set the scan_saves consequently
                * **Check if the modules are initialized**
                * **Do the acquisition calling the DAQ_Scan_Acquisition object**
                * **Connect the queue-command, the update_scan_GUI and thread_status functions.**

            See Also
            --------
            update_file_paths, DAQ_utils.set_scan_spiral, DAQ_utils.set_scan_linear, DAQ_Scan_Acquisition, DAQ_Scan_main.queue_command, update_scan_GUI, thread_status
        """
        try:
            # set the filename and path
            self.update_file_paths()
            scan_path=Path(self.DAQscan_settings.child('saving_options','current_scan_path').value())
            current_filename=self.DAQscan_settings.child('saving_options','current_filename').value()


            # set the moves positions according to data from user
            if "1D" in self.DAQscan_settings.child('scan_options','scan_type').value():
                move_names_scan=[self.DAQscan_settings.child('Move_Detectors','Moves').value()['selected'][0]] #selected move modules names
            else:
                move_names_scan=self.DAQscan_settings.child('Move_Detectors','Moves').value()['selected'][0:2]

            move_names=[mod.title for mod in self.move_modules] # names of all move modules initialized
            self.move_modules_scan=[] #list of move modules used for this scan
            for name in move_names_scan:
                self.move_modules_scan.append(self.move_modules[move_names.index(name)])#create list of modules used for this current scan

            det_names_scan=self.DAQscan_settings.child('Move_Detectors','Detectors').value()['selected']# names of all selected detector modules initialized
            det_names=[mod.title for mod in self.detector_modules]
            self.det_modules_scan=[]#list of detector modules used for this scan
            for name in det_names_scan:
                self.det_modules_scan.append(self.detector_modules[det_names.index(name)])

            self.scan_saves=[]

            if self.DAQscan_settings.child('scan_options','scan_type').value() == "Scan1D":
                move_module_name=move_names_scan[0]
                start=self.DAQscan_settings.child('scan_options','scan1D_settings','start_1D').value()
                stop=self.DAQscan_settings.child('scan_options','scan1D_settings','stop_1D').value()
                step=self.DAQscan_settings.child('scan_options','scan1D_settings','step_1D').value()
                if self.DAQscan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=="Linear":
                    self.scan_parameters.axis_1D=utils.linspace_step(start,stop,step)
                elif self.DAQscan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                    steps=[]
                    for step in utils.linspace_step(start,stop,step):
                        steps.extend([step,start])
                    self.scan_parameters.axis_1D=np.array(steps)

                self.scan_parameters.Nsteps=np.size(self.scan_parameters.axis_1D)
                self.ui.N_scan_steps_sb.setValue(self.scan_parameters.Nsteps)

                self.scan_moves=[[[move_module_name,pos]] for pos in self.scan_parameters.axis_1D]

                for ind,pos in enumerate(self.scan_moves):
                    self.scan_saves.append([OrderedDict(det_name=det_name,file_path=str(scan_path.joinpath(current_filename+"_"+det_name+'_{:03d}.dat'.format(ind))),indexes=OrderedDict(indx=ind)) for det_name in det_names_scan])


            elif self.DAQscan_settings.child('scan_options','scan_type').value() == "Scan2D":
                if len(move_names_scan)!=2:

                    msgBox=QtWidgets.QMessageBox(parent=None)
                    msgBox.setWindowTitle("Error")
                    msgBox.setText("There are not enough selected move modules")
                    ret=msgBox.exec();
                    return


                move_module_name1=move_names_scan[0]
                move_module_name2=move_names_scan[1]

                start_axis1=self.DAQscan_settings.child('scan_options','scan2D_settings','start_2d_axis1').value()
                start_axis2=self.DAQscan_settings.child('scan_options','scan2D_settings','start_2d_axis2').value()

                if self.DAQscan_settings.child('scan_options','scan2D_settings','scan2D_type').value()=='Spiral':

                    Rstep_2d=self.DAQscan_settings.child('scan_options','scan2D_settings','Rstep_2d').value()
                    Rmax=self.DAQscan_settings.child('scan_options','scan2D_settings','Rmax_2d').value()
                    Nsteps,axis_1_indexes,axis_2_indexes,axis_1_unique,axis_2_unique,axis_1,axis_2,positions=daq_utils.set_scan_spiral(start_axis1, start_axis2,
                                                                                                                                       Rmax, Rstep_2d)
                else:
                    stop_axis1=self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis1').value()
                    step_axis1=self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis1').value()
                    stop_axis2=self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis2').value()
                    step_axis2=self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis2').value()

                    if self.DAQscan_settings.child('scan_options','scan2D_settings','scan2D_type').value()=='Linear':
                        Nsteps,axis_1_indexes,axis_2_indexes,axis_1_unique,axis_2_unique,axis_1,axis_2,positions=daq_utils.set_scan_linear(start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=False)
                    elif self.DAQscan_settings.child('scan_options','scan2D_settings','scan2D_type').value()=='back&forth':
                        Nsteps,axis_1_indexes,axis_2_indexes,axis_1_unique,axis_2_unique,axis_1,axis_2,positions=daq_utils.set_scan_linear(start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=True)


                self.scan_parameters.axis_2D_1=axis_1_unique
                self.scan_parameters.axis_2D_2=axis_2_unique
                self.scan_parameters.axis_2D_1_indexes=axis_1_indexes
                self.scan_parameters.axis_2D_2_indexes=axis_2_indexes
                self.scan_parameters.Nsteps=Nsteps
                self.ui.N_scan_steps_sb.setValue(self.scan_parameters.Nsteps)
                self.scan_moves=[[[move_module_name1,pos1],[move_module_name2,pos2]] for pos1,pos2 in positions]

                for ind,pos in enumerate(self.scan_moves):
                    ind1=axis_1_indexes[ind]
                    ind2=axis_2_indexes[ind]
                    self.scan_saves.append([OrderedDict(det_name=det_name,file_path=str(scan_path.joinpath(current_filename+"_"+det_name+'_{:03d}_{:03d}.dat'.format(ind1,ind2))),indexes=OrderedDict(indx=ind1,indy=ind2)) for det_name in det_names_scan])


            #check if the modules are initialized

            for module in self.move_modules_scan:
                if not module.Initialized_state:
                    raise Exception('module '+module.title+" is not initialized")

            for module in self.det_modules_scan:
                if not module.Initialized_state:
                    raise Exception('module '+module.title+" is not initialized")

            self.ui.start_scan_pb.setEnabled(True)
            self.ui.stop_scan_pb.setEnabled(True)


            self.PyMoDAQ=DAQ_Scan_Acquisition(self.DAQscan_settings,self.save_parameters.h5_file,self.save_parameters.current_group,
                                          self.move_modules_scan,self.det_modules_scan,self.scan_moves,self.scan_saves)

            #self.DAQ_thread.pymodaq=pymodaq
            #pymodaq.moveToThread(self.DAQ_thread)


            self.command_DAQ_signal[list].connect(self.PyMoDAQ.queue_command)
            self.PyMoDAQ.scan_data_tmp[dict].connect(self.update_scan_GUI)
            self.PyMoDAQ.status_sig[list].connect(self.thread_status)

            #self.DAQ_thread.start()


        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')
            self.ui.start_scan_pb.setEnabled(False)
            self.ui.stop_scan_pb.setEnabled(False)

    @pyqtSlot(edict)
    def update_scan_GUI(self,datas):
        """
            Update the graph in the Graphic Interface from the given datas switching 0D/1D/2D consequently.

            =============== =============================== ===========================
            **Parameters**    **Type**                       **Description**
            *datas*           double precision float array   the data values to update
            =============== =============================== ===========================

            See Also
            --------
            update_2D_graph, update_1D_graph, update_status
        """
        #datas=edict(positions=self.scan_read_positions,datas=self.scan_read_datas)
        self.scan_positions=datas['positions']
        try:
            if "2D" in self.DAQscan_settings.child('scan_options','scan_type').value(): #means 2D cartography type scan
                if 'data0D' in datas.datas.keys():
                    self.update_2D_graph(datas.datas['data0D'])
                #if 'data1D' in datas.datas.keys():
                #    self.update_3D_graph(data.datass['data1D'])
            else:
                if 'data0D' in datas.datas.keys():
                    if datas.datas['data0D'] is not None:
                        self.update_1D_graph(datas.datas['data0D'])
                if 'data1D' in datas.datas.keys():
                    if datas.datas['data1D'] is not None:
                        self.update_2D_graph(datas.datas['data1D'])

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')

    def save_scan(self):
        """

        """
        try:
            filters = tables.Filters(complevel=self.DAQscan_settings.child('saving_options','compression_options', 'h5comp_level').value(),
                              complib=self.DAQscan_settings.child('saving_options','compression_options','h5comp_library').value()) 

            if self.scan_data_1D.shape!=():
                scan_1D_group=self.save_parameters.h5_file.create_group(self.save_parameters.current_group,'scan_1D')
                if self.scan_x_axis.shape!=():
                    xarray=self.save_parameters.h5_file.create_carray(scan_1D_group,'scan_x_axis',obj=self.scan_x_axis, title='data',filters=filters)
                    xarray.set_attr('shape',xarray.shape)
                    xarray.attrs['type']='data'
                    xarray.attrs['data_type']='1D'

                for ind in range(self.scan_data_1D.shape[1]):
                    array=self.save_parameters.h5_file.create_carray(scan_1D_group,'Scan_Data_{:03d}'.format(ind),obj=self.scan_data_1D[:,ind], title='data',filters=filters)
                    array.set_attr('shape',array.shape)
                    array.attrs['type']='data'
                    array.attrs['data_type']='1D'


            if self.scan_data_2D!=[]:
                scan_2D_group=self.save_parameters.h5_file.create_group(self.save_parameters.current_group,'scan_2D')
                if self.scan_x_axis.shape!=():
                    xarray=self.save_parameters.h5_file.create_carray(scan_2D_group,'scan_x_axis',obj=self.scan_x_axis, title='data',filters=filters)
                    xarray.set_attr('shape',xarray.shape)
                    xarray.attrs['type']='data'
                    xarray.attrs['data_type']='1D'
                if not(self.scan_y_axis.shape==() or self.scan_y_axis.shape==(0,)):
                    yarray=self.save_parameters.h5_file.create_carray(scan_2D_group,'scan_y_axis',obj=self.scan_y_axis, title='data',filters=filters)
                    yarray.set_attr('shape',yarray.shape)
                    yarray.attrs['type']='data'
                    yarray.attrs['data_type']='1D'

                for ind,data2D in enumerate(self.scan_data_2D):
                    array=self.save_parameters.h5_file.create_carray(scan_2D_group,'Scan_Data_{:03d}'.format(ind),obj=data2D, title='data',filters=filters)
                    array.set_attr('shape',array.shape)
                    array.attrs['type']='data'
                    array.attrs['data_type']='2D'



            item=self.ui.scan1D_graph.plotItem
            png = QtGui.QImage(int(item.size().width()), int(item.size().height()), QtGui.QImage.Format_ARGB32)
            painter = QtGui.QPainter(png)
            painter.setRenderHints(painter.Antialiasing | painter.TextAntialiasing)
            item.scene().render(painter, QtCore.QRectF(), item.mapRectToScene(item.boundingRect()))
            painter.end()

            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.WriteOnly)
            png=png.scaled(100,100,QtCore.Qt.KeepAspectRatio)
            png.save(buffer,"png")

            string=buffer.data().data()
            self.save_parameters.current_group._v_attrs['pixmap1D']=string




            item=self.ui.scan2D_graph.ui.plotitem
            png = QtGui.QImage(int(item.size().width()), int(item.size().height()), QtGui.QImage.Format_ARGB32)
            painter = QtGui.QPainter(png)
            painter.setRenderHints(painter.Antialiasing | painter.TextAntialiasing)
            item.scene().render(painter, QtCore.QRectF(), item.mapRectToScene(item.boundingRect()))
            painter.end()

            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.WriteOnly)
            png=png.scaled(100,100,QtCore.Qt.KeepAspectRatio)
            png.save(buffer,"png")

            string=buffer.data().data()
            self.save_parameters.current_group._v_attrs['pixmap2D']=string

            if self.ui.overlay2D_pb.isChecked():
                #display list of actual saved 2Dscans
                self.list_2Dscans()

            self.save_parameters.h5_file.flush()

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')



    def update_2D_graph(self,datas):
        """
            Update the 2D graphic window in the Graphic Interface with the given datas (if not none).

            Depending on scan type :
                * *2D scan* :
                    * Calibrate the axis positions between graphic and scan
                    * Update scan datas with the given datas values.
                    * Set an image with the updated scan data
                * *1D scan* :
                    * Calibrate the axis positions between graphic and scan
                    * Update scan datas with the given datas values.
                    * Concatenate 1D vectors to make a 2D image
                    * Set an image with the updated scan data

            =============== =============================== ===========================
            **Parameters**    **Type**                       **Description**
            *datas*           double precision float array   the data values to update
            =============== =============================== ===========================

            See Also
            --------
            update_status
        """
        try:
            if datas != dict(): # no data to display
                if "2D" in self.DAQscan_settings.child('scan_options','scan_type').value():    #scan2D type cartography
                    if not(self.plot_2D_ini):
                        self.plot_2D_ini=True
                        self.scan_x_axis=self.scan_parameters.axis_2D_1
                        self.scan_y_axis=self.scan_parameters.axis_2D_2
                        self.ui.scan2D_graph.set_scaling_axes(edict(scaled_xaxis=edict(label=self.scan_moves[0][0][0],units=None,offset=np.min(self.scan_x_axis),scaling=np.mean(np.diff(self.scan_x_axis))),scaled_yaxis=edict(label=self.scan_moves[0][1][0],units=None,offset=np.min(self.scan_y_axis),scaling=np.mean(np.diff(self.scan_y_axis)))))
                        self.scan_data_2D=[np.zeros((len(self.scan_parameters.axis_2D_2),len(self.scan_parameters.axis_2D_1))) for ind in range(max((3,len(datas))))]
                        #self.scan_data_2D_to_save=np.zeros((self.scan_parameters.Nsteps,len(datas['datas'])+2))

                    pos_axis_1=self.scan_positions[0][1]
                    pos_axis_2=self.scan_positions[1][1]
                    #self.scan_data_2D_to_save[self.ind_scan,:]=np.concatenate((np.array([pos_axis_1,pos_axis_2]),np.array(datas['datas'][:])))
                    self.scan_x_axis=self.scan_parameters.axis_2D_1
                    self.scan_y_axis=self.scan_parameters.axis_2D_2
                    ind_pos_axis_1=self.scan_parameters.axis_2D_1_indexes[self.ind_scan]
                    ind_pos_axis_2=self.scan_parameters.axis_2D_2_indexes[self.ind_scan]
                    for ind_plot in range(min((3,len(datas)))):
                        self.scan_data_2D[ind_plot][ind_pos_axis_2,ind_pos_axis_1]=list(datas.values())[ind_plot]

                    self.ui.scan2D_graph.setImage(*self.scan_data_2D)
                else: # scan 1D with concatenation of vectors making a 2D image
                    if not(self.plot_2D_ini):
                        self.plot_2D_ini=True
                        
                        data=datas[list(datas.keys())[0]]
                        Ny=len(data[list(data.keys())[0]])

                        self.scan_y_axis=np.array([])
                        if self.DAQscan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                            self.scan_x_axis=self.scan_parameters.axis_1D[0::2]
                        else:
                            self.scan_x_axis=self.scan_parameters.axis_1D

                        Nx=len(self.scan_x_axis)

                        if 'x_axis'in data.keys():
                            self.scan_y_axis=data['x_axis']
                        else:
                            self.scan_y_axis=np.linspace(0,Ny-1,Ny)
                        self.ui.scan2D_graph.set_scaling_axes(edict(scaled_xaxis=edict(label=self.scan_moves[0][0][0],units=None,offset=np.min(self.scan_x_axis),scaling=np.mean(np.diff(self.scan_x_axis))),scaled_yaxis=edict(label="",units=None,offset=np.min(self.scan_y_axis),scaling=np.mean(np.diff(self.scan_y_axis)))))
                        self.scan_data_2D=[]
                        for ind,key in enumerate(datas):
                            if ind>=3:
                                break
                            self.scan_data_2D.append(np.zeros([datas[key]['data'].shape[0]]+[Nx]))
                        #self.scan_data_2D_to_save=np.zeros((self.scan_parameters.Nsteps,Ny,len(datas)))


                    if self.DAQscan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                        if not utils.odd_even(self.ind_scan):
                            self.scan_x_axis[self.ind_scan/2]=self.scan_positions[0][1]
                            for ind_plot,key in enumerate(datas.keys()):
                                self.scan_data_2D[ind_plot][:,int(self.ind_scan/2)]=datas[key]['data']

                    else:
                        for ind_plot,key in enumerate(datas.keys()):
                            self.scan_data_2D[ind_plot][:,self.ind_scan]=datas[key]['data']

                    self.ui.scan2D_graph.setImage(*self.scan_data_2D)


        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')

    def update_1D_graph(self,datas):
        """
            Update the 1D graphic window in the Graphic Interface with the given datas.

            Depending of scan type :
                * *'Linear back to start'* scan :
                    * Calibrate axis positions between graph and scan
                    * Update scan datas from the given datas values
                    * Set data on item attribute
                * *'linear'* or else scan :
                    * Calibrate axis positions between graph and scan
                    * Update scan datas from the given datas values

            =============== ============================== =====================================
            **Parameters**    **Type**                      **Description**
            *datas*          Double precision float array   The datas to be showed in the graph
            =============== ============================== =====================================

            See Also
            --------
            update_status
        """
        try:
            self.scan_y_axis=np.array([])
            if self.plot_items==[]:
                for ind in range(len(datas)):
                    self.plot_items.append(self.ui.scan1D_graph.plot(pen=self.plot_colors[ind]))

                if self.DAQscan_settings.child('scan_options','scan_type').value()=='Scan1D' and self.DAQscan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                    self.scan_x_axis=np.zeros((self.scan_parameters.Nsteps/2))
                    self.scan_data_1D=np.zeros((self.scan_parameters.Nsteps/2,len(datas))) #length is doubled beacause one add strat position for each position
                else:
                    self.scan_x_axis=np.zeros((self.scan_parameters.Nsteps))
                    self.scan_data_1D=np.zeros((self.scan_parameters.Nsteps,len(datas)))

                #self.scan_data_1D_to_save=np.zeros((self.scan_parameters.Nsteps,len(datas)+1))
                self.ui.scan1D_graph.plotItem.getAxis('bottom').setLabel(self.scan_moves[0][0][0])
                self.ui.scan1D_graph.plotItem.getAxis('left').setLabel(self.DAQscan_settings.child('scan_options','plot_from').value())


            if self.DAQscan_settings.child('scan_options','scan_type').value()=='Scan1D' and self.DAQscan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                if not utils.odd_even(self.ind_scan):
                    self.scan_x_axis[self.ind_scan/2]=self.scan_positions[0][1]
                    self.scan_data_1D[self.ind_scan/2,:]=np.array(list(datas.values())[-1::-1]) #to preserve order of saved datas
                    for ind_plot,item in enumerate(self.plot_items):
                        item.setData(self.scan_x_axis[0:self.ind_scan/2],self.scan_data_1D[0:self.ind_scan/2,ind_plot])
            else:
                self.scan_x_axis[self.ind_scan]=self.scan_positions[0][1]
                self.scan_data_1D[self.ind_scan,:]=np.array(list(datas.values())[-1::-1]) #to preserve order of saved datas

                for ind_plot,item in enumerate(self.plot_items):
                    item.setData(self.scan_x_axis[0:self.ind_scan],self.scan_data_1D[0:self.ind_scan,ind_plot])

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time,log_type='log')

    @pyqtSlot(list)
    def thread_status(self,status): # general function to get datas/infos from all threads back to the main
        """
            | General function to get datas/infos from all threads back to the main.
            |

            Switch the status with :
                * *"Update status"* : Update the status bar with the status attribute txt message
                * *"Update_scan_index"* : Set the value of the User Interface - indice_scan_sb attribute.
                * *"Scan_done"* : Save the scan and init the positions
                * *"Timeout"* : Set the "Timeout occured" in the User Interface-log message

            See Also
            --------
            update_status, save_scan, set_ini_positions
        """
        if status[0]=="Update_Status":
            if len(status)>2:
                self.update_status(status[1],wait_time=self.wait_time,log_type=status[2])
            else:
                self.update_status(status[1],wait_time=self.wait_time)

        elif status[0]=="Update_scan_index":
            self.ind_scan=status[1]
            self.ui.indice_scan_sb.setValue(status[1])
        elif status[0]=="Scan_done":
            self.ui.scan_done_LED.set_as_true()
            self.save_scan()
            self.set_ini_positions()
        elif status[0]=="Timeout":
            self.ui.log_message.setText('Timeout occured')




    def update_status(self,txt,wait_time=0,log_type=None):
        """
            Show the txt message in the status bar with a delay of wait_time ms.

            =============== =========== =======================
            **Parameters**    **Type**    **Description**
            *txt*             string      The message to show
            *wait_time*       int         the delay of showing
            *log_type*        string      the type of the log
            =============== =========== =======================
        """
        try:
            self.ui.statusbar.showMessage(txt,wait_time)
            if log_type is not None:
                self.log_signal.emit(self.title+': '+txt)
                logging.info(self.title+': '+txt)
        except Exception as e:
            pass


class DAQ_Scan_Acquisition(QObject):
    """
        =========================== ========================================
        **Attributes**               **Type**
        *scan_data_tmp*              instance of pyqtSignal
        *status_sig*                 instance of pyqtSignal
        *stop_scan_flag*             boolean
        *settings*                   instance og pyqtgraph.parametertree
        *filters*                    instance of tables.Filters
        *ind_scan*                   int
        *detector_modules*           Object list
        *detector_modules_names*     string list
        *move_modules*               Object list
        *move_modules_names*         string list
        *scan_moves*                 float list
        *scan_x_axis*                float array
        *scan_y_axis*                float array
        *scan_z_axis*                float array
        *scan_x_axis_unique*         float array
        *scan_y_axis_unique*         float array
        *scan_z_axis_unique*         float array
        *scan_shape*                 int
        *Nscan_steps*                int
        *scan_read_positions*        list
        *scan_read_datas*            list
        *scan_saves*                 dictionnary list
        *move_done_flag*             boolean
        *det_done_flag*              boolean
        *timeout_scan_flag*          boolean
        *timer*                      instance of QTimer
        *move_done_positions*        dictionnary
        *det_done_datas*             dictionnary
        *h5_file*                    instance class File from tables module
        *h5_file_current_group*      instance of Group
        *h5_file_det_groups*         Group list
        *h5_file_move_groups*        Group list
        *h5_file_channels_group*     Group dictionnary
        =========================== ========================================

    """
    scan_data_tmp=pyqtSignal(dict)
    status_sig = pyqtSignal(list)
    def __init__(self,settings=None,h5_file=None,h5_file_current_group=None,move_modules=[],detector_modules=[],scan_moves=[],scan_saves=[]):
        """
            DAQ_Scan_Acquisition deal with the acquisition part of daq_scan.

            See Also
            --------
            custom_tree.parameter_to_xml_string
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(QObject,self).__init__()

        self.stop_scan_flag=False
        self.settings=settings
        self.filters = tables.Filters(complevel=self.settings.child('saving_options','compression_options', 'h5comp_level').value(),
                              complib=self.settings.child('saving_options','compression_options','h5comp_library').value())        #options to save data to h5 file using compression zlib library and level 5 compression

        self.ind_scan=None
        self.detector_modules=detector_modules
        self.detector_modules_names=[mod.title for mod in self.detector_modules]
        self.move_modules=move_modules
        self.move_modules_names=[mod.title for mod in self.move_modules]
        self.scan_moves=scan_moves
        self.scan_x_axis=None
        self.scan_y_axis=None
        self.scan_z_axis=None
        self.scan_x_axis_unique=None
        self.scan_y_axis_unique=None
        self.scan_z_axis_unique=None
        self.scan_shape=None
        self.Nscan_steps=len(scan_moves)
        self.scan_read_positions=[]
        self.scan_read_datas=[]
        self.scan_saves=scan_saves
        self.move_done_flag=False
        self.det_done_flag=False
        self.timeout_scan_flag=False
        self.timer=QTimer();self.timer.setSingleShot(True);self.timer.timeout.connect(self.timeout);
        self.move_done_positions=edict()
        self.det_done_datas=edict()
        self.h5_file=h5_file
        self.h5_file_current_group=h5_file_current_group
        self.h5_file_det_groups=[]
        self.h5_file_move_groups=[]
        self.h5_file_channels_group=edict()
        #save settings from move modules
        for ind_move,move_name in enumerate(self.move_modules_names):
            move_group_name='Move{:03.0f}'.format(ind_move)
            if not self.h5_file_current_group.__contains__(move_group_name):
                self.h5_file_move_groups.append(self.h5_file.create_group(self.h5_file_current_group,move_group_name))
                self.h5_file_move_groups[-1]._v_attrs.Move_name=move_name
                self.h5_file_move_groups[-1]._v_attrs.type='move'
                self.h5_file_move_groups[-1]._v_attrs.settings=custom_tree.parameter_to_xml_string(self.move_modules[ind_move].settings)
            else:
                self.h5_file_move_groups.append(self.h5_file_current_group._f_get_child(move_group_name))

        #save settings from detector modules
        for ind_det,det_name in enumerate(self.detector_modules_names):
            det_group_name='Det{:03.0f}'.format(ind_det)
            if not self.h5_file_current_group.__contains__(det_group_name):
                self.h5_file_det_groups.append(self.h5_file.create_group(self.h5_file_current_group,det_group_name))
                self.h5_file_det_groups[-1]._v_attrs.Detector_name=det_name
                self.h5_file_det_groups[-1]._v_attrs.type='detector'
                #settings=Parameter.create(name='Det Settings', type='group')
                #settings.clearChildren()
                #settings.restoreState(self.detector_modules[ind_det].settings.saveState(filter='user'))

                settings_str=custom_tree.parameter_to_xml_string(self.detector_modules[ind_det].settings)
                if self.detector_modules[ind_det].DAQ_type!='DAQ0D':
                    settings_str=b'<All_settings title="All Settings" type="group">'+settings_str
                    for ind_viewer,viewer in enumerate(self.detector_modules[ind_det].ui.viewers):
                        settings_str+='<Viewer{:0d}_ROI_settings title="ROI Settings" type="group">'.format(ind_viewer).encode()
                        settings_str+=custom_tree.parameter_to_xml_string(viewer.roi_settings)+'</Viewer{:0d}_ROI_settings>'.format(ind_viewer).encode()
                    settings_str+=b'</All_settings>'
                self.h5_file_det_groups[-1]._v_attrs.settings=settings_str
            else:
                self.h5_file_det_groups.append(self.h5_file_current_group._f_get_child(det_group_name))
            self.h5_file_channels_group[det_name]=edict(channels0D=[],channels1D=OrderedDict(),channels2D=OrderedDict())

    @pyqtSlot(list)
    def queue_command(self,command):
        """
            Treat the queue of commands from the current command to act, between :
                * *start_acquisition*
                * *stop_acquisition*
                * *set_ini_position*
                * *move_stages*

            =============== ============== =========================
            **Parameters**    **Type**      **Description**
            command           string list   the command string list
            =============== ============== =========================

            See Also
            --------
            start_acquisition, set_ini_positions, move_stages
        """
        if command[0]=="start_acquisition":
            self.start_acquisition()


        elif command[0]=="stop_acquisition":
            self.stop_scan_flag=True

        elif command[0]=="set_ini_positions":
            self.set_ini_positions()

        elif command[0]=="move_stages":
            self.move_stages(command[1])

    def set_ini_positions(self):
        """
            | Set the positions from the scan_move attribute.
            |
            | Move all activated modules to specified positions.
            | Check the module corresponding to the name assigned in pos.

            See Also
            --------
            DAQ_Move_main.daq_move.Move_Abs
        """
        try:
            positions=self.scan_moves[0]
            for ind_move,pos in enumerate(positions): #move all activated modules to specified positions
                if pos[0]!=self.move_modules[ind_move].title: # check the module correspond to the name assigned in pos
                    raise Exception('wrong move module assignment')
                self.move_modules[ind_move].Move_Abs(pos[1])
        except Exception as e:
            self.status_sig.emit(["Update_Status",str(e),'log'])

    pyqtSlot(str,float)
    def move_done(self,name,position):
        """
            | Update the move_done_positions attribute if needed.
            | If position attribute is setted, for all move modules launched, update scan_read_positions with a [modulename, position] list.

            ============== ============ =================
            **Parameters**    **Type**    **Description**
            *name*            string     the module name
            *position*        float      ??? 
            ============== ============ =================
        """
        try:
            if name not in list(self.move_done_positions.keys()):
                self.move_done_positions[name]=position

            if len(self.move_done_positions.items())==len(self.move_modules):


                list_tmp=[]
                for name_tmp in self.move_modules_names:
                    list_tmp.append([name_tmp,self.move_done_positions[name_tmp]])
                self.scan_read_positions=list_tmp

                self.move_done_flag=True
                #print(self.scan_read_positions[-1])
        except Exception as e:
            self.status_sig.emit(["Update_Status",str(e),'log'])

    pyqtSlot(edict) #edict(name=self.title,data0D=None,data1D=None,data2D=None)
    def det_done(self,data):
        """
            | Initialize 0D/1D/2D datas from given data parameter.
            | Update h5_file group and array.
            | Save 0D/1D/2D datas.

            =============== ============================== ======================================
            **Parameters**    **Type**                      **Description**
            *data*          Double precision float array   The initializing data of the detector
            =============== ============================== ======================================
        """
        try:
            if data['name'] not in list(self.det_done_datas.keys()):
                self.det_done_datas[data['name']]=data
            if len(self.det_done_datas.items())==len(self.detector_modules):

                self.scan_read_datas=self.det_done_datas[self.settings.child('scan_options','plot_from').value()].copy()

                if self.ind_scan==0:#first occurence=> initialize the channels
                    for ind_det,det_name in enumerate(self.detector_modules_names):
                        #initialize 0D datas
                        if self.det_done_datas[det_name]['data0D'] is not None: #save Data0D if present
                            if len(self.det_done_datas[det_name]['data0D'])!=0: #save Data0D only if not empty (could happen)
                                try:
                                    data0D_group=self.h5_file.create_group(self.h5_file_det_groups[ind_det],'Data0D')
                                    data0D_group._v_attrs.type='data0D'
                                    arrays=[]
                                
                                    for ind_channel,key in enumerate(self.det_done_datas[det_name]['data0D'].keys()):
                                
                                        try:
                                            array=self.h5_file.create_carray(data0D_group,"CH{:03d}".format(ind_channel),obj=np.zeros(self.scan_shape), title=key,filters=self.filters)
                                            array.set_attr('scan_type',self.settings.child('scan_options','scan_type').value())
                                            #array.attrs['type']='data'
                                            array.set_attr('data_type','0D')
                                            array.set_attr('data_name',key)
                                            array.set_attr('type','channel0D')
                                            array.set_attr('shape',self.scan_shape)
                                            arrays.append(array)
                                        except: pass
                                
                                    self.h5_file_channels_group[det_name]['channels0D'].append(arrays)
                                except: pass
                        #initialize 1D datas
                        if self.det_done_datas[det_name]['data1D'] is not None: #save Data1D if present
                            if len(self.det_done_datas[det_name]['data1D'])!=0: #save Data0D only if not empty (could happen)
                                try:
                                    data1D_group=self.h5_file.create_group(self.h5_file_det_groups[ind_det],'Data1D')
                                    data1D_group._v_attrs.type='data1D'
                                except: pass
                                for ind_channel,(key,channel) in enumerate(self.det_done_datas[det_name]['data1D'].items()):
                                    try:
                                        channel_group=self.h5_file.create_group(data1D_group,"CH{:03d}".format(ind_channel))
                                        channel_group._v_attrs.Channel_name=key
                                        if 'x_axis' in channel.keys():
                                            x_axis=channel['x_axis']
                                            xarray=self.h5_file.create_array(channel_group,"x_axis",obj=x_axis, title=key)
                                            xarray.set_attr('shape',xarray.shape)
                                            xarray.attrs['type']='data'
                                            xarray.attrs['data_type']='1D'
                                        array=self.h5_file.create_carray(channel_group,'Data',obj=np.zeros(self.scan_shape+[len(channel['data'])]), title='data',filters=self.filters)
                                        array.set_attr('scan_type',self.settings.child('scan_options','scan_type').value())
                                        array.set_attr('data_type','1D')
                                        #array.attrs['type']='data'
                                        array.set_attr('data_name',key)
                                        array.set_attr('type','channel1D')
                                        array.set_attr('shape',self.scan_shape+[len(channel['data'])])
                                        self.h5_file_channels_group[det_name]['channels1D']["CH{:03d}".format(ind_channel)]=array
                                    except: pass

                        #initialize 2D datas

                        if self.det_done_datas[det_name]['data2D'] is not None and self.settings.child('saving_options','save_2D').value(): #save Data2D if present and of options is checked
                            if len(self.det_done_datas[det_name]['data2D'])!=0: #save Data0D only if not empty (could happen)
                                try:
                                    data2D_group=self.h5_file.create_group(self.h5_file_det_groups[ind_det],'Data2D')
                                    data2D_group._v_attrs.type='data2D'
                                except: pass
                                for ind_channel,(key,channel) in enumerate(self.det_done_datas[det_name]['data2D'].items()):
                                    try:
                                        channel_group=self.h5_file.create_group(data2D_group,"CH{:03d}".format(ind_channel))
                                        channel_group._v_attrs.Channel_name=key
                                        if 'x_axis' in channel.keys():
                                            x_axis=channel['x_axis']
                                            xarray=self.h5_file.create_array(channel_group,"x_axis",obj=x_axis, title=key)
                                            xarray.set_attr('shape',xarray.shape)
                                            xarray.attrs['type']='data'
                                            xarray.attrs['data_type']='1D'
                                        if 'y_axis' in channel.keys():
                                            y_axis=channel['y_axis']
                                            yarray=self.h5_file.create_array(channel_group,"y_axis",obj=y_axis, title=key)
                                            yarray.set_attr('shape',yarray.shape)
                                            yarray.attrs['type']='data'
                                            yarray.attrs['data_type']='1D'
                                        shape=self.scan_shape[:]
                                        for ind_index in channel['data'].shape:
                                            shape+=[ind_index]
                                        array=self.h5_file.create_carray(channel_group,'Data',obj=np.zeros(shape), title='data',filters=self.filters)
                                        array.set_attr('scan_type',self.settings.child('scan_options','scan_type').value())
                                        array.set_attr('data_type','2D')
                                        #array.attrs['type']='data'
                                        array.set_attr('data_name',key)
                                        array.set_attr('shape',shape)
                                        array.set_attr('type','channel2D')
                                        self.h5_file_channels_group[det_name]['channels2D']["CH{:03d}".format(ind_channel)]=array
                                    except: pass


                if len(self.scan_saves[self.ind_scan][0]['indexes'])==1:
                    indexes=tuple([self.scan_saves[self.ind_scan][0]['indexes']['indx']])
                elif len(self.scan_saves[self.ind_scan][0]['indexes'])==2:
                    indexes=tuple([self.scan_saves[self.ind_scan][0]['indexes']['indx'],self.scan_saves[self.ind_scan][0]['indexes']['indy']])
                else:
                    raise Exception('Wrong indexes dimensionality')

                for ind_det,det_name in enumerate(self.detector_modules_names):
                    #save 0D data
                    for ind_channel,arrays in enumerate(self.h5_file_channels_group[det_name]['channels0D']):
                        for array in arrays:
                            array.__setitem__(indexes,value=self.det_done_datas[det_name]['data0D'][array._v_attrs.data_name])
                    #save 1D data
                    for ind_channel,(chan_key,array) in enumerate(self.h5_file_channels_group[det_name]['channels1D'].items()):
                        array.__setitem__(indexes,value=self.det_done_datas[det_name]['data1D'][array.attrs.data_name]['data'])

                    #save 2D data
                    for ind_channel,(chan_key,array) in enumerate(self.h5_file_channels_group[det_name]['channels2D'].items()):
                        array.__setitem__(indexes,value=self.det_done_datas[det_name]['data2D'][array.attrs.data_name]['data'])

                self.det_done_flag=True
                self.scan_data_tmp.emit(edict(positions=self.scan_read_positions,datas=self.scan_read_datas))
        except Exception as e:
            self.status_sig.emit(["Update_Status",str(e),'log'])

    def timeout(self):
        """
            Send the status signal *'Time out during acquisition'* and stop the timer.
        """
        self.timeout_scan_flag=True
        self.timer.stop()
        self.status_sig.emit(["Update_Status","Timeout during acquisition",'log'])
        self.status_sig.emit(["Timeout"])

    def move_stages(self,positions):
        """
            Move all the activated modules to the specified positions.

            =============== ============ =============================================
            **Parameters**    **Type**    **Description**
            *positions*       tuple list  The list of the positions related to indices
            =============== ============ =============================================

            See Also
            --------
            DAQ_Move_main.daq_move.Move_Abs, move_done, det_done, check_array_in_h5, wait_for_move_done, wait_for_det_done, det_done
        """
        for ind_move,pos in enumerate(positions): #move all activated modules to specified positions
            self.move_modules[ind_move].Move_Abs(pos)

    def start_acquisition(self):
        try:
            status=''
            for mod in self.move_modules:
                mod.move_done_signal.connect(self.move_done)
            for mod in self.detector_modules:
                mod.grab_done_signal.connect(self.det_done)

            self.scan_read_positions=[]
            self.scan_read_datas=[]
            self.stop_scan_flag=False
            Naxis=len(self.scan_moves[0])


            self.scan_x_axis=np.array([pos[0][1] for pos in self.scan_moves])
            self.scan_x_axis_unique=np.unique(self.scan_x_axis)
            self.check_array_in_h5('scan_x_axis',self.h5_file_current_group,self.scan_x_axis)
            self.check_array_in_h5('scan_x_axis_unique',self.h5_file_current_group,self.scan_x_axis_unique)

            if Naxis==1: #"means scan 1D"
                if self.settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                    self.scan_shape=[len(self.scan_x_axis)]

                else:
                    self.scan_shape=[len(self.scan_x_axis_unique)]
            else:
                self.scan_shape=[len(self.scan_x_axis_unique)]

            if Naxis==2:#"means scan 2D"
                self.scan_y_axis=np.array([pos[1][1] for pos in self.scan_moves])
                self.scan_y_axis_unique=np.unique(self.scan_y_axis)
                self.check_array_in_h5('scan_y_axis',self.h5_file_current_group,self.scan_y_axis)
                self.check_array_in_h5('scan_y_axis_unique',self.h5_file_current_group,self.scan_y_axis_unique)
                self.scan_shape.append(len(self.scan_y_axis_unique))
            elif Naxis>2:#"means scan 3D" not really implemented yet
                self.scan_z_axis=np.array([pos[2][1] for pos in self.scan_moves])
                self.scan_z_axis_unique=np.unique(self.scan_z_axis)
                self.check_array_in_h5('scan_z_axis',self.h5_file_current_group,self.scan_z_axis)
                self.check_array_in_h5('scan_z_axis_unique',self.h5_file_current_group,self.scan_z_axis_unique)
                self.scan_shape.append(len(self.scan_z_axis_unique))

            self.status_sig.emit(["Update_Status","Acquisition has started",'log'])
            for ind_scan,positions in enumerate(self.scan_moves): #move motors of modules
                self.ind_scan=ind_scan
                self.status_sig.emit(["Update_scan_index",ind_scan])
                if self.stop_scan_flag or  self.timeout_scan_flag:
                    if self.stop_scan_flag:
                        status='Data Acquisition has been stopped by user'
                        self.status_sig.emit(["Update_Status",status,'log'])
                    break
                self.move_done_positions=dict()
                self.move_done_flag=False
                for ind_move,pos in enumerate(positions): #move all activated modules to specified positions
                    if pos[0]!=self.move_modules[ind_move].title: # check the module correspond to the name assigned in pos
                        raise Exception('wrong move module assignment')
                    self.move_modules[ind_move].Move_Abs(pos[1])

                self.wait_for_move_done()

                paths =self.scan_saves[ind_scan] #start acquisition
                if self.stop_scan_flag or  self.timeout_scan_flag:
                    if self.stop_scan_flag:
                        status='Data Acquisition has been stopped by user'
                        self.status_sig.emit(["Update_Status",status,'log'])
                    break
                self.det_done_flag=False
                self.det_done_datas=dict()
                for ind_det, path in enumerate(paths): #path on the form edict(det_name=...,file_path=...,indexes=...)
                    if path['det_name']!=self.detector_modules[ind_det].title: # check the module correspond to the name assigned in path
                        raise Exception('wrong det module assignment')
                    self.detector_modules[ind_det].SnapShot(str(path['file_path']))

                self.wait_for_det_done()



            for mod in self.move_modules:
                mod.move_done_signal.disconnect(self.move_done)
            for mod in self.detector_modules:
                mod.grab_done_signal.disconnect(self.det_done)
            self.status_sig.emit(["Update_Status","Acquisition has finished",'log'])
            self.status_sig.emit(["Scan_done"])

            self.timer.stop()
        except Exception as e:
            status=str(e)
            self.status_sig.emit(["Update_Status",status,'log'])

    def check_array_in_h5(self,arr_name,group,obj):
        if arr_name in group._v_children.keys():
            group._f_get_child(arr_name).remove()
        arr=self.h5_file.create_array(group,arr_name,obj)
        arr.set_attr('type','navigation_axis')
        arr.set_attr('data_type','1D')
        arr.set_attr('shape',obj.shape)
        return arr

    def wait_for_det_done(self):
        self.timeout_scan_flag=False
        self.timer.start(self.settings.child('time_flow','timeout').value())
        while not(self.det_done_flag or  self.timeout_scan_flag):
            #wait for grab done signals to end
            QtWidgets.QApplication.processEvents()

    def wait_for_move_done(self):
        self.timeout_scan_flag=False
        self.timer.start(self.settings.child('time_flow','timeout').value())


        while not(self.move_done_flag or  self.timeout_scan_flag):
            #wait for move done signals to end
            QtWidgets.QApplication.processEvents()





if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow();fname="";
    win.setVisible(False)
    splash=QtGui.QPixmap('..//documentation//splash.png')
    splash_sc=QtWidgets.QSplashScreen(splash,Qt.WindowStaysOnTopHint)
    splash_sc.show()
    splash_sc.raise_()
    splash_sc.showMessage('Loading Main components',color=Qt.white)
    QtWidgets.QApplication.processEvents()

    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    win.setWindowTitle('pymodaq Scan')
    win.setVisible(False)
    prog = DAQ_Scan(area,fname)
    QThread.sleep(4)
    splash_sc.finish(win)
    win.setVisible(True)
    
    
    sys.exit(app.exec_())

