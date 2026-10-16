from pymodaq_data import DataToExport
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase


@ChoiceModelFactory.register_choice()
class TrueChoiceModel(ChoiceModelBase):
    model_name = 'true'

    params = []

    def evaluate(self, dte: DataToExport) -> bool:
        return True