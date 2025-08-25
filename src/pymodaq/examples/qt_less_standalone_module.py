"""
Example how to create an actuator or detector module, which does not require Qt, nor any GUI functionality.

You can connect to this qtless module with a PyMoDAQ LECODirector module (the detector or actuator version, both are preinstalled),
as if it were any pymodaq module.

This example works best with an Actuator Director Module as it has fake movements, but does not return any detector value.
In this example, the name is "qt_less" (defined in the final if clause), which you have to give as the "actor" argument to the Director module.

Add any code in the methods defined below, for example instrument access and execute the file.
For remote control, you need to start a Coordinator, as described for remote control via LECO.
"""

import logging
from time import sleep
from typing import List, Union

from pyleco.utils.listener import Listener


class QtLessModule:
    """Some module doing things without Qt.
    
    You can run an instance of this class anywhere in your LECO network.
    Then you can control this instance with a PyMoDAQ LECODirectorModule (in mock modules) as if it were a PyMoDAQ module.

    Just add any logic you wish to the methods below.
    """

    def __init__(self, name: str, host: str = "localhost", **kwargs) -> None:
        super().__init__()
        self.listener = Listener(name=name, host=host, timeout=1, **kwargs)
        self._fake_position = 0
        self.start_listen()
        self._stored = []

    def start_listen(self) -> None:
        """Start to listen on incoming commands."""
        self.listener.start_listen()
        self.communicator = self.listener.get_communicator()
        self.register_rpc_methods()

    def register_rpc_methods(self) -> None:
        """Make the following methods available via LECO."""
        register_rpc_method = self.communicator.register_rpc_method
        register_rpc_method(self.set_info)
        register_rpc_method(self.send_data)
        register_rpc_method(self.move_abs)
        register_rpc_method(self.move_rel)
        register_rpc_method(self.move_home)
        register_rpc_method(self.get_actuator_value)
        register_rpc_method(self.stop_motion)
        register_rpc_method(self.set_remote_name)

    def stop_listen(self) -> None:
        """Stop to listen on incoming commands."""
        self.listener.stop_listen()

    # smethods for being remote controlled
    # these methods are executed and cannot talk to the controlling module directly.
    # if you need to send a response (for example with a value) you have to store the information and
    # send it after these methods have been executed.
    def set_remote_name(self, name: str) -> None:
        """Define what the name of the remote for answers is."""
        self.remote_name = name

    # generic commands
    def set_info(self, path: List[str], param_dict_str: str) -> None:
        print("set_info", path, param_dict_str)

    # detector commands
    def send_data(self, grabber_type: str = "") -> None:
        print("send_data")

    # actuator commands
    def move_abs(self, position: Union[float, str]) -> None:
        print("move_abs", position)
        self._fake_position = float(position)

    def move_rel(self, position: Union[float, str]) -> None:
        print("move_rel", position)
        self._fake_position += float(position)

    def move_home(self) -> None:
        self._fake_position = 0
        print("move_home")

    def get_actuator_value(self) -> None:
        """Request that the actuator value is sent later on."""
        # according to DAQ_Move, this supersedes "check_position"
        print("get_actuator_value")
        # send the actuator position after this method has finished execution.
        # this method sends the result to the controlling control module.
        self.send_later(
            receiver=self.remote_name,
            method="set_position",
            position=self._fake_position,
        )

    def stop_motion(self,) -> None:
        # not implemented in DAQ_Move!
        print("stop_motion")

    # end of methods for being remote controlled

    def send_later(self, receiver, method, **kwargs):
        """Store information to send it later."""
        self._stored.append((receiver, method, kwargs))

    def send_stored(self):
        """Send messages stored for later sending."""
        while self._stored:
            receiver, method, kwargs = self._stored.pop()
            self.communicator.ask_rpc(receiver=receiver, method=method, **kwargs)


if __name__ == "__main__":
    print("listening endlessly as 'qt_less'")
    log = logging.getLogger()
    log.addHandler(logging.StreamHandler())
    # log.setLevel(logging.DEBUG)
    m = QtLessModule("qt_less")
    try:
        while True:
            sleep(0.1)
            m.send_stored()
    except KeyboardInterrupt:
        m.stop_listen()
