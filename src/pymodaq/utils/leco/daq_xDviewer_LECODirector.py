
from typing import Union

from easydict import EasyDict as edict

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main

from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.tcp_ip.serializer import DeSerializer

from pymodaq.utils.leco.leco_director import LECODirector, leco_parameters
from pymodaq.utils.leco.director_utils import DetectorDirector


class DAQ_xDViewer_LECODirector(LECODirector, DAQ_Viewer_base):
    """A control module, which in the dashboard, allows to control a remote Viewer module.

    This is the base class for the viewer LECO director modules.
    """

    settings: Parameter
    controller: DetectorDirector

    params_GRABBER = []

    message_list = LECODirector.message_list + ["Quit", "Send Data 0D", "Send Data 1D",
                                                "Send Data 2D", "Send Data ND",
                                                "Status", "Done", "Server Closed",
                                                "Info", "Infos", "Info_xml", 'x_axis', 'y_axis']
    socket_types = ["GRABBER"]
    params = [
    ] + comon_parameters + leco_parameters

    def __init__(self, parent=None, params_state=None, grabber_type: str = "0D", **kwargs) -> None:
        super().__init__(parent=parent, params_state=params_state, **kwargs)
        self.register_rpc_methods((
            self.set_x_axis,
            self.set_y_axis,
            self.set_data,
        ))

        self.client_type = "GRABBER"
        self.x_axis = None
        self.y_axis = None
        self.data = None
        self.grabber_type = grabber_type
        self.ind_data = 0
        self.data_mock = None

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
        self.status.update(edict(initialized=False, info="", x_axis=None, y_axis=None,
                                 controller=None))
        actor_name = self.settings.child("actor_name").value()
        self.controller = self.ini_detector_init(  # type: ignore
            old_controller=controller,
            new_controller=DetectorDirector(actor=actor_name, communicator=self.communicator),
            )
        self.controller.set_remote_name(self.communicator.full_name)  # type: ignore
        try:
            # self.settings.child(('infos')).addChildren(self.params_GRABBER)

            # init axes from image , here returns only None values (to tricky to di it with the
            # server and not really necessary for images anyway)
            self.x_axis = self.get_xaxis()
            self.y_axis = self.get_yaxis()
            self.status.x_axis = self.x_axis
            self.status.y_axis = self.y_axis
            self.status.initialized = True
            return self.status

        except Exception as e:
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def get_xaxis(self):
        """
            Obtain the horizontal axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the horizontal camera pixels.
        """
        pass
        return self.x_axis

    def get_yaxis(self):
        """
            Obtain the vertical axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the vertical camera pixels.
        """
        pass
        return self.y_axis

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
        try:
            self.ind_grabbed = 0  # to keep track of the current image in the average
            self.Naverage = Naverage
            self.controller.set_remote_name(self.communicator.full_name)
            self.controller.send_data(grabber_type=self.grabber_type)

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), "log"]))

    def stop(self):
        """
            not implemented.
        """
        pass
        return ""

    # Methods for RPC calls
    def set_x_axis(self, data, label: str = "", units: str = ""):
        # TODO make to work
        self.x_axis = dict(data=data, label=label, units=units)
        self.emit_x_axis()

    def set_y_axis(self, data, label: str = "", units: str = ""):
        # TODO make to work
        self.y_axis = dict(data=data, label=label, units=units)
        self.emit_y_axis()

    def set_data(self, data: Union[list, str]) -> None:
        """
        Set the grabbed data signal.

        corresponds to the "data_ready" signal

        :param data: If None, look for the additional object
        """
        if isinstance(data, str):
            deserializer = DeSerializer.from_b64_string(data)
            dte = deserializer.dte_deserialization()
            self.dte_signal.emit(dte)
        else:
            raise NotImplementedError("Not implemented to set a list of values.")


if __name__ == '__main__':
    main(__file__)
