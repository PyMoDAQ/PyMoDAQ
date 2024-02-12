from typing import List, Tuple, Any, TYPE_CHECKING
import sys
import datetime

import numpy as np
from qtpy import QtWidgets

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils import config as configmod
from pymodaq.utils.data import DataDim, DataWithAxes

from pymodaq.utils.gui_utils.utils import start_qapplication
from pymodaq.utils.plotting.plotter.plotter import PlotterBase, PlotterFactory

from matplotlib import pyplot as plt

if TYPE_CHECKING:
    pass

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


class Plotter(PlotterBase):
    backend = 'matplotlib'

    def __init__(self, **_ignored):
        super().__init__()


@PlotterFactory.register()
class Plotter1D(Plotter):
    """ """
    data_dim = DataDim['Data1D'].name

    def plot(self, dwa: DataWithAxes) -> plt.Figure:
        fig = plt.figure()

        for data_array in dwa:
            plt.plot(dwa.axes[0].get_data(), data_array)
        plt.legend(dwa.labels)
        plt.title(f'{dwa.name} taken the {datetime.datetime.fromtimestamp(dwa.timestamp)}')
        plt.xlabel(f'{dwa.axes[0].label} ({dwa.axes[0].units})')
        plt.ylabel(dwa.name)
        return fig


@PlotterFactory.register()
class Plotter2D(Plotter):
    """ """
    data_dim = DataDim['Data2D'].name

    def plot(self, dwa: DataWithAxes) -> plt.Figure:
        fig = plt.figure()
        xaxis = dwa.get_axis_from_index(1)[0]
        yaxis = dwa.get_axis_from_index(0)[0]

        x = xaxis.get_data()
        y = yaxis.get_data()
        for ind_plot, dwa_array in enumerate(dwa):
            plt.subplot(1, len(dwa), ind_plot+1)
            X, Y = np.meshgrid(x, y)
            plt.pcolormesh(X, Y, dwa_array)
            plt.title(f'{dwa.name}/{dwa.labels[ind_plot]} taken the {datetime.datetime.fromtimestamp(dwa.timestamp)}')
            plt.xlabel(f'{xaxis.label} ({xaxis.units})')
            plt.ylabel(f'{yaxis.label} ({yaxis.units})')
        return fig


if __name__ == '__main__':
    from pymodaq.utils import data as data_mod
    import numpy as np
    from pymodaq.utils.math_utils import gauss1D, gauss2D
    from pymodaq.utils.plotting.plotter.plotter import PlotterFactory
    plotter_factory = PlotterFactory()

    x = np.linspace(0, 100, 101)
    y = np.linspace(0, 100, 101)
    y1 = gauss2D(x, 50, 20, y, 40, 7)


    QtWidgets.QApplication.processEvents()
    dwa = data_mod.DataRaw('mydata', data=[y1],
                            axes=[data_mod.Axis('xaxis', 'x units', data=x, index=0,
                                                spread_order=0),
                                  data_mod.Axis('yaxis', 'y units', data=y, index=1,
                                                spread_order=0)
                                  ],
                            nav_indexes=())

    fig = dwa.plot('matplotlib')
    fig.savefig('myplot.png')