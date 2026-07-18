from qtpy import QtWidgets, QtCore
import numpy as np
from pymodaq_utils.math_utils import gauss1D, odd_even

from pymodaq_gui.utils.widgets.lcd import LCD



def test_lcd_display(qtbot):
    from pymodaq_utils.math_utils import gauss1D
    import numpy as np

    x = np.linspace(0, 200, 10)
    y1 = 100 * gauss1D(x, 75, 100)
    y2 = gauss1D(x, 120, 100, 2)

    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)

    prog = LCD(widget, Nvals=2, show_graph=False)
    widget.show()
    for ind in range(len(x)):

        prog.setvalues([np.atleast_1d(y1[ind]),
                        np.atleast_1d(y2[ind])],
                       show_graph=odd_even(ind))
        QtWidgets.QApplication.processEvents()
        QtCore.QThread.msleep(10)