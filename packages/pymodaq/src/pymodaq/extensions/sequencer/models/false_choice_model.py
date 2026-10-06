from pymodaq_data import DataToExport
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase


@ChoiceModelFactory.register_choice()
class FalseChoiceModel(ChoiceModelBase):
    model_name = 'false'

    params = []

    def execute(self, dte: DataToExport):
        self.parent_elt.go_to_signal.emit(False)
