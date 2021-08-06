from PyQt5 import QtWidgets, QtCore
import sys
import os
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from pymodaq.daq_utils.managers import preset_manager_utils
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.exceptions import ScannerException
from pymodaq.daq_utils.scanner import Scanner, scan_types, adaptive_losses
from pathlib import Path
from pymodaq.daq_utils.parameter.pymodaq_ptypes import GroupParameterCustom as GroupParameter
from pyqtgraph.parametertree.Parameter import registerParameterType
from collections import OrderedDict

logger = utils.set_logger(utils.get_module_name(__file__))

batch_path = utils.get_set_batch_path()

params = [
    {'title': 'Actuators/Detectors Selection', 'name': 'modules', 'type': 'group', 'children': [
        {'title': 'detectors', 'name': 'detectors', 'type': 'itemselect'},
        {'title': 'Actuators', 'name': 'actuators', 'type': 'itemselect'},
    ]},
    ]


class BatchManager:

    params = [{'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'batch_default'},
              {'title': 'Scans', 'name': 'scans', 'type': 'group', 'children': []}]

    def __init__(self, msgbox=False, actuators=[], detectors=[], path=None):
        self.actuators = actuators
        self.detectors = detectors

        self.scans = OrderedDict([])

        self.tree = ParameterTree()
        self.tree.setMinimumWidth(400)
        self.tree.setMaximumWidth(500)
        self.tree.setMinimumHeight(500)

        if path is None:
            path = batch_path
        else:
            assert isinstance(path, Path)
        self.batch_path = path

        self.settings = None


        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Scan Batch Manager?")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            new_button = msgBox.addButton("New", QtWidgets.QMessageBox.ActionRole)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == new_button:
                self.set_new_batch()

            elif msgBox.clickedButton() == modify_button:
                self.set_file_batch()
            else:  # cancel
                pass


    def get_act_dets(self):
        acts = dict([])
        dets = dict([])
        for name in self.scans:
            acts[name] = self.settings.child('scans', name, 'modules',
                            'actuators').value()['selected']
            dets[name] = self.settings.child('scans', name, 'modules',
                                             'detectors').value()['selected']
        return acts, dets

    def set_file_batch(self, filename=None, show=True):
        """

        """

        if filename is None or filename == False:
            filename = gutils.select_file(start_path=self.batch_path, save=False, ext='xml')
            if filename == '':
                return

        status = False
        settings_tmp = Parameter.create(title='Batch', name='settings_tmp',
                                        type='group', children=ioxml.XML_file_to_parameter(str(filename)))

        children = settings_tmp.child('scans').children()
        self.settings = Parameter.create(title='Batch', name='settings', type='group', children=self.params)
        actuators = children[0].child('modules', 'actuators').value()['all_items']
        if actuators != self.actuators:
            gutils.show_message('The loaded actuators from the batch file do not corresponds to the'
                                ' dashboard actuators')
            return
        else:
            self.actuators = actuators

        detectors = children[0].child('modules', 'detectors').value()['all_items']
        if detectors != self.detectors:
            gutils.show_message('The loaded detectors from the batch file do not corresponds to the'
                                ' dashboard detectors')
            return
        else:
            self.detectors = detectors

        for child in children:
            self.add_scan(name=child.name(), title=child.opts['title'])
            self.settings.child('scans', child.name()).restoreState(child.saveState())

        if show:
            status = self.show_tree()
        else:
            self.tree.setParameters(self.settings, showTop=False)
        return status

    def set_scans(self):
        infos = []
        acts, dets = self.get_act_dets()
        for scan in self.scans:
            infos.append(f'{scan}: {acts[scan]} / {dets[scan]}')
            infos.append(f'{scan}: {self.scans[scan].set_scan()}')
        return infos

    def set_new_batch(self):
        self.settings = Parameter.create(title='Batch', name='settings', type='group', children=self.params)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        status = self.show_tree()
        return status

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

                pass

            elif change == 'parent':
                pass

    def show_tree(self):
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        add_scan = QtWidgets.QPushButton('Add Scan')
        add_scan.clicked.connect(self.add_scan)
        self.tree.setParameters(self.settings, showTop=False)
        vlayout.addWidget(add_scan)
        vlayout.addWidget(self.tree)
        dialog.setLayout(vlayout)

        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)
        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this Scan batch')
        res = dialog.exec()

        if res == dialog.Accepted:
            # save managers parameters in a xml file
            # start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            # start = os.path.join("..",'daq_scan')
            ioxml.parameter_to_xml_file(
                self.settings, os.path.join(self.batch_path, self.settings.child('filename').value()))

        return res == dialog.Accepted

    def add_scan(self, name=None, title=None):
        if name is None or name is False:
            name_prefix = 'scan'
            child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.settings.child('scans').children()]
            if child_indexes == []:
                newindex = 0
            else:
                newindex = max(child_indexes) + 1
            name = f'{name_prefix}{newindex:02.0f}'
            title = f'Scan {newindex:02.0f}'

        child = {'title': title, 'name': name, 'type': 'group', 'removable': True, 'children': params}

        self.scans[name] = Scanner(actuators=[self.actuators[0]], adaptive_losses=adaptive_losses)
        self.settings.child('scans').addChild(child)
        self.settings.child('scans', name, 'modules',
                            'actuators').setValue(dict(all_items=self.actuators,
                                                       selected=[self.actuators[0]]))
        self.settings.child('scans', name, 'modules',
                            'detectors').setValue(dict(all_items=self.detectors,
                                                       selected=[self.detectors[0]]))

        self.settings.child('scans', name).addChild(
            self.scans[name].settings)


class BatchScanner(QtCore.QObject):
    def __init__(self, area, actuators=[], detectors=[]):
        super().__init__()
        self.dockarea = area
        self.batchmanager = BatchManager(actuators=actuators, detectors=detectors, path=batch_path)

    @property
    def scans(self):
        return self.batchmanager.scans

    @property
    def scans_names(self):
        return list(self.batchmanager.scans.keys())

    def get_act_dets(self):
        return self.batchmanager.get_act_dets()

    def setupUI(self):
        # %% create scan dock and make it a floating window
        self.batch_dock = gutils.Dock("BatchScanner", size=(1, 1), autoOrientation=False)  # give this dock the minimum possible size
        self.dockarea.addDock(self.batch_dock, 'left')
        self.batch_dock.float()

        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(QtWidgets.QVBoxLayout())


        widget_infos = QtWidgets.QWidget()
        self.widget_infos_list = QtWidgets.QListWidget()
        widget_infos.setLayout(QtWidgets.QHBoxLayout())
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        widget_infos.layout().addWidget(splitter)
        splitter.addWidget(self.batchmanager.tree)
        splitter.addWidget(self.widget_infos_list)
        self.batch_dock.addWidget(self.widget)
        self.widget.layout().addWidget(widget_infos)
        #self.create_menu()

    def create_menu(self, menubar=None):
        """
        """
        # %% create Settings menu
        if menubar is None:
            menubar = QtWidgets.QMenuBar()
            self.widget.layout().insertWidget(0, menubar)

        self.batch_menu = menubar.addMenu('Batch Configs')
        action_new = self.batch_menu.addAction('New Batch')
        action_new.triggered.connect(self.batchmanager.set_new_batch)
        action_modify = self.batch_menu.addAction('Modify Batch')
        action_modify.triggered.connect(self.batchmanager.set_file_batch)
        self.batch_menu.addSeparator()
        self.load_batch = self.batch_menu.addMenu('Load Batchs')

        slots = dict([])
        for ind_file, file in enumerate(batch_path.iterdir()):
            if file.suffix == '.xml':
                filestem = file.stem
                slots[filestem] = self.load_batch.addAction(filestem)
                slots[filestem].triggered.connect(
                    self.create_menu_slot(batch_path.joinpath(file)))


    def load_file(self, filepath=None):
        if filepath is None:
            path = gutils.select_file(start_path=batch_path, save=False, ext='xml')
            if path != '':
                filepath = path
            else:
                return
        self.batchmanager.set_file_batch(str(filepath), show=False)


        infos = self.batchmanager.set_scans()
        self.widget_infos_list.addItems(infos)

    def create_menu_slot(self, filename):
        return lambda: self.load_file(filename)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)

    # prog = BatchManager(msgbox=False, actuators=['Xaxis', 'Yaxis'], detectors=['Det0D', 'Det1D'])
    # prog.set_file_batch('C:\\Users\\weber\\pymodaq_local\\batch_configs\\batch_default.xml', show=False)
    # prog.set_scans()

    main = BatchScanner(area, actuators=['Xaxis', 'Yaxis', 'theta axis'],
                        detectors=['Det 2D', 'Det 0D', 'Det 1D'])
    main.setupUI()
    main.create_menu()
    win.show()
    sys.exit(app.exec_())

