from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_move.utility_classes import DAQ_Move_base, comon_parameters_fun
from easydict import EasyDict as edict


class DAQ_Move_PID(DAQ_Move_base):
    """
    """
    _controller_units = 'whatever'
    is_multiaxes = True
    stage_names = []

    params = comon_parameters_fun(is_multiaxes, stage_names, master=False)

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)


    def update_position(self, dict_val):
        self.current_position = dict_val[self.parent.title]

    def check_position(self):
        self.controller['emit_curr_points'].emit()
        pos = self.current_position
        #
        # pos = self.get_position_with_scaling(pos)
        # self.current_position = pos
        self.emit_status(ThreadCommand('check_position', [pos]))
        return pos

    def close(self):
        pass

    def commit_settings(self, param):
        pass

    def ini_stage(self, controller=None):
        """
        """
        try:
            self.status.update(edict(info="", controller=None, initialized=False))
            if self.settings.child('multiaxes', 'ismultiaxes').value() and self.settings.child('multiaxes',
                                                                         'multi_status').value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller = controller
            else:  # Master stage
                self.controller = None  # any object that will control the stages

            self.controller['curr_point'].connect(self.update_position)

            info = "PID stage"
            self.status.info = info
            self.status.controller = self.controller
            self.status.initialized = True
            return self.status

        except Exception as e:
            self.status.info = str(e)
            self.status.initialized = False
            return self.status

    def move_Abs(self, position):
        """
        """
        position = self.check_bound(position)
        # position=self.set_position_with_scaling(position)
        # print(position)
        self.target_position = position

        self.controller['setpoint'].emit({self.parent.title: self.target_position})
        self.poll_moving()

    def move_Rel(self, position):
        """
        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position

        self.controller['setpoint'].emit({self.parent.title: self.target_position})
        self.poll_moving()

    def move_Home(self):
        """
        """
        self.emit_status(ThreadCommand('Update_Status', ['Move Home not implemented']))

    def stop_motion(self):
        """
          Call the specific move_done function (depending on the hardware).

          See Also
          --------
          move_done
        """
        self.move_done()
