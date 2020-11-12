
try:  #in a try statement for compilation on readthedocs server but if this fail, you cannot use the code
    from .daq_utils import daq_utils as utils
    logger = utils.set_logger('pymodaq', add_handler=True, base_logger=True)
    logger.info('')
    logger.info('')
    logger.info('')
    logger.info('************************')
    logger.info('Starting PyMoDAQ modules')
    logger.info('************************')
    logger.info('')
    logger.info('')
    logger.info('')

    if __name__ == '__main__':
        import sys
        from PyQt5 import QtWidgets
        from pymodaq.daq_utils.gui_utils import DockArea
        from pymodaq.dashboard import DashBoard
        app = QtWidgets.QApplication(sys.argv)
        win = QtWidgets.QMainWindow()
        area = DockArea()
        win.setCentralWidget(area)
        win.resize(1000, 500)
        win.setWindowTitle('PyMoDAQ Dashboard')

        # win.setVisible(False)
        prog = DashBoard(area)
        sys.exit(app.exec_())

except Exception as e:
    logger.exception(str(e))
    print("Couldn't create the local folder to store logs , presets...")




