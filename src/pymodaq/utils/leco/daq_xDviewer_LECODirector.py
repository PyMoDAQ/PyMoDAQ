from __future__ import annotations
from typing import Optional, Union

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.control_modules.thread_commands import ThreadStatus, ThreadStatusViewer
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq_data import DataToExport
from pymodaq_utils.serialize.factory import SerializableFactory
from pymodaq_utils.utils import ThreadCommand, getLineInfo

from pymodaq.utils import data  # for serialization factory registration  # noqa: F401
from pymodaq_gui.parameter import Parameter

from pymodaq.utils.leco.leco_director import LECODirector, leco_parameters
from pymodaq.utils.leco.director_utils import DetectorDirector
from pymodaq_utils.logger import set_logger, get_module_name

import numpy as np

logger = set_logger(get_module_name(__file__))


class DAQ_xDViewer_LECODirector(LECODirector, DAQ_Viewer_base):
    """A control module, which in the dashboard, allows to control a remote Viewer module.

    This is the base class for the viewer LECO director modules.
    """

    settings: Parameter
    controller: DetectorDirector

    params_GRABBER = []

    socket_types = ["GRABBER"]
    params = comon_parameters + leco_parameters
    live_mode_available = True

    def __init__(
        self,
        parent=None,
        params_state=None,
        grabber_type: str = "0D",
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs,
    ) -> None:
        DAQ_Viewer_base.__init__(self, parent=parent, params_state=params_state)
        if host is not None:
            self.settings["host"] = host
        if port is not None:
            self.settings["port"] = port
        LECODirector.__init__(self, host=self.settings["host"], port=self.settings["port"])

        self.register_binary_rpc_methods((self.set_data,))

        self.client_type = "GRABBER"
        self.x_axis = None
        self.y_axis = None
        self.data = None
        self.grabber_type = grabber_type
        self.ind_data = 0
        self.data_mock = None
        self.start_timer()

    def ini_detector(self, controller=None):
        """
            | Initialisation procedure of the detector updating the status dictionary.
            |
            | Init axes from image , here returns only None values (to tricky to di it with the
              server and not really necessary for images anyway)

            See Also
            --------
            utility_classes.DAQ_TCP_server.init_server, get_xaxis, get_yaxis
        """

        actor_name = self.settings["actor_name"]
        if self.is_master:
            self.controller = DetectorDirector(actor=actor_name,
                                               communicator=self.communicator)
            try:
                self.controller.set_remote_name(self.communicator.full_name)
            except TimeoutError:
                logger.warning("Timeout setting remote name.")
        else:
            self.controller = controller

        self.controller.get_settings()

        initialized = True
        info = 'Viewer Director ready'
        return info, initialized

    def grab_data(self, Naverage=1, **kwargs):
        """
            Start new acquisition.
            Grabbed indice is used to keep track of the current image in the average.

            ============== ========== ==============================
            **Parameters**   **Type**  **Description**

            *Naverage*        int       Number of images to average
            ============== ========== ==============================

            See Also
            --------
            utility_classes.DAQ_TCP_server.process_cmds
        """

        self.ind_grabbed = 0  # to keep track of the current image in the average
        self.Naverage = Naverage
        if kwargs.get('live', False):
            self.controller.send_data_grab()
        else:
            self.controller.send_data_snap()

    def stop(self):
        """Stop grabbing."""
        self.controller.stop_grab()

    def set_data(self, data: Union[dict,list, str, float, None],
                 additional_payload: Optional[list[bytes]] = None) -> None:
        """
        Set the grabbed data signal.

        corresponds to the "data_ready" signal

        :param data: If None, look for the additional object
        """
        if additional_payload:
            dte = SerializableFactory().get_apply_deserializer(additional_payload[0])
        elif data is not None:
            axes = []
            labels = []
            multichannel = False
            if isinstance(data, dict):
                axes = [
                    Axis( label=axis.get('label', ''),
                          units=axis.get('units', ''),
                          data=np.array(axis.get('data', [])),
                          index=ind
                    ) for ind, axis in enumerate(data.get('axes', []))
                ]
                labels = data.get('labels', [])
                multichannel = data.get('multichannel', False)
                data = data.get('data', [])
            if multichannel:
                # data[0] may fail if data is empty, but it shouldn't happen
                ndim = np.array(data[0]).ndim
                data = [np.atleast_1d(d) for d in data]
            else:
                ndim = np.array(data).ndim
                data = [np.atleast_1d(data)]

            dfp = DataFromPlugins(self.controller.actor, data=data, axes=axes[:ndim], labels=labels)
            dte = DataToExport('Copy', data=[dfp])
        else:
            raise ValueError("Can't set_data when data is None")
        self.dte_signal.emit(dte)


if __name__ == '__main__':
    main(__file__, init=False)
