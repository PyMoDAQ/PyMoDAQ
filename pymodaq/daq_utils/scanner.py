import sys
from collections import OrderedDict
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, pyqtSignal, QLocale

from pymodaq.daq_utils.daq_utils import linspace_step, odd_even, greater2n, find_index
from pymodaq.daq_utils.plotting.scan_selector import ScanSelector
import pymodaq.daq_utils.daq_utils as utils
import pymodaq.daq_utils.gui_utils as gutils
import itertools
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
from pymodaq.daq_utils.drop_table_view import TableModel, SpinBoxDelegate
from pymodaq.daq_utils.exceptions import ScannerException


scan_types = ['Scan1D', 'Scan2D', 'Sequential']
scan_subtypes = dict(Scan1D=['Linear', 'Adaptive', 'Linear back to start', 'Random'],
                     Scan2D=['Spiral', 'Linear', 'Adaptive', 'back&forth', 'Random'],
                     Sequential=['Linear', 'Adaptive'])


class ScanInfo:
    def __init__(self, Nsteps=0, positions=None, axes_indexes=None, axes_unique=None):
        """

        Parameters
        ----------
        Nsteps: (int) Number of steps of the scan
        positions: (ndarray) multidimensional array of Nsteps 0th dimension length where each element is the position
        positions_indexes: (ndarray) multidimensional array of Nsteps 0th dimension length where each element is the index
         of the corresponding positions within the axis_unique
        axes_unique: (list of ndarray) list of sorted (and with unique values) 1D arrays of unique positions of each defined axes
        """
        self.Nsteps = Nsteps
        self.positions = positions
        self.axes_indexes = axes_indexes
        self.axes_unique = axes_unique


class ScanParameters:
    """
    Utility class to define and store information about scans to be done
    """

    def __init__(self, scan_type='Scan1D', scan_subtype='Linear', starts=[], stops=[], steps=[], positions=None):
        """

        Parameters
        ----------
        scan_type: (str) one value of the scan_types list items
        scan_subtype: (str) ne value of the scan_subtypes dict items for the scan_type key
        starts: (list of floats) list of starts position of each axis
        stops: (list of floats) list of stops position of each axis
        steps: (list of floats) list of steps position of each axis
        positions: (ndarray) containing the positions already calculated from some method. If not None, this is used to
                define the scan_info (otherwise one use the starts, stops and steps)
        """
        if scan_type not in scan_types:
            raise ValueError(f'Chosen scan_type value ({scan_type}) is not possible. Should be among : {str(scan_types)}')
        if scan_subtype not in scan_subtypes:
            raise ValueError(
                f'Chosen scan_subtype value ({scan_subtype}) is not possible. Should be among : {str(scan_subtypes[scan_type])}')
        self.scan_type = scan_type
        self.scan_subtype = scan_subtype
        self.starts = starts
        self.stops = stops
        self.steps = steps

        self.scan_info = ScanInfo(Nsteps=0, positions=positions)

        self.set_scan()

    def __getattr__(self, item):
        if item == 'Nsteps':
            return self.scan_info.Nsteps
        elif item == 'positions':
            return self.scan_info.positions
        elif item == 'axes_indexes':
            return self.scan_info.axes_indexes
        elif item == 'axes_unique':
            return self.scan_info.axes_unique


    def set_scan(self):

        if self.positions is not None:
            axes_unique = []
            for ax in self.positions:
                axes_unique.append(np.unique(ax))
            axes_indexes = np.zeros_like(self.positions)
            for ind in range(self.positions.shape[0]):
                for ind_pos, pos in enumerate(self.positions[ind]):
                    axes_indexes[ind, ind_pos] = utils.find_index(axes_unique[ind_pos], pos)[0][0]

            self.scan_info = ScanInfo(Nsteps=self.positions.shape[0], axes_unique=axes_unique,
                                      axes_indexes=axes_indexes, positions=self.positions)

        else:
            #TODO
            if self.scan_type == "Scan1D":

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
                    scan_parameters = set_scan_spiral(start_axis1, start_axis2, Rmax, Rstep_2d)

                else:
                    stop_axis1 = self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis1').value()
                    step_axis1 = self.settings.child('scan_options', 'scan2D_settings', 'step_2d_axis1').value()
                    stop_axis2 = self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis2').value()
                    step_axis2 = self.settings.child('scan_options', 'scan2D_settings', 'step_2d_axis2').value()
                    if self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'back&forth':
                        scan_parameters = set_scan_linear(start_axis1, start_axis2,
                                                          stop_axis1, stop_axis2, step_axis1, step_axis2,
                                                          back_and_force=True)

                    elif self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'Linear':
                        scan_parameters = set_scan_linear(
                            start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=False)

                    elif self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'Random':
                        scan_parameters = set_scan_random(start_axis1, start_axis2,
                                                          stop_axis1, stop_axis2, step_axis1, step_axis2)


            elif self.settings.child('scan_options', 'scan_type').value() == "Sequential":
                starts = [self.table_model.get_data(ind, 1) for ind in range(self.table_model.rowCount(None))]
                stops = [self.table_model.get_data(ind, 2) for ind in range(self.table_model.rowCount(None))]
                steps = [self.table_model.get_data(ind, 3) for ind in range(self.table_model.rowCount(None))]
                scan_parameters = set_scan_sequential(starts, stops, steps)

            self.settings.child('scan_options', 'Nsteps').setValue(scan_parameters.Nsteps)
            self.scan_params_signal.emit(scan_parameters)
            return scan_parameters

    def __repr__(self):
        if self.scan_subtype != 'Adaptive':
            return f'[{self.scan_type}/{self.scan_subtype}] scanner with {self.scan_info.Nsteps} positions)'
        else:
            return f'[{self.scan_type}/{self.scan_subtype}] scanner with unknown (yet) positions to reach'

