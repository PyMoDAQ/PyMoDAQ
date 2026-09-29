import dataclasses

import weakref
from typing import Any

from serializall import SerializableFactory

from qtpy import QtCore, QtWidgets

from pymodaq.control_modules.enums import MoveType
from pymodaq.control_modules.units import get_unit_to_display
from pymodaq.utils.data import DataActuator
from pymodaq.utils.managers.modules import ModuleType
from pymodaq.utils.scanner.scanner import Orientation
from pymodaq_data import DataToExport, Q_
from pymodaq_gui.parameter.pymodaq_ptypes import GroupParameter, registerParameterType
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError

from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from qt_themes import get_theme

from pymodaq_utils.categorizing import categorize_items, find_last_index

ser_factory = SerializableFactory()


class ActuatorScalableParameter(GroupParameter):
    """
    """

    def __init__(self, **opts):
        opts['type'] = 'act_move'
        opts['addText'] = 'Add'

        opts['addMenu'] = categorize_items(opts['actuators'])
        super().__init__(**opts)

    def addNew(self, typ: tuple):
        """
        """

        typ = typ[-1]  # Only need last entry here
        if typ in [child.name() for child in self.children()]:
            return
        child = {'title': f'{typ}',
                 'name': f'{typ}',
                 'type': 'float',
                 'removable': True,
                 }
        self.addChild(child)

registerParameterType('act_move_elt', ActuatorScalableParameter, override=True)

@dataclasses.dataclass
class ValueUnits:
    value: float
    units: str

    def __repr__(self):
        return f'{self.value} {self.units}'


class ActuatorsValuesUnits:

    def __init__(self):
        self._actuators: dict[str, ValueUnits] = {}

    def __len__(self):
        return len(self._actuators)

    def add_update_actuator(self, act_name: str, value: float, units: str):
        self._actuators[act_name] = ValueUnits(value=value, units=units)

    def get_value_units(self, act_name: str) -> ValueUnits:
        return self._actuators[act_name]

    @property
    def actuators(self) -> list[str]:
        return list(self._actuators.keys())

    def __repr__(self):
        repr = ''
        for act_name in self._actuators:
            repr += f'{act_name}: {self._actuators[act_name]} / '
        return repr

    def to_dict(self) -> dict[str, str]:
        return {act_name: (f'{self.get_value_units(act_name).value} '
                           f'{self.get_value_units(act_name).units}') for act_name in self._actuators}


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class MoveElt(SeqEltBase):

    elt_name = 'move'
    children_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wait_move_done = True
        self._actuator_and_value = ActuatorsValuesUnits()


    def initialize_element(self):
        pass

    def set_wait_move_done(self, not_wait=True):
        self._wait_move_done = not not_wait

    def do_things_with_dashboard(self):
        pass

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:

        base_widget.settings = Parameter.create(name='settings',
                                                type='act_move_elt',
                                                actuators=self.dashboard.modules_manager.actuators_name)
        for act_name in self._actuator_and_value.actuators:
            base_widget.settings.addNew((act_name,))
            base_widget.settings.child(act_name).setValue(
                self._actuator_and_value.get_value_units(act_name).value)
            base_widget.settings.child(act_name).setOpts(
                suffix=self._actuator_and_value.get_value_units(act_name).units)
        base_widget.settings.sigTreeStateChanged.connect(self._on_tree_changed)
        base_widget.settings_tree = ParameterTree()
        base_widget.settings_tree.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Interactive,
        )
        base_widget.settings_tree.resizeColumnToContents(0)
        base_widget.settings_tree.setParameters(base_widget.settings, showTop=False)
        base_widget.insert_widget(base_widget.settings_tree)

        base_widget.add_action('wait_move_done', 'WaitForMoveDone',
                               icon_name='hourglass',
                               icon_color=get_theme().green,
                               icon_checked='hourglass_disabled',
                               icon_checked_color=get_theme().red,
                               checkable=True,
                               checked=not self._wait_move_done)
        base_widget.connect_action('wait_move_done', self.set_wait_move_done)

        if (base_widget.parent() is not None and
            hasattr(base_widget.parent(), 'popup_hiding')):
            base_widget.parent().popup_hiding.connect(self._on_editor_closing)

        return base_widget

    def _on_tree_changed(self, param_parent, changes):
        for param, change, data in changes:
            path = param_parent.childPath(param)
            if change == "childAdded":
                child: Parameter = data[0]
                actuator = self.dashboard.modules_manager.get_mod_from_name(child.name(), mod=ModuleType.Actuator)
                child.setOpts(suffix=get_unit_to_display(actuator.units))
                self._actuator_and_value.add_update_actuator(child.name(),
                                                             child.value(),
                                                             get_unit_to_display(actuator.units),)

            elif change == "value":
                self._actuator_and_value.add_update_actuator(
                    param.name(), data, param.opts['suffix'])

            elif change == "parent":
                pass

            elif change == "options":
                pass

            elif change == "limits":
                pass

            elif change == 'contextMenu':
                pass

    def _on_editor_closing(self):
        pass

    def _execute(self, dte: DataToExport=None):
        """ Move the Actuators to their value and wait or not depending on the
        wait_move_done boolean"""
        dte_move = DataToExport('actuators', data=[
            DataActuator(
                act_name,
                data=self._actuator_and_value.get_value_units(act_name).value,
                units=self._actuator_and_value.get_value_units(act_name).units
            ) for act_name in self._actuator_and_value.actuators
            if act_name in self.dashboard.modules_manager.actuators_name
        ])
        self.dashboard.modules_manager.move_actuators_with_callback(
            dte_move,
            mode=MoveType.ABS,
            callback=self._on_move_done,
            do_connect_modules=True)
        if not self._wait_move_done:
            self.done_signal.emit()

    def _on_move_done(self, dte: DataToExport):
        self.dashboard.modules_manager.forget_callback(
            self._on_move_done,
            module_type=ModuleType.Actuator,
            disconnect_modules=True)

        self.save_data(dte) # to log the data
        if self._wait_move_done:
            self.done_signal.emit()

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        move_dict = self._actuator_and_value.to_dict()
        move_dict['wait_move_done'] = self._wait_move_done
        return move_dict

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self._wait_move_done = dict_config.pop('wait_move_done', True)
        for act_name in dict_config:
            quantity = Q_(dict_config[act_name])
            self._actuator_and_value.add_update_actuator(act_name, quantity.magnitude, quantity.units)

    def _eq(self, other: 'MoveElt'):
        """ Custom method to reimplement to assert two elements are equals"""
        return self.to_dict() == other.to_dict()

    def __repr__(self):
        return f"{super().__repr__()} - {self._actuator_and_value}"

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or raise ElementError
        if the user may do something!
        """
        for act_name in self._actuator_and_value.actuators:
            if act_name not in self.dashboard.modules_manager.actuators_name:
                raise ElementError(f'Actuator {act_name} not available in Dashboard')

    def size_hint(self) -> QtCore.QSize:
        return QtCore.QSize(200, 150 + 35 * len(self._actuator_and_value))
