from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.holders.condition_holder_base import ConditionHolderBase


choice_factory = ChoiceModelFactory()


class ConditionHolder(ConditionHolderBase):
    """ Holds one pluggable ChoiceModel (true/false/threshold/user_input/composite) - the
    ChoiceModelBase/ChoiceModelFactory specialization of ConditionHolderBase. Shared by
    ChoiceElt and WhileElt: `self.condition = ConditionHolder(self, combo_tooltip=...)`.
    """
    factory = choice_factory
    dict_key = 'choice_model'
    # Explicit, rather than leaving it to fall back to factory.models[0] (whichever
    # choice_models/*.py file pkgutil happens to import first, alphabetically). That's not
    # hypothetical: adding composite_choice_model.py made 'composite' sort before 'false',
    # silently flipping every new ChoiceElt's default from the trivial 'false' to the much
    # heavier composite model - see ConditionHolderBase.default_model_name.
    default_model_name = 'false'
