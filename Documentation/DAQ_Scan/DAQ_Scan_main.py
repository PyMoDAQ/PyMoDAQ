from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QTimer, QDateTime, QDate, QTime

import sys
from PyMoDAQ.DAQ_Scan.GUI.DAQ_Scan_GUI import Ui_Form
from PyMoDAQ.DAQ_Move.hardware import DAQ_Move_Stage_type
from collections import OrderedDict
from PyMoDAQ.DAQ_Utils import python_lib as mylib
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
import PyMoDAQ.DAQ_Utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
import numpy as np


from PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor import Image_View_Multicolor

import matplotlib.image as mpimg
from PyMoDAQ.DAQ_Move.DAQ_Move_main import DAQ_Move
from PyMoDAQ.DAQ_Viewer.DAQ_viewer_main import DAQ_Viewer
from PyMoDAQ.DAQ_Move import hardware as movehardware

from PyMoDAQ.DAQ_Viewer import hardware2D, hardware1D, hardware0D

from PyMoDAQ.DAQ_Utils.plotting.QLED.qled import QLED
from easydict import EasyDict as edict
from PyMoDAQ.DAQ_Utils import DAQ_utils
from pathlib import Path
import tables
import datetime

import pickle
import os
from pyqtgraph.parametertree.Parameter import registerParameterType

class QSpinBox_ro(QtWidgets.QSpinBox):
    def __init__(self, **kwargs):
        super(QtWidgets.QSpinBox,self).__init__()
        self.setMaximum(100000)
        self.setReadOnly(True)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
class PresetScalableGroupMove( pTypes.GroupParameter):
    """
        |

        ================ =============
        **Attributes**    **Type**
        *opts*            dictionnary
        ================ =============

        See Also
        --------
        hardware.DAQ_Move_Stage_type
    """
    def __init__(self, **opts):
        opts['type'] = 'groupmove'
        opts['addText'] = "Add"
        opts['addList'] = DAQ_Move_Stage_type.names()
        pTypes.GroupParameter.__init__(self, **opts)

    def addNew(self, typ):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        childnames=[par.name() for par in self.children()]
        if childnames==[]:
            newindex=0
        else:
            newindex=len(childnames)

        params=DAQ_Move.params
        for param in params:
            if param['type']=='itemselect' or param['type']=='list':
                param['show_pb']=True


        class_=getattr(movehardware,'DAQ_Move_'+typ)
        params_hardware=getattr(class_,'params')
        for param in params_hardware:
            if param['type']=='itemselect' or param['type']=='list':
                param['show_pb']=True
        params[1]['children']=params_hardware
        params[0]['children'][0]['value']=typ

        child={'title': 'Move {:02.0f}'.format(newindex) ,'name': 'move{:02.0f}'.format(newindex), 'type': 'group', 'children': [
                {'title': 'Name:' , 'name': 'name', 'type': 'str', 'value': 'Move {:02.0f}'.format(newindex)},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params
               }],'removable':True, 'renamable':False}

        self.addChild(child)
registerParameterType('groupmove', PresetScalableGroupMove, override=True)
class PresetScalableGroupDet( pTypes.GroupParameter):
    """
        =============== ==============
        **Attributes**    **Type**
        *opts*            dictionnary
        *options*         string list
        =============== ==============

        See Also
        --------
        hardware0D.DAQ_0DViewer_Det_type, hardware1D.DAQ_1DViewer_Det_type, hardware2D.DAQ_2DViewer_Det_type
    """
    def __init__(self, **opts):
        opts['type'] = 'groupdet'
        opts['addText'] = "Add"
        options=[]
        for name in hardware0D.DAQ_0DViewer_Det_type.names():
            options.append('DAQ0D/'+name)
        for name in hardware1D.DAQ_1DViewer_Det_type.names():
            options.append('DAQ1D/'+name)
        for name in hardware2D.DAQ_2DViewer_Det_type.names():
            options.append('DAQ2D/'+name)
        opts['addList'] = options

        pTypes.GroupParameter.__init__(self, **opts)

    def addNew(self, typ):
        """
            Add a child.

            =============== ===========
            **Parameters**    **Type**
            *typ*             string
            =============== ===========
        """
        childnames=[par.name() for par in self.children()]
        if childnames==[]:
            newindex=0
        else:
            newindex=len(childnames)

        params=DAQ_Viewer.params
        for param in params:
            if param['type']=='itemselect' or param['type']=='list':
                param['show_pb']=True

        params[0]['children'][0]['value']=typ[0:5]
        params[0]['children'][1]['value']=typ[6:]
        params[0]['children'][4]['visible']=True

        if '0D' in typ:
            class_=getattr(hardware0D,'DAQ_0DViewer_'+typ[6:])
        elif '1D' in typ:
            class_=getattr(hardware1D,'DAQ_1DViewer_'+typ[6:])
        elif '2D' in typ:
            class_=getattr(hardware2D,'DAQ_2DViewer_'+typ[6:])
            params[0]['children'][5]['visible']=True

        params_hardware=getattr(class_,'params')
        for param in params_hardware:
            if param['type']=='itemselect' or param['type']=='list':
                param['show_pb']=True

        params[2]['children']=params_hardware
        child={'title': 'Det {:02.0f}'.format(newindex) ,'name': 'det{:02.0f}'.format(newindex), 'type': 'group', 'children': [
                {'title': 'Name:' , 'name': 'name', 'type': 'str', 'value': 'Det {:02.0f}'.format(newindex)},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params
               }],'removable':True, 'renamable':False}

        self.addChild(child)
