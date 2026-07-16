import numpy as np

from qtpy import QtWidgets

from pymodaq_data import DataToExport, DataRaw, Axis
from pymodaq_gui.utils.utils import mkQApp
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D

def main(data_distribution='uniform'):
    """either 'uniform' or 'spread'"""
    app = mkQApp('Viewer2D')

    widget = QtWidgets.QWidget()

    if data_distribution == 'uniform':
        data_to_plot = generate_uniform_data()

    elif data_distribution == 'spread':
        data_spread = np.load('../../../resources/triangulation_data.npy')
        data_to_plot = DataRaw(name='mydata',
                               distribution='spread',
                               data=[data_spread[:,2]],
                               nav_indexes=(0,),
                               axes=[Axis('xaxis', units='xpxl', data=data_spread[:,0], index=0, spread_order=0),
                                     Axis('yaxis', units='ypxl', data=data_spread[:,1], index=0, spread_order=1)])

    prog = Viewer2D(widget)
    widget.show()

    prog.view.get_action('histo').trigger()
    prog.view.get_action('autolevels').trigger()

    prog.show_data(data_to_plot)
    app.exec()


def generate_uniform_data() -> DataRaw:
    from pymodaq_utils.math_utils import gauss2D
    Nx = 100
    Ny = Nx // 2
    data_random = np.random.normal(size=(Ny, Nx))

    xscaling, xoffset = 1, 20
    yscaling, yoffset = 1, 40

    x = xscaling * np.linspace(0, Nx - 1, Nx) + xoffset
    y = yscaling * np.linspace(0, Ny - 1, Ny) + yoffset

    print(x)
    print(y)
    x0 = 45 + xoffset
    y0 = 25 + yoffset
    data_red = 20 * np.cos((x-x0) / 5) * gauss2D(x, x0, Nx / 10, y, y0, Ny / 10, 1, 90) + 0.5 * data_random

    data_to_plot = DataRaw(name='mydata', distribution='uniform',
                                   data=[data_red],
                                   labels=['myreddata'],
                                   axes=[Axis('xaxis', units='xpxl', data=x, index=1),
                                         Axis('yaxis', units='ypxl', data=y, index=0)])
    return data_to_plot




if __name__ == '__main__':  # pragma: no cover
    main()

