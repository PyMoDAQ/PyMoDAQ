import sys

from qtpy import QtWidgets, QtCore

from pymodaq_gui.parameter import ParameterTree
from pymodaq_gui.utils.dock import Dock, DockLabel, DockArea


def test_dock_and_label(qtbot):

    labelv = DockLabel('mysuperlabel', fontSize='25px')
    docky = Dock('MysuperDockLogger', fontSize='30px')
    dockx = Dock('MysuperDockLoggerx', fontSize='30px')
    area = DockArea()
    area.addDock(docky)
    area.addDock(dockx)
    dockx.addWidget(ParameterTree())
    labelv.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter)
    f = labelv.font()
    f.setPixelSize(25)
    labelv.setFont(f)
    docky.label.setFont(f)
    labelv.show()
    area.show()
    QtWidgets.QApplication.processEvents()
    print(f'labelv size hint: {labelv.sizeHint()}')
    print(f'labelv size: {labelv.size()}')
    print(f'labelv margins: {labelv.contentsMargins().top()}, {labelv.contentsMargins().bottom()}')

