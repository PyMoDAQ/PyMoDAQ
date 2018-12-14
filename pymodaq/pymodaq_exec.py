import sys
import os
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QThread
from pyqtgraph.dockarea import DockArea


def scan():
    from pymodaq.daq_scan.daq_scan_main import DAQ_Scan

    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    fname = ""
    win.setVisible(False)
    splash = QtGui.QPixmap(os.path.join('documentation','splash.png'))
    splash_sc = QtWidgets.QSplashScreen(splash, Qt.WindowStaysOnTopHint)
    splash_sc.show()
    splash_sc.raise_()
    splash_sc.showMessage('Loading Main components', color=Qt.white)
    QtWidgets.QApplication.processEvents()

    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('pymodaq Scan')
    win.setVisible(False)
    prog = DAQ_Scan(area, fname)
    QThread.sleep(2)
    splash_sc.finish(win)
    win.setVisible(True)

    sys.exit(app.exec_())


def move():
    from pymodaq.daq_move.daq_move_main import DAQ_Move

    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    prog = DAQ_Move(Form,title="test",preset=[dict(object='Stage_type_combo',method='setCurrentText',value='PI')],init=False)
    Form.show()
    sys.exit(app.exec_())



def viewer():
    from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer

    from pymodaq.daq_utils.daq_enums import DAQ_type
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    win.setWindowTitle('pymodaq main')
    prog = DAQ_Viewer(area,title="Testing",DAQ_type=DAQ_type['DAQ1D'].name)
    win.show()
    sys.exit(app.exec_())

def h5browser():
    from pymodaq.daq_utils.h5browser import H5Browser
    app = QtWidgets.QApplication(sys.argv);
    win = QtWidgets.QWidget()
    #h5file=tables.open_file('C:\\Users\\Weber\\Labo\\Programmes Python\\pymodaq\\daq_utils\\test.h5')
    prog = H5Browser(win)
    win.show()
    sys.exit(app.exec_())
