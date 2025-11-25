from typing import List, Tuple, Any, TYPE_CHECKING, Union
import sys
import datetime

import numpy as np

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import config as configmod
from pymodaq_data.data import DataDim, DataWithAxes, DataToExport
from pymodaq_utils import utils
from pymodaq_data.plotting.plotter.plotter import PlotterBase, PlotterFactory

from matplotlib import pyplot as plt

if TYPE_CHECKING:
    pass

logger = set_logger(get_module_name(__file__))
config = configmod.Config()

PLOT_COLORS = utils.plot_colors.copy()
PLOT_COLORS.remove((255, 255, 255))  # remove white color as plotted on white background
PLOT_COLORS = [(np.array(color) / 255).tolist() for color in PLOT_COLORS]  # translation to matplotlib


@PlotterFactory.register()
class Plotter(PlotterBase):
    backend = 'matplotlib'

    def __init__(self, **_ignored):
        super().__init__()
        self.n_lines = 1
        self.n_columns = 1
        self.ind_line = 0
        self.ind_column = 0

    def plot(self, data: Union[DataWithAxes, DataToExport], *args, viewer=None,
             **kwargs) -> plt.Figure:
        fig = plt.figure()

        if isinstance(data, DataWithAxes):
            self.n_columns = len(data) if data.dim.name == 'Data2D' else 1
            self.plot_dwa(data, *args, **kwargs)
        elif isinstance(data, DataToExport):
            self.n_columns = max([len(dwa) if dwa.dim.name == 'Data2D' else 1 for dwa in data])
            self.n_lines = len(data)
            self.plot_dte(data, *args, **kwargs)
        plt.tight_layout()
        fig.suptitle(f'{data.name} taken the {datetime.datetime.fromtimestamp(data.timestamp)}')
        return fig

    def plot_dwa(self, dwa: DataWithAxes, *args, **kwargs):
        if dwa.dim.name == 'Data1D':
            if len(dwa.axes) == 0:
                dwa.create_missing_axes()
            self.ind_column = 0
            self.plot1D(dwa, *args, **kwargs)
        elif dwa.dim.name == 'Data2D':
            if len(dwa.axes) < 2:
                dwa.create_missing_axes()
            self.plot2D(dwa, *args, **kwargs)

    def plot_dte(self, dte: DataToExport, *args, **kwargs):
        for ind in range(len(dte)):
            self.ind_line = ind
            self.plot_dwa(dte[ind], *args, **kwargs)

    def plot1D(self, dwa: DataWithAxes, *args, **kwargs):
        plt.subplot(self.n_lines, self.n_columns,
                    (self.n_columns * self.ind_line) + 1)
        for ind_data, data_array in enumerate(dwa):
            plt.plot(dwa.axes[0].get_data(), data_array, *args,  color=PLOT_COLORS[ind_data],
                     **kwargs)
            if dwa.errors is not None:
                plt.fill_between(dwa.axes[0].get_data(), data_array - dwa.get_error(ind_data),
                                 data_array + dwa.get_error(ind_data), *args,
                                 color=PLOT_COLORS[ind_data] + [0.3], **kwargs)
        plt.legend(dwa.labels)
        #plt.title(f'{dwa.name}')
        plt.xlabel(f'{dwa.axes[0].label} ({dwa.axes[0].units})')
        plt.ylabel(dwa.name)

    def plot2D(self, dwa: DataWithAxes, *args, **kwargs):
        xaxis = dwa.get_axis_from_index(1)[0]
        yaxis = dwa.get_axis_from_index(0)[0]

        x = xaxis.get_data()
        y = yaxis.get_data()
        for ind_plot, dwa_array in enumerate(dwa):
            self.ind_column = ind_plot
            plt.subplot(self.n_lines, self.n_columns,
                        (self.n_columns * self.ind_line) + ind_plot + 1)
            X, Y = np.meshgrid(x, y)
            plt.pcolormesh(X, Y, dwa_array, *args, **kwargs)
            plt.title(f'{dwa.name}/{dwa.labels[ind_plot]}')
            plt.xlabel(f'{xaxis.label} ({xaxis.units})')
            plt.ylabel(f'{yaxis.label} ({yaxis.units})')


# if __name__ == '__main__':
#     from pymodaq.utils import data as data_mod
#     import numpy as np
#     from pymodaq.utils.math_utils import gauss1D, gauss2D
#     from pymodaq.utils.plotting.plotter.plotter import PlotterFactory
#     plotter_factory = PlotterFactory()
#
#     x = np.linspace(0, 100, 101)
#     y = np.linspace(0, 100, 101)
#     y1 = gauss2D(x, 50, 20, y, 40, 7)
#
#
#     QtWidgets.QApplication.processEvents()
#     dwa = data_mod.DataRaw('mydata', data=[y1, y1, y1],
#                            axes=[data_mod.Axis('xaxis', 'x units', data=x, index=0,
#                                                 spread_order=0),
#                                   data_mod.Axis('yaxis', 'y units', data=y, index=1,
#                                                 spread_order=0)
#                                   ],
#                            labels=['MAG', 'PHASE'],
#                            nav_indexes=())
#     dte = dwa.as_dte('mydte')
#     dwa_mean = dwa.mean()
#     dwa_mean.name = 'mean'
#     dwa_mean_2 = dwa.mean(1)
#     dwa_mean_2.name = 'mean2'
#     dte.append(dwa_mean)
#     dte.append(dwa_mean_2)
#
#     fig = dwa.plot('matplotlib')
#     fig.savefig('myplot.png')
#
#     fig2 = dte.plot('matplotlib')
#     fig2.savefig('mydte.png')
