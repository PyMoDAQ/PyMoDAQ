from PyQt5 import QtWidgets
import sys
import os

from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter.pymodaq_ptypes import GroupParameterCustom as GroupParameter
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree.Parameter import registerParameterType
from pymodaq.daq_utils.gui_utils import select_file

# check if overshoot_configurations directory exists on the drive
from pymodaq.daq_utils.daq_utils import get_set_overshoot_path
overshoot_path = get_set_overshoot_path()


class PresetScalableGroupMove(GroupParameter):
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
        opts['type'] = 'groupmoveover'
        opts['addText'] = "Add"
        opts['addList'] = opts['movelist']
        super().__init__(**opts)

    def addNew(self, name):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        name_prefix = 'move'
        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]
        if not child_indexes:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        child = {'title': name, 'name': f'{name_prefix}{newindex:02.0f}', 'type': 'group', 'removable': True,
                 'children': [
                     {'title': 'Move if overshoot?:', 'name': 'move_overshoot', 'type': 'bool', 'value': True},
                     {'title': 'Position:', 'name': 'position', 'type': 'float', 'value': 0}], 'removable': True,
                 'renamable': False}

        self.addChild(child)


registerParameterType('groupmoveover', PresetScalableGroupMove, override=True)


class PresetScalableGroupDet(GroupParameter):
    """
        =============== ==============
        **Attributes**    **Type**
        *opts*            dictionnary
        *options*         string list
        =============== ==============

        See Also
        --------
    """

    def __init__(self, **opts):
        opts['type'] = 'groupdetover'
        opts['addText'] = "Add"
        opts['addList'] = opts['detlist']
        opts['movelist'] = opts['movelist']

        super().__init__(**opts)

    def addNew(self, name):
        """
            Add a child.

            =============== ===========  ================
            **Parameters**    **Type**   **Description*
            *typ*             string     the viewer name
            =============== ===========  ================
        """
        try:
            name_prefix = 'det'
            child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]
            if not child_indexes:
                newindex = 0
            else:
                newindex = max(child_indexes) + 1

            child = {'title': name, 'name': f'{name_prefix}{newindex:02.0f}', 'type': 'group', 'children': [
                {'title': 'Trig overshoot?:', 'name': 'trig_overshoot', 'type': 'bool', 'value': True},
                {'title': 'Overshoot value:', 'name': 'overshoot_value', 'type': 'float', 'value': 20},
                {'title': 'Triggered Moves:', 'name': 'params', 'type': 'groupmoveover',
                 'movelist': self.opts['movelist']}], 'removable': True, 'renamable': False}

            self.addChild(child)
        except Exception as e:
            print(str(e))


registerParameterType('groupdetover', PresetScalableGroupDet, override=True)


class OvershootManager:
    def __init__(self, msgbox=False, det_modules=[], move_modules=[]):

        self.overshoot_params = None
        self.det_modules = det_modules
        self.move_modules = move_modules

        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Overshoot Manager?")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            new_button = msgBox.addButton("New", QtWidgets.QMessageBox.ActionRole)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == new_button:
                self.set_new_overshoot()

            elif msgBox.clickedButton() == modify_button:
                path = select_file(start_path=overshoot_path, save=False, ext='xml')
                if path != '':
                    self.set_file_overshoot(str(path))
            else:  # cancel
                pass

    def set_file_overshoot(self, filename, show=True):
        """

        """
        children = ioxml.XML_file_to_parameter(filename)
        self.overshoot_params = Parameter.create(title='Overshoot', name='Overshoot', type='group', children=children)
        if show:
            self.show_overshoot()

    def set_new_overshoot(self, file=None):
        if file is None:
            file = 'overshoot_default'
        param = [{'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': file}]
        params_det = [{'title': 'Detectors:', 'name': 'Detectors', 'type': 'groupdetover', 'detlist': self.det_modules,
                       'movelist': self.move_modules}]  # [PresetScalableGroupDet(name="Detectors")]
        self.overshoot_params = Parameter.create(title='Preset', name='Preset', type='group',
                                                 children=param + params_det)

        self.show_overshoot()

    def show_overshoot(self):
        """

        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        tree.setParameters(self.overshoot_params, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this managers')
        res = dialog.exec()

        if res == dialog.Accepted:
            # save managers parameters in a xml file
            # start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            # start = os.path.join("..",'daq_scan')
            ioxml.parameter_to_xml_file(
                self.overshoot_params, os.path.join(overshoot_path, self.overshoot_params.child('filename').value()))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    prog = OvershootManager(True, ['det camera', 'det current'], ['Move X', 'Move Y'])

    sys.exit(app.exec_())
