import sys
from collections import OrderedDict
import datetime
import numpy as np

from PyQt5 import  QtWidgets
from PyQt5.QtCore import pyqtSlot, QLocale, QDate, QThread

from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D

from pymodaq.daq_utils.h5modules import H5Browser, H5Saver

config = utils.load_config()
logger = utils.set_logger(utils.get_module_name(__file__))


class CustomAppExample(gutils.CustomApp):

    # list of dicts enabling the settings tree on the user interface
    params = [
        {'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
            {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
             'value': config['data_saving']['h5file']['save_path']},
            {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
            {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QDate.currentDate()},
            {'title': 'Do something, such as showing data:', 'name': 'do_something', 'type': 'bool', 'value': False},
            {'title': 'Something done:', 'name': 'something_done', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Infos:', 'name': 'info', 'type': 'text', 'value': ""},
            {'title': 'push:', 'name': 'push', 'type': 'bool_push', 'value': False}
        ]},
        {'title': 'Other settings:', 'name': 'other_settings', 'type': 'group', 'children': [
            {'title': 'List of stuffs:', 'name': 'list_stuff', 'type': 'list', 'value': 'first',
                'values': ['first', 'second', 'third'], 'tip': 'choose a stuff from the list'},
            {'title': 'List of integers:', 'name': 'list_int', 'type': 'list', 'value': 0,
                'values': [0, 256, 512], 'tip': 'choose a stuff from this int list'},
            {'title': 'one integer:', 'name': 'an_integer', 'type': 'int', 'value': 500, },
            {'title': 'one float:', 'name': 'a_float', 'type': 'float', 'value': 2.7, },
        ]},
    ]

    def __init__(self, dockarea):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super().__init__(dockarea)

        # init the object parameters
        self.raw_data = []

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        logger.debug('setting actions')
        self.addaction('quit', 'Quit', 'close2', "Quit program", toolbar=self.toolbar)
        self.addaction('grab', 'Grab', 'camera', "Grab from camera", checkable=True, toolbar=self.toolbar)
        self.addaction('load', 'Load', 'Open', "Load target file (.h5, .png, .jpg) or data from camera",
                       checkable=False, toolbar=self.toolbar)
        self.addaction('save', 'Save', 'SaveAs', "Save current data", checkable=False, toolbar=self.toolbar)
        logger.debug('actions set')

    def setup_docks(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('setting docks')
        self.dock_settings = gutils.Dock('Settings', size=(350, 350))
        self.dockarea.addDock(self.dock_settings, 'left')
        self.dock_settings.addWidget(self.settings_tree, 10)

        self.dock_logger = gutils.Dock("Logger")
        self.logger_list = QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)
        self.dock_logger.addWidget(self.logger_list)
        self.dockarea.addDock(self.dock_logger, 'bottom', self.dock_settings)

        # create a dock containing a viewer object, could be 0D, 1D or 2D depending what kind of data one want to plot here a 0D
        dock_Viewer0D = gutils.Dock('Viewer dock', size=(350, 350))
        self.dockarea.addDock(dock_Viewer0D, 'right', self.dock_logger)
        target_widget = QtWidgets.QWidget()
        self.target_viewer = Viewer0D(target_widget)
        dock_Viewer0D.addWidget(target_widget)

        # create 2 docks to display the DAQ_Viewer (one for its settings, one for its viewer)
        dock_detector_settings = gutils.Dock("Detector Settings", size=(350, 350))
        self.dockarea.addDock(dock_detector_settings, 'right', self.dock_settings)
        dock_detector = gutils.Dock("Detector Viewer", size=(350, 350))
        self.dockarea.addDock(dock_detector, 'right', dock_detector_settings)
        # init one daq_viewer object named detector

        self.detector = DAQ_Viewer(self.dockarea, dock_settings=dock_detector_settings,
                               dock_viewer=dock_detector, title="A detector", DAQ_type='DAQ0D')
        # set its type to 'Mock'
        self.detector.daq_type = 'Mock'
        # init the detector and wait 1000ms for the completion
        self.detector.init_det()
        self.detector.settings.child('main_settings', 'wait_time').setValue(100)
        QtWidgets.QApplication.processEvents()
        QThread.msleep(1000)

        logger.debug('docks are set')

    def connect_things(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('connecting things')
        self.log_signal[str].connect(self.add_log)  # connect together this custom signal with the add_log method

        self.detector.grab_done_signal.connect(self.data_done)

        self.actions['quit'].connect(self.quit_function)
        self.actions['load'].connect(self.load_file)
        self.actions['save'].connect(self.save_data)

        self.actions['grab'].connect(self.detector.grab)

        logger.debug('connecting done')

    def setup_menu(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('settings menu')
        file_menu = self.mainwindow.menuBar().addMenu('File')
        self.affect_to('quit', file_menu)
        file_menu.addSeparator()
        self.affect_to('load', file_menu)
        self.affect_to('save', file_menu)

        self.affect_to('quit', file_menu)

        logger.debug('menu set')

    def value_changed(self, param):
        logger.debug(f'calling value_changed with param {param.name()}')
        if param.name() == 'do_something':
            if param.value():
                self.log_signal.emit('Do something')
                self.detector.grab_done_signal.connect(self.show_data)
                self.raw_data = []  # init the data to be finally saved
                self.settings.child('main_settings', 'something_done').setValue(True)
            else:
                self.log_signal.emit('Stop Doing something')
                self.detector.grab_done_signal.disconnect()
                self.settings.child('main_settings', 'something_done').setValue(False)

        logger.debug(f'Value change applied')

    @pyqtSlot(OrderedDict)
    def data_done(self, data):
        # print(data)
        pass

    @pyqtSlot(OrderedDict)
    def show_data(self, data):
        """
        do stuff with data from the detector if its grab_done_signal has been connected
        Parameters
        ----------
        data: (OrderedDict) #OrderedDict(name=self.title,x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
        """
        data0D = [[data['data0D'][key]['data']] for key in data['data0D']]
        if self.raw_data == []:
            self.raw_data = data0D
        else:
            if len(self.raw_data) != len(data0D):
                self.raw_data = data0D
            else:
                for ind in range(len(data0D)):
                    self.raw_data[ind].append(data0D[ind][0])

        self.target_viewer.show_data(data0D)

    def load_file(self):
        # init the data browser module
        widg = QtWidgets.QWidget()
        self.data_browser = H5Browser(widg)
        widg.show()

    def quit_function(self):
        # close all stuff that need to be
        self.detector.quit_fun()
        QtWidgets.QApplication.processEvents()
        self.mainwindow.close()

    def run_detector(self):
        self.detector.ui.grab_pb.click()

    def save_data(self):
        try:
            path = gutils.select_file(start_path=self.settings.child('main_settings', 'base_path').value(), save=True,
                                      ext='h5')
            if path is not None:
                # init the file object with an addhoc name given by the user
                h5saver = H5Saver(save_type='custom')
                h5saver.init_file(update_h5=True, addhoc_file_path=path)

                # save all metadata
                settings_str = ioxml.parameter_to_xml_string(self.settings)
                settings_str = b'<All_settings>' + settings_str
                settings_str += ioxml.parameter_to_xml_string(self.detector.settings) + ioxml.parameter_to_xml_string(
                    h5saver.settings) + b'</All_settings>'

                data_group = h5saver.add_data_group(h5saver.raw_group, group_data_type='data0D',
                                                    title='data from custom app',
                                                    settings_as_xml=settings_str)

                for dat in self.raw_data:
                    channel = h5saver.add_CH_group(data_group)
                    data_dict = dict(data=np.array(dat),
                                     x_axis=dict(data=np.linspace(0, len(dat) - 1, len(dat)), units='pxl'))
                    h5saver.add_data(channel, data_dict=data_dict, scan_type='')

                st = 'file {:s} has been saved'.format(str(path))
                self.add_log(st)
                self.settings.child('main_settings', 'info').setValue(st)

                h5saver.close_file()

        except Exception as e:
            logger.exception(str(e))

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
        logger.info(txt)


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = QtWidgets.QMainWindow()
    dockarea = gutils.DockArea()
    mainwindow.setCentralWidget(dockarea)

    prog = CustomAppExample(dockarea)

    mainwindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
