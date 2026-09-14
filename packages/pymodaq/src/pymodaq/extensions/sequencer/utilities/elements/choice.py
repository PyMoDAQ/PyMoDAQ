from typing import TYPE_CHECKING, Any
import numpy as np
import weakref

from pymodaq_gui.parameter.utils import ParameterWithPath, Parameter
from pyqtgraph import mkColor

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory


from pymodaq_data import DataToExport, DataWithAxes, DataRaw
from pymodaq_gui.managers.parameter_manager import ParameterManager, ParameterTreeWidget
from pymodaq_gui.utils.widgets import SpinBox

from qt_themes import get_theme
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_gui.utils.widgets.combo import ComboBox
from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.states import ValueTransition
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar


ser_factory = SerializableFactory()
choice_factory = ChoiceModelFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class ChoiceElt(SeqEltBase):

    elt_name = 'choice'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.modules_manager = ModulesManager()

        self._choice_model: ChoiceModelBase = None

        self._go_to_true: int = 1
        self._go_to_false: int = 2

        self.value_true_transition = ValueTransition(
            self.go_to_signal, True,
            source_state=self.mstate,
            )

        self.value_false_transition = ValueTransition(
            self.go_to_signal, False, self.mstate)

        self.mstate.addTransition(self.value_true_transition)
        self.mstate.addTransition(self.value_false_transition)

    def do_things_with_dashboard(self):
        self.dashboard.experiment_manager.applied_entry.connect(self.update_modules)
        self.update_modules()

    def update_modules(self):
        self.modules_manager.detectors_all = self.dashboard.modules_manager.detectors_all
        self.modules_manager.selected_detectors_name = [det.title for det in  self.dashboard.modules_manager.detectors_all]
        self.modules_manager.actuators_all = self.dashboard.modules_manager.actuators_all
        self.modules_manager.selected_actuators_name = [act.title for act in self.dashboard.modules_manager.actuators_all]
        self.choice_model.updated_module_manager()

    @property
    def choice_model(self) -> ChoiceModelBase:
        if self._choice_model is None:
            self.choice_model = choice_factory.models[0]
        return self._choice_model

    @choice_model.setter
    def choice_model(self, value: str):
        self._choice_model = choice_factory.get_model(value)(self)

    @QtCore.Slot(str)
    def set_choice_model(self, value: str):
        self.choice_model = value

    @property
    def go_to_true(self) -> int:
        return self._go_to_true

    @go_to_true.setter
    def go_to_true(self, value: int):
        self._go_to_true = value
        target_elt = self.get_elt_from_id(value)
        if target_elt is not None:
            self.value_true_transition.update_target(target_elt.mstate)

    @QtCore.Slot(int)
    def set_go_to_true(self, value: int):
        """ set go_true given the value which is the index of the get_ids or self.get_elts_as_str
        return lists
        """
        id = self.get_ids(without_ids=self.without_ids,
                          without_types=self.without_types)[value]
        self.go_to_true = id

    @property
    def without_ids(self):
        return (self.id, )

    @property
    def without_types(self):
        return (AddButtonPlaceholder, )

    @property
    def go_to_false(self) -> int:
        return self._go_to_false

    @go_to_false.setter
    def go_to_false(self, value: int):
        self._go_to_false = value
        target_elt = self.get_elt_from_id(value)
        if target_elt is not None:
            self.value_false_transition.update_target(target_elt.mstate)

    def set_go_to_false(self, value: int):
        id = self.get_ids(without_ids=self.without_ids,
                          without_types=self.without_types)[value]
        self.go_to_false = id

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        combo_true = ComboBox()
        with QtCore.QSignalBlocker(combo_true):
            combo_true.addItems(self.get_elts_as_str(without_ids=self.without_ids,
                                                     without_types=self.without_types))
            combo_true.setCurrentText(str(self.get_elt_from_id(self.go_to_true)))
            combo_true.setStyleSheet(
                f"""background-color: #{hex(mkColor(get_theme().green).rgb())[2:]};
                    color: #{hex(mkColor(get_theme().base).rgb())[2:]};
                """)
            combo_true.currentIndexChanged.connect(self.set_go_to_true)
            combo_true.setToolTip('Go to this elt if True')
        base_widget.add_widget_top(combo_true)

        combo_false = ComboBox()
        with QtCore.QSignalBlocker(combo_false):
            combo_false.addItems(self.get_elts_as_str(without_ids=self.without_ids,
                                                      without_types=self.without_types))
            combo_false.setCurrentText(str(self.get_elt_from_id(self.go_to_false)))
            combo_false.setStyleSheet(
                f"""background-color: #{hex(mkColor(get_theme().red).rgb())[2:]};
                    color: #{hex(mkColor(get_theme().base).rgb())[2:]};
                """)
            combo_false.currentIndexChanged.connect(self.set_go_to_false)
            combo_false.setToolTip('Go to this elt if False')
        base_widget.add_widget_top(combo_false)

        combo = ComboBox()
        with QtCore.QSignalBlocker(combo_false):
            combo.addItems(choice_factory.models)
            combo.setCurrentText(self.choice_model.model_name)
            combo.currentTextChanged.connect(self.set_choice_model)

            combo.setToolTip('Choice Model')
        base_widget.insert_widget(combo, 1)


        parameter_tree = ParameterTreeWidget()
        parameter_tree.tree.setParameters(self.choice_model.settings, showTop=False)
        self.param_tree_widget = weakref.ref(parameter_tree)
        parameter_tree.tree.setMinimumHeight(len(self.choice_model.settings.children()) * 50)
        combo.currentTextChanged.connect(lambda: self.update_params(parameter_tree))
        base_widget.insert_widget(parameter_tree.widget, 2)
        base_widget.tree = parameter_tree
        parameter_tree.widget.setVisible(len(self.choice_model.params) != 0)
        return base_widget

    def update_params(self, param: ParameterTreeWidget):
        param.widget.setVisible(len(self.choice_model.params) != 0)
        param.tree.setParameters(self.choice_model.settings, showTop=False)
        param.tree.setMinimumHeight(len(self.choice_model.settings.children()) * 50)

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        dict_config =  {'go_to_true': self.go_to_true,
                        'go_to_false': self.go_to_false,
                        'choice_model': self.choice_model.model_name}
        dict_config.update(self.choice_model.to_dict())
        return dict_config

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.go_to_true = dict_config.pop('go_to_true')
        self.go_to_false = dict_config.pop('go_to_false')
        self.choice_model = dict_config.pop('choice_model')
        self.choice_model.from_dict(dict_config)

    def _eq(self, other: 'ChoiceElt') -> bool:
        """ Custom method to reimplement to assert two elements are equals"""
        if not (hasattr(other, 'go_to_true') or hasattr(other, 'go_to_false')):
            return False
        if not (self.go_to_false == other.go_to_false and
                self.go_to_true == other.go_to_true and
                self.choice_model.model_name == other.choice_model.model_name):
            return False
        return self.choice_model.__eq__(other.choice_model)

    def __repr__(self):
        return f'{super().__repr__()} - Model: {self.choice_model.model_name} - True: {self.go_to_true} - False: {self.go_to_false}'

    def update_target_states(self):
        if self.value_false_transition.targetState() is None:
            self.value_false_transition.setTargetState(self.get_elt_from_id(self.go_to_false).mstate)
        if self.value_true_transition.targetState() is None:
            self.value_true_transition.setTargetState(self.get_elt_from_id(self.go_to_true).mstate)

    def _execute(self, dte: DataToExport=None):
        self.choice_model.execute(dte)


    def check_set_is_valid(self) -> bool:
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!
        """
        self.update_target_states()
        if self.value_false_transition.targetState() is None:
            raise ElementError(f'Element {self} has no existing False value target state')
        if self.value_true_transition.targetState() is None:
            raise ElementError(f'Element {self} has no existing True value target state')
        self.choice_model.check_set_is_valid()

