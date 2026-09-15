from typing import Any
import weakref

from serializall import SerializableFactory

from qtpy import QtCore, QtGui

from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.daq_viewer_ui.ui_base import ActionIconNames
from pymodaq_gui.managers.action_manager import QAction
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_data import DataToExport
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect


from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.managers.modules import ModuleType

ser_factory = SerializableFactory()
logger = set_logger(get_module_name(__file__))


class Status(StrEnum):
    SNAP = 'Snap'
    GRAB = 'Grab'
    STOP = 'Stop'


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class GrabElt(SeqEltBase):

    elt_name = 'grab'
    children_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules_manager = ModulesManager()
        self._detectors: list[str] = []
        self._selected: list[str] = []

        self._status = Status.SNAP

        self._items: weakref.ref[ItemSelect] = None
        for child_name in ('actuators', 'probe_data', 'test_actuator'):
            self.modules_manager.settings.child(child_name).show(False)
        self.modules_manager.settings_tree.setVisible(False)

    @property
    def detectors(self) -> list[str]:
        return self._detectors

    @detectors.setter
    def detectors(self, value: list[str]):
        self._detectors = value

    @property
    def selected(self) -> list[str]:
        return self._selected

    @selected.setter
    def selected(self, value: list[str]):
        self._selected = value

    @property
    def status(self) -> Status | str:
        return self._status

    @status.setter
    def status(self, status: Status):
        self._status = status

    def set_status(self, status: Status):
        self.status = status

    def do_things_with_dashboard(self):
        self.dashboard.experiment_manager.applied_entry.connect(self.update_modules)
        self.update_modules()

    def update_modules(self):
        self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all
        self.detectors = self.modules_manager.detectors_name
        self.filter_selected_wrt_manager()

    def filter_selected_wrt_manager(self):
        """  Filter selected given the presence of the detector in the manager """
        selected = []
        for sel in self.selected:
            if sel in self.modules_manager.detectors_name:
                selected.append(sel)
            else:
                logger.warning(f'Could not select the detector: {sel} as not declared in '
                               f'the ModulesManager instance/ DashBoard')
        self.selected = selected

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        item_select = ItemSelect(hasCheckbox=True, parent=base_widget)
        self._items = weakref.ref(item_select)
        item_select.set_value(dict(all_items=self.detectors,
                                   selected = self.selected,))
        item_select.itemChanged.connect(self.update_detectors_from_combo)
        base_widget.insert_widget(item_select)

        base_widget.action_group = QtGui.QActionGroup(base_widget)
        base_widget.action_group.setExclusive(True)

        base_widget.add_action(Status.SNAP, Status.SNAP,
                               icon_name=ActionIconNames.SNAP,
                               checkable=True,
                               icon_checked_color=get_theme().green,
                               tip='Snap',
                               toolbar=base_widget.toolbar,
                               before='execute')
        base_widget.add_action(Status.GRAB, Status.GRAB,
                               icon_name=ActionIconNames.GRAB,
                               checkable=True,
                               icon_checked_color=get_theme().green,
                               tip='Grab',
                               toolbar=base_widget.toolbar,
                               before='execute')
        base_widget.add_action(Status.STOP, Status.STOP,
                               icon_name='stop_circle',
                               tip='Stop any current Grab on the selected detectors',
                               icon_checked_color=get_theme().green,
                               checkable=True,
                               toolbar=base_widget.toolbar,
                               before='execute')

        for action_name in Status.values():
            base_widget.action_group.addAction(base_widget.get_action(action_name))

        base_widget.action_group.triggered.connect(lambda action: self._on_actions_triggered(action.text()))
        base_widget.set_action_checked(self.status, True)
        return base_widget

    def _on_actions_triggered(self, action_name: str):
        self.status = Status(action_name)

    def update_detectors_from_combo(self):
        if self._items is not None and self._items() is not None:
            self.selected = self._items().get_value()['selected']

    def clean_signals(self):
        for mod in self.get_selected_detectors():
            try:
                mod.grab_done_signal.disconnect(self.save_data)
            except TypeError as e:
                pass

    def get_selected_detectors(self) -> list[DAQ_Viewer]:
        return [self.modules_manager.get_mod_from_name(det, mod=ModuleType.Detector) for det in self.selected]

    def _execute(self, dte: DataToExport=None):
        self.filter_selected_wrt_manager()
        self.clean_signals()

        if len(self.selected) == 0:
            self.done_signal.emit()
        elif self.status == Status.STOP:
            for mod in self.get_selected_detectors():
                mod.stop()
            self.clean_signals()
            self.done_signal.emit()

        elif self.status == Status.SNAP:
            # trigger an async snap (but state holds until data has been acquired)
            self.modules_manager.selected_detectors_name = self.selected
            self.modules_manager.grab_data_with_callback(
                callback=self._data_snapped,
            )
        else:
            # trigger a grab and immediately move on to the next state!
            for mod in self.get_selected_detectors():
                mod.grab_done_signal.connect(self.save_data)  # without underscore to trigger whatever is necessary in
                # base class. You can do specific things in the _save_data reimplemented method
                mod.grab()
            self.done_signal.emit()

    def _data_snapped(self, dte: DataToExport):
        self.modules_manager.forget_callback(self._data_snapped,
                                             module_type=ModuleType.Detector,
                                             disconnect_modules=True)
        dte.name = dte[0].origin
        self.save_data(dte)
        self.done_signal.emit()

    def _save_data(self, dte: DataToExport):
        #todo: do whatever is needed with those data,
        # a log mechanism is already implemented within save_data (and the main Sequencer app)
        pass

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return {'detectors': self.detectors,
                'selected': self.selected,
                'status': self.status.value,}

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.detectors = dict_config.pop('detectors', [])
        self.selected = dict_config.pop('selected', [])
        self.status = Status(dict_config.pop('status', Status.SNAP.value))

    def _eq(self, other: 'GrabElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.detectors == other.detectors and
                self.selected == other.selected and
                self.status == other.status)

    def __repr__(self):
        return f"{super().__repr__()} - {self.selected} - {self.status}"

    def size_hint(self) -> QtCore.QSize:
        return QtCore.QSize(250, 250)

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        return None
