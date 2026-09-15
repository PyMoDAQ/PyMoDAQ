from qtpy import QtWidgets
from pymodaq_data import DataToExport
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase


@ChoiceModelFactory.register_choice()
class UserInput(ChoiceModelBase):
    model_name = 'user_input'

    params = []

    def execute(self, dte: DataToExport):

        msgBox = QtWidgets.QMessageBox()
        msgBox.setText("Previous steps are finished")
        msgBox.setInformativeText("Are you ok to proceed or go back?")
        button_proceed = msgBox.addButton('Proceed', QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        button_goback = msgBox.addButton('Go back', QtWidgets.QMessageBox.ButtonRole.RejectRole)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
        msgBox.exec()

        self.parent_elt.go_to_signal.emit(msgBox.clickedButton() == button_proceed)
