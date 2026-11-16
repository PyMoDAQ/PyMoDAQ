from typing import Any

from qtpy import QtCore

from pymodaq_data import DataToExport
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter.pymodaq_ptypes import GroupParameter, registerParameterType
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase
from pymodaq.extensions.sequencer.utilities.element_factory import ElementError


choice_factory = ChoiceModelFactory()


class ConditionsGroupParameter(GroupParameter):
    """ Group parameter holding the sub-conditions of a CompositeChoiceModel

    Displays an "Add condition" menu (populated with the available choice model names) and,
    when a menu entry is selected, emits `sigConditionAdded` so the owning CompositeChoiceModel
    (which alone knows how to instantiate the corresponding ChoiceModelBase) can do the real
    work of creating the sub-condition and its settings row.
    """
    sigConditionAdded = QtCore.Signal(str)

    def __init__(self, **opts):
        opts['type'] = 'composite_conditions'
        opts.setdefault('addText', 'Add condition')
        opts.setdefault('addMenu', [])
        super().__init__(**opts)

    def addNew(self, typ: tuple):
        self.sigConditionAdded.emit(typ[-1])


registerParameterType('composite_conditions', ConditionsGroupParameter, override=True)


@ChoiceModelFactory.register_choice()
class CompositeChoiceModel(ChoiceModelBase):
    """ Combine several sub-conditions (of any other registered choice model type) with a
    boolean operator (AND/OR/XOR) to produce a single True/False result.

    Each sub-condition is evaluated in sequence (not concurrently) and the individual booleans
    are reduced with the chosen operator: AND requires all of them True, OR requires at least
    one True, XOR is True when an odd number of them are True (the standard associative
    generalization of XOR to more than two operands).
    """
    model_name = 'composite'

    params = [
        {'title': 'Operator', 'name': 'operator', 'type': 'list',
         'limits': ['AND', 'OR', 'XOR'], 'value': 'AND',
         'tip': 'AND: true if all conditions are true. OR: true if at least one condition is '
                'true. XOR: true if an odd number of conditions are true.'},
        {'title': 'Conditions', 'name': 'conditions', 'type': 'composite_conditions'},
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._conditions: dict[str, ChoiceModelBase] = {}
        self._next_condition_ind = 0

        conditions_param: ConditionsGroupParameter = self.settings.child('conditions')
        conditions_param.setOpts(
            addMenu=[name for name in choice_factory.models if name != self.model_name])
        conditions_param.sigConditionAdded.connect(self.add_condition)
        conditions_param.sigChildRemoved.connect(self._on_condition_removed)

    def updated_module_manager(self):
        """ called whenever the parent modules manager is updated """
        for sub_model in self._conditions.values():
            sub_model.updated_module_manager()

    def add_condition(self, model_name: str, loaded_dict: dict[str, Any] = None):
        """ Add a new sub-condition of the given model_name, optionally restoring its state
        from a previously saved dict (as produced by `to_dict`, minus the 'model_name' key)
        """
        sub_model = choice_factory.get_model(model_name)(self.parent_elt)
        if loaded_dict is not None:
            sub_model.from_dict(dict(loaded_dict))

        row_name = f'condition_{self._next_condition_ind}'
        self._next_condition_ind += 1
        self._conditions[row_name] = sub_model

        # Reparent the sub-model's own settings group as-is (renamed/retitled) rather than
        # copying its children out, so the sub-model's own `self.settings[...]` accessors
        # (used in its evaluate/to_dict/from_dict/...) keep working unchanged.
        sub_model.settings.setName(row_name)
        sub_model.settings.setOpts(title=model_name, removable=True)
        self.settings.child('conditions').addChild(sub_model.settings)

    def _on_condition_removed(self, parent: Parameter, removed_row: Parameter):
        self._conditions.pop(removed_row.name(), None)

    def _condition_rows(self) -> list[Parameter]:
        return self.settings.child('conditions').children()

    def evaluate(self, dte: DataToExport) -> bool:
        results = [self._conditions[row.name()].evaluate(dte) for row in self._condition_rows()]
        if not results:
            return False
        operator = self.settings['operator']
        if operator == 'AND':
            return all(results)
        elif operator == 'OR':
            return any(results)
        else:  # XOR: true if an odd number of conditions are true
            return sum(results) % 2 == 1

    def check_set_is_valid(self):
        """ Check if the current settings of this model are valid """
        if len(self._condition_rows()) == 0:
            raise ElementError(
                f'Element {self.parent_elt} has a composite condition with no sub-condition')
        for row in self._condition_rows():
            self._conditions[row.name()].check_set_is_valid()

    def to_dict(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this model params
        """
        return {
            'operator': self.settings['operator'],
            'conditions': [
                {'model_name': self._conditions[row.name()].model_name,
                 **self._conditions[row.name()].to_dict()}
                for row in self._condition_rows()
            ],
        }

    def from_dict(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.settings['operator'] = dict_config.pop('operator')
        for condition_dict in dict_config.pop('conditions'):
            condition_dict = dict(condition_dict)
            model_name = condition_dict.pop('model_name')
            self.add_condition(model_name, loaded_dict=condition_dict)
