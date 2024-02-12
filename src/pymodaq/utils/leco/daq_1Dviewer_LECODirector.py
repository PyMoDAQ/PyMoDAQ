
from pymodaq.utils.leco.daq_xDviewer_LECODirector import DAQ_xDViewer_LECODirector, main


class DAQ_1DViewer_LECODirector(DAQ_xDViewer_LECODirector):
    """A control module, which in the dashboard, allows to control a remote Viewer module"""

    def __init__(self, parent=None, params_state=None, grabber_type: str = "1D", **kwargs) -> None:
        super().__init__(parent=parent, params_state=params_state, grabber_type=grabber_type,
                         **kwargs)


if __name__ == '__main__':
    main(__file__)
