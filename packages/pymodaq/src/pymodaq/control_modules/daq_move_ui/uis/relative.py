from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory, DAQMoveUiBase


@ActuatorUIFactory.register('Relative')
class DAQMoveUIRelative(DAQMoveUiBase):
    def setup_docks_and_widgets(self):
        pass

    def setup_move_actions(self):
        self.ui_base.setup_relative_actions()

        self.ui_base.connect_action('move_rel_plus',
                                    lambda: self.ui_base.emit_move_rel('+'))
        self.ui_base.connect_action('move_rel_minus',
                                    lambda: self.ui_base.emit_move_rel('-'))

    def setup_action_visibility(self):
        self.ui_base.set_action_visible('show_controls', False)
        self.ui_base.set_action_visible('show_graph', False)
        self.ui_base.set_action_visible('refresh_value', False)
