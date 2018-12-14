from pymodaq.plugins.hardware.andor.daq_AndorSDK2 import DAQ_AndorSDK2


class DAQ_1DViewer_Shamrock(DAQ_AndorSDK2):
    """
        =============== ==================

        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
    control_type = "both" #could be "camera", "shamrock" or "both"

    def __init__(self, *args, **kwargs):

        super(DAQ_1DViewer_Shamrock, self).__init__(*args, control_type=self.control_type, **kwargs)

