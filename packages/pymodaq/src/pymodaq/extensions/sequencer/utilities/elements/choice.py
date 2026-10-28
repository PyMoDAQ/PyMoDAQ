from typing import Any, Union

from serializall import SerializableFactory

from pymodaq_utils.warnings import deprecation_msg

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, SeqEltCategory
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.elements.switch import SwitchElt
from pymodaq.extensions.sequencer.utilities.holders.rule import Rule


ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class ChoiceElt(SwitchElt):
    """ Branches to one of two other elements (by id, anywhere in the tree) based on a
    pluggable condition.

    The permanently-locked 2-Rule case of SwitchElt's general Rule list: exactly one
    pluggable-condition Rule (go_to_true/choice_model) plus the mandatory fallback
    (go_to_false, since the fallback is the only other thing that can ever fire once the
    condition Rule doesn't match) - no add/remove-Rule UI or API. go_to_true/go_to_false/
    choice_model stay as plain properties over those two rules' storage, so this class's
    public shape and saved-sequence format (go_to_true/go_to_false/choice_model, flat, no
    rules/fallback nesting) are completely unaffected by the SwitchElt redesign.
    """

    elt_name = 'choice'
    elt_category = SeqEltCategory.LOGIC
    rules_locked = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._condition_rule = self._insert_rule()
        self._condition_rule.label = 'True'
        self._fallback.label = 'False'

    def _rule_title(self, rule: Rule, display_index: Union[int, None] = None) -> str:
        return rule.label  # 'True' / 'False'

    @property
    def condition(self):
        return self._condition_rule.condition

    @property
    def choice_model(self):
        return self._condition_rule.condition.model

    @choice_model.setter
    def choice_model(self, value: str):
        self._condition_rule.condition.model = value

    def set_choice_model(self, value: str):
        """ Deprecated: set `choice_model` directly instead. """
        deprecation_msg('ChoiceElt.set_choice_model is deprecated, set choice_model directly')
        self.choice_model = value

    @property
    def go_to_true(self) -> int | str:
        return self._condition_rule.go_to

    @go_to_true.setter
    def go_to_true(self, value: int | str):
        self._condition_rule.go_to = value

    def set_go_to_true(self, index: int):
        """ Deprecated: set `go_to_true` directly with an element id instead. `index` here is
        an index into `get_ids(without_ids=self.without_ids, without_types=self.without_types)`,
        not an id. """
        deprecation_msg('ChoiceElt.set_go_to_true is deprecated, set go_to_true directly with an element id')
        self.go_to_true = self.get_ids(without_ids=(self.id,), without_types=(AddButtonPlaceholder,))[index]

    @property
    def go_to_false(self) -> int | str:
        return self._fallback.go_to

    @go_to_false.setter
    def go_to_false(self, value: int | str):
        self._fallback.go_to = value

    def set_go_to_false(self, index: int):
        """ Deprecated: set `go_to_false` directly with an element id instead. `index` here is
        an index into `get_ids(without_ids=self.without_ids, without_types=self.without_types)`,
        not an id. """
        deprecation_msg('ChoiceElt.set_go_to_false is deprecated, set go_to_false directly with an element id')
        self.go_to_false = self.get_ids(without_ids=(self.id,), without_types=(AddButtonPlaceholder,))[index]

    @property
    def without_ids(self):
        """ Deprecated: was only ever used to build set_go_to_true/set_go_to_false's index. """
        deprecation_msg('ChoiceElt.without_ids is deprecated')
        return (self.id,)

    @property
    def without_types(self):
        """ Deprecated: was only ever used to build set_go_to_true/set_go_to_false's index. """
        deprecation_msg('ChoiceElt.without_types is deprecated')
        return (AddButtonPlaceholder,)

    def to_dict_custom(self) -> dict[str, Any]:
        dict_config = {'go_to_true': self.go_to_true,
                       'go_to_false': self.go_to_false}
        dict_config.update(self.condition.to_dict())
        return dict_config

    def from_dict_custom(self, dict_config: dict[str, Any]):
        self.go_to_true = dict_config.pop('go_to_true')
        self.go_to_false = dict_config.pop('go_to_false')
        self.condition.from_dict(dict_config)

    def __repr__(self):
        return (f'{self.id} - {self.elt_name.capitalize()} - Model: {self.choice_model.model_name} '
               f'- True: {self.go_to_true} - False: {self.go_to_false}')