class Scanner(QObject):
    scan_params_signal = pyqtSignal(ScanParameters)

    params = [{'title': 'Scanner settings', 'name': 'scan_options', 'type': 'group', 'children': [
                {'title': 'Calculate positions:', 'name': 'calculate_positions', 'type': 'action'},
                {'title': 'N steps:', 'name': 'Nsteps', 'type': 'int', 'value': 0, 'readonly': True},
                {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'values': scan_types,
                         'value': scan_types[0]},
               {'title': 'Scan1D settings', 'name': 'scan1D_settings', 'type': 'group', 'children': [
                    {'title': 'Scan type:', 'name': 'scan1D_type', 'type': 'list',
                     'values': scan_subtypes['Scan1D'], 'value': scan_subtypes['Scan1D'][0],
                     'tip': 'For adaptive, an algo will '
                     'determine the positions to check within the scan bounds. The defined step will be set as the'
                     'biggest feature size the algo should reach.'},
                    {'title': 'Selection:', 'name': 'scan1D_selection', 'type': 'list',
                     'values': ['Manual', 'FromROI PolyLines']},
                    {'title': 'From module:', 'name': 'scan1D_roi_module', 'type': 'list', 'values': [], 'visible': False},
                    {'title': 'Start:', 'name': 'start_1D', 'type': 'float', 'value': 0.},
                    {'title': 'stop:', 'name': 'stop_1D', 'type': 'float', 'value': 10.},
                    {'title': 'Step:', 'name': 'step_1D', 'type': 'float', 'value': 1.}
                ]},
                {'title': 'Scan2D settings', 'name': 'scan2D_settings', 'type': 'group', 'visible': False, 'children': [
                    {'title': 'Scan type:', 'name': 'scan2D_type', 'type': 'list',
                     'values': scan_subtypes['Scan2D'], 'value': scan_subtypes['Scan2D'][0],
                     'tip': 'For adaptive, an algo will '
                     'determine the positions to check within the scan bounds. The defined step will be set as the'
                     'biggest feature size the algo should reach.'},
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
                {'title': 'Sequential settings', 'name': 'seq_settings', 'type': 'group', 'visible': False, 'children': [
                    {'title': 'Scan type:', 'name': 'scanseq_type', 'type': 'list',
                     'values': scan_subtypes['Sequential'], 'value': scan_subtypes['Sequential'][0], 'tip': 'For adaptive, an algo will '
                     'determine the positions to check within the scan bounds. The defined step will be set as the'
                     'biggest feature size the algo should reach.'},
                    {'title': 'Load sequence', 'name': 'load_seq', 'type': 'action'},
                    {'title': 'Save sequence', 'name': 'save_seq', 'type': 'action'},
                    {'title': 'Sequences', 'name': 'seq_table', 'type': 'table_view', 'delegate': SpinBoxDelegate},
                ]},
                ]},
                ]

    def __init__(self, scanner_items=OrderedDict([]), scan_type='Scan1D', actuators=[]):
        """

        Parameters
        ----------
        scanner_items: (items used by ScanSelector for chosing scan area or linear traces)
        scan_type: type of scan selector
        actuators: list of actuators names
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
        self.table_model = None

        self.scan_selector.widget.setVisible(False)
        self.scan_selector.show_scan_selector(visible=False)
        self.settings.child('scan_options', 'seq_settings', 'load_seq').sigActivated.connect(self.load_sequence_xml)
        self.settings.child('scan_options', 'seq_settings', 'save_seq').sigActivated.connect(self.save_sequence_xml)
        if actuators != []:
            self.actuators = actuators

        self.set_scan()

    def load_sequence_xml(self):
        fname = gutils.select_file(start_path=None, save=False, ext='xml')
        if fname is not None:
            new_par = custom_tree.XML_file_to_parameter(fname)
            self.settings.child('scan_options', 'seq_settings').restoreState(new_par.saveSate())


    def save_sequence_xml(self):
        fname = gutils.select_file(start_path=None, save=True, ext='xml')
        if fname is not None:
            custom_tree.parameter_to_xml_file(self.settings.child('scan_options', 'seq_settings'), fname)

    @property
    def actuators(self):
        return self._actuators

    @actuators.setter
    def actuators(self, act_list):
        self._actuators = act_list
        self.update_model()

    def update_model(self):
        self.table_model = TableModelScanner([[name, 0., 1., 0.1] for name in self._actuators],
                              header=['Actuator', 'Start', 'Stop', 'Step'],
                              editable=[False, True, True, True])
        self.table_view = custom_tree.get_widget_from_tree(self.settings_tree, custom_tree.TableViewCustom)[0]

        self.table_view.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)

        self.table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QTableView.SingleSelection)

        self.table_view.setDragEnabled(True)
        self.table_view.setDropIndicatorShown(True)
        self.table_view.setAcceptDrops(True)
        self.table_view.viewport().setAcceptDrops(True)
        self.table_view.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.table_view.setDragDropMode(QtWidgets.QTableView.InternalMove)
        self.table_view.setDragDropOverwriteMode(False)

        styledItemDelegate = QtWidgets.QStyledItemDelegate()
        styledItemDelegate.setItemEditorFactory(SpinBoxDelegate())
        self.table_view.setItemDelegate(styledItemDelegate)

        self.settings.child('scan_options', 'seq_settings', 'seq_table').setValue(self.table_model)

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
                        self.settings.child('scan_options', 'seq_settings').hide()
                        self.settings_tree.setMaximumHeight(300)
                        if self.settings.child('scan_options', 'scan1D_settings', 'scan1D_selection').value() == 'Manual':
                            self.scan_selector.show_scan_selector(visible=False)
                        else:
                            self.scan_selector.show_scan_selector(visible=True)
                    elif data == 'Scan2D':
                        self.settings.child('scan_options', 'scan1D_settings').hide()
                        self.settings.child('scan_options', 'scan2D_settings').show()
                        self.settings.child('scan_options', 'seq_settings').hide()
                        self.settings_tree.setMaximumHeight(300)
                        if self.settings.child('scan_options', 'scan2D_settings', 'scan2D_selection').value() == 'Manual':
                            self.scan_selector.show_scan_selector(visible=False)
                        else:
                            self.scan_selector.show_scan_selector(visible=True)
                        self.update_scan_type(self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type'))
                        self.update_scan_2D_positions()

                    elif data == 'Sequential':
                        self.settings.child('scan_options', 'scan1D_settings').hide()
                        self.settings.child('scan_options', 'scan2D_settings').hide()
                        self.settings.child('scan_options', 'seq_settings').show()
                        self.settings_tree.setMaximumHeight(600)


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
                    except Exception as e:
                        raise ScannerException(f'Invalid call to setScan ({str(e)})')

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
            scan_parameters = ScanParameters(scan_type="Scan1D",
                        scan_subtype=self.settings.child('scan_options', 'sscan_type', 'scanseq_type').value())

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
                scan_parameters = set_scan_spiral(start_axis1, start_axis2, Rmax, Rstep_2d)

            else:
                stop_axis1 = self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis1').value()
                step_axis1 = self.settings.child('scan_options', 'scan2D_settings', 'step_2d_axis1').value()
                stop_axis2 = self.settings.child('scan_options', 'scan2D_settings', 'stop_2d_axis2').value()
                step_axis2 = self.settings.child('scan_options', 'scan2D_settings', 'step_2d_axis2').value()
                if self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'back&forth':
                    scan_parameters = set_scan_linear(start_axis1, start_axis2,
                                                      stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=True)
    
                elif self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'Linear':
                    scan_parameters = set_scan_linear(
                        start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=False)
    
                elif self.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').value() == 'Random':
                    scan_parameters = set_scan_random(start_axis1, start_axis2,
                                                      stop_axis1, stop_axis2, step_axis1, step_axis2)


        elif self.settings.child('scan_options', 'scan_type').value() == "Sequential":
            starts = [self.table_model.get_data(ind, 1) for ind in range(self.table_model.rowCount(None))]
            stops = [self.table_model.get_data(ind, 2) for ind in range(self.table_model.rowCount(None))]
            steps = [self.table_model.get_data(ind, 3) for ind in range(self.table_model.rowCount(None))]
            scan_parameters = set_scan_sequential(starts, stops, steps)


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
            raise ScannerException(str(e))

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
            raise ScannerException(str(e))

class TableModelScanner(TableModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_data(self, row, col, value):
        """
        make sure the values and signs of the start, stop and step values are "correct"
        Parameters
        ----------
        row: (int) row within the table that is to be changed
        col: (int) col within the table that is to be changed
        value: (float) new value for the value defined by row and col

        Returns
        -------
        bool: True is the new value is fine (change some other values if needed) otherwise False
        """
        start = self.data(self.index(row, 1), QtCore.Qt.DisplayRole)
        stop = self.data(self.index(row, 2), QtCore.Qt.DisplayRole)
        step = self.data(self.index(row, 3), QtCore.Qt.DisplayRole)
        isstep = False
        if col == 1:  #the start
            start = value
        elif col == 2: #the stop
            stop = value
        else: #the step
            isstep = True
            step = value

        if np.abs(step) < 1e-12 or start == stop:
            return False
        if np.sign(stop - start) != np.sign(step):
            if isstep:
                self._data[row][2] = -stop
            else:
                self._data[row][3] = -step
        return True


def set_scan_linear(start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=False,
                    oversteps=10000):
    """
        Set a linear scan
    Parameters
    ----------
    start_axis1
    start_axis2
    stop_axis1
    stop_axis2
    step_axis1
    step_axis2
    back_and_force: (bool) if True insert between two steps a position back to start (to be used as a reference in the scan analysis)
    oversteps: (int) maximum number of calculated steps (stops the steps calculation if over the first power of 2 greater than oversteps)

    Returns
    -------
    ScanParameters instance

    See Also
    --------
    ScanParameters
    """

    scan_type = 'Scan2D'
    scan_subtype = 'Linear'

    if np.abs(step_axis1) < 1e-12 or \
            np.abs(step_axis2) < 1e-12 or \
            np.sign(stop_axis1 - start_axis1) != np.sign(step_axis1) or \
            np.sign(stop_axis2 - start_axis2) != np.sign(step_axis2) or \
            start_axis1 == stop_axis1 or \
            start_axis2 == stop_axis2:
        return ScanParameters(1, np.array([0]), np.array([0]), np.array([start_axis1]),
                              np.array([start_axis2]), [np.array([start_axis1]), np.array([start_axis2])],
                              scan_type=scan_type, scan_subtype=scan_subtype)

    else:
        axis_1_unique = linspace_step(start_axis1, stop_axis1, step_axis1)
        len1 = len(axis_1_unique)

        axis_2_unique = linspace_step(start_axis2, stop_axis2, step_axis2)
        len2 = len(axis_2_unique)
        # if number of steps is over oversteps, reduce both axis in the same ratio
        if len1 * len2 > oversteps:
            axis_1_unique = axis_1_unique[:int(np.ceil(np.sqrt(oversteps * len1 / len2)))]
            axis_2_unique = axis_2_unique[:int(np.ceil(np.sqrt(oversteps * len2 / len1)))]

        positions = []
        axis_1_indexes = []
        axis_2_indexes = []
        axis_1 = []
        axis_2 = []
        for ind_x, pos1 in enumerate(axis_1_unique):
            if back_and_force:
                for ind_y, pos2 in enumerate(axis_2_unique):
                    if not odd_even(ind_x):
                        positions.append([pos1, pos2])
                        axis_1.append(pos1)
                        axis_2.append(pos2)
                        axis_1_indexes.append(ind_x)
                        axis_2_indexes.append(ind_y)
                    else:
                        positions.append([pos1, axis_2_unique[len(axis_2_unique) - ind_y - 1]])
                        axis_1.append(pos1)
                        axis_2.append(axis_2_unique[len(axis_2_unique) - ind_y - 1])
                        axis_1_indexes.append(ind_x)
                        axis_2_indexes.append(len(axis_2_unique) - ind_y - 1)
            else:
                for ind_y, pos2 in enumerate(axis_2_unique):
                    axis_1.append(pos1)
                    axis_2.append(pos2)
                    positions.append([pos1, pos2])
                    axis_1_indexes.append(ind_x)
                    axis_2_indexes.append(ind_y)

        Nsteps = len(positions)
        return ScanParameters(Nsteps, np.array(axis_1_indexes), np.array(axis_2_indexes), axis_1_unique, axis_2_unique,
                              positions,
                              scan_type=scan_type, scan_subtype=scan_subtype)


def set_scan_random(start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, oversteps=10000):
    """

    Parameters
    ----------
    start_axis1
    start_axis2
    stop_axis1
    stop_axis2
    step_axis1
    step_axis2

    Returns
    -------

    """
    scan_type = 'Scan2D'
    scan_subtype = 'Random'
    if np.abs(step_axis1) < 1e-12 or \
            np.abs(step_axis2) < 1e-12 or \
            np.sign(stop_axis1 - start_axis1) != np.sign(step_axis1) or \
            np.sign(stop_axis2 - start_axis2) != np.sign(step_axis2) or \
            start_axis1 == stop_axis1 or \
            start_axis2 == stop_axis2:
        return ScanParameters(1, np.array([0]), np.array([0]), np.array([start_axis1]),
                              np.array([start_axis2]), [np.array([start_axis1]), np.array([start_axis2])],
                              scan_type=scan_type, scan_subtype=scan_subtype)

    scan_parameters = set_scan_linear(start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2,
                                      back_and_force=False, oversteps=oversteps)


    positions_shuffled = scan_parameters.positions[:]
    np.random.shuffle(positions_shuffled)
    axis_1_indexes = []
    axis_2_indexes = []

    for pos in positions_shuffled:
        axis_1_indexes.append(np.where(scan_parameters.axis_2D_1 == pos[0])[0][0])
        axis_2_indexes.append(np.where(scan_parameters.axis_2D_2 == pos[1])[0][0])

    Nsteps = len(scan_parameters.positions)
    return ScanParameters(Nsteps, axis_1_indexes, axis_2_indexes, scan_parameters.axis_2D_1, scan_parameters.axis_2D_2,
                          positions_shuffled,
                              scan_type=scan_type, scan_subtype=scan_subtype)


def set_scan_spiral(start_axis1, start_axis2, rmax, rstep, oversteps=10000):
    """

    Parameters
    ----------
    start_axis1
    start_axis2
    rmax
    rstep
    oversteps: (int) maximum number of calculated steps (stops the steps calculation if over the first power of 2 greater than oversteps)

    Returns
    -------
    ScanParameters instance

    See Also
    --------
    ScanParameters
    """
    scan_type = 'Scan2D'
    scan_subtype = 'Spiral'
    if rmax == 0 or np.abs(rmax) < 1e-12 or np.abs(rstep) < 1e-12:
        return ScanParameters(1, np.array([0]), np.array([0]), np.array([start_axis1]),
                              np.array([start_axis2]), [np.array([start_axis1]), np.array([start_axis2])],
                              scan_type=scan_type, scan_subtype=scan_subtype)

    ind = 0
    flag = True
    oversteps = greater2n(oversteps)  # make sure the position matrix is still a square

    Nlin = np.trunc(rmax / rstep)
    axis_1_indexes = [0]
    axis_2_indexes = [0]
    while flag:
        if odd_even(ind):
            step = 1
        else:
            step = -1
        if flag:

            for ind_step in range(ind):
                axis_1_indexes.append(axis_1_indexes[-1] + step)
                axis_2_indexes.append(axis_2_indexes[-1])
                if len(axis_1_indexes) >= (2 * Nlin + 1) ** 2 or len(axis_1_indexes) >= oversteps:
                    flag = False
                    break
        if flag:
            for ind_step in range(ind):

                axis_1_indexes.append(axis_1_indexes[-1])
                axis_2_indexes.append(axis_2_indexes[-1] + step)
                if len(axis_1_indexes) >= (2 * Nlin + 1) ** 2 or len(axis_1_indexes) >= oversteps:
                    flag = False
                    break
        ind += 1

    axis_1_indexes = np.array(axis_1_indexes, dtype=int)
    axis_2_indexes = np.array(axis_2_indexes, dtype=int)

    axis_1_unique = np.unique(axis_1_indexes)
    axis_1_unique = axis_1_unique.astype(float)
    axis_2_unique = np.unique(axis_2_indexes)
    axis_2_unique = axis_2_unique.astype(float)
    axis_1 = np.zeros_like(axis_1_indexes, dtype=float)
    axis_2 = np.zeros_like(axis_2_indexes, dtype=float)

    positions = []
    for ind in range(len(axis_1)):
        axis_1[ind] = axis_1_indexes[ind] * rstep + start_axis1
        axis_2[ind] = axis_2_indexes[ind] * rstep + start_axis2
        positions.append([axis_1[ind], axis_2[ind]])

    for ind in range(len(axis_1_unique)):
        axis_1_unique[ind] = axis_1_unique[ind] * rstep + start_axis1
        axis_2_unique[ind] = axis_2_unique[ind] * rstep + start_axis2

    axis_1_indexes = axis_1_indexes - np.min(axis_1_indexes)
    axis_2_indexes = axis_2_indexes - np.min(axis_2_indexes)

    Nsteps = len(positions)
    return ScanParameters(Nsteps, axis_1_indexes, axis_2_indexes, axis_1_unique, axis_2_unique, positions,
                              scan_type=scan_type, scan_subtype=scan_subtype)


def pos_above_stops(positions, steps, stops):
    state = []
    for pos, step, stop in zip(positions, steps, stops):
        if step >= 0:
            state.append(pos > stop)
        else:
            state.append(pos < stop)
    return state


def set_scan_sequential(starts=[0.0, 10.0], stops=[10.0, 0.0], steps=[1.0, -1.0]):
    """
    Create a list of positions (one for each actuator == one for each element in starts list) that are sequential
    Parameters
    ----------
    starts: list
            list of starts of all selected actuators
    stops: list
                list of stops of all selected actuators
    steps: list

    Returns
    -------
    positions: list of list
    """

    scan_type = 'Sequential'
    scan_subtype = 'Linear'

    axis_seq = [linspace_step(starts[ind], stops[ind], steps[ind]) for ind in range(len(starts))]


    all_positions = [starts[:]]
    positions = starts[:]
    state = pos_above_stops(positions, steps, stops)
    while not state[0]:
        if not np.any(np.array(state)):
            positions[-1] += steps[-1]

        else:
            indexes_true = np.where(np.array(state))
            positions[indexes_true[-1][0]] = starts[indexes_true[-1][0]]
            positions[indexes_true[-1][0]-1] += steps[indexes_true[-1][0]-1]

        state = pos_above_stops(positions, steps, stops)
        if not np.any(np.array(state)):
            all_positions.append(positions[:])



    axis_seq_indexes = []
    for poss in all_positions:
        indexes = []
        for ind, pos in enumerate(poss):
            indexes.append(find_index(axis_seq[ind], pos)[0][0])
        axis_seq_indexes.append(indexes)


    Nsteps = len(all_positions)
    return ScanParameters(Nsteps, positions=all_positions, axis_seq=axis_seq, axis_seq_indexes=axis_seq_indexes,
                              scan_type=scan_type, scan_subtype=scan_subtype))

#Parameter only
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    prog = Scanner(actuators=['Xaxis', 'Yaxis', 'Theta Axis'])
    prog.settings_tree.show()
    prog.actuators = ['xxx', 'yyy']

    sys.exit(app.exec_())

# if __name__ == '__main__':
#     from pymodaq.daq_utils.daq_utils import DockArea
#     from pyqtgraph.dockarea import Dock
#     from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
#     from pymodaq.daq_utils.plotting.navigator import Navigator
#     from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
#     class UI():
#         def __init__(self):
#             pass
#
#
#     class FakeDaqScan():
#
#         def __init__(self, area):
#             self.area = area
#             self.detector_modules = None
#             self.ui = UI()
#             self.dock = Dock('2D scan', size=(500, 300), closable=False)
#
#             form = QtWidgets.QWidget()
#             self.ui.scan2D_graph = Viewer2D(form)
#             self.dock.addWidget(form)
#             self.area.addDock(self.dock)
#
#     app = QtWidgets.QApplication(sys.argv)
#     win = QtWidgets.QMainWindow()
#     area = DockArea()
#
#     win.setCentralWidget(area)
#     win.resize(1000, 500)
#     win.setWindowTitle('pymodaq main')
#     fake = FakeDaqScan(area)
#
#     prog = DAQ_Viewer(area, title="Testing", DAQ_type='DAQ2D', parent_scan=fake)
#     prog.ui.IniDet_pb.click()
#     QThread.msleep(1000)
#     QtWidgets.QApplication.processEvents()
#     prog2 = Navigator()
#     widgnav = QtWidgets.QWidget()
#     prog2 = Navigator(widgnav)
#     nav_dock = Dock('Navigator')
#     nav_dock.addWidget(widgnav)
#     area.addDock(nav_dock)
#     QThread.msleep(1000)
#     QtWidgets.QApplication.processEvents()
#
#
#     fake.detector_modules=[prog, prog2]
#     items = OrderedDict()
#     items[prog.title]=dict(viewers=[view for view in prog.ui.viewers],
#                            names=[view.title for view in prog.ui.viewers],
#                            )
#     items['Navigator'] = dict(viewers=[prog2.viewer],
#                              names=['Navigator'])
#     items["DaqScan"] = dict(viewers=[fake.ui.scan2D_graph],
#                              names=["DaqScan"])
#
#
#
#     prog = Scanner(items)
#     prog.settings_tree.show()
#     win.show()
#     sys.exit(app.exec_())