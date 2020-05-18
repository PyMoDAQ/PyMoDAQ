from PyQt5 import QtWidgets

import sys
import numpy as np

from pymodaq.daq_utils.math_utils import FourierFilterer

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv);
    prog = FourierFilterer()

    from pymodaq.daq_utils.daq_utils import gauss1D

    xdata=np.linspace(0,400,401)
    x0=50
    dx=20
    tau = 27
    tau2=100
    ydata_gauss=10*gauss1D(xdata,x0,dx)+np.random.rand(len(xdata))
    ydata_expodec = np.zeros((len(xdata)))
    ydata_expodec[:50] = 10*gauss1D(xdata[:50],x0,dx,2)
    ydata_expodec[50:] = 10*np.exp(-(xdata[50:]-x0)/tau)#+10*np.exp(-(xdata[50:]-x0)/tau2)
    ydata_expodec += 2*np.random.rand(len(xdata))
    ydata_sin =10+2*np.sin(2*np.pi*0.1*xdata-np.deg2rad(55))+np.sin(2*np.pi*0.008*xdata-np.deg2rad(-10))+2*np.random.rand(len(xdata))

    prog.show_data(dict(data=ydata_sin, xaxis=xdata))
    sys.exit(app.exec_())
