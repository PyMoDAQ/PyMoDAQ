
from qtpy import QtWidgets


from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory, DAQMoveUiBase
from pymodaq_utils.config import GlobalConfig as Config


config = Config()

@ActuatorUIFactory.register('Binary')
class DAQMoveUISimple(DAQMoveUiBase):

    def setup_docks_and_widgets(self):
        pass

    def setup_move_actions(self):
        self.ui_base.setup_absolute_actions()

    def setup_action_visibility(self):
        self.ui_base.set_action_visible('show_controls', True)
        self.ui_base.set_action_visible('show_graph', True)
        self.ui_base.set_action_visible('refresh_value', True)