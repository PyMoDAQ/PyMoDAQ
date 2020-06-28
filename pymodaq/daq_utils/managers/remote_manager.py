import os, sys
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QEvent, QBuffer, QIODevice, QLocale, Qt, QVariant, QModelIndex
from PyQt5 import QtGui, QtWidgets, QtCore
import time
import numpy as np
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.gui_utils import select_file
from pyqtgraph.parametertree import Parameter, ParameterTree, registerParameterType, parameterTypes
from pymodaq.daq_utils import custom_parameter_tree as custom_tree

logger = utils.set_logger(utils.get_module_name(__file__))
remote_path = utils.get_set_remote_path()
remote_types = ['ShortCut', 'Joystick']

actuator_actions = ['MoveRel']
detector_actions = ['Snap', 'Grab', 'Stop']


try:
    import pygame
except ImportError as e:
    remote_types.pop('Joystick')
    logger.warning('Could not load pygame module, no joystick configurable')

class ScalableGroupRemote(parameterTypes.GroupParameter):
    """
    """

    def __init__(self, **opts):
        opts['type'] = 'groupremote'
        opts['addText'] = "Add"
        if 'remote' not in opts:
            opts['remote'] = remote_types[0]
        if 'addList' not in opts:
            opts['addList'] = []
        super().__init__(**opts)

    def addNew(self, typ):
        """
            Add a child.
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        params = [{'title': 'Action:', 'name': 'action', 'type': 'list', 'value': typ, 'values': self.opts['addList']},
                  {'title': 'Remote:', 'name': 'remote_type', 'type': 'list', 'value': 'Keyboard',
                   'values': ['Keyboard', 'Joystick']},
                  ]
        params.extend([
                  {'title': 'Set Shortcut:', 'name': 'set_shortcut', 'type': 'bool_push', 'label': 'Set',
                   'value': False},
                  {'title': 'Shortcut:', 'name': 'shortcut', 'type': 'str', 'value': ''},
                  {'title': 'Set Joystick ID:', 'name': 'set_joystick', 'type': 'bool_push', 'label': 'Set',
                   'value': False, 'visible': False},
                  {'title': 'Joystick ID:', 'name': 'joystickID', 'type': 'int', 'value': -1, 'visible': False},
                  ])


        # for param in params:
        #     if param['type'] == 'itemselect' or param['type'] == 'list':
        #         param['show_pb'] = True

        child = {'title': f'Action {newindex:02d}', 'name': f'action{newindex:02d}', 'type': 'group',
                 'removable': True, 'children': params, 'removable': True, 'renamable': False}

        self.addChild(child)
registerParameterType('groupremote', ScalableGroupRemote, override=True)


class ScalableGroupModules(parameterTypes.GroupParameter):
    """
    """

    def __init__(self, **opts):
        opts['type'] = 'groupremote'
        opts['addText'] = "Add"
        if 'modtype' not in opts:
            opts['modtype'] = 'Actuator'
        if 'addList' not in opts:
            opts['addList'] = []
        super().__init__(**opts)

    def addNew(self, typ):
        """
            Add a child.
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        if self.opts['modtype'] == 'Actuator':
            addlist = actuator_actions
        else:
            addlist = detector_actions

        params = [
            {'title': 'Actions:', 'name': 'actions', 'type': 'groupremote', 'value': typ,
             'values': self.opts['addList'], 'addList': addlist},
            ]


        # for param in params:
        #     if param['type'] == 'itemselect' or param['type'] == 'list':
        #         param['show_pb'] = True

        if self.opts['modtype'] == 'Actuator':
            child = {'title': f'Actuator {typ}', 'name': f'act_{typ}', 'type': 'group',
                 'removable': True, 'children': params, 'removable': True, 'renamable': False}
        else:
            child = {'title': f'Detector {typ}', 'name': f'det_{typ}', 'type': 'group',
                 'removable': True, 'children': params, 'removable': True, 'renamable': False}

        if child['name'] not in [child.name() for child in self.children()]:
            self.addChild(child)
registerParameterType('groupmodules', ScalableGroupModules, override=True)
    

class ShortcutSelection(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        horwidget = QtWidgets.QWidget()
        layout.addWidget(horwidget)
        hor_layout = QtWidgets.QHBoxLayout()
        horwidget.setLayout(hor_layout)
        label = QtWidgets.QLabel('Pressed key on the keyboard:')
        self.label = QtWidgets.QLabel('')

        hor_layout.addWidget(label)
        hor_layout.addWidget(self.label)

        buttonBox = QtWidgets.QDialogButtonBox()
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.label)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def keyPressEvent(self, event):
        keyseq = QtGui.QKeySequence(event.key())
        self.label.setText(keyseq.toString())

