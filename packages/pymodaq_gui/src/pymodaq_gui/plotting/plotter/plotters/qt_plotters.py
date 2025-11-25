from typing import List, Tuple, Any, TYPE_CHECKING, Union
import sys

from qtpy import QtWidgets

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import config as configmod
from pymodaq_gui.utils.utils import start_qapplication


from pymodaq_data.plotting.plotter.plotter import PlotterBase, PlotterFactory
from pymodaq_data.data import DataWithAxes, DataToExport
from pymodaq_gui.plotting.data_viewers import (Viewer1D, Viewer2D, ViewerND, ViewerDispatcher,
                                                 Viewer0D, ViewersEnum)
from pymodaq_gui.plotting.data_viewers.viewer import ViewerBase, viewer_factory
from pymodaq_gui.utils.dock import DockArea

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


@PlotterFactory.register()
class Plotter(PlotterBase):
    backend = 'qt'

    def __init__(self, **_ignored):
        super().__init__()

    def plot(self, data: Union[DataWithAxes, DataToExport], viewer=None, **kwargs) -> ViewerBase:
        """

        Parameters
        ----------
        data
        viewer
        kwargs

        Returns
        -------

        """
        do_exit = False
        qapp = QtWidgets.QApplication.instance()
        if qapp is None:
            do_exit = True
            qapp = start_qapplication()

        if viewer is None:
            if isinstance(data, DataToExport):
                widget = DockArea()
                viewer = ViewerDispatcher(widget, title=data.name)
            else:
                widget = QtWidgets.QWidget()
                viewer_enum = ViewersEnum.get_viewers_enum_from_data(data)
                viewer = viewer_factory.get(viewer_enum.name, parent=widget)
            widget.show()

        if viewer is not None:
            viewer.show_data(data, **kwargs)
            if isinstance(viewer, Viewer1D):
                if not viewer.is_action_checked('errors'):
                    viewer.get_action('errors').trigger()
            QtWidgets.QApplication.processEvents()

        if do_exit:
            sys.exit(qapp.exec())
        return viewer


if __name__ == '__main__':
    from pymodaq.utils import data as data_mod
    import numpy as np
    from pymodaq.utils.math_utils import gauss1D
    from pymodaq.utils.plotting.plotter.plotter import PlotterFactory

    qapp = start_qapplication()

    plotter_factory = PlotterFactory()

    x = np.random.randint(201, size=201)
    y1 = gauss1D(x, 75, 25)
    y2 = gauss1D(x, 120, 50, 2)

    QtWidgets.QApplication.processEvents()
    dwa = data_mod.DataRaw('mydata', data=[y1, y2],
                            axes=[data_mod.Axis('myaxis', 'units', data=x, index=0,
                                                spread_order=0)],
                            nav_indexes=())

    dwa.plot('qt')
    dwa.as_dte('mydte').plot('qt')
    sys.exit(qapp.exec())
