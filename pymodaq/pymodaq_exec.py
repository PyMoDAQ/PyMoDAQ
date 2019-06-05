import sys
import os
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QThread
from pymodaq.daq_utils.daq_utils import DockArea


def scan():
    app = QtWidgets.QApplication(sys.argv)
    from pymodaq.daq_scan.daq_scan_main import DAQ_Scan


    splash_path = os.path.join(os.path.split(__file__)[0],'daq_scan', 'splash.png')
    splash = QtGui.QPixmap(splash_path)
    if splash is None:
        print('no splash')
    splash_sc = QtWidgets.QSplashScreen(splash, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

    splash_sc.show()
    QtWidgets.QApplication.processEvents()
    splash_sc.raise_()
    splash_sc.showMessage('Loading Main components', color=Qt.white)
    QtWidgets.QApplication.processEvents()

    win = QtWidgets.QMainWindow()
    win.setVisible(False)
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('pymodaq Scan')

    # win.setVisible(False)
    prog = DAQ_Scan(area)
    QThread.sleep(0)
    win.show()
    splash_sc.finish(win)
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


if __name__ == '__main__':
    scan()