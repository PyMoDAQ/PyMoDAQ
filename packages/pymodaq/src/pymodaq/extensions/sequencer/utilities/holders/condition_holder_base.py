from typing import Any, Optional, TYPE_CHECKING
import weakref

from qtpy import QtCore

from pymodaq_gui.managers.parameter_manager import ParameterTreeWidget
from pymodaq_gui.utils.widgets.combo import ComboBox

from pymodaq.extensions.sequencer.utilities.holders.modules_manager_binding import ModulesManagerBinding
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

if TYPE_CHECKING:
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase


class ConditionHolderBase:
    """ Shared machinery for "holds one pluggable model, picked via a combo + nested settings
    tree, with detector/actuator refresh delegated to ModulesManagerBinding" - used today by
    ConditionHolder (ChoiceModelBase/ChoiceModelFactory), and designed to be shared by a
    planned SwitchConditionHolder (SwitchModelBase/SwitchModelFactory) once that lands.

    Plain single inheritance, not a mixin, on purpose: a concrete subclass only needs to
    specialize `factory` and `dict_key` (SwitchConditionHolder's planned shape additionally
    overrides the `model` setter to wire up `outcomes_changed`) - ordinary inheritance, no
    cooperative super() across siblings, not the kind of multiple inheritance that caused the
    ordering bugs the mixin version of this code had (see git history).
    """

    #: the ChoiceModelFactory/SwitchModelFactory instance to pick registered models from
    factory = None
    #: the key this condition's chosen model name is saved under in to_dict/from_dict
    dict_key: str = None
    #: model_name a brand new instance resolves its lazy default to. None falls back to
    #: factory.models[0] (whichever model happened to be discovered/registered first) - leave
    #: unset only when that's harmless (e.g. ConditionHolder's true/false are both trivial);
    #: set explicitly whenever the default actually matters (see SwitchConditionHolder).
    default_model_name: str = None

    def __init__(self, elt: 'SeqEltBase', combo_tooltip: Optional[str] = None):
        self.elt = elt
        self.combo_tooltip = combo_tooltip
        self.modules_binding = ModulesManagerBinding.attach(elt, on_refresh=self._on_modules_refreshed)
        self._model = None

    def bind_to_dashboard(self):
        self.modules_binding.bind()

    def _on_modules_refreshed(self):
        if self._model is not None:
            self.model.updated_module_manager()

    @property
    def model(self):
        if self._model is None:
            self.model = self.default_model_name or self.factory.models[0]
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = self.factory.get_model(value)(self.elt)

    def set_model(self, value: str):
        self.model = value

    def create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        combo = ComboBox()
        with QtCore.QSignalBlocker(combo):
            combo.addItems(self.factory.models)
            combo.setCurrentText(self.model.model_name)
            combo.currentTextChanged.connect(self.set_model)
            if self.combo_tooltip:
                combo.setToolTip(self.combo_tooltip)
        base_widget.insert_widget(combo, 1)

        parameter_tree = ParameterTreeWidget()
        parameter_tree.tree.setParameters(self.model.settings, showTop=False)
        self._param_tree_widget = weakref.ref(parameter_tree)
        parameter_tree.tree.setMinimumHeight(len(self.model.settings.children()) * 50)
        combo.currentTextChanged.connect(lambda: self._update_params(parameter_tree))
        base_widget.insert_widget(parameter_tree.widget, 2)
        base_widget.tree = parameter_tree
        parameter_tree.widget.setVisible(len(self.model.params) != 0)
        return base_widget

    def _update_params(self, param: ParameterTreeWidget):
        param.widget.setVisible(len(self.model.params) != 0)
        param.tree.setParameters(self.model.settings, showTop=False)
        param.tree.setMinimumHeight(len(self.model.settings.children()) * 50)

    def to_dict(self) -> dict[str, Any]:
        dict_config = {self.dict_key: self.model.model_name}
        dict_config.update(self.model.to_dict())
        return dict_config

    def from_dict(self, dict_config: dict[str, Any]):
        self.model = dict_config.pop(self.dict_key)
        self.model.from_dict(dict_config)

    def eq(self, other: 'ConditionHolderBase') -> bool:
        # The model's own __eq__ only compares to_dict(), which is identically {} for
        # parameter-less models (true/false) - check model_name too, or two different model
        # types would spuriously compare equal.
        return (self.model.model_name == other.model.model_name and
                self.model == other.model)

    def check_set_is_valid(self):
        self.model.check_set_is_valid()