class JoystickButtonsSelection(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUI()
        pygame.init()
        pygame.joystick.init()
        joystick_count = pygame.joystick.get_count()
        for ind in range(joystick_count):
            joystick = pygame.joystick.Joystick(ind)
            joystick.init()
        self.startTimer(10)

    def timerEvent(self, event):
        for event in pygame.event.get():  # User did something.
            if 'joy' in event.dict:
                self.joystick_ID.setValue(event.joy)
            if event.type == pygame.QUIT:  # If user clicked close.
                done = True  # Flag that we are done so we exit this loop.
            elif event.type == pygame.JOYBUTTONDOWN:
                self.button_ID.setValue(event.button)
            elif event.type == pygame.JOYAXISMOTION :
                self.axis_ID.setValue(event.axis)
                self.axis_value.setValue(event.value)
            elif event.type == pygame.JOYHATMOTION:
                pass


    def setupUI(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        label = QtWidgets.QLabel('Press a button or move an axis on the Joystick:')
        layout.addWidget(label)

        horwidget1 = QtWidgets.QWidget()
        layout.addWidget(horwidget1)
        hor_layout = QtWidgets.QHBoxLayout()
        horwidget1.setLayout(hor_layout)


        self.joystick_ID = custom_tree.SpinBoxCustom()
        self.joystick_ID.setValue(-1)
        self.joystick_ID.setReadOnly(True)
        hor_layout.addWidget(QtWidgets.QLabel('Joystick ID:'))
        hor_layout.addWidget(self.joystick_ID)

        horwidget2 = QtWidgets.QWidget()
        layout.addWidget(horwidget2)
        hor_layout2 = QtWidgets.QHBoxLayout()
        horwidget2.setLayout(hor_layout2)
        self.button_ID = custom_tree.SpinBoxCustom(bounds=(-1, 100))
        self.button_ID.setReadOnly(True)
        self.button_ID.setValue(-1)
        hor_layout2.addWidget(QtWidgets.QLabel('Button ID:'))
        hor_layout2.addWidget(self.button_ID)

        horwidget3 = QtWidgets.QWidget()
        layout.addWidget(horwidget3)
        hor_layout3 = QtWidgets.QHBoxLayout()
        horwidget3.setLayout(hor_layout3)
        self.axis_ID = custom_tree.SpinBoxCustom(bounds=(-1, 100))
        self.axis_ID.setReadOnly(True)
        self.axis_ID.setValue(-1)
        hor_layout3.addWidget(QtWidgets.QLabel('Axis ID:'))
        hor_layout3.addWidget(self.axis_ID)

        horwidget4 = QtWidgets.QWidget()
        layout.addWidget(horwidget4)
        hor_layout4 = QtWidgets.QHBoxLayout()
        horwidget4.setLayout(hor_layout4)
        self.axis_value = custom_tree.SpinBoxCustom(bounds=(-1., 1.))
        self.axis_value.setReadOnly(True)
        self.axis_value.setValue(0.0)
        hor_layout4.addWidget(QtWidgets.QLabel('Axis Value:'))
        hor_layout4.addWidget(self.axis_value)

        buttonBox = QtWidgets.QDialogButtonBox()
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)



class RemoteManager(QObject):

    def __init__(self, actuators=[], detectors=[], msgbox=False):
        super().__init__()
        self.actuators = actuators
        self.detectors = detectors
        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Preset Manager?")
            msgBox.setInformativeText("What do you want to do?");
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            new_button = msgBox.addButton("New", QtWidgets.QMessageBox.ActionRole)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == new_button:
                self.set_new_preset()

            elif msgBox.clickedButton() == modify_button:
                path = select_file(start_path=remote_path, save=False, ext='xml')
                if path != '':
                    self.set_file_preset(str(path))
            else:  # cancel
                pass

    def set_new_preset(self):
        param = [
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'remote_default'},
        ]
        params_action = [{'title': 'Actuator Actions:', 'name': 'act_actions', 'type': 'groupmodules',
                          'addList': self.actuators, 'modtype': 'Actuator'},
                         {'title': 'Detector Actions:', 'name': 'det_actions', 'type': 'groupmodules',
                          'addList': self.detectors, 'modtype': 'Detector'}
                         ]  # PresetScalableGroupMove(name="Moves")]
        self.shortcut_params = Parameter.create(title='Preset', name='Preset', type='group',
                                                children=param + params_action)
        self.shortcut_params.sigTreeStateChanged.connect(self.parameter_tree_changed)

        self.show_preset()

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
            path = self.shortcut_params.childPath(param)
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'remote_type':
                    status = data == 'Keyboard'
                    param.parent().child(('set_shortcut')).show(status)
                    param.parent().child(('shortcut')).show(status)
                    param.parent().child(('set_joystick')).show(not status)
                    param.parent().child(('joystickID')).show(not status)

                elif param.name() == 'set_shortcut':
                    msgBox = ShortcutSelection()
                    ret = msgBox.exec()
                    if ret:
                        param.parent().child(('shortcut')).setValue(msgBox.label.text())
                elif param.name() == 'set_joystick':
                    msgBox = JoystickButtonsSelection()
                    ret = msgBox.exec()
                    if ret:
                        param.parent().child(('joystickID')).setValue(msgBox.button_ID.value())

            elif change == 'parent':
                pass

    def set_file_preset(self, filename, show=True):
        """

        """
        children = custom_tree.XML_file_to_parameter(filename)
        self.shortcut_params = Parameter.create(title='Shortcuts:', name='shortcuts', type='group', children=children)
        if show:
            self.show_preset()

    def show_preset(self):
        """

        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        # tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        tree.setParameters(self.shortcut_params, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about the actions and their shortcuts')
        res = dialog.exec()

        if res == dialog.Accepted:
            # save preset parameters in a xml file
            custom_tree.parameter_to_xml_file(self.shortcut_params, os.path.join(remote_path,
                                                                                 self.shortcut_params.child(
                                                                                     ('filename')).value()))

if __name__ == '__main__':
    actuators = ['act0', 'act1', 'act2']
    detectors = ['det0', 'det1', 'det2']
    app = QtWidgets.QApplication(sys.argv)
    #prog = RemoteManager(actuators=actuators, detectors=detectors, msgbox=True)
    msgBox = JoystickButtonsSelection()
    ret = msgBox.exec()
    sys.exit(app.exec_())