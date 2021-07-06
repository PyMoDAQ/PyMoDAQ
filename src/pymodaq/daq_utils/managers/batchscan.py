from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot, pyqtSignal
import sys
import os
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from pymodaq.daq_utils.managers import preset_manager_utils
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils
from pymodaq.daq_utils.scanner import Scanner, scan_types
from pathlib import Path
from pymodaq.daq_utils.parameter.pymodaq_ptypes import GroupParameterCustom as GroupParameter
from pyqtgraph.parametertree.Parameter import registerParameterType
from collections import OrderedDict

logger = utils.set_logger(utils.get_module_name(__file__))


modules_params = [
    {'title': 'Actuators/Detectors Selection', 'name': 'modules', 'type': 'group', 'children': [
        {'title': 'detectors', 'name': 'detectors', 'type': 'itemselect'},
        {'title': 'Actuators', 'name': 'actuators', 'type': 'itemselect'},
    ]},]


class BatchScan:



    params = [{'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'preset_default'},
              {'title': 'Scans', 'name': 'scans', 'type': 'group', 'children': []}]

    def __init__(self, msgbox=False, actuators=[], detectors=[]):
        self.actuators = actuators
        self.detectors = detectors
        self.selected_actuators = []
        self.selected_detectors = []
        self.scans = OrderedDict([])

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
                path = gui_utils.select_file(start_path=self.preset_path, save=False, ext='xml')
                if path != '':
                    self.set_file_batch(str(path))
            else:  # cancel
                pass

    def set_file_batch(self, filename, show=True):
        """

        """
        status = False
        self.pid_type = False
        children = ioxml.XML_file_to_parameter(filename)
        self.settings = Parameter.create(title='Preset', name='Preset', type='group', children=children)
        if show:
            status = self.show_preset()
        return status

    def set_new_batch(self):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)
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

        return res == dialog.Accepted

    def add_scan(self):

        name_prefix = 'scan'
        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.settings.child('scans').children()]
        if child_indexes == []:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1



        child = {'title': 'Scan {:02.0f}'.format(newindex), 'name': f'{name_prefix}{newindex:02.0f}',
                 'type': 'group',
                 'removable': True, 'children': modules_params}


        self.scans[f'{name_prefix}{newindex:02.0f}'] = Scanner(actuators=self.actuators[0])



        self.settings.child('scans').addChild(child)


        self.settings.child('scans', f'{name_prefix}{newindex:02.0f}', 'modules',
                            'actuators').setValue(dict(all_items=self.actuators,
                                                       selected=self.actuators[0]))
        self.settings.child('scans', f'{name_prefix}{newindex:02.0f}', 'modules',
                            'detectors').setValue(dict(all_items=self.detectors,
                                                       selected=self.detectors[0]))

        self.settings.child('scans', f'{name_prefix}{newindex:02.0f}').addChildren(Scanner.params)

    @pyqtSlot(list)
    def update_actuators(self, actuators):
        self.scanner.actuators = actuators



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    prog = BatchScan(msgbox=True, actuators=['Xaxis', 'Yaxis'], detectors=['Det0D', 'Det1D'])

    sys.exit(app.exec_())

