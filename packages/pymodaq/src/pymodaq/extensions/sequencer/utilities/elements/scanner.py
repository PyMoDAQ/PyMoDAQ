import weakref
from typing import Any

from serializall import SerializableFactory

from qtpy import QtCore, QtWidgets

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.enums import MoveType
from pymodaq.utils.managers.modules import ModuleType
from pymodaq.utils.scanner.scanner import Orientation
from pymodaq_data import DataToExport
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.elements.repeat import RepeatElt
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.scanner import Scanner


ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class ScannerElt(SeqEltBase):

    elt_name = 'scanner'
    children_allowed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._ind_execute = 0
        self.scanner = Scanner()
        self.scanner_ref: weakref.ref[Scanner] = None

        self._actuators_all_to_restore: list[str] = None
        self._actuators_selected_to_restore: list[str] = None

    def initialize_element(self):
        self._ind_execute = 0

    def do_things_with_dashboard(self):
        if self._actuators_all_to_restore is not None:
            act_all_to_restore: list[DAQ_Move] = []
            for act_name in self._actuators_all_to_restore:
                if act_name in self.dashboard.modules_manager.actuators_name:
                    act_all_to_restore.append(
                        self.dashboard.modules_manager.get_mod_from_name(act_name,
                                                                         mod=ModuleType.Actuator))
            self._actuators_all_to_restore = None
        else:
            act_all_to_restore = self.dashboard.modules_manager.actuators_all

        act_selected_to_restore: list[DAQ_Move] = []
        if self._actuators_selected_to_restore is not None:
            for act_name in self._actuators_selected_to_restore:
                if act_name in self.dashboard.modules_manager.actuators_name:
                    act_selected_to_restore.append(
                        self.dashboard.modules_manager.get_mod_from_name(act_name,
                                                                         mod=ModuleType.Actuator))
            self._actuators_selected_to_restore = None

        self.scanner.actuators_all = act_all_to_restore
        self.scanner.actuators = act_selected_to_restore

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        self.scanner_ref = weakref.ref(Scanner(actuators=self.scanner.actuators_all,
                                               selected_actuators=self.scanner.actuators,
                                               orientation=Orientation.HORIZONTAL))

        base_widget.insert_widget(self.scanner_ref().parent_widget)
        self.scanner_ref().settings.child('actuators').show()
        self.scanner_ref().from_dict(self.scanner.to_dict(use_real_actuators=True))

        if base_widget.parent() is not None:
            base_widget.parent().popup_hiding.connect(self._on_editor_closing)

        return base_widget

    def _on_editor_closing(self):
        if self.scanner_ref is not None and self.scanner_ref() is not None:
            self.scanner.from_dict(self.scanner_ref().to_dict(use_real_actuators=True))
            self.scanner.save_scanner_settings()

    def _execute(self, dte: DataToExport=None):
        if self._ind_execute == 0:
            self.scanner.set_scan()

        if self._ind_execute < self.scanner.n_steps:
            next_values = self.scanner.positions_at(self._ind_execute)
            self.dashboard.modules_manager.move_actuators_with_callback(
                dte_act = next_values,
                mode= MoveType.ABS,
                callback = self._on_move_done,
                do_connect_modules=True)

            """ This will execute the children state and its bundled elements n_repeat times"""
            self._ind_execute += 1
        else:
            self._ind_execute = 0
            self.done_signal.emit()

    def _on_move_done(self):
        self.dashboard.modules_manager.forget_callback(self._on_move_done,
                                                       module_type = ModuleType.Actuator,
                                                       disconnect_modules = True
                                                       )
        self.children_signal.emit()

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return self.scanner.to_dict()

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        #loading from file implies actuators is a list of str but at the moment of restoring the elt, the dashboard has
        # not been set yet and self.scanner has also no actuators yet...
        if len(dict_config['actuators']) > 0 and isinstance(dict_config['actuators'][0], str):
            self._actuators_all_to_restore = dict_config['actuators']
            dict_config['actuators'] = []  # will be restored later, when dashboard is set

        if len(dict_config['selected']) > 0 and isinstance(dict_config['selected'][0], str):
            self._actuators_selected_to_restore = dict_config['selected']
            dict_config['selected'] = []  # will be restored later, when dashboard is set

        self.scanner.from_dict(dict_config)

    def _eq(self, other: 'ScannerElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return self.scanner.to_dict() == other.scanner.to_dict()

    def __repr__(self):
        return f'{super().__repr__()} - {self.scanner}'

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        self.scanner.set_scan()
        if not (self.scanner.n_steps >= 1):
            raise ElementError(f'Element {self}: at least one scan step required')

    def size_hint(self) -> QtCore.QSize:
        return QtCore.QSize(200, 300)
