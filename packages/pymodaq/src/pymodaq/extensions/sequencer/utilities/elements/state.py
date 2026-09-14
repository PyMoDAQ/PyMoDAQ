from typing import Any
import weakref


from qtpy import QtCore
from qt_themes import get_theme
from serializall import SerializableFactory

from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_data import DataToExport
from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq_gui.managers.manager_base import ManagerActions
from pymodaq_gui.utils.widgets.combo import ComboBox

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()
logger = set_logger(get_module_name(__file__))

@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class StateElt(SeqEltBase):

    elt_name = 'state'
    children_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state_manager = StateManager()

        self._state: str = self.state_manager.entry
        self._states: list[str] = self.state_manager.entries
        self._experiment: str = self.state_manager.experiment_filename

        self._combo: weakref.ref[ComboBox] | None = None  # weakref to the combobox holding the states

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str):
        self._state = value

    @property
    def experiment(self) -> str:
        return self._experiment

    @experiment.setter
    def experiment(self, value: str):
        self._experiment = value

    @property
    def states(self) -> list[str]:
        return self._states

    @states.setter
    def states(self, values: list[str]):
        self._states = values
        self.update_combo_states()

    def set_states(self, values: list[str]):
        self.states = values

    def update_combo_states(self):
        if self._combo is not None and self._combo() is not None:
            self._combo().set_items(self.states)

    @QtCore.Slot(str)
    def set_state(self, value: str):
        self.state = value

    def do_things_with_dashboard(self):
        self.state_manager: 'StateManager' = self.dashboard.state_manager
        self.state_manager.applied_entry.connect(
            lambda: self.done_signal.emit())
        self.state_manager.new_entry.connect(self.set_states)
        self.update_states()

    def update_states(self):
        self.states = self.state_manager.entries
        self.experiment = self.state_manager.experiment_filename
        self.filter_state_wrt_manager()

    def filter_state_wrt_manager(self):
        """  Filter selected given the presence of the detector in the manager """
        if self.state not in self.state_manager.entries:
            self.state = 'default'
            logger.warning(f'Could not select this state: {self.state} as not declared in '
                               f'the StateManager instance of the DashBoard')

    def _create_widget(self, base_widget:WidgetWithToolbar) -> WidgetWithToolbar:

        self.add_action('show_state', 'Show Manager', self.state_manager.icon_name,
                        "Show State Manager",
                        checkable=True, icon_checked_color=get_theme().green,
                        toolbar=base_widget.toolbar)
        self.connect_action('show_state', self.state_manager.force_show)
        combo = ComboBox(base_widget)
        combo.set_items(self.state_manager.entries)
        base_widget.add_widget_top(combo)
        combo.setCurrentText(self.state)
        combo.currentTextChanged.connect(self.set_state)
        self._combo = weakref.ref(combo)
        self.state_manager.parent.closeEvent = lambda event: self.set_action_checked('show_state', False)

        return base_widget

    def _execute(self, dte: DataToExport):
        self.state_manager.entry = self.state
        self.state_manager.execute_entry()

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        return {'state': self.state,
                'experiment': self.experiment,
                'states': self.states,}

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.experiment = dict_config.pop('experiment')
        self.states = dict_config.pop('states')
        self.state = dict_config.pop('state')

    def _eq(self, other: 'StateElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return (self.state_manager.entry == other.state_manager.entry and
                self.state_manager.experiment_filename == other.state_manager.experiment_filename)

    def __repr__(self):
        return f'{super().__repr__()} - {self.state}'

    def size_hint(self) -> QtCore.QSize:
        size = super().size_hint()
        return QtCore.QSize(250, size.height())

    def check_set_is_valid(self) -> bool:
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        if not self.dashboard.experiment_manager.entry_applied:
            raise ElementError('No Experiment has been applied in the DashBoard')

        if self.state not in self.state_manager.entries:
            raise ElementError(
                f'Error with element {self}: State {self.state} not available for the current experiment')