registerParameterType('groupdet', PresetScalableGroupDet, override=True)

def set_param_from_param(param_old,param_new):
    """
        Walk through parameters children and set values using new parameter values.
    """
    for child_old in param_old.children():
        path=param_old.childPath(child_old)
        child_new=param_new.child(*path)
        param_type=child_old.type()
        if 'group' not in param_type: #covers 'group', custom 'groupmove'...
            try:
                if 'list' in param_type:#check if the value is in the limits of the old params (limits are usually set at initialization)
                    if child_new.value() in child_old.opts['limits']:
                        child_old.setValue(child_new.value())
                elif 'str' in param_type or 'browsepath' in param_type or 'text' in param_type:
                    if child_new.value()!="":#to make sure one doesnt overwrite something
                        child_old.setValue(child_new.value())
                else:
                    child_old.setValue(child_new.value())
            except Exception as e:
                pass
        else:
            set_param_from_param(child_old,child_new)


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
              *preset_params*         instance of pyqtgraph.parametertree
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
            | DAQ_Scan(parent,fname="",move_modules=None,detector_modules=None) is a user interface that will enable scanning of motors controlled by the module DAQ_Move and acquisition of signals using DAQ_0DViewer,DAQ_1DViewer or DAQ_2DViewer.
            |
            | Parent is the parent Widget ( a QWidget in general).
            |
            | Fname is a path pointing to a png image to be displayed at the beginning in the 2D viewer of the scan module.
            |
            | Move_modules is a dict of the type move_modules=dict(polarization=DAQ_Move_polarization) where DAQ_Move_polarization is an instance of the DAQ_Move class.
            |
            | Detector_modules is a dict of the type detector_modules=dict(current=DAQ_0D_current) where DAQ_0D_current is an instance of the DAQ_0DViewer class.
            |
            | The detector module can be any instance in the list:  DAQ_0DViewer, DAQ_1DViewer, DAQ_2DViewer. These modules have in common a signal: export_data_signal exporting a dict of the type: dict:=[x_axis=...,data=list of vectors...,data_measurements=list of floats] to be connected to main GUI
            |



            See Also
            --------
            move_to_crosshair, DAQscan_settings_changed, update_plot_det_items, update_scan_type, add_comments, add_log, set_scan, Quit_fun, start_scan, stop_scan, set_ini_positions
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Scan,self).__init__()
        self.title='DAQ_Scan'
        splash=QtGui.QPixmap('..//Documentation//splash.png')
        self.splash_sc=QtWidgets.QSplashScreen(splash,Qt.WindowStaysOnTopHint)
        self.init_prog=True

        self.ui=Ui_Form()
        widgetsettings=QtWidgets.QWidget()
        self.ui.setupUi(widgetsettings)


        self.dockarea=parent
        self.mainwindow=parent.parent()


        #%% create scan dock and make it a floating window
        self.ui.scan_dock = Dock("Scan", size=(1, 1), autoOrientation=False)     ## give this dock the minimum possible size
        self.ui.scan_dock.setOrientation('vertical')

        self.ui.scan_dock.addWidget(widgetsettings)
        self.dockarea.addDock(self.ui.scan_dock,'left')
        self.ui.scan_dock.float()

        #%% create logger dock
        self.ui.logger_dock=Dock("Logger")
        self.ui.logger_list=QtWidgets.QListWidget()
        self.ui.logger_list.setMinimumWidth(300)
        self.ui.logger_dock.addWidget(self.ui.logger_list)
        self.dockarea.addDock(self.ui.logger_dock,'top')
        self.ui.logger_dock.setVisible(False)

        #%% init the 2D viewer
        form=QtWidgets.QWidget()
        self.ui.scan2D_graph=Image_View_Multicolor(form)
        self.ui.scan2D_layout.addWidget(form)
        self.ui.scan2D_graph.ui.Show_histogram.setChecked(False)
        self.ui.scan2D_graph.ui.histogram_blue.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_green.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_red.setVisible(False)
        self.ui.move_to_crosshair_cb=QtWidgets.QCheckBox("Move at crosshair")
        self.ui.scan2D_graph.ui.horizontalLayout_2.addWidget(self.ui.move_to_crosshair_cb)
        self.ui.scan2D_graph.ui.crosshair.crosshair_dragged.connect(self.move_to_crosshair)

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




        #displaying the settings Tree

        self.settings_tree = ParameterTree()

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
            {'title': 'Base path:','name': 'base_path', 'type': 'browsepath', 'value': 'C:\Data'},
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

        param=[{'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'preset_default'}]
        params_move = [{'title': 'Moves:', 'name': 'Moves', 'type': 'groupmove'}]# PresetScalableGroupMove(name="Moves")]
        params_det =  [{'title': 'Detectors:', 'name': 'Detectors', 'type': 'groupdet'}]#[PresetScalableGroupDet(name="Detectors")]
        self.preset_params=Parameter.create(title='Preset', name='Preset', type='group', children=param+params_move+params_det)


        self.dataset_attributes=Parameter.create(name='Attributes', type='group', children=params_dataset)
        self.scan_attributes=Parameter.create(name='Attributes', type='group', children=params_scan)
        ##self.scan_attributes_tree = ParameterTree()
        ##self.scan_attributes_tree.setParameters(self.scan_attributes, showTop=False)

        self.scan_x_axis=None
        self.scan_y_axis=None
        self.scan_data_1D=None
        self.scan_data_2D=None
        self.ind_scan=None
        self.scan_data_2D_to_save=None
        self.scan_data_1D_to_save=None

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
            fname=DAQ_utils.select_file(start_path=None,save=True, ext='dock')
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
            fname=DAQ_utils.select_file(save=False, ext='dock')
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
        now=datetime.datetime.now()
        new_item=QtWidgets.QListWidgetItem(str(now)+": "+txt)
        self.ui.logger_list.addItem(new_item)

        self.save_parameters.logger_array.append(str(now)+": "+txt)


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
        settings_menu=menubar.addMenu('Settings')
        docked_menu=settings_menu.addMenu('Docked windows')
        action_load=docked_menu.addAction('Load Layout')
        action_save=docked_menu.addAction('Save Layout')
        action_clear=settings_menu.addAction('Clear moves/Detectors')
        action_clear.triggered.connect(self.clear_move_det_controllers)

        action_load.triggered.connect(self.load_layout_state)
        action_save.triggered.connect(self.save_layout_state)
        action_show_log=docked_menu.addAction('Show/hide log window')
        action_show_log.setCheckable(True)
        action_show_log.toggled.connect(self.ui.logger_dock.setVisible)



        preset_menu=menubar.addMenu('Preset Modes')
        action=preset_menu.addAction('Create a preset')
        action.triggered.connect(lambda: self.show_file_attributes(type_info='preset'))

        load_preset=preset_menu.addMenu('Load presets')
        load_mock=load_preset.addAction('Mock preset')
        load_canon=load_preset.addAction('Canon Preset')
        load_mock.triggered.connect(lambda: self.set_preset_mode('mock'))
        load_canon.triggered.connect(lambda: self.set_preset_mode('canon'))

        start,end=os.path.split(os.path.realpath(__file__))
        load_actions=[]
        for file in os.listdir(os.path.join(start,'preset_modes')):
            if file.endswith(".xml"):
                (filesplited,ext)=os.path.splitext(file)
                load_actions.append(load_preset.addAction(filesplited))
                load_actions[-1].triggered.connect(lambda: self.set_preset_mode(os.path.join(start,'preset_modes',file)))

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
                * **Connex_U** : initialize docks and modules procedure. Append an instance of DAQ_Move to the move_modules list.
                * **Connex_V** : initialize docks and modules procedure. Append an instance of DAQ_Move to the move_modules list.
                * **DAQ0D** : initialize viewer's dock and modules procedure. Append an instance of DAQ_Viewer to the detector_modules list.
                * **DAQ1D** : initialize viewer's dock and modules procedure. Append an instance of DAQ_Viewer to the detector_modules list.
                * **DAQ2D** : initialize viewer's dock and modules procedure. Append an instance of DAQ_Viewer to the detector_modules list.

            Returns
            -------
            (object list, object list) tuple
                The initialized Mock preset containing all the modules needed.

            See Also
            --------
            DAQ_Move_main.DAQ_Move, stop_moves,  DAQ_viewer_main.DAQ_Viewer
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
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
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
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
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
            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
        except Exception as e:
            pass

        try:
            det_name='Spectrum'
            self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
            self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
            self.dockarea.addDock(self.det_docks_settings[-1], 'bottom')
            self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])
            daq_type='DAQ1D'
            control_type='Mock'
            detector_modules.append(DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type))
            detector_modules[-1].ui.Detector_type_combo.setCurrentText(control_type)
            detector_modules[-1].ui.IniDet_pb.click()
            detector_modules[-1].settings.child('main_settings','overshoot').show()
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

    def set_canon_preset(self):
        """
            Set a Canon preset in 6 steps :
                * **Connex_U** : initialize docks and modules procedure. Append an instance of DAQ_Move to the move_modules list. Update settings tree with com_port child.
                * **Connex_V** : initialize docks and modules procedure. Append an instance of DAQ_Move to the move_modules list. Update settings tree with com_port child.
                * **Loading Detector Modules** (Hardware parameter settings procedure):
                    * *Kinesis* Power : Append an instance of DAQ_Move to the move_modules list. Update settings tree with serial number
                    * *Kinesis* Polarization : Append an instance of DAQ_Move to the move_modules list. Update settings tree with serial number
                    * *Kinesis_Flipper* Flipper : Append an instance of DAQ_Move to the move_modules list. Update settings tree with serial number
                    * *Kinesis_Flipper* Injection power : Append an instance of DAQ_Move to the move_modules list. Update settings tree with serial number
                    * *Kinesis Injection* power : Append an instance of DAQ_Move to the move_modules list. Update settings tree with serial number
                    * *PI* Delay : Append an instance of DAQ_Move to the move_modules list.

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
            DAQ_Move_main.DAQ_Move, stop_moves
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
            move_modules[-1].settings.child('Move_Settings','axis_address').setValue('U')
            com_ports=move_modules[-1].settings.child('Move_Settings','com_port').opts['limits']
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            for com in com_ports:
                if 'COM5' in com:
                    move_modules[-1].settings.child('Move_Settings','com_port').setValue(com)
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
            move_modules[-1].settings.child('Move_Settings','axis_address').setValue('V')
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            com_ports=move_modules[-1].settings.child('Move_Settings','com_port').opts['limits']
            for com in com_ports:
                if 'COM5' in com:
                    move_modules[-1].settings.child('Move_Settings','com_port').setValue(com)
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
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            serials=move_modules[-1].settings.child('Move_Settings','serial_number').opts['limits']
            for ser in serials:
                if '55000520' in ser:
                    move_modules[-1].settings.child('Move_Settings','serial_number').setValue(ser)
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
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            serials=move_modules[-1].settings.child('Move_Settings','serial_number').opts['limits']
            for ser in serials:
                if '55000309' in ser:
                    move_modules[-1].settings.child('Move_Settings','serial_number').setValue(ser)
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
            serials=move_modules[-1].settings.child('Move_Settings','serial_number').opts['limits']
            for ser in serials:
                if '37873712' in ser:
                    move_modules[-1].settings.child('Move_Settings','serial_number').setValue(ser)
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
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            serials=move_modules[-1].settings.child('Move_Settings','serial_number').opts['limits']
            for ser in serials:
                if '55000902' in ser:
                    move_modules[-1].settings.child('Move_Settings','serial_number').setValue(ser)
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
            move_modules[-1].settings.child('Move_Settings','scaling','scaling').setValue(0.66666)
            move_modules[-1].settings.child('Move_Settings','scaling','offset').setValue(106.42)
            move_modules[-1].settings.child('Move_Settings','scaling','use_scaling').setValue(True)
            move_modules[-1].settings.child('Main_Settings','movebounds').show()
            move_modules[-1].bounds_signal[bool].connect(self.stop_moves)
            devices=move_modules[-1].settings.child('Move_Settings','devices').opts['limits']
            for dev in devices:
                if 'PI' in dev:
                    move_modules[-1].settings.child('Move_Settings','devices').setValue(dev)
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

            * For each move in the obtained preset_params parameterTree's "move_type" children:
                * append to the move docks the corresponding Dock
                * append to the move_modules list the corresponding instance of DAQ_Move object.
                * in case of conex move type, update the settings tree with
                    * *axis_adress*
                    * *com_port limits*
                    * *com_port values*
            * For each detector in the obtained preset_param tree:
                * append to the det_types the corresponding det_type child.
                * append to the detector_modules list the corresponding instance of DAQ_Move object.
                * Update settings tree with avershoot

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
            custom_tree.XML_file_to_parameter, set_param_from_param, stop_moves, update_status,DAQ_Move_main.DAQ_Move, DAQ_viewer_main.DAQ_Viewer
        """
        children=custom_tree.XML_file_to_parameter(filename)
        preset_params=Parameter.create(title='Preset', name='Preset', type='group', children=children )
        self.preset_params=preset_params #so that it will be loaded as it is when one want to modify it (using create preset)
        self.move_docks=[]
        move_forms=[]
        move_modules=[]
        move_types=[]
        self.conex_count=0#this is in order to count the number of axes relate to the same conex controller
        self.conex_controller=None
        for ind_move,move in enumerate(preset_params.child(('Moves')).children()):
            try:
                move_name=move.child(('name')).value()
                move_settings=move.child(('params'))

                move_type=move_settings.child('Main_Settings','Move_type').value()
                move_types.append(move_type)
                self.move_docks.append(Dock(move_name, size=(150,250)))
                if ind_move==0:
                    self.dockarea.addDock(self.move_docks[-1], 'right',self.ui.logger_dock)
                else:
                    self.dockarea.addDock(self.move_docks[-1], 'right',self.move_docks[-2])
                move_forms.append(QtWidgets.QWidget())
                mov_mod_tmp=DAQ_Move(move_forms[-1],move_name)

                mov_mod_tmp.ui.Stage_type_combo.setCurrentText(move_type)

                set_param_from_param(mov_mod_tmp.settings,move_settings)

                mov_mod_tmp.settings.child('Main_Settings','movebounds').show()
                mov_mod_tmp.bounds_signal[bool].connect(self.stop_moves)
                self.move_docks[-1].addWidget(move_forms[-1])
                move_modules.append(mov_mod_tmp)
                if move_type=='Conex': #specific here because both conex share the same controller
                    self.conex_count+=1
                    mov_mod_tmp.settings.child('Move_Settings','axis_address').setValue(move_settings.child('Move_Settings','axis_address').value())
                    com_ports=mov_mod_tmp.settings.child('Move_Settings','com_port').opts['limits']
                    com=move_settings.child('Move_Settings','com_port').value() #get the value from the preset
                    if com in com_ports:
                        try:
                            mov_mod_tmp.settings.child('Move_Settings','com_port').setValue(com)
                            if self.conex_count<=1:
                                self.conex_controller=mov_mod_tmp.controller
                            else:
                                mov_mod_tmp.controller=self.conex_controller #it uses the previous conex controller as a controller

                        except: pass
                    else:
                        raise Exception('{:s} is not a valid COM port'.format(com))

                mov_mod_tmp.ui.IniStage_pb.click()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(2000)
                QtWidgets.QApplication.processEvents()

            except Exception as e:
                self.update_status(str(e),wait_time=self.wait_time,log_type='log')

        self.det_docks_settings=[]
        self.det_docks_viewer=[]
        detector_modules=[]
        det_types=[]
        for ind_det,det in enumerate(preset_params.child(('Detectors')).children()):
            try:
                det_name=det.child(('name')).value()
                det_settings=det.child(('params'))

                daq_type=det_settings.child('main_settings','DAQ_type').value()
                det_type=det_settings.child('main_settings','detector_type').value()
                det_types.append(det_type)


                self.det_docks_settings.append(Dock(det_name+" settings", size=(150,250)))
                self.det_docks_viewer.append(Dock(det_name+" viewer", size=(350,350)))
                if ind_det==0 or ind_det==3:
                    self.dockarea.addDock(self.det_docks_settings[-1], 'bottom')
                else:
                    self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.det_docks_viewer[-2])

                self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])

                det_mod_tmp=DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                    dock_viewer=self.det_docks_viewer[-1],title=det_name,DAQ_type=daq_type)
                det_mod_tmp.ui.Detector_type_combo.setCurrentText(det_type)
                det_mod_tmp.settings.child('main_settings','overshoot').show()
                det_mod_tmp.overshoot_signal[bool].connect(self.stop_moves)
                set_param_from_param(det_mod_tmp.settings,det_settings)

                detector_modules.append(det_mod_tmp) #if no error so far add it to the list

                det_mod_tmp.ui.IniDet_pb.click()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(2000)
                QtWidgets.QApplication.processEvents()
            except Exception as e:
                self.update_status(str(e),wait_time=self.wait_time,log_type='log')

        return move_modules,detector_modules

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

            self.splash_sc.show()
            self.splash_sc.raise_()
            QtWidgets.QApplication.processEvents()

            self.clear_move_det_controllers()
            if filename=='mock':
                move_modules,detector_modules= self.set_Mock_preset()
            elif filename=='canon':
                move_modules,detector_modules= self.set_canon_preset()
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
            items_det=[module.title for module in detector_modules]
            preset_items_det=[items_det[0]]

            items_move=[module.title for module in move_modules]
            preset_items_move=[items_move[0]]

            self.DAQscan_settings.child('Move_Detectors','Detectors').setValue(dict(all_items=items_det,selected=preset_items_det))
            self.DAQscan_settings.child('Move_Detectors','Moves').setValue(dict(all_items=items_move,selected=preset_items_move))
            self.DAQscan_settings.child('scan_options','plot_from').setLimits(preset_items_det)
            self.DAQscan_settings.child('scan_options','plot_from').setValue(preset_items_det[0])


            self.splash_sc.close()

        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def stop_moves(self):
        """
            Foreach module of the move module object liost, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.DAQ_Move.Stop_Motion
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
                    #positions are in 2Dimage coordinates, so this has to be scaled
                    posx_real=self.scan_parameters.axis_2D_1[int(posx)]
                    posy_real=self.scan_parameters.axis_2D_2[int(posy)]
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


            scan_path,current_filename,dataset_path=DAQ_utils.set_current_scan_path(base_path,base_name,update_h5)
            self.DAQscan_settings.child('saving_options','current_scan_path').setValue(str(scan_path))



            self.save_parameters.h5_file_path=dataset_path.joinpath(dataset_path.name+".h5")
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
                raw_data_group = self.save_parameters.h5_file.create_group("/", 'Raw_datas', 'Data from DAQ_Scan and detector modules')
                self.save_metadata(raw_data_group,'dataset_info')
                #selected_data_group = self.save_parameters.h5_file.create_group("/", 'Selected_datas', 'Data currently selected')
                #analysis_data_group= self.save_parameters.h5_file.create_group("/", 'Analysed_datas', 'Data analysed from raw data')



            raw_data_group=self.save_parameters.h5_file.root.Raw_datas
            if not(raw_data_group.__contains__(current_filename)):#check if Scan00i is a group
                self.save_parameters.current_group=self.save_parameters.h5_file.create_group(raw_data_group,current_filename) #if not it is created
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
            else:
                self.save_parameters.logger_array=self.save_parameters.h5_file.get_node(raw_data_group, name=logger)



            #set attributes to the current group, such as scan_type....
            self.scan_attributes.child('scan_info','scan_type').setValue(self.DAQscan_settings.child('scan_options','scan_type').value())
            self.scan_attributes.child('scan_info','scan_name').setValue(current_filename)
            self.set_metadata_about_current_scan()
            self.save_metadata(self.save_parameters.current_group,'scan_info')

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
        elif type_info=='preset':
            tree.setParameters(self.preset_params, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog);
        if type_info=='preset':
            buttonBox.addButton('Save',buttonBox.AcceptRole)
            buttonBox.accepted.connect(dialog.accept)
            buttonBox.addButton('Cancel',buttonBox.RejectRole)
            buttonBox.rejected.connect(dialog.reject)
        else:
            buttonBox.addButton('Apply',buttonBox.AcceptRole)
            buttonBox.accepted.connect(dialog.accept)
        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this {}'.format(type_info))
        res=dialog.exec()

        if res==dialog.Accepted and type_info=='preset':
            #save preset parameters in a xml file
            start,end=os.path.split(os.path.realpath(__file__))
            custom_tree.parameter_to_xml_file(self.preset_params,os.path.join(start,'preset_modes',self.preset_params.child(('filename')).value()))
            self.create_menu(self.menubar)

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
        # type='dataset_info' or 'scan_info'
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
                    self.scan_parameters.axis_1D=mylib.linspace_step(start,stop,step)
                elif self.DAQscan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                    steps=[]
                    for step in mylib.linspace_step(start,stop,step):
                        steps.extend([step,start])
                    self.scan_parameters.axis_1D=np.array(steps)

                self.scan_parameters.Nsteps=np.size(self.scan_parameters.axis_1D)
                self.ui.N_scan_steps_sb.setValue(self.scan_parameters.Nsteps)

                self.scan_moves=[[[move_module_name,pos]] for pos in self.scan_parameters.axis_1D]

                for ind,pos in enumerate(self.scan_moves):
                    self.scan_saves.append([edict(det_name=det_name,file_path=str(scan_path.joinpath(current_filename+"_"+det_name+'_{:03d}.dat'.format(ind))),indexes=OrderedDict(indx=ind)) for det_name in det_names_scan])


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
                    Nsteps,axis_1,axis_2,positions=DAQ_utils.set_scan_spiral(start_axis1,start_axis2,
                                                               Rmax,Rstep_2d)
                else:
                    stop_axis1=self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis1').value()
                    step_axis1=self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis1').value()
                    stop_axis2=self.DAQscan_settings.child('scan_options','scan2D_settings','stop_2d_axis2').value()
                    step_axis2=self.DAQscan_settings.child('scan_options','scan2D_settings','step_2d_axis2').value()

                    if self.DAQscan_settings.child('scan_options','scan2D_settings','scan2D_type').value()=='Linear':
                        Nsteps,axis_1,axis_2,positions=DAQ_utils.set_scan_linear(start_axis1,start_axis2,stop_axis1,stop_axis2,step_axis1,step_axis_2,back_and_force=False)
                    elif self.DAQscan_settings.child('scan_options','scan2D_settings','scan2D_type').value()=='back&forth':
                        Nsteps,axis_1,axis_2,positions=DAQ_utils.set_scan_linear(start_axis1,start_axis2,stop_axis1,stop_axis2,step_axis1,step_axis_2,back_and_force=True)


                self.scan_parameters.axis_2D_1=axis_1
                self.scan_parameters.axis_2D_2=axis_2
                self.scan_parameters.Nsteps=Nsteps
                self.ui.N_scan_steps_sb.setValue(self.scan_parameters.Nsteps)
                self.scan_moves=[[[move_module_name1,pos1],[move_module_name2,pos2]] for pos1,pos2 in positions]

                for ind,pos in enumerate(self.scan_moves):
                    ind1=list(axis_1).index(pos[0][1])
                    ind2=list(axis_2).index(pos[1][1])
                    self.scan_saves.append([edict(det_name=det_name,file_path=str(scan_path.joinpath(current_filename+"_"+det_name+'_{:03d}_{:03d}.dat'.format(ind1,ind2))),indexes=OrderedDict(indx=ind1,indy=ind2)) for det_name in det_names_scan])


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

            #self.DAQ_thread.PyMoDAQ=PyMoDAQ
            #PyMoDAQ.moveToThread(self.DAQ_thread)


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
            Not implemented.
        """
        try:
            #self.ui.scan3D_graph.setImage(self.scan_data_3D)
            pass
            #filename=str(self.scan_parameters.scan_path.joinpath(self.scan_parameters.current_filename+".dat"))
            #if "2D" in self.scan_parameters.scan_type:
            #    np.savetxt(filename,self.scan_data_2D_to_save,fmt='%.6e',delimiter='\t')
            #elif "2D" in self.ui.plot_type_cb.currentText():
            #    for ind_channel in range(self.scan_data_2D_to_save.shape[1]):
            #        np.savetxt(filename[:-4]+"_CH{:03d}.dat".format(ind_channel),self.scan_data_2D_to_save[:,ind_channel,:],fmt='%.6e',delimiter='\t')
            #else:
            #    np.savetxt(filename,self.scan_data_1D_to_save,fmt='%.6e',delimiter='\t')
            #image_path=str(self.scan_parameters.scan_path.joinpath(self.scan_parameters.current_filename+".png"))
            #self.dockarea.parent.grab().save(image_path);

            #scan_group=self.save_parameters.h5_file.create_group(self.save_parameters.current_group,"Scan_data")


            #if "2D" in self.scan_parameters.scan_type:
            #    self.save_parameters.h5_file.create_array(scan_group,"x_axis",self.scan_data_2D_to_save[:,0])
            #    self.save_parameters.h5_file.create_array(scan_group,"y_axis",self.scan_data_2D_to_save[:,1])
            #    self.save_parameters.h5_file.create_array(scan_group,"Data",self.scan_data_2D_to_save[:,2:])

            #elif "2D" in self.ui.plot_type_cb.currentText():
            #    self.save_parameters.h5_file.create_array(scan_group,"x_axis",self.scan_x_axis)
            #    self.save_parameters.h5_file.create_array(scan_group,"y_axis",self.scan_y_axis)
            #    self.save_parameters.h5_file.create_array(scan_group,"Data",self.scan_data_2D_to_save)
            #else:
            #    self.save_parameters.h5_file.create_array(scan_group,"x_axis",self.scan_data_1D_to_save[:,0])
            #    self.save_parameters.h5_file.create_array(scan_group,"Data",self.scan_data_1D_to_save[:,1:])



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
                    ind_pos_axis_1=mylib.find_index(self.scan_x_axis,pos_axis_1)[0][0]
                    ind_pos_axis_2=mylib.find_index(self.scan_y_axis,pos_axis_2)[0][0]
                    for ind_plot in range(min((3,len(datas)))):
                        self.scan_data_2D[ind_plot][ind_pos_axis_2,ind_pos_axis_1]=list(datas.values())[ind_plot]

                    self.ui.scan2D_graph.setImage(*self.scan_data_2D)
                else: # scan 1D with concatenation of vectors making a 2D image
                    if not(self.plot_2D_ini):
                        self.plot_2D_ini=True
                        Nx=self.scan_parameters.Nsteps
                        data=datas[list(datas.keys())[0]]
                        Ny=len(data[list(data.keys())[0]])

                        self.scan_x_axis=self.scan_parameters.axis_1D
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

                    pos_axis_1=self.scan_positions[0][1]
                    ind_pos_axis_1=mylib.find_index(self.scan_x_axis,pos_axis_1)[0][0]
                    for ind_plot,key in enumerate(datas.keys()):
                        self.scan_data_2D[ind_plot][:,ind_pos_axis_1]=datas[key]['data']

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
                if not mylib.odd_even(self.ind_scan):
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
            DAQ_Scan_Acquisition deal with the acquisition part of DAQ_Scan.

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
                    settings_str=b'<All_settings>'+settings_str
                    settings_str+=custom_tree.parameter_to_xml_string(self.detector_modules[ind_det].ui.viewer.roi_settings)+b'</All_settings>'

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
            DAQ_Move_main.DAQ_Move.Move_Abs
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
                                data0D_group=self.h5_file.create_group(self.h5_file_det_groups[ind_det],'Data0D')
                                data0D_group._v_attrs.type='data0D'
                                arrays=[]
                                for ind_channel,key in enumerate(self.det_done_datas[det_name]['data0D'].keys()):

                                    try:
                                        array=self.h5_file.create_carray(data0D_group,"CH{:03d}".format(ind_channel),obj=np.zeros(self.scan_shape), title=key,filters=self.filters)
                                        array.set_attr('scan_type',self.settings.child('scan_options','scan_type').value())
                                        array.set_attr('data_type','0D')
                                        array.set_attr('data_name',key)
                                        array.set_attr('shape',self.scan_shape)
                                        arrays.append(array)
                                    except: pass
                                self.h5_file_channels_group[det_name]['channels0D'].append(arrays)
                        #initialize 1D datas
                        if self.det_done_datas[det_name]['data1D'] is not None: #save Data1D if present
                            if len(self.det_done_datas[det_name]['data1D'])!=0: #save Data0D only if not empty (could happen)
                                data1D_group=self.h5_file.create_group(self.h5_file_det_groups[ind_det],'Data1D')
                                data1D_group._v_attrs.type='data1D'
                                for ind_channel,(key,channel) in enumerate(self.det_done_datas[det_name]['data1D'].items()):
                                    try:
                                        channel_group=self.h5_file.create_group(data1D_group,"CH{:03d}".format(ind_channel))
                                        channel_group._v_attrs.Channel_name=key
                                        if 'x_axis' in channel.keys():
                                            x_axis=channel['x_axis']
                                            xarray=self.h5_file.create_array(channel_group,"x_axis",obj=x_axis, title=key)
                                            xarray.set_attr('shape',xarray.shape)
                                        array=self.h5_file.create_carray(channel_group,'Data',obj=np.zeros(self.scan_shape+[len(channel['data'])]), title='data',filters=self.filters)
                                        array.set_attr('scan_type',self.settings.child('scan_options','scan_type').value())
                                        array.set_attr('data_type','1D')
                                        array.set_attr('data_name',key)
                                        array.set_attr('shape',self.scan_shape+[len(channel['data'])])
                                        self.h5_file_channels_group[det_name]['channels1D']["CH{:03d}".format(ind_channel)]=array
                                    except: pass

                        #initialize 2D datas

                        if self.det_done_datas[det_name]['data2D'] is not None and self.settings.child('saving_options','save_2D').value(): #save Data2D if present and of options is checked
                            if len(self.det_done_datas[det_name]['data2D'])!=0: #save Data0D only if not empty (could happen)
                                data2D_group=self.h5_file.create_group(self.h5_file_det_groups[ind_det],'Data2D')
                                data2D_group._v_attrs.type='data2D'
                                for ind_channel,(key,channel) in enumerate(self.det_done_datas[det_name]['data2D'].items()):
                                    try:
                                        channel_group=self.h5_file.create_group(data2D_group,"CH{:03d}".format(ind_channel))
                                        channel_group._v_attrs.Channel_name=key
                                        if 'x_axis' in channel.keys():
                                            x_axis=channel['x_axis']
                                            xarray=self.h5_file.create_array(channel_group,"x_axis",obj=x_axis, title=key)
                                            xarray.set_attr('shape',xarray.shape)
                                        if 'y_axis' in channel.keys():
                                            y_axis=channel['y_axis']
                                            yarray=self.h5_file.create_array(channel_group,"y_axis",obj=y_axis, title=key)
                                            yarray.set_attr('shape',yarray.shape)
                                        shape=self.scan_shape[:]
                                        for ind_index in channel['data'].shape:
                                            shape+=[ind_index]
                                        array=self.h5_file.create_carray(channel_group,'Data',obj=np.zeros(shape), title='data',filters=self.filters)
                                        array.set_attr('scan_type',self.settings.child('scan_options','scan_type').value())
                                        array.set_attr('data_type','2D')
                                        array.set_attr('data_name',key)
                                        array.set_attr('shape',shape)
                                        self.h5_file_channels_group[det_name]['channels2D']["CH{:03d}".format(ind_channel)]=array
                                    except: pass



                indexes=tuple(self.scan_saves[self.ind_scan][0]['indexes'].values())

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
            DAQ_Move_main.DAQ_Move.Move_Abs, move_done, det_done, check_array_in_h5, wait_for_move_done, wait_for_det_done, det_done
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

            if Naxis>1:#"means scan 2D"
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
    splash=QtGui.QPixmap('..//Documentation//splash.png')
    splash_sc=QtWidgets.QSplashScreen(splash,Qt.WindowStaysOnTopHint)
    splash_sc.show()
    splash_sc.raise_()
    QtWidgets.QApplication.processEvents()

    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    win.setWindowTitle('PyMoDAQ Scan')
    prog = DAQ_Scan(area,fname)
    QThread.sleep(4)
    win.show()
    splash_sc.finish(win)
    sys.exit(app.exec_())

