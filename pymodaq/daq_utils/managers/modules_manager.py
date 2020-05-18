from collections import OrderedDict
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QEvent, QBuffer, QIODevice, QLocale, Qt, QVariant, QModelIndex
from PyQt5 import QtGui, QtWidgets, QtCore
import time

from pymodaq.daq_utils import daq_utils as utils

from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter

logger = utils.set_logger(utils.get_module_name(__file__))


class ModulesManager(QObject):

    detectors_changed = pyqtSignal(list)
    actuators_changed = pyqtSignal(list)
    det_done_signal = pyqtSignal(OrderedDict)
    move_done_signal = pyqtSignal(OrderedDict)
    timeout_signal = pyqtSignal(bool)

    params = [{'title': 'Actuators/Detectors Selection', 'name': 'modules', 'type': 'group', 'children': [
                    {'title': 'detectors', 'name': 'detectors', 'type': 'itemselect'},
                    {'title': 'Actuators', 'name': 'actuators', 'type': 'itemselect'},
                ]},

              {'title': "Moves done?", 'name': 'move_done', 'type': 'led', 'value': False},
              {'title': "Detections done?", 'name': 'det_done', 'type': 'led', 'value': False},

              {'title': 'Data dimensions', 'name': 'data_dimensions', 'type': 'group', 'children': [
                  {'title': "Probe detector's data", 'name': 'probe_data', 'type': 'action'},
                  {'title': 'Data0D list:', 'name': 'det_data_list0D', 'type': 'itemselect'},
                  {'title': 'Data1D list:', 'name': 'det_data_list1D', 'type': 'itemselect'},
                  {'title': 'Data2D list:', 'name': 'det_data_list2D', 'type': 'itemselect'},
                  {'title': 'DataND list:', 'name': 'det_data_listND', 'type': 'itemselect'},
              ]}
             ]

    def __init__(self, detectors=[], actuators=[], selected_detectors=[], selected_actuators=[], timeout=10000):
        super().__init__()

        for mod in selected_actuators:
            assert mod in actuators
        for mod in selected_detectors:
            assert mod in detectors

        self.timeout = timeout  #in ms

        self.det_done_datas = OrderedDict()
        self.det_done_flag = False

        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(300)
        self.settings_tree.setParameters(self.settings, showTop=False)
        
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)
        
        self.settings.child('data_dimensions', 'probe_data').sigActivated.connect(self.get_det_data_list)

        self._detectors = []
        self._actuators = []

        self.grab_done_signals = []
        self.det_commands_signal = []

        self.set_actuators(actuators, selected_actuators)
        self.set_detectors(detectors, selected_detectors)

    @classmethod
    def get_names(cls, modules):
        return [mod.title for mod in modules]

    def get_mods_from_names(self, names, mod='det'):
        mods = []
        for name in names:
            d = self.get_mod_from_name(name, mod)
            if d is not None:
                mods.append(d)
        return mods

    def get_mod_from_name(self, name, mod='det'):
        if mod == 'det':
            modules = self._detectors
        else:
            modules = self._actuators

        if name in self.get_names(modules):
            return modules[self.get_names(modules).index(name)]
        else:
            logger.warning(f'No detector with this name: {name}')
            return None

    def set_actuators(self, actuators, selected_actuators):
        self._actuators = actuators
        self.settings.child('modules', 'actuators').setValue(dict(all_items=self.get_names(actuators),
                                                                  selected=self.get_names(selected_actuators)))

    def set_detectors(self, detectors, selected_detectors):
        self._detectors = detectors
        self.settings.child('modules', 'detectors').setValue(dict(all_items=self.get_names(detectors),
                                                                  selected=self.get_names(selected_detectors)))

    @property
    def detectors(self):
        return self.get_mods_from_names(self.selected_detectors_name)

    @property
    def actuators(self):
        return self.get_mods_from_names(self.selected_actuators_name, mod='act')

    @property
    def detectors_name(self):
        return self.settings.child('modules', 'detectors').value()['all_items']

    @property
    def selected_detectors_name(self):
        return self.settings.child('modules', 'detectors').value()['selected']

    @property
    def actuators_name(self):
        return self.settings.child('modules', 'actuators').value()['all_items']

    @property
    def selected_actuators_name(self):
        return self.settings.child('modules', 'actuators').value()['selected']

    def parameter_tree_changed(self, param, changes):
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
            path = self.settings.childPath(param)
            if change == 'childAdded':
                pass

            elif change == 'value':

                if param.name() == 'detectors':
                    self.detectors_changed.emit(data['selected'])

                elif param.name() == 'actuators':
                    self.actuators_changed.emit(data['selected'])

            elif change == 'parent':
                pass

    def get_det_data_list(self):
        self.grab_done_signals = [mod.grab_done_signal for mod in self.detectors]
        self.det_commands_signal = [mod.command_detector for mod in self.detectors]

        for sig in self.grab_done_signals:
            sig.connect(self.det_done)

        datas = self.grab_datas()

        data_list0D = []
        data_list1D = []
        data_list2D = []
        data_listND = []

        for k in datas.keys():
            if 'data0D' in datas[k].keys():
                data_list0D.extend([f'{k}/{name}' for name in datas[k]['data0D'].keys()])
            if 'data1D' in datas[k].keys():
                data_list1D.extend([f'{k}/{name}' for name in datas[k]['data1D'].keys()])
            if 'data2D' in datas[k].keys():
                data_list2D.extend([f'{k}/{name}' for name in datas[k]['data2D'].keys()])
            if 'dataND' in datas[k].keys():
                data_listND.extend([f'{k}/{name}' for name in datas[k]['dataND'].keys()])

        self.settings.child('data_dimensions', 'det_data_list0D').setValue(
            dict(all_items=data_list0D, selected=[]))
        self.settings.child('data_dimensions', 'det_data_list1D').setValue(
            dict(all_items=data_list1D, selected=[]))
        self.settings.child('data_dimensions', 'det_data_list2D').setValue(
            dict(all_items=data_list2D, selected=[]))
        self.settings.child('data_dimensions', 'det_data_listND').setValue(
            dict(all_items=data_listND, selected=[]))

        try:
            for sig in self.grab_done_signals:
                sig.disconnect(self.det_done)
        except Exception as e:
            logger.error(str(e))

    def grab_datas(self):
        self.det_done_datas = OrderedDict()
        self.det_done_flag = False
        self.settings.child(('det_done')).setValue(self.det_done_flag)
        tzero = time.perf_counter()

        for ind_det in range(len(self.det_commands_signal)):
            self.det_commands_signal[ind_det].emit(utils.ThreadCommand("single", [1]))

        while not self.det_done_flag:
            #wait for grab done signals to end

            QtWidgets.QApplication.processEvents()
            if time.perf_counter()-tzero > self.timeout:
                self.timeout_signal.emit(True)
                logger.error('Timeout Fired during waiting for data to be acquired')
                break

        self.det_done_signal.emit(self.det_done_datas)
        return self.det_done_datas




    @pyqtSlot(OrderedDict)  # edict(name=self.title,data0D=None,data1D=None,data2D=None)
    def det_done(self, data):
        try:
            if data['name'] not in list(self.det_done_datas.keys()):
                self.det_done_datas[data['name']] = data
            if len(self.det_done_datas.items()) == len(self.detectors):
                self.det_done_flag = True
                self.settings.child(('det_done')).setValue(self.det_done_flag)
        except Exception as e:
            logger.exception(str(e))

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    from PyQt5.QtCore import QThread
    from pymodaq.daq_utils.gui_utils import DockArea
    from pyqtgraph.dockarea import Dock
    from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer


    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('pymodaq main')

    prog = DAQ_Viewer(area, title="Testing2D", DAQ_type='DAQ2D')
    prog2 = DAQ_Viewer(area, title="Testing1D", DAQ_type='DAQ1D')
    prog3 = DAQ_Viewer(area, title="Testing0D", DAQ_type='DAQ0D')

    QThread.msleep(1000)
    prog.ui.IniDet_pb.click()
    prog2.ui.IniDet_pb.click()
    prog3.ui.IniDet_pb.click()

    QtWidgets.QApplication.processEvents()
    win.show()

    manager = ModulesManager(actuators=[], detectors=[prog, prog2, prog3], selected_detectors=[prog2])
    manager.settings_tree.show()

    sys.exit(app.exec_())