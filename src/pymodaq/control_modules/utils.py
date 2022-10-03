# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""
from qtpy import QtCore

from daq_utils.daq_utils import ThreadCommand


class ControlModule(QtCore.QObject):
    """Abstract Base class common to both DAQ_Move and DAQ_Viewer control modules

    Attributes
    ----------

    init_signal: Signal[bool]
        This signal is emitted when the chosen hardware is correctly initialized
    command_hardware: Signal[ThreadCommand]
        This signal is used to communicate with the instrument plugin within a separate thread
    command_tcpip: Signal[ThreadCommand]
        This signal is used to communicate trhough the TCP/IP Network
    quit_signal: Signal[]
        This signal is emitted when the user requested to stop the module

    See Also
    --------
    :class:`ThreadCommand`
    """
    init_signal = QtCore.Signal(bool)
    command_hardware = QtCore.Signal(ThreadCommand)
    command_tcpip = QtCore.Signal(ThreadCommand)
    quit_signal = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._title = ""

    @property
    def module_type(self):
        return type(self).__name__

    @property
    def initialized_state(self):
        return self._initialized_state

    @property
    def title(self):
        return self._title

    def grab(self):
        """Programmatic entry to grab data from detectors or current value from actuator"""
        raise NotImplementedError

    def quit_fun(self):
        """Programmatic entry to quit the controle module"""
        raise NotImplementedError

    def init_hardware(self, do_init=True):
        """Programmatic entry to initialize/deinitialize the control module

        Parameters
        ----------
        do_init: bool
            if True initialize the selected hardware else deinitialize it

        See Also
        --------
        :meth:`init_hardware_ui`
        """
        raise NotImplementedError

    def init_hardware_ui(self, do_init=True):
        """Programmatic entry to simulated a click on the user interface init button

        Parameters
        ----------
        do_init: bool
            if True initialize the selected hardware else deinitialize it

        Notes
        -----
        This method should be preferred to :meth:`init_hardware`
        """
        raise NotImplementedError


class ControlModuleUI(QtCore.QObject):

    command_sig = QtCore.Signal(ThreadCommand)

    def display_status(self, txt, wait_time):
        self.statusbar.showMessage(txt, wait_time)

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        raise NotImplementedError

    def send_init(self):
        """Shoudl be implemented to send to the main app the fact that someone pressed init"""
        raise NotImplementedError