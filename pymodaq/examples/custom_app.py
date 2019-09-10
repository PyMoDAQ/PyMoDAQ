import sys
import tables
from collections import OrderedDict
import datetime
import os
import numpy as np

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QLocale, QDateTime, QRectF, QDate, QThread

from pyqtgraph.dockarea import Dock
from pymodaq.daq_utils.daq_utils import DockArea
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_utils.daq_utils import select_file


from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq.daq_move.daq_move_main import DAQ_Move
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.h5browser import browse_data
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.h5browser import H5Browser


class CustomApp(QtWidgets.QWidget, QObject):
    #custom signal that will be fired sometimes. Could be connected to an external object method or an internal method
    log_signal = pyqtSignal(str)

    #list of dicts enabling the settings tree on the user interface
    params = [{'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
                {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
                {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QDate.currentDate()},
                {'title': 'Do something:', 'name': 'do_something', 'type': 'bool', 'value': False},
                {'title': 'Something done:', 'name': 'something_done', 'type': 'led', 'value': False, 'readonly': True},
                {'title': 'Infos:', 'name': 'info', 'type': 'text', 'value': ""},
                ]},
              {'title': 'Other settings:', 'name': 'other_settings', 'type': 'group', 'children': [
                  {'title': 'List of stuffs:', 'name': 'list_stuff', 'type': 'list', 'value': 'first',
                   'values': ['first', 'second', 'third'], 'tip': 'choose a stuff from the list'},
                  {'title': 'List of integers:', 'name': 'list_int', 'type': 'list', 'value': 0,
                   'values': [0, 256, 512], 'tip': 'choose a stuff from this int list'},
                  {'title': 'one integer:', 'name': 'an_integer', 'type': 'int', 'value': 500,},
                  {'title': 'one float:', 'name': 'a_float', 'type': 'float', 'value': 2.7,},
                  ]},
              ]

    def __init__(self, parent):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(CustomApp, self).__init__()
        if not isinstance(parent, DockArea):
            raise Exception('no valid parent container, expected a DockArea')
        self.dockarea = parent
        self.mainwindow = parent.parent()

        #init the object parameters
        self.one_parameter = None
        self.another_parameter = None
        self.detector = None
        self.save_file_pathname = None
        self.raw_data = []


        #init the user interface
        self.set_GUI()

    def set_GUI(self):
        ###########################################
        ###########################################
        #init the docks containing the main widgets

        #############################################
        #this one for the custom application settings
        dock_settings = Dock('Settings', size=(350, 350))
        self.dockarea.addDock(dock_settings, 'left')
        # create main parameter tree
        self.settings_tree = ParameterTree()
        dock_settings.addWidget(self.settings_tree, 10)
        self.settings_tree.setMinimumWidth(300)
        #create a Parameter object containing the settings
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        #load the tree with this parameter object
        self.settings_tree.setParameters(self.settings, showTop=False)
        #any change to the tree on the user interface will call the parameter_tree_changed method where all actions will be applied
        self.settings.sigTreeStateChanged.connect(
            self.parameter_tree_changed)

        ################################################################
        #create a logger dock where to store info senf from the programm
        self.dock_logger = Dock("Logger")
        self.logger_list = QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)
        self.dock_logger.addWidget(self.logger_list)
        self.dockarea.addDock(self.dock_logger, 'bottom', dock_settings)
        # dock_logger.setVisible(False)
        #connect together this custom signal with the add_log method
        self.log_signal[str].connect(self.add_log)

        #######################################################################################################################
        #create a dock containing a viewer object, could be 0D, 1D or 2D depending what kind of data one want to plot here a 0D
        dock_Viewer0D = Dock('Viewer dock', size=(350, 350))
        self.dockarea.addDock(dock_Viewer0D, 'right', self.dock_logger)
        target_widget = QtWidgets.QWidget()
        self.target_viewer = Viewer0D(target_widget)
        dock_Viewer0D.addWidget(target_widget)

        ###################################################################################
        #create 2 docks to display the DAQ_Viewer (one for its settings, one for its viewer)
        dock_detector_settings = Dock("Detector Settings", size=(350, 350))
        self.dockarea.addDock(dock_detector_settings, 'right', dock_settings)
        dock_detector = Dock("Detector Viewer", size=(350, 350))
        self.dockarea.addDock(dock_detector, 'right', dock_detector_settings)
        #init one daq_viewer object named detector
        self.detector = DAQ_Viewer(self.dockarea, dock_settings=dock_detector_settings,
                                                 dock_viewer=dock_detector, title="A detector", DAQ_type='DAQ0D')
        #set its type to 'Mock'
        control_type = 'Mock'
        self.detector.ui.Detector_type_combo.setCurrentText(control_type)
        #init the detector and wait 1000ms for the completion
        self.detector.ui.IniDet_pb.click()
        self.detector.settings.child('main_settings', 'wait_time').setValue(100)
        QtWidgets.QApplication.processEvents()
        QThread.msleep(1000)
        self.detector.grab_done_signal.connect(self.data_done)

        #############################
        #create a dock for a DAQ_Move
        dock_move = Dock("Move module", size=(350, 350))
        self.dockarea.addDock(dock_move, 'right', self.dock_logger)
        move_widget = QtWidgets.QWidget()
        self.move = DAQ_Move(move_widget)
        dock_move.addWidget(move_widget)
        self.move.ui.IniStage_pb.click()
        QtWidgets.QApplication.processEvents()
        QThread.msleep(1000)





        ############################################
        # creating a menubar
        self.menubar = self.mainwindow.menuBar()
        self.create_menu(self.menubar)

        #creating a toolbar
        self.toolbar = QtWidgets.QToolBar()
        self.create_toolbar()
        self.mainwindow.addToolBar(self.toolbar)

    @pyqtSlot(OrderedDict)
    def data_done(self,data):
        print(data)


    @pyqtSlot(QRectF)
    def update_weighted_settings(self, rect):
        self.settings.child('weighting_settings', 'x0').setValue(int(rect.x()))
        self.settings.child('weighting_settings', 'y0').setValue(int(rect.y()))
        self.settings.child('weighting_settings', 'width').setValue(max([1, int(rect.width())]))
        self.settings.child('weighting_settings', 'height').setValue(max([1, int(rect.height())]))

    def parameter_tree_changed(self, param, changes):
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'do_something':
                    if param.value():
                        self.log_signal.emit('Do something')
                        self.detector.grab_done_signal.connect(self.show_data)
                        self.settings.child('main_settings', 'something_done').setValue(True)
                    else:
                        self.log_signal.emit('Stop Doing something')
                        self.detector.grab_done_signal.disconnect()
                        self.settings.child('main_settings', 'something_done').setValue(False)


            elif change == 'parent':
                pass

    @pyqtSlot(OrderedDict)
    def show_data(self,data):
        """
        do stuff with data from the detector if its grab_done_signal has been connected
        Parameters
        ----------
        data: (OrderedDict) #OrderedDict(name=self.title,x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
        """
        data0D = [[data['data0D'][key]] for key in data['data0D']]
        self.raw_data.append(data0D)
        self.target_viewer.show_data(data0D)

    def create_menu(self, menubar):
        """
        """
        menubar.clear()

        #%% create file menu
        file_menu=menubar.addMenu('File')
        load_action=file_menu.addAction('Load file')
        load_action.triggered.connect(self.load_file)
        save_action=file_menu.addAction('Save file')
        save_action.triggered.connect(self.save_data)

        file_menu.addSeparator()
        quit_action=file_menu.addAction('Quit')
        quit_action.triggered.connect(self.quit_function)

        settings_menu=menubar.addMenu('Settings')
        docked_menu=settings_menu.addMenu('Docked windows')
        action_load=docked_menu.addAction('Load Layout')
        action_save=docked_menu.addAction('Save Layout')


    def load_file(self):
        #init the data browser module
        widg = QtWidgets.QWidget()
        self.data_browser = H5Browser(widg)
        widg.show()

    def quit_function(self):
        #close all stuff that need to be
        self.detector.quit_fun()
        QtWidgets.QApplication.processEvents()
        self.mainwindow.close()

    def create_toolbar(self):
        iconquit = QtGui.QIcon()
        iconquit.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/close2.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.quit_action = QtWidgets.QAction(iconquit, "Quit program", None)
        self.toolbar.addAction(self.quit_action)
        self.quit_action.triggered.connect(self.quit_function)


        icon_detector = QtGui.QIcon()
        icon_detector.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/camera.png"), QtGui.QIcon.Normal,
                                  QtGui.QIcon.Off)
        self.detector_action = QtWidgets.QAction(icon_detector, "Grab from camera", None)
        self.detector_action.setCheckable(True)
        self.toolbar.addAction(self.detector_action)
        self.detector_action.triggered.connect(lambda: self.run_detector())

        iconload = QtGui.QIcon()
        iconload.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Open.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.loadaction = QtWidgets.QAction(iconload, "Load target file (.h5, .png, .jpg) or data from camera", None)
        self.toolbar.addAction(self.loadaction)
        self.loadaction.triggered.connect(self.load_file)


        iconsave = QtGui.QIcon()
        iconsave.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/SaveAs.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.saveaction = QtWidgets.QAction(iconsave, "Save current data", None)
        self.toolbar.addAction(self.saveaction)
        self.saveaction.triggered.connect(self.save_data)

    def run_detector(self):
        self.detector.ui.grab_pb.click()


    def save_data(self):
        try:
            fname = utils.select_file(start_path=self.save_file_pathname, save=True, ext='h5')

            if not (not (fname)):
                with tables.open_file(str(fname), mode='w', title='an example h5 file name') as h5file:
                    data_to_save = np.squeeze(np.array(self.raw_data))
                    #save metadata
                    h5file.root._v_attrs['settings'] = custom_tree.parameter_to_xml_string(self.settings)
                    for ind in range(data_to_save.shape[1]):
                        arr = h5file.create_array('/', 'data_{:d}'.format(ind), data_to_save[:,ind])
                        arr._v_attrs['shape'] = data_to_save.shape[0]
                        arr._v_attrs['type'] = 'data1D'

                    arr = h5file.create_array('/', 'data_2D', data_to_save)
                    arr._v_attrs['shape'] = data_to_save.shape
                    arr._v_attrs['type'] = 'data2D'



                    logger = "logging"
                    text_atom = tables.atom.ObjectAtom()
                    logger_array = h5file.create_vlarray('/', logger, atom=text_atom)
                    logger_array._v_attrs['type'] = 'list'
                    for ind_log in range(self.logger_list.count()):
                        txt = self.logger_list.item(ind_log).text()
                        logger_array.append(txt)

                st = 'file {:s} has been saved'.format(fname)
                self.add_log(st)
                self.settings.child('min_settings', 'info').setValue(st)


        except Exception as e:
            self.add_log(str(e))


    @pyqtSlot(str)
    def add_log(self, txt):
        """
            Add a log to the logger list from the given text log and the current time

            ================ ========= ======================
            **Parameters**   **Type**   **Description**

             *txt*             string    the log to be added
            ================ ========= ======================

        """
        now = datetime.datetime.now()
        new_item = QtWidgets.QListWidgetItem(str(now) + ": " + txt)
        self.logger_list.addItem(new_item)
        ##to do
        ##self.save_parameters.logger_array.append(str(now)+": "+txt)

    @pyqtSlot(str)
    def emit_log(self, txt):
        """
            Emit a log-signal from the given log index

            =============== ======== =======================
            **Parameters**  **Type** **Description**

             *txt*           string   the log to be emitted
            =============== ======== =======================

        """
        self.log_signal.emit(txt)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('pymodaq example')
    prog = CustomApp(area)
    win.show()
    sys.exit(app.exec_())