from pymodaq.plugins.hardware.NIDAQmx.DAQ_NIDAQmx import DAQ_NIDAQmx


class DAQ_0DViewer_NIDAQmx(DAQ_NIDAQmx):
    """
        ==================== ========================
        **Attributes**         **Type**
        *data_grabed_signal*   instance of pyqtSignal
        *params*               dictionnary list
        *task*
        ==================== ========================

        See Also
        --------
        refresh_hardware
    """
    control_type = "0D"  # could be "0D", "1D"

    def __init__(self, *args, **kwargs):
        super(DAQ_0DViewer_NIDAQmx, self).__init__(*args, control_type=self.control_type, **kwargs)

