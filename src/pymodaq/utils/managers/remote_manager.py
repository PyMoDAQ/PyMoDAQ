import os
import sys

from qtpy.QtCore import QObject, Signal
from qtpy import QtGui, QtWidgets


from pymodaq.utils.config import get_set_remote_path

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.utils import select_file
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType, GroupParameter

logger = set_logger(get_module_name(__file__))
remote_path = get_set_remote_path()
remote_types = ['ShortCut', 'Joystick']

actuator_actions = ['move_rel', 'move_rel_p', 'move_rel_m']
detector_actions = ['snap', 'grab', 'stop']
remote_types = ['Keyboard', 'Joystick']

try:
    import pygame
    is_pygame = True
except ModuleNotFoundError as e:
    remote_types.pop(remote_types.index('Joystick'))
    logger.warning('Could not load pygame module, no joystick configurable')
    is_pygame = False


class ScalableGroupRemote(GroupParameter):
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
        name_prefix = 'action'  # or 'det_' but they have same length
        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]
        if not child_indexes:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        params = [{'title': 'Action:', 'name': 'action', 'type': 'list', 'value': typ, 'limits': self.opts['addList']},
                  {'title': 'Remote:', 'name': 'remote_type', 'type': 'list', 'value': 'Keyboard',
                   'limits': remote_types},
                  ]
        params.extend([
            {'title': 'Set Shortcut:', 'name': 'set_shortcut', 'type': 'bool_push', 'label': 'Set',
             'value': False},
            {'title': 'Shortcut:', 'name': 'shortcut', 'type': 'str', 'value': ''},
            {'title': 'Set Joystick ID:', 'name': 'set_joystick', 'type': 'bool_push', 'label': 'Set',
             'value': False, 'visible': False},

            {'title': 'Joystick ID:', 'name': 'joystickID', 'type': 'int', 'value': -1, 'visible': False},
            {'title': 'Actionner type:', 'name': 'actionner_type', 'type': 'list', 'limits': ['Axis', 'Button', 'Hat'],
             'visible': False},
            {'title': 'Actionner ID:', 'name': 'actionnerID', 'type': 'int', 'value': -1, 'visible': False},
        ])

        # for param in params:
        #     if param['type'] == 'itemselect' or param['type'] == 'list':
        #         param['show_pb'] = True

        child = {'title': f'Action {newindex:02d}', 'name': f'{name_prefix}{newindex:02d}', 'type': 'group',
                 'removable': True, 'children': params, 'removable': True, 'renamable': False}

        self.addChild(child)


registerParameterType('groupremote', ScalableGroupRemote, override=True)


class ScalableGroupModules(GroupParameter):
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
        name_prefix = 'act_'  # or 'det_' but they have same length
        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]
        if not child_indexes:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        if self.opts['modtype'] == 'Actuator':
            addlist = actuator_actions
        else:
            addlist = detector_actions

        params = [
            {'title': 'Actions:', 'name': 'actions', 'type': 'groupremote', 'value': typ,
             'limits': self.opts['addList'], 'addList': addlist},
        ]

        # for param in params:
        #     if param['type'] == 'itemselect' or param['type'] == 'list':
        #         param['show_pb'] = True

        if self.opts['modtype'] == 'Actuator':
            child = {'title': f'Actuator {typ}', 'name': f'{name_prefix}{newindex:03d}',
                     'type': 'group',
                     'removable': True, 'children': params, 'removable': True, 'renamable': False}
        else:
            child = {'title': f'Detector {typ}', 'name': f'det_{newindex:03d}', 'type': 'group',
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

        self.selection = None

        pygame.init()
        pygame.joystick.init()
        # width, height = 64 * 10, 64 * 8
        # self.screen = pygame.display.set_mode((width, height))
        joystick_count = pygame.joystick.get_count()
        self.joysticks = []
        for ind in range(joystick_count):
            self.joysticks.append(pygame.joystick.Joystick(ind))
            self.joysticks[-1].init()
        self.startTimer(10)

    def timerEvent(self, event):
        for event in pygame.event.get():  # User did something.
            if 'joy' in event.dict:
                self.settings.child(('joystickID')).setValue(event.joy)
                self.selection = dict(joy=event.joy)
            if event.type == pygame.QUIT:  # If user clicked close.
                self.reject()
            elif event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYBUTTONUP:
                self.settings.child(('buttonID')).show(True)
                self.settings.child(('axisID')).show(False)
                self.settings.child(('hatID')).show(False)
                self.settings.child(('axis_value')).show(False)
                self.settings.child(('hat_value1')).show(False)
                self.settings.child(('hat_value2')).show(False)
                self.settings.child(('buttonID')).setValue(event.button)
                self.selection.update(dict(button=event.button))
            elif event.type == pygame.JOYAXISMOTION:
                self.settings.child(('buttonID')).show(False)
                self.settings.child(('axisID')).show(True)
                self.settings.child(('hatID')).show(False)
                self.settings.child(('axis_value')).show(True)
                self.settings.child(('axisID')).setValue(event.axis)
                self.settings.child(('axis_value')).setValue(event.value)
                self.settings.child(('hat_value1')).show(False)
                self.settings.child(('hat_value2')).show(False)
                self.selection.update(dict(axis=event.axis, value=event.value))
            elif event.type == pygame.JOYHATMOTION:
                self.settings.child(('buttonID')).show(False)
                self.settings.child(('axisID')).show(False)
                self.settings.child(('hatID')).show(True)
                self.settings.child(('axis_value')).show(True)
                self.settings.child(('hat_value1')).show(True)
                self.settings.child(('hat_value2')).show(True)
                self.settings.child(('hat_value1')).setValue(event.value[0])
                self.settings.child(('hat_value2')).setValue(event.value[1])
                self.selection.update(dict(hat=event.hat, value=event.value))

    def setupUI(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        label = QtWidgets.QLabel('Press a button or move an axis on the Joystick:')
        layout.addWidget(label)

        params = [{'title': 'Joystick ID', 'name': 'joystickID', 'type': 'int', 'value': -1},
                  {'title': 'Button ID', 'name': 'buttonID', 'type': 'int', 'value': -1, 'visible': False},
                  {'title': 'Axis ID', 'name': 'axisID', 'type': 'int', 'value': -1, 'visible': False},
                  {'title': 'Value:', 'name': 'axis_value', 'type': 'float', 'value': 0., 'visible': False},
                  {'title': 'Hat ID', 'name': 'hatID', 'type': 'int', 'value': -1, 'visible': False},
                  {'title': 'Value x:', 'name': 'hat_value1', 'type': 'int', 'value': 0, 'visible': False},
                  {'title': 'Value y:', 'name': 'hat_value2', 'type': 'int', 'value': 0, 'visible': False}, ]

        self.settings = Parameter.create(name='settings', type='group', children=params)
        self.settings_tree = ParameterTree()
        # tree.setMinimumWidth(400)
        # self.settings_tree.setMinimumHeight(500)
        self.settings_tree.setParameters(self.settings, showTop=False)

        layout.addWidget(self.settings_tree)

        buttonBox = QtWidgets.QDialogButtonBox()
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)


class RemoteManager(QObject):
    remote_changed = Signal(dict)

    def __init__(self, actuators=[], detectors=[], msgbox=False):
        super().__init__()
        self.actuators = actuators
        self.detectors = detectors
        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Preset Manager?")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            new_button = msgBox.addButton("New", QtWidgets.QMessageBox.ActionRole)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == new_button:
                self.set_new_remote()

            elif msgBox.clickedButton() == modify_button:
                path = select_file(start_path=remote_path, save=False, ext='xml')
                if path != '':
                    self.set_file_remote(str(path))
            else:  # cancel
                pass
        params = [{'title': 'Activate all', 'name': 'activate_all', 'type': 'action'},
                  {'title': 'Deactivate all', 'name': 'deactivate_all', 'type': 'action'},
                  {'title:': 'Actions', 'name': 'action_group', 'type': 'group'}]

        self.remote_actions = dict(shortcuts=dict([]), joysticks=dict([]))
        self.remote_settings = Parameter.create(title='Remote Settings', name='remote', type='group',
                                                children=params)
        self.remote_settings.sigTreeStateChanged.connect(self.remote_settings_changed)
        self.remote_settings_tree = ParameterTree()
        self.remote_settings_tree.setParameters(self.remote_settings, showTop=False)
        self.remote_settings.child(('activate_all')).sigActivated.connect(lambda: self.activate_all(True))
        self.remote_settings.child(('deactivate_all')).sigActivated.connect(lambda: self.activate_all(False))

    def activate_all(self, activate=True):
        for child in self.remote_settings.child(('action_group')).children():
            child.setValue(activate)

    def set_remote_configuration(self):
        # remove existing shorcuts
        while len(self.remote_actions['shortcuts']):
            self.remote_actions['shortcuts'].pop(list(self.remote_actions['shortcuts'].keys())[0])

        while len(self.remote_actions['joysticks']):
            self.remote_actions['joysticks'].pop(list(self.remote_actions['joysticks'].keys())[0])
        all_actions = []
        for child in self.remote_params.child('act_actions').children():
            module_name = child.opts['title'].split('Actuator ')[1]
            module_type = 'act'
            for action in child.child(('actions')).children():
                all_actions.append((module_name, action, module_type))
        for child in self.remote_params.child('det_actions').children():
            module_name = child.opts['title'].split('Detector ')[1]
            module_type = 'det'
            for action in child.child(('actions')).children():
                all_actions.append((module_name, action, module_type))

        for ind, action_tuple in enumerate(all_actions):
            module, action, module_type = action_tuple
            if action.child('remote_type').value() == 'Keyboard':
                # stc = QtWidgets.QShortcut(QtGui.QKeySequence(action.child(('shortcut')).value()), self.dockarea)
                self.remote_settings.child(('action_group')).addChild(
                    {'title': f"{module}: {action.child(('action')).value()} "
                              f"{action.child(('shortcut')).value()}:",
                     'name': f'shortcut{ind:02d}', 'type': 'led_push', 'value': False})
                self.remote_actions['shortcuts'][f'shortcut{ind:02d}'] = \
                    dict(shortcut=action.child(('shortcut')).value(), activated=False, name=f'shortcut{ind:02d}',
                         action=action.child(('action')).value(), module_name=module, module_type=module_type)
            else:
                self.remote_settings.child(('action_group')).addChild(
                    {'title': f"{module}: {action.child(('action')).value()}=>"
                              f"J{action.child(('joystickID')).value()}/"
                              f"{action.child(('actionner_type')).value()}"
                              f"{action.child(('actionnerID')).value()}:",
                     'name': f'joy{ind:02d}', 'type': 'led_push', 'value': False})
                self.remote_actions['joysticks'][f'joy{ind:02d}'] = \
                    dict(joystickID=action.child(('joystickID')).value(),
                         actionner_type=action.child(('actionner_type')).value(),
                         actionnerID=action.child(('actionnerID')).value(),
                         activated=False, name=f'joy{ind:02d}',
                         action=action.child(('action')).value(),
                         module_name=module, module_type=module_type)

        self.activate_all()

    def set_new_remote(self, file=None):
        if file is None:
            file = 'remote_default'
        param = [
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': file},
        ]
        params_action = [{'title': 'Actuator Actions:', 'name': 'act_actions', 'type': 'groupmodules',
                          'addList': self.actuators, 'modtype': 'Actuator'},
                         {'title': 'Detector Actions:', 'name': 'det_actions', 'type': 'groupmodules',
                          'addList': self.detectors, 'modtype': 'Detector'}
                         ]  # PresetScalableGroupMove(name="Moves")]
        self.remote_params = Parameter.create(title='Preset', name='Preset', type='group',
                                              children=param + params_action)
        self.remote_params.sigTreeStateChanged.connect(self.parameter_tree_changed)
        logger.info('Creating a new remote file')
        self.show_remote()

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
            path = self.remote_params.childPath(param)
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'remote_type':
                    status = data == 'Keyboard'
                    param.parent().child(('set_shortcut')).show(status)
                    param.parent().child(('shortcut')).show(status)
                    param.parent().child(('set_joystick')).show(not status)
                    param.parent().child(('joystickID')).show(not status)
                    param.parent().child(('actionner_type')).show(not status)
                    param.parent().child(('actionnerID')).show(not status)

                elif param.name() == 'set_shortcut':
                    msgBox = ShortcutSelection()
                    ret = msgBox.exec()
                    if ret:
                        param.parent().child(('shortcut')).setValue(msgBox.label.text())
                elif param.name() == 'set_joystick':
                    msgBox = JoystickButtonsSelection()
                    ret = msgBox.exec()
                    if ret:
                        param.parent().child(('joystickID')).setValue(msgBox.selection['joy'])
                        """
                        possible cases: ['Axis', 'Button', 'Hat']
                        """
                        if 'axis' in msgBox.selection:
                            param.parent().child(('actionner_type')).setValue('Axis')
                            param.parent().child(('actionnerID')).setValue(msgBox.selection['axis'])
                        elif 'button' in msgBox.selection:
                            param.parent().child(('actionner_type')).setValue('Button')
                            param.parent().child(('actionnerID')).setValue(msgBox.selection['button'])
                        elif 'hat' in msgBox.selection:
                            param.parent().child(('actionner_type')).setValue('Hat')
                            param.parent().child(('actionnerID')).setValue(msgBox.selection['hat'])

            elif change == 'parent':
                pass

    def remote_settings_changed(self, param, changes):
        for param, change, data in changes:
            path = self.remote_params.childPath(param)
            if change == 'childAdded':
                pass

            elif change == 'value':
                if 'shortcut' in param.name():
                    self.remote_actions['shortcuts'][param.name()]['activated'] = data
                    self.remote_changed.emit(dict(action_type='shortcut',
                                                  action_name=param.name(),
                                                  action_dict=self.remote_actions['shortcuts'][param.name()]))
                elif 'joy' in param.name():
                    self.remote_actions['joysticks'][param.name()]['activated'] = data
                    self.remote_changed.emit(dict(action_type='joystick',
                                                  action_name=param.name(),
                                                  action_dict=self.remote_actions['joysticks'][param.name()]))

    def set_file_remote(self, filename, show=True):
        """

        """
        children = ioxml.XML_file_to_parameter(filename)
        self.remote_params = Parameter.create(title='Shortcuts:', name='shortcuts', type='group', children=children)
        if show:
            self.show_remote()

    def show_remote(self):
        """

        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        # tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        tree.setParameters(self.remote_params, showTop=False)

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
            ioxml.parameter_to_xml_file(
                self.remote_params, os.path.join(remote_path, self.remote_params.child('filename').value()))


if __name__ == '__main__':
    actuators = ['act0', 'act1', 'act2']
    detectors = ['det0', 'det1', 'det2']
    app = QtWidgets.QApplication(sys.argv)
    #prog = RemoteManager(actuators=actuators, detectors=detectors, msgbox=True)
    msgBox = JoystickButtonsSelection()
    ret = msgBox.exec()
    sys.exit(app.exec_())
