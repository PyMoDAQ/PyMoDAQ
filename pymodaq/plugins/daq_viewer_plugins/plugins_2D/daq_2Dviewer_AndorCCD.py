from pymodaq.plugins.hardware.andor.daq_AndorSDK2 import DAQ_AndorSDK2


class DAQ_2DViewer_AndorCCD(DAQ_AndorSDK2):
    """
        =============== ==================

        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
    control_type = "camera" #could be "camera", "shamrock" or "both"
    hardware_averaging = False

    def __init__(self, *args, **kwargs):

        super(DAQ_2DViewer_AndorCCD, self).__init__(*args, control_type=self.control_type, **kwargs)

