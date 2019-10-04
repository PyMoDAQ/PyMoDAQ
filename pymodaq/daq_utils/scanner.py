import sys
from collections import OrderedDict
import numpy as np
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QTimer, QDateTime, QDate, QTime
from pymodaq.daq_utils.plotting.scan_selector import ScanSelector
import pymodaq.daq_utils.daq_utils as utils
import itertools

from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter



class Scanner(QObject):
    scan_params_signal = pyqtSignal(utils.ScanParameters)

    params = [{'title': 'Scanner settings', 'name': 'scan_options', 'type': 'group', 'children': [
                {'title': 'Calculate positions:', 'name': 'calculate_positions', 'type': 'action'},
                {'title': 'N steps:', 'name': 'Nsteps', 'type': 'int', 'value': 0, 'readonly': True},
                {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'values': ['Scan1D', 'Scan2D'],
                         'value': 'Scan1D'},
                {'title': 'Scan1D settings', 'name': 'scan1D_settings', 'type': 'group', 'children': [
                    {'title': 'Scan type:', 'name': 'scan1D_type', 'type': 'list',
                     'values': ['Linear', 'Linear back to start', 'Random'], 'value': 'Linear'},
                    {'title': 'Selection:', 'name': 'scan1D_selection', 'type': 'list',
                     'values': ['Manual', 'FromROI PolyLines']},
                    {'title': 'From module:', 'name': 'scan1D_roi_module', 'type': 'list', 'values': [], 'visible': False},
                    {'title': 'Start:', 'name': 'start_1D', 'type': 'float', 'value': 0.},
                    {'title': 'stop:', 'name': 'stop_1D', 'type': 'float', 'value': 10.},
                    {'title': 'Step:', 'name': 'step_1D', 'type': 'float', 'value': 1.}
                ]},
                {'title': 'Scan2D settings', 'name': 'scan2D_settings', 'type': 'group', 'visible': False, 'children': [
                    {'title': 'Scan type:', 'name': 'scan2D_type', 'type': 'list',
                     'values': ['Spiral', 'Linear', 'back&forth', 'Random'], 'value': 'Spiral'},
                    {'title': 'Selection:', 'name': 'scan2D_selection', 'type': 'list', 'values': ['Manual', 'FromROI']},
                    {'title': 'From module:', 'name': 'scan2D_roi_module', 'type': 'list', 'values': [], 'visible': False},
                    {'title': 'Start Ax1:', 'name': 'start_2d_axis1', 'type': 'float', 'value': 0., 'visible': True},
                    {'title': 'Start Ax2:', 'name': 'start_2d_axis2', 'type': 'float', 'value': 10., 'visible': True},
                    {'title': 'stop Ax1:', 'name': 'stop_2d_axis1', 'type': 'float', 'value': 10., 'visible': False},
                    {'title': 'stop Ax2:', 'name': 'stop_2d_axis2', 'type': 'float', 'value': 40., 'visible': False},
                    {'title': 'Step Ax1:', 'name': 'step_2d_axis1', 'type': 'float', 'value': 1., 'visible': False},
                    {'title': 'Step Ax2:', 'name': 'step_2d_axis2', 'type': 'float', 'value': 5., 'visible': False},
                    {'title': 'Rstep:', 'name': 'Rstep_2d', 'type': 'float', 'value': 1., 'visible': True},
                    {'title': 'Rmax:', 'name': 'Rmax_2d', 'type': 'float', 'value': 10., 'visible': True}
                ]},

                ]},
                ]

    def __init__(self, scanner_items=OrderedDict([]), scan_type = 'Scan1D'):
        """

        Parameters
        ----------
        parent
        scanner_items: (items used by ScanSelector for chosing scan area or linear traces)
        """

        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Scanner, self).__init__()

        self.settings_tree = None
        self.setupUI()

        self.scan_selector = ScanSelector(scanner_items, scan_type)
        self.settings.child('scan_options', 'scan1D_settings').setValue(scan_type)
        #self.scan_selector.settings.child('scan_options', 'scan_type').hide()
        self.scan_selector.scan_select_signal.connect(self.update_scan_2D_positions)

        self.settings.child('scan_options', 'scan1D_settings', 'scan1D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)
        self.settings.child('scan_options', 'scan2D_settings', 'scan2D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)

        self.scan_selector.widget.setVisible(False)
        self.scan_selector.show_scan_selector(visible=False)
        self.set_scan()

    @property
    def viewers_items(self):
        return self.scan_selector.viewers_items

    @viewers_items.setter
    def viewers_items(self, items):
        self.scan_selector.remove_scan_selector()
        self.scan_selector.viewers_items = items
        self.settings.child('scan_options', 'scan1D_settings', 'scan1D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)
        self.settings.child('scan_options', 'scan2D_settings', 'scan2D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)

    def parameter_tree_changed(self,param,changes):
        """

        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'scan_type':
                    self.scan_selector.settings.child('scan_options', 'scan_type').setValue(data)
                    if data == 'Scan1D':
                        self.settings.child('scan_options', 'scan1D_settings').show()
                        self.settings.child('scan_options', 'scan2D_settings').hide()
                        if self.settings.child('scan_options', 'scan1D_settings', 'scan1D_selection').value() == 'Manual':
                            self.scan_selector.show_scan_selector(visible=False)
                        else:
                            self.scan_selector.show_scan_selector(visible=True)
                    elif data == 'Scan2D':
                        self.settings.child('scan_options', 'scan1D_settings').hide()
                        self.settings.child('scan_options', 'scan2D_settings').show()
                        if self.settings.child('scan_options', 'scan2D_settings', 'scan2D_selection').value() == 'Manual':
                            self.scan_selector.show_scan_selector(visible=False)
                        else:
                            self.scan_selector.show_scan_selector(visible=True)
                    self.update_scan_type(self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type'))
                    self.update_scan_2D_positions()


                elif param.name() == 'scan1D_roi_module' or param.name() == 'scan2D_roi_module':
                    self.scan_selector.settings.child('scan_options', 'sources').setValue(param.value())

                elif param.name() == 'scan1D_selection':
                    if param.value() == 'Manual':
                        self.scan_selector.show_scan_selector(visible=False)
                        self.settings.child('scan_options', 'scan1D_settings','scan1D_roi_module').hide()
                        self.settings.child('scan_options', 'scan1D_settings', 'start_1D').show()
                        self.settings.child('scan_options', 'scan1D_settings', 'stop_1D').show()
                    else:
                        self.scan_selector.show_scan_selector(visible=True)
                        self.settings.child('scan_options','scan1D_settings','scan1D_roi_module').show()
                        self.settings.child('scan_options', 'scan1D_settings', 'start_1D').hide()
                        self.settings.child('scan_options', 'scan1D_settings', 'stop_1D').hide()

                elif param.name() == 'scan2D_selection':
                    if param.value() == 'Manual':
                        self.scan_selector.show_scan_selector(visible=False)
                        self.settings.child('scan_options', 'scan2D_settings', 'scan2D_roi_module').hide()
                    else:
                        self.scan_selector.show_scan_selector(visible=True)
                        self.settings.child('scan_options', 'scan2D_settings', 'scan2D_roi_module').show()

                    self.update_scan_type(self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type'))

                elif param.name() == 'scan2D_type':
                    self.update_scan_type(self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type'))

                else:
                    try:
                        self.set_scan()
                    except:
                        pass

            elif change == 'parent':
                pass

    def setupUI(self):
        # layout = QtWidgets.QHBoxLayout()
        # layout.setSpacing(0)
        # self.parent.setLayout(layout)
        self.settings_tree = ParameterTree()
        self.settings = Parameter.create(name='Scanner_Settings', title='Scanner Settings', type='group', children=self.params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings_tree.setMaximumHeight(300)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)
        self.settings.child('scan_options', 'calculate_positions').sigActivated.connect(self.set_scan)
        #layout.addWidget(self.settings_tree)

    def set_scan(self):

        if self.settings.child('scan_options', 'scan_type').value() == "Scan1D":
            scan_parameters = utils.ScanParameters()

            start = self.settings.child('scan_options', 'scan1D_settings', 'start_1D').value()
            stop = self.settings.child('scan_options', 'scan1D_settings', 'stop_1D').value()
            step = self.settings.child('scan_options', 'scan1D_settings', 'step_1D').value()
    
            if self.settings.child('scan_options', 'scan1D_settings', 'scan1D_selection').value() == 'Manual':
                steps_x = utils.linspace_step(start, stop, step)
                steps_y = steps_x
            else:  # from ROI
                viewer = self.scan_selector.scan_selector_source
                positions = self.scan_selector.scan_selector.getArrayIndexes(spacing=step)
    
                steps_x, steps_y = zip(*positions)
                steps_x, steps_y = viewer.scale_axis(np.array(steps_x), np.array(steps_y))

            if self.settings.child('scan_options', 'scan1D_settings', 'scan1D_type').value() == "Linear":
                scan_parameters.axis_2D_1 = steps_x
                scan_parameters.axis_2D_2 = steps_y
    
    
            elif self.settings.child('scan_options', 'scan1D_settings',
                                             'scan1D_type').value() == 'Linear back to start':
                stepss_x = []
                stepss_y = []
                for stepx in steps_x:
                    stepss_x.extend([stepx, start])
                for stepy in steps_y:
                    stepss_y.extend([stepy, start])
                scan_parameters.axis_2D_1 = np.array(stepss_x)
                scan_parameters.axis_2D_2 = np.array(stepss_y)
            elif self.settings.child('scan_options', 'scan1D_settings', 'scan1D_type').value() == 'Random':
                positions = list(zip(steps_x, steps_y))
                np.random.shuffle(positions)
                x, y = zip(*positions)
                scan_parameters.axis_2D_1 = list(x)
                scan_parameters.axis_2D_2 = list(y)

            scan_parameters.positions = list(
                itertools.zip_longest(scan_parameters.axis_2D_1, scan_parameters.axis_2D_2, fillvalue=None))
    
            scan_parameters.Nsteps = len(scan_parameters.positions)

        elif self.settings.child('scan_options', 'scan_type').value() == "Scan2D":

            start_axis1 = self.settings.child('scan_options', 'scan2D_settings', 'start_2d_axis1').value()
            start_axis2 = self.settings.child('scan_options', 'scan2D_settings', 'start_2d_axis2').value()
    
            if self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'Spiral':
    
                Rstep_2d = self.settings.child('scan_options', 'scan2D_settings', 'Rstep_2d').value()
                Rmax = self.settings.child('scan_options', 'scan2D_settings', 'Rmax_2d').value()
                scan_parameters = utils.set_scan_spiral(start_axis1, start_axis2, Rmax, Rstep_2d)

            else:
                stop_axis1 = self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis1').value()
                step_axis1 = self.settings.child('scan_options', 'scan2D_settings', 'step_2d_axis1').value()
                stop_axis2 = self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis2').value()
                step_axis2 = self.settings.child('scan_options', 'scan2D_settings', 'step_2d_axis2').value()
                if self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'back&forth':
                    scan_parameters = utils.set_scan_linear(start_axis1, start_axis2,
                                                stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=True)
    
                elif self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'Linear':
                    scan_parameters = utils.set_scan_linear(
                        start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=False)
    
                elif self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'Random':
                    scan_parameters = utils.set_scan_random(start_axis1, start_axis2,
                                                                stop_axis1, stop_axis2, step_axis1, step_axis2)


        self.settings.child('scan_options', 'Nsteps').setValue(scan_parameters.Nsteps)
        self.scan_params_signal.emit(scan_parameters)
        return scan_parameters

    def update_scan_2D_positions(self):
        try:
            viewer = self.scan_selector.scan_selector_source
            pos_dl = self.scan_selector.scan_selector.pos()
            pos_ur = self.scan_selector.scan_selector.pos()+self.scan_selector.scan_selector.size()
            pos_dl_scaled = viewer.scale_axis(pos_dl[0], pos_dl[1])
            pos_ur_scaled= viewer.scale_axis(pos_ur[0], pos_ur[1])

            if self.settings.child('scan_options','scan2D_settings', 'scan2D_type').value() == 'Spiral':
                self.settings.child('scan_options', 'scan2D_settings', 'start_2d_axis1').setValue(np.mean((pos_dl_scaled[0],pos_ur_scaled[0])))
                self.settings.child('scan_options', 'scan2D_settings', 'start_2d_axis2').setValue(np.mean((pos_dl_scaled[1],pos_ur_scaled[1])))
                self.settings.child('scan_options', 'scan2D_settings', 'Rmax_2d').setValue(np.min((np.abs((pos_ur_scaled[0]-pos_dl_scaled[0])/2),(pos_ur_scaled[1]-pos_dl_scaled[1])/2)))

            else:
                self.settings.child('scan_options', 'scan2D_settings', 'start_2d_axis1').setValue(pos_dl_scaled[0])
                self.settings.child('scan_options', 'scan2D_settings', 'start_2d_axis2').setValue(pos_dl_scaled[1])
                self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis1').setValue(pos_ur_scaled[0])
            self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis2').setValue(pos_ur_scaled[1])
        except Exception as e:
            print(e)

    def update_scan_type(self, param):
        """
            Update the scan type from the given parameter.

            =============== ================================= ========================
            **Parameters**    **Type**                         **Description**
            *param*           instance of pyqtgraph parameter  the parameter to treat
            =============== ================================= ========================

            See Also
            --------
            update_status
        """
        try:
            state=param.value()=='Spiral'
            self.settings.child('scan_options','scan2D_settings','stop_2d_axis1').setOpts(visible=not state,value=self.settings.child('scan_options','scan2D_settings','stop_2d_axis1').value())
            self.settings.child('scan_options','scan2D_settings','stop_2d_axis2').setOpts(visible=not state,value=self.settings.child('scan_options','scan2D_settings','stop_2d_axis2').value())
            self.settings.child('scan_options','scan2D_settings','step_2d_axis1').setOpts(visible=not state,value=self.settings.child('scan_options','scan2D_settings','step_2d_axis1').value())
            self.settings.child('scan_options','scan2D_settings','step_2d_axis2').setOpts(visible=not state,value=self.settings.child('scan_options','scan2D_settings','step_2d_axis2').value())
            self.settings.child('scan_options','scan2D_settings','Rstep_2d').setOpts(visible=state,value=self.settings.child('scan_options','scan2D_settings','Rstep_2d').value())
            self.settings.child('scan_options','scan2D_settings','Rmax_2d').setOpts(visible=state,value=self.settings.child('scan_options','scan2D_settings','Rstep_2d').value())
        except Exception as e:
            print(e)



if __name__ == '__main__':
    from pymodaq.daq_utils.daq_utils import DockArea
    from pyqtgraph.dockarea import Dock
    from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
    from pymodaq.daq_utils.plotting.navigator import Navigator
    from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
    class UI():
        def __init__(self):
            pass


    class FakeDaqScan():

        def __init__(self, area):
            self.area = area
            self.detector_modules = None
            self.ui = UI()
            self.dock = Dock('2D scan', size=(500, 300), closable=False)

            form = QtWidgets.QWidget()
            self.ui.scan2D_graph = Viewer2D(form)
            self.dock.addWidget(form)
            self.area.addDock(self.dock)

    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()

    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('pymodaq main')
    fake = FakeDaqScan(area)

    prog = DAQ_Viewer(area, title="Testing", DAQ_type='DAQ2D', parent_scan=fake)
    prog.ui.IniDet_pb.click()
    QThread.msleep(1000)
    QtWidgets.QApplication.processEvents()
    prog2 = Navigator()
    widgnav = QtWidgets.QWidget()
    prog2 = Navigator(widgnav)
    nav_dock = Dock('Navigator')
    nav_dock.addWidget(widgnav)
    area.addDock(nav_dock)
    QThread.msleep(1000)
    QtWidgets.QApplication.processEvents()


    fake.detector_modules=[prog, prog2]
    items = OrderedDict()
    items[prog.title]=dict(viewers=[view for view in prog.ui.viewers],
                           names=[view.title for view in prog.ui.viewers],
                           )
    items['Navigator'] = dict(viewers=[prog2.viewer],
                             names=['Navigator'])
    items["DaqScan"] = dict(viewers=[fake.ui.scan2D_graph],
                             names=["DaqScan"])



    prog = Scanner(items)
    prog.settings_tree.show()
    win.show()
    sys.exit(app.exec_())