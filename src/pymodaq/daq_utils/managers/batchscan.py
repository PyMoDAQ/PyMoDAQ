from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot, pyqtSignal
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


class BatchScan:

    params = [{'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'batch_default'},
              {'title': 'Scans', 'name': 'scans', 'type': 'group', 'children': []}]

    def __init__(self, area=None, msgbox=False, actuators=[], detectors=[], path=None):
        self.dockarea = area
        self.actuators = actuators
        self.detectors = detectors
        self.selected_actuators = []
        self.selected_detectors = []
        self.scans = OrderedDict([])

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
                path = gutils.select_file(start_path=self.batch_path, save=False, ext='xml')
                if path != '':
                    self.set_file_batch(str(path))
            else:  # cancel
                pass
        else:
            self.setupUI()

    def set_file_batch(self, filename, show=True):
        """

        """
        status = False
        settings_tmp = Parameter.create(title='Batch', name='settings_tmp',
                                        type='group', children=ioxml.XML_file_to_parameter(filename))

        children = settings_tmp.child('scans').children()
        self.settings = Parameter.create(title='Batch', name='settings', type='group', children=self.params)
        actuators = children[0].child('modules', 'actuators').value()['all_items']
        if actuators != self.actuators:
            raise ScannerException('The loaded actuators from the batch file do not corresponds to the'
                                   ' dashboard actuators')
        else:
            self.actuators = actuators

        detectors = children[0].child('modules', 'detectors').value()['all_items']
        if detectors != self.detectors:
            raise ScannerException('The loaded detectors from the batch file do not corresponds to the'
                                   ' dashboard detectors')
        else:
            self.detectors = detectors

        for child in children:
            self.add_scan(name=child.name(), title=child.opts['title'])
            self.settings.child('scans', child.name()).restoreState(child.saveState())

        if show:
            status = self.show_tree()
        else:
            self.tree = ParameterTree()
            self.tree.setMinimumWidth(400)
            self.tree.setMinimumHeight(500)
            self.tree.setParameters(self.settings, showTop=False)
            self.infos_list = QtWidgets.QListWidget()


            self.batch_dock.addWidget(self.tree)
            self.batch_dock.addWidget(self.infos_list)
        return status

    def set_scans(self):
        for scan in self.scans:
            info = self.scans[scan].set_scan()
            self.infos_list.addItem(f'{scan}: {info}')

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
        self.tree = ParameterTree()
        self.tree.setMinimumWidth(400)
        self.tree.setMinimumHeight(500)
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
        if name is None:
            name_prefix = 'scan'
            child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.settings.child('scans').children()]
            if child_indexes == []:
                newindex = 0
            else:
                newindex = max(child_indexes) + 1
            name = f'{name_prefix}{newindex:02.0f}'
            title = f'Scan {newindex:02.0f}'


        child = {'title': title, 'name': name,
                 'type': 'group',
                 'removable': True, 'children': params}


        self.scans[name] = Scanner(actuators=[self.actuators[0]],
                                                               adaptive_losses=adaptive_losses)
        self.settings.child('scans').addChild(child)
        self.settings.child('scans', name, 'modules',
                            'actuators').setValue(dict(all_items=self.actuators,
                                                       selected=[self.actuators[0]]))
        self.settings.child('scans', name, 'modules',
                            'detectors').setValue(dict(all_items=self.detectors,
                                                       selected=[self.detectors[0]]))

        self.settings.child('scans', name).addChild(
            self.scans[name].settings)

    def setupUI(self):
        # %% create scan dock and make it a floating window
        self.batch_dock = gutils.Dock("Scan", size=(1, 1), autoOrientation=False)  # give this dock the minimum possible size
        self.dockarea.addDock(self.batch_dock, 'left')
        self.batch_dock.float()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)

    prog = BatchScan(area=area, msgbox=False, actuators=['Xaxis', 'Yaxis'], detectors=['Det0D', 'Det1D'])
    prog.set_file_batch('C:\\Users\\weber\\pymodaq_local\\batch_configs\\batch_default.xml', show=False)
    prog.set_scans()
    win.show()
    sys.exit(app.exec_())

