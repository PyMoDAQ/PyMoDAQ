import sys
from collections import OrderedDict
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, pyqtSignal, QLocale, pyqtSlot

from pymodaq.daq_utils.parameter import ioxml

from pymodaq.daq_utils.daq_utils import linspace_step, odd_even, greater2n
from pymodaq.daq_utils.plotting.scan_selector import ScanSelector
import pymodaq.daq_utils.daq_utils as utils
import pymodaq.daq_utils.gui_utils as gutils
from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils.plotting.plot_utils import QVector
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.parameter.pymodaq_ptypes as pymodaq_types  # to be placed after importing Parameter

from pymodaq.daq_utils.exceptions import ScannerException

logger = utils.set_logger(utils.get_module_name(__file__))
config = utils.load_config()

scan_types = ['Scan1D', 'Scan2D', 'Sequential', 'Tabular']
scan_subtypes = dict(Scan1D=['Linear', 'Adaptive', 'Linear back to start', 'Random'],
                     Scan2D=['Spiral', 'Linear', 'Adaptive', 'Back&Forth', 'Random'],
                     Sequential=['Linear'],
                     Tabular=['Linear', 'Adaptive'])

try:
    import adaptive
    from adaptive.learner import learner1D
    from adaptive.learner import learner2D
    adaptive_losses = dict(
        loss1D=['default', 'curvature', 'uniform'],
        loss2D=['default', 'resolution', 'uniform', 'triangle'])

except Exception:
    scan_subtypes['Scan1D'].pop(scan_subtypes['Scan1D'].index('Adaptive'))
    scan_subtypes['Scan2D'].pop(scan_subtypes['Scan2D'].index('Adaptive'))
    scan_subtypes['Tabular'].pop(scan_subtypes['Tabular'].index('Adaptive'))
    adaptive_losses = None
    adaptive = None
    logger.info('adaptive module is not present, no adaptive scan possible')




class ScanInfo:
    def __init__(self, Nsteps=0, positions=None, axes_indexes=None, axes_unique=None, **kwargs):
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
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def __repr__(self):
        if self.positions is not None:
            return f'[ScanInfo with {self.Nsteps} positions of shape {self.positions.shape})'
        else:
            return '[ScanInfo with position is None)'




class ScanParameters:
    """
    Utility class to define and store information about scans to be done
    """

    def __init__(self, Naxes=1, scan_type='Scan1D', scan_subtype='Linear', starts=None, stops=None, steps=None,
                 positions=None, adaptive_loss=None):
        """

        Parameters
        ----------
        Naxes: (int) number of axes used to do the scan
        scan_type: (str) one value of the scan_types list items
        scan_subtype: (str) ne value of the scan_subtypes dict items for the scan_type key
        starts: (list of floats) list of starts position of each axis
        stops: (list of floats) list of stops position of each axis
        steps: (list of floats) list of steps position of each axis
        positions: (ndarray) containing the positions already calculated from some method. If not None, this is used to
                define the scan_info (otherwise one use the starts, stops and steps)

        See Also
        --------
        daq_utils.plotting.scan_selector
        """
        self.Naxes = Naxes
        if scan_type not in scan_types:
            raise ValueError(
                f'Chosen scan_type value ({scan_type}) is not possible. Should be among : {str(scan_types)}')
        if scan_subtype not in scan_subtypes[scan_type]:
            raise ValueError(
                f'Chosen scan_subtype value ({scan_subtype}) is not possible. Should be among : {str(scan_subtypes[scan_type])}')
        self.scan_type = scan_type
        self.scan_subtype = scan_subtype
        self.adaptive_loss = adaptive_loss
        self.vectors = None

        # if positions is not None:
        #     self.starts = np.min(positions, axis=0)
        #     self.stops = np.max(positions, axis=0)
        # else:
        self.starts = starts
        self.stops = stops

        self.steps = steps

        self.scan_info = ScanInfo(Nsteps=0, positions=positions, adaptive_loss=adaptive_loss)

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
        else:
            if hasattr(self.scan_info, item):
                return getattr(self.scan_info, item)
            else:
                raise ValueError(f'no attribute named {item}')

    def get_info_from_positions(self, positions):
        if positions is not None:
            if len(positions.shape) == 1:
                positions = np.expand_dims(positions, 1)
            axes_unique = []
            for ax in positions.T:
                axes_unique.append(np.unique(ax))
            axes_indexes = np.zeros_like(positions, dtype=np.int)
            for ind in range(positions.shape[0]):
                for ind_pos, pos in enumerate(positions[ind]):
                    axes_indexes[ind, ind_pos] = utils.find_index(axes_unique[ind_pos], pos)[0][0]

            return ScanInfo(Nsteps=positions.shape[0], axes_unique=axes_unique,
                            axes_indexes=axes_indexes, positions=positions, adaptive_loss=self.adaptive_loss)
        else:
            return ScanInfo()

    def set_scan(self):
        steps_limit = config['scan']['steps_limit']
        Nsteps = self.evaluate_Nsteps()
        if Nsteps > steps_limit:
            self.scan_info = ScanInfo(Nsteps=Nsteps)
            return self.scan_info

        if self.scan_type == "Scan1D":
            if self.positions is not None:
                positions = self.positions
            else:
                positions = utils.linspace_step(self.starts[0], self.stops[0], self.steps[0])

            if self.scan_subtype == "Linear":
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Linear back to start':
                positions = np.insert(positions, range(1, len(positions) + 1), positions[0], axis=0)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Random':
                np.random.shuffle(positions)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Adaptive':
                # return an "empty" ScanInfo as positions will be "set" during the scan
                self.scan_info = ScanInfo(Nsteps=0, positions=np.array([0, 1]), axes_unique=[np.array([])],
                                          axes_indexes=np.array([]), adaptive_loss=self.adaptive_loss)

            else:               # pragma: no cover
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')

        elif self.scan_type == "Scan2D":
            if np.abs((self.stops[0]-self.starts[0]) / self.steps[0]) > steps_limit:
                return ScanInfo()

            if self.scan_subtype == 'Spiral':
                positions = set_scan_spiral(self.starts, self.stops, self.steps)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Back&Forth':
                positions = set_scan_linear(self.starts, self.stops, self.steps, back_and_force=True)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Linear':
                positions = set_scan_linear(self.starts, self.stops, self.steps, back_and_force=False)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Random':
                positions = set_scan_random(self.starts, self.stops, self.steps)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Adaptive':
                # return an "empty" ScanInfo as positions will be "set" during the scan
                self.scan_info = ScanInfo(Nsteps=0, positions=np.zeros([0, 2]), axes_unique=[np.array([])],
                                          axes_indexes=np.array([]), adaptive_loss=self.adaptive_loss)
            else:
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')

        elif self.scan_type == "Sequential":
            if self.scan_subtype == 'Linear':
                positions = set_scan_sequential(self.starts, self.stops, self.steps)
                self.scan_info = self.get_info_from_positions(positions)
            else:
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')

        elif self.scan_type == 'Tabular':
            if self.scan_subtype == 'Linear':
                if self.positions is not None:
                    self.starts = np.min(self.positions, axis=0)
                    self.stops = np.max(self.positions, axis=0)
                self.scan_info = self.get_info_from_positions(self.positions)
            elif self.scan_subtype == 'Adaptive':
                # return an "empty" ScanInfo as positions will be "set" during the scan
                # but adds some usefull info such as total length and list of vectors
                self.vectors = []
                length = 0.

                for ind in range(len(self.starts)):
                    self.vectors.append(QVector(self.starts[ind][0], self.starts[ind][1],
                                           self.stops[ind][0], self.stops[ind][1]))
                    length += self.vectors[-1].norm()

                self.scan_info = ScanInfo(Nsteps=0, positions=np.zeros([0, self.Naxes]), axes_unique=[np.array([])],
                                          axes_indexes=np.array([]), vectors=self.vectors, length=length,
                                          adaptive_loss=self.adaptive_loss)
            else:
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')
        return self.scan_info

    def evaluate_Nsteps(self):
        Nsteps = 1
        if self.starts is not None:
            for ind in range(len(self.starts)):
                if self.scan_subtype != 'Spiral':
                    Nsteps *= np.abs((self.stops[ind] - self.starts[ind]) / self.steps[ind])+1
                else:
                    Nsteps *= np.abs(2 * (self.stops[ind] / self.steps[ind]) + 1)
        return Nsteps

    def __repr__(self):
        if self.vectors is not None:
            bounds = f'bounds as vectors: {self.vectors} and curvilinear step: {self.steps}'
        else:
            bounds = f' bounds (starts/stops/steps): {self.starts}/{self.stops}/{self.steps})'

        if self.scan_subtype != 'Adaptive':
            return f'[{self.scan_type}/{self.scan_subtype}] scanner with {self.scan_info.Nsteps} positions and ' + bounds
        else:
            return f'[{self.scan_type}/{self.scan_subtype}] scanner with unknown (yet) positions to reach and ' + bounds


class Scanner(QObject):
    scan_params_signal = pyqtSignal(ScanParameters)

    params = [#{'title': 'Scanner settings', 'name': 'scan_options', 'type': 'group', 'children': [
        {'title': 'Calculate positions:', 'name': 'calculate_positions', 'type': 'action'},
        {'title': 'N steps:', 'name': 'Nsteps', 'type': 'int', 'value': 0, 'readonly': True},

        {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'values': scan_types,
         'value': config['scan']['default']},
        {'title': 'Scan1D settings', 'name': 'scan1D_settings', 'type': 'group', 'children': [
            {'title': 'Scan subtype:', 'name': 'scan1D_type', 'type': 'list',
             'values': scan_subtypes['Scan1D'], 'value': config['scan']['scan1D']['type'],
             'tip': 'For adaptive, an algo will '
                    'determine the positions to check within the scan bounds. The defined step will be set as the'
                    'biggest feature size the algo should reach.'},
            {'title': 'Loss type', 'name': 'scan1D_loss', 'type': 'list',
             'values': [], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Start:', 'name': 'start_1D', 'type': 'float', 'value': config['scan']['scan1D']['start']},
            {'title': 'stop:', 'name': 'stop_1D', 'type': 'float', 'value': config['scan']['scan1D']['stop']},
            {'title': 'Step:', 'name': 'step_1D', 'type': 'float', 'value': config['scan']['scan1D']['step']}
        ]},
        {'title': 'Scan2D settings', 'name': 'scan2D_settings', 'type': 'group', 'visible': False, 'children': [
            {'title': 'Scan subtype:', 'name': 'scan2D_type', 'type': 'list',
             'values': scan_subtypes['Scan2D'], 'value': config['scan']['scan2D']['type'],
             'tip': 'For adaptive, an algo will '
                    'determine the positions to check within the scan bounds. The defined step will be set as the'
                    'biggest feature size the algo should reach.'},
            {'title': 'Loss type', 'name': 'scan2D_loss', 'type': 'list',
             'values': [], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Selection:', 'name': 'scan2D_selection', 'type': 'list', 'values': ['Manual', 'FromROI']},
            {'title': 'From module:', 'name': 'scan2D_roi_module', 'type': 'list', 'values': [], 'visible': False},
            {'title': 'Start Ax1:', 'name': 'start_2d_axis1', 'type': 'float',
             'value': config['scan']['scan2D']['start1'], 'visible': True},
            {'title': 'Start Ax2:', 'name': 'start_2d_axis2', 'type': 'float',
             'value': config['scan']['scan2D']['start2'], 'visible': True},
            {'title': 'Step Ax1:', 'name': 'step_2d_axis1', 'type': 'float',
             'value': config['scan']['scan2D']['step1'], 'visible': True},
            {'title': 'Step Ax2:', 'name': 'step_2d_axis2', 'type': 'float',
             'value': config['scan']['scan2D']['step2'], 'visible': True},
            {'title': 'Npts/axis', 'name': 'npts_by_axis', 'type': 'int', 'min': 1,
             'value': config['scan']['scan2D']['npts'],
             'visible': True},
            {'title': 'Stop Ax1:', 'name': 'stop_2d_axis1', 'type': 'float',
             'value': config['scan']['scan2D']['stop1'], 'visible': True,
             'readonly': True, },
            {'title': 'Stop Ax2:', 'name': 'stop_2d_axis2', 'type': 'float',
             'value': config['scan']['scan2D']['stop2'], 'visible': True,
             'readonly': True, },

        ]},
        {'title': 'Sequential settings', 'name': 'seq_settings', 'type': 'group', 'visible': False, 'children': [
            {'title': 'Scan subtype:', 'name': 'scanseq_type', 'type': 'list',
             'values': scan_subtypes['Sequential'], 'value': scan_subtypes['Sequential'][0], },
            {'title': 'Sequences', 'name': 'seq_table', 'type': 'table_view',
             'delegate': gutils.SpinBoxDelegate},
        ]},
        {'title': 'Tabular settings', 'name': 'tabular_settings', 'type': 'group', 'visible': False, 'children': [
            {'title': 'Scan subtype:', 'name': 'tabular_subtype', 'type': 'list',
             'values': scan_subtypes['Tabular'], 'value': config['scan']['tabular']['type'],
             'tip': 'For adaptive, an algo will '
                    'determine the positions to check within the scan bounds. The defined step will be set as the'
                    'biggest feature size the algo should reach.'},
            {'title': 'Loss type', 'name': 'tabular_loss', 'type': 'list',
             'values': [], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Selection:', 'name': 'tabular_selection', 'type': 'list',
             'values': ['Manual', 'Polylines']},
            {'title': 'From module:', 'name': 'tabular_roi_module', 'type': 'list', 'values': [],
             'visible': False},
            {'title': 'Curvilinear Step:', 'name': 'tabular_step', 'type': 'float',
             'value': config['scan']['tabular']['curvilinear']},
            {'title': 'Positions', 'name': 'tabular_table', 'type': 'table_view',
             'delegate': gutils.SpinBoxDelegate, 'menu': True},
        ]},
        {'title': 'Load settings', 'name': 'load_xml', 'type': 'action'},
        {'title': 'Save settings', 'name': 'save_xml', 'type': 'action'},
    ]#}]

    def __init__(self, scanner_items=OrderedDict([]), scan_type='Scan1D', actuators=[], adaptive_losses=None):
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
        self.settings.child('scan_type').setValue(scan_type)
        # self.scan_selector.settings.child('scan_options', 'scan_type').hide()
        self.scan_selector.scan_select_signal.connect(self.update_scan_2D_positions)
        self.scan_selector.scan_select_signal.connect(self.update_tabular_positions)

        self.settings.child('tabular_settings', 'tabular_roi_module').setOpts(
            limits=self.scan_selector.sources_names)
        self.settings.child('scan2D_settings', 'scan2D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)
        self.table_model = None

        if adaptive_losses is not None:
            if 'loss1D' in adaptive_losses:
                self.settings.child('scan1D_settings', 'scan1D_loss').setOpts(
                    limits=adaptive_losses['loss1D'], visible=False)
            if 'loss1D' in adaptive_losses:
                self.settings.child('tabular_settings', 'tabular_loss').setOpts(
                    limits=adaptive_losses['loss1D'], visible=False)
            if 'loss2D' in adaptive_losses:
                self.settings.child('scan2D_settings', 'scan2D_loss').setOpts(
                    limits=adaptive_losses['loss2D'], visible=False)

        if actuators != []:
            self.actuators = actuators
        else:
            stypes = scan_types[:]
            stypes.pop(stypes.index('Sequential'))
            self.settings.child('scan_type').setLimits(stypes)
            self.settings.child('scan_type').setValue(stypes[0])

        self.scan_selector.widget.setVisible(False)
        self.scan_selector.show_scan_selector(visible=False)
        self.settings.child('load_xml').sigActivated.connect(self.load_xml)
        self.settings.child('save_xml').sigActivated.connect(self.save_xml)

        self.set_scan()
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    def load_xml(self):
        fname = gutils.select_file(start_path=None, save=False, ext='xml')
        if fname is not None and fname != '':
            par = ioxml.XML_file_to_parameter(fname)
            self.settings.restoreState(Parameter.create(name='settings', type='group', children=par).saveState())
            self.update_model()
            scan_type = self.settings.child('scan_type').value()
            if scan_type == 'Sequential':
                self.table_model = self.settings.child('seq_settings', 'seq_table').value()
            elif scan_type == 'Tabular':
                self.table_model = self.settings.child('tabular_settings', 'tabular_table').value()
            self.set_scan()

    def save_xml(self):
        """
        """
        fname = gutils.select_file(start_path=None, save=True, ext='xml')
        if fname is not None and fname != '':
            ioxml.parameter_to_xml_file(self.settings, fname)

    def set_config(self):
        scan_type = config['scan']['default']
        self.settings.child('scan_type').setValue(scan_type)

        self.settings.child('scan1D_settings', 'scan1D_type').setValue(config['scan']['scan1D']['type'])
        self.settings.child('scan1D_settings', 'start_1D').setValue(config['scan']['scan1D']['start'])
        self.settings.child('scan1D_settings', 'stop_1D').setValue(config['scan']['scan1D']['stop'])
        self.settings.child('scan1D_settings', 'step_1D').setValue(config['scan']['scan1D']['step'])

        self.settings.child('scan2D_settings', 'scan2D_type').setValue(config['scan']['scan2D']['type'])
        self.settings.child('scan2D_settings', 'start_2d_axis1').setValue(
            config['scan']['scan2D']['start1'])
        self.settings.child('scan2D_settings', 'start_2d_axis2').setValue(
            config['scan']['scan2D']['start2'])
        self.settings.child('scan2D_settings', 'step_2d_axis2').setValue(
            config['scan']['scan2D']['step1'])
        self.settings.child('scan2D_settings', 'step_2d_axis2').setValue(
            config['scan']['scan2D']['step2'])
        self.settings.child('scan2D_settings', 'npts_by_axis').setValue(
            config['scan']['scan2D']['npts'])
        self.settings.child('scan2D_settings', 'stop_2d_axis1').setValue(
            config['scan']['scan2D']['stop1'])
        self.settings.child('scan2D_settings', 'stop_2d_axis2').setValue(
            config['scan']['scan2D']['stop2'])

        self.settings.child('tabular_settings', 'tabular_subtype').setValue(
            config['scan']['tabular']['type'])
        self.settings.child('tabular_settings', 'tabular_step').setValue(
            config['scan']['tabular']['curvilinear'])

    @property
    def actuators(self):
        """
        Returns as a list the name of the actuators selected to describe the actual scan
        """
        return self._actuators

    @actuators.setter
    def actuators(self, act_list):
        self._actuators = act_list
        if len(act_list) >= 1:
            tip = f'Ax1 corresponds to the {act_list[0]} actuator'
            self.settings.child('scan2D_settings', 'start_2d_axis1').setOpts(tip=tip)
            self.settings.child('scan2D_settings', 'stop_2d_axis1').setOpts(tip=tip)
            self.settings.child('scan2D_settings', 'step_2d_axis1').setOpts(tip=tip)
            if len(act_list) >= 2:
                tip = f'Ax2 corresponds to the {act_list[1]} actuator'
            self.settings.child('scan2D_settings', 'start_2d_axis2').setOpts(tip=tip)
            self.settings.child('scan2D_settings', 'stop_2d_axis2').setOpts(tip=tip)
            self.settings.child('scan2D_settings', 'step_2d_axis2').setOpts(tip=tip)

        self.update_model()

    def update_model(self, init_data=None):
        try:
            scan_type = self.settings.child('scan_type').value()
            if scan_type == 'Sequential':
                if init_data is None:
                    if self.table_model is not None:
                        init_data = []
                        names = [row[0] for row in self.table_model.get_data_all()]
                        for name in self._actuators:
                            if name in names:
                                ind_row = names.index(name)
                                init_data.append(self.table_model.get_data_all()[ind_row])
                            else:
                                init_data.append([name, 0., 1., 0.1])
                    else:
                        init_data = [[name, 0., 1., 0.1] for name in self._actuators]
                self.table_model = TableModelSequential(init_data, )
                self.table_view = putils.get_widget_from_tree(self.settings_tree, pymodaq_types.TableViewCustom)[0]
                self.settings.child('seq_settings', 'seq_table').setValue(self.table_model)
            elif scan_type == 'Tabular':
                if init_data is None:
                    init_data = [[0. for name in self._actuators]]

                self.table_model = TableModelTabular(init_data, [name for name in self._actuators])
                self.table_view = putils.get_widget_from_tree(self.settings_tree, pymodaq_types.TableViewCustom)[1]
                self.settings.child('tabular_settings', 'tabular_table').setValue(self.table_model)
        except Exception as e:
            logger.exception(str(e))

        if scan_type == 'Sequential' or scan_type == 'Tabular':
            self.table_view.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.table_view.horizontalHeader().setStretchLastSection(True)
            self.table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
            self.table_view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
            styledItemDelegate = QtWidgets.QStyledItemDelegate()
            styledItemDelegate.setItemEditorFactory(gutils.SpinBoxDelegate())
            self.table_view.setItemDelegate(styledItemDelegate)

            self.table_view.setDragEnabled(True)
            self.table_view.setDropIndicatorShown(True)
            self.table_view.setAcceptDrops(True)
            self.table_view.viewport().setAcceptDrops(True)
            self.table_view.setDefaultDropAction(QtCore.Qt.MoveAction)
            self.table_view.setDragDropMode(QtWidgets.QTableView.InternalMove)
            self.table_view.setDragDropOverwriteMode(False)

        if scan_type == 'Tabular':
            self.table_view.add_data_signal[int].connect(self.table_model.add_data)
            self.table_view.remove_row_signal[int].connect(self.table_model.remove_data)
            self.table_view.load_data_signal.connect(self.table_model.load_txt)
            self.table_view.save_data_signal.connect(self.table_model.save_txt)

    @property
    def viewers_items(self):
        return self.scan_selector.viewers_items

    @viewers_items.setter
    def viewers_items(self, items):
        self.scan_selector.remove_scan_selector()
        self.scan_selector.viewers_items = items
        self.settings.child('tabular_settings', 'tabular_roi_module').setOpts(
            limits=self.scan_selector.sources_names)
        self.settings.child('scan2D_settings', 'scan2D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)

    def parameter_tree_changed(self, param, changes):
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

                    if data == 'Scan1D':
                        self.settings.child('scan1D_settings').show()
                        self.settings.child('scan2D_settings').hide()
                        self.settings.child('seq_settings').hide()
                        self.settings.child('tabular_settings').hide()
                        self.settings_tree.setMaximumHeight(500)

                    elif data == 'Scan2D':
                        self.settings.child('scan1D_settings').hide()
                        self.settings.child('scan2D_settings').show()
                        self.settings.child('seq_settings').hide()
                        self.settings.child('tabular_settings').hide()
                        self.settings_tree.setMaximumHeight(500)
                        self.scan_selector.settings.child('scan_options', 'scan_type').setValue(data)
                        if self.settings.child('scan2D_settings',
                                               'scan2D_selection').value() == 'Manual':
                            self.scan_selector.show_scan_selector(visible=False)
                        else:
                            self.scan_selector.show_scan_selector(visible=True)
                            self.update_scan_2D_positions()
                        self.update_scan2D_type(param)

                    elif data == 'Sequential':
                        self.settings.child('scan1D_settings').hide()
                        self.settings.child('scan2D_settings').hide()
                        self.settings.child('seq_settings').show()
                        self.settings.child('tabular_settings').hide()
                        self.update_model()
                        self.settings_tree.setMaximumHeight(600)

                    elif data == 'Tabular':
                        self.settings.child('scan1D_settings').hide()
                        self.settings.child('scan2D_settings').hide()
                        self.settings.child('seq_settings').hide()
                        self.settings.child('tabular_settings').show()
                        self.settings.child('tabular_settings', 'tabular_step').hide()

                        self.update_tabular_positions()
                        self.settings_tree.setMaximumHeight(600)
                        self.scan_selector.settings.child('scan_options', 'scan_type').setValue(data)
                        if self.settings.child('tabular_settings',
                                               'tabular_selection').value() == 'Manual':
                            self.scan_selector.show_scan_selector(visible=False)
                        else:
                            self.scan_selector.show_scan_selector(visible=True)

                elif param.name() == 'scan1D_type':
                    status = 'adaptive' in param.value().lower()
                    self.settings.child('scan1D_settings', 'scan1D_loss').show(status)

                elif param.name() == 'tabular_subtype':
                    isadaptive = 'adaptive' in self.settings.child('tabular_settings',
                                                                   'tabular_subtype').value().lower()
                    ismanual = self.settings.child('tabular_settings',
                                                   'tabular_selection').value() == 'Manual'
                    self.settings.child('tabular_settings', 'tabular_loss').show(isadaptive)
                    self.settings.child('tabular_settings',
                                        'tabular_step').show(not isadaptive and not ismanual)
                    self.update_tabular_positions()

                elif param.name() == 'tabular_roi_module' or param.name() == 'scan2D_roi_module':
                    self.scan_selector.settings.child('scan_options', 'sources').setValue(param.value())

                elif param.name() == 'tabular_selection':
                    isadaptive = 'adaptive' in self.settings.child('tabular_settings',
                                                                   'tabular_subtype').value().lower()
                    ismanual = self.settings.child('tabular_settings',
                                                   'tabular_selection').value() == 'Manual'
                    self.settings.child('tabular_settings',
                                        'tabular_step').show(not isadaptive and not ismanual)
                    if data == 'Polylines':
                        self.settings.child('tabular_settings', 'tabular_roi_module').show()
                        self.scan_selector.show_scan_selector(visible=True)
                    else:
                        self.settings.child('tabular_settings', 'tabular_roi_module').hide()
                        self.scan_selector.show_scan_selector(visible=False)
                        self.update_tabular_positions()

                elif param.name() == 'tabular_step':
                    self.update_tabular_positions()
                    self.set_scan()

                elif param.name() == 'scan2D_selection':
                    if param.value() == 'Manual':
                        self.scan_selector.show_scan_selector(visible=False)
                        self.settings.child('scan2D_settings', 'scan2D_roi_module').hide()
                    else:
                        self.scan_selector.show_scan_selector(visible=True)
                        self.settings.child('scan2D_settings', 'scan2D_roi_module').show()

                    self.update_scan2D_type(param)

                elif param.name() in putils.iter_children(self.settings.child('scan2D_settings'), []):
                    self.update_scan2D_type(param)
                    self.set_scan()

                elif param.name() == 'Nsteps':
                    pass  # just do nothing (otherwise set_scan will be fired, see below)

                else:
                    try:
                        self.set_scan()
                    except Exception as e:
                        logger.error(f'Invalid call to setScan ({str(e)})')

            elif change == 'parent':
                pass

    def setupUI(self):
        # layout = QtWidgets.QHBoxLayout()
        # layout.setSpacing(0)
        # self.parent.setLayout(layout)
        self.settings_tree = ParameterTree()
        self.settings = Parameter.create(name='Scanner_Settings', title='Scanner Settings', type='group',
                                         children=self.params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings_tree.setMaximumHeight(500)

        self.settings.child('calculate_positions').sigActivated.connect(self.set_scan)
        # layout.addWidget(self.settings_tree)

    def set_scan(self):
        scan_type = self.settings.child('scan_type').value()

        if scan_type == "Scan1D":
            start = self.settings.child('scan1D_settings', 'start_1D').value()
            stop = self.settings.child('scan1D_settings', 'stop_1D').value()
            step = self.settings.child('scan1D_settings', 'step_1D').value()
            self.scan_parameters = ScanParameters(Naxes=1, scan_type="Scan1D",
                                                  scan_subtype=self.settings.child('scan1D_settings',
                                                                                   'scan1D_type').value(),
                                                  starts=[start], stops=[stop], steps=[step],
                                                  adaptive_loss=self.settings.child('scan1D_settings',
                                                                                    'scan1D_loss').value())

        elif scan_type == "Scan2D":
            starts = [self.settings.child('scan2D_settings', 'start_2d_axis1').value(),
                      self.settings.child('scan2D_settings', 'start_2d_axis2').value()]
            stops = [self.settings.child('scan2D_settings', 'stop_2d_axis1').value(),
                     self.settings.child('scan2D_settings', 'stop_2d_axis2').value()]
            steps = [self.settings.child('scan2D_settings', 'step_2d_axis1').value(),
                     self.settings.child('scan2D_settings', 'step_2d_axis2').value()]
            self.scan_parameters = ScanParameters(Naxes=2, scan_type="Scan2D",
                                                  scan_subtype=self.settings.child('scan2D_settings',
                                                                                   'scan2D_type').value(),
                                                  starts=starts, stops=stops, steps=steps,
                                                  adaptive_loss=self.settings.child('scan2D_settings',
                                                                                    'scan2D_loss').value())

        elif scan_type == "Sequential":
            starts = [self.table_model.get_data(ind, 1) for ind in range(self.table_model.rowCount(None))]
            stops = [self.table_model.get_data(ind, 2) for ind in range(self.table_model.rowCount(None))]
            steps = [self.table_model.get_data(ind, 3) for ind in range(self.table_model.rowCount(None))]
            self.scan_parameters = ScanParameters(Naxes=len(starts), scan_type="Sequential",
                                                  scan_subtype=self.settings.child('seq_settings',
                                                                                   'scanseq_type').value(),
                                                  starts=starts, stops=stops, steps=steps)

        elif scan_type == 'Tabular':
            positions = np.array(self.table_model.get_data_all())
            Naxes = positions.shape[1]
            if self.settings.child('tabular_settings', 'tabular_subtype').value() == 'Adaptive':
                starts = positions[:-1]
                stops = positions[1:]
                steps = [self.settings.child('tabular_settings', 'tabular_step').value()]
                positions = None
            else:
                starts = None
                stops = None
                steps = None

            self.scan_parameters = ScanParameters(Naxes=Naxes, scan_type="Tabular",
                                                  scan_subtype=self.settings.child('tabular_settings',
                                                                                   'tabular_subtype').value(),
                                                  starts=starts, stops=stops, steps=steps, positions=positions,
                                                  adaptive_loss=self.settings.child('tabular_settings',
                                                                                    'tabular_loss').value())

        self.settings.child('Nsteps').setValue(self.scan_parameters.Nsteps)
        self.scan_params_signal.emit(self.scan_parameters)
        return self.scan_parameters

    def update_tabular_positions(self):
        try:
            if self.settings.child('scan_type').value() == 'Tabular':
                if self.settings.child('tabular_settings',
                                       'tabular_selection').value() == 'Polylines':  # from ROI
                    viewer = self.scan_selector.scan_selector_source

                    if self.settings.child('tabular_settings', 'tabular_subtype').value() == 'Linear':
                        positions = self.scan_selector.scan_selector.getArrayIndexes(
                            spacing=self.settings.child('tabular_settings', 'tabular_step').value())
                    elif self.settings.child('tabular_settings',
                                             'tabular_subtype').value() == 'Adaptive':
                        positions = self.scan_selector.scan_selector.get_vertex()

                    steps_x, steps_y = zip(*positions)
                    steps_x, steps_y = viewer.scale_axis(np.array(steps_x), np.array(steps_y))
                    positions = np.transpose(np.array([steps_x, steps_y]))
                    self.update_model(init_data=positions)
                else:
                    self.update_model()
            else:
                self.update_model()
        except Exception as e:
            logger.exception(str(e))

    def update_scan_2D_positions(self):
        try:
            viewer = self.scan_selector.scan_selector_source
            pos_dl = self.scan_selector.scan_selector.pos()
            pos_ur = self.scan_selector.scan_selector.pos() + self.scan_selector.scan_selector.size()
            pos_dl_scaled = viewer.scale_axis(pos_dl[0], pos_dl[1])
            pos_ur_scaled = viewer.scale_axis(pos_ur[0], pos_ur[1])

            if self.settings.child('scan2D_settings', 'scan2D_type').value() == 'Spiral':
                self.settings.child('scan2D_settings', 'start_2d_axis1').setValue(
                    np.mean((pos_dl_scaled[0], pos_ur_scaled[0])))
                self.settings.child('scan2D_settings', 'start_2d_axis2').setValue(
                    np.mean((pos_dl_scaled[1], pos_ur_scaled[1])))

                nsteps = 2 * np.min((np.abs((pos_ur_scaled[0] - pos_dl_scaled[0]) / 2) / self.settings.child(
                     'scan2D_settings', 'step_2d_axis1').value(), np.abs(
                    (pos_ur_scaled[1] - pos_dl_scaled[1]) / 2) / self.settings.child(
                     'scan2D_settings', 'step_2d_axis2').value()))

                self.settings.child('scan2D_settings', 'npts_by_axis').setValue(nsteps)

            else:
                self.settings.child('scan2D_settings', 'start_2d_axis1').setValue(pos_dl_scaled[0])
                self.settings.child('scan2D_settings', 'start_2d_axis2').setValue(pos_dl_scaled[1])
                self.settings.child('scan2D_settings', 'stop_2d_axis1').setValue(pos_ur_scaled[0])
                self.settings.child('scan2D_settings', 'stop_2d_axis2').setValue(pos_ur_scaled[1])

        except Exception as e:
            raise ScannerException(str(e))

    def update_scan2D_type(self, param):
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
            self.settings.child('scan2D_settings', 'step_2d_axis1').show()
            self.settings.child('scan2D_settings', 'step_2d_axis2').show()
            scan_subtype = self.settings.child('scan2D_settings', 'scan2D_type').value()
            self.settings.child('scan2D_settings', 'scan2D_loss').show(scan_subtype == 'Adaptive')
            if scan_subtype == 'Adaptive':
                if self.settings.child('scan2D_settings', 'scan2D_loss').value() == 'resolution':
                    self.settings.child('scan2D_settings', 'step_2d_axis1').setOpts(
                        title='Minimal feature (%):',
                        tip='Features smaller than this will not be probed first. In percent of maximal scanned area length',
                        visible=True)
                    self.settings.child('scan2D_settings', 'step_2d_axis2').setOpts(
                        title='Maximal feature (%):',
                        tip='Features bigger than this will be probed first. In percent of maximal scanned area length',
                        visible=True)
                else:
                    self.settings.child('scan2D_settings', 'step_2d_axis1').hide()
                    self.settings.child('scan2D_settings', 'step_2d_axis2').hide()
            else:
                self.settings.child('scan2D_settings', 'step_2d_axis1').setOpts(title='Step Ax1:',
                                                                                                tip='Step size for ax1 in actuator units')
                self.settings.child('scan2D_settings', 'step_2d_axis2').setOpts(title='Step Ax2:',
                                                                                                tip='Step size for ax2 in actuator units')

            if scan_subtype == 'Spiral':
                self.settings.child('scan2D_settings',
                                    'start_2d_axis1').setOpts(title='Center Ax1')
                self.settings.child('scan2D_settings',
                                    'start_2d_axis2').setOpts(title='Center Ax2')

                self.settings.child('scan2D_settings',
                                    'stop_2d_axis1').setOpts(title='Rmax Ax1', readonly=True,
                                                             tip='Read only for Spiral scan type, set the step and Npts/axis')
                self.settings.child('scan2D_settings',
                                    'stop_2d_axis2').setOpts(title='Rmax Ax2', readonly=True,
                                                             tip='Read only for Spiral scan type, set the step and Npts/axis')
                self.settings.child('scan2D_settings',
                                    'npts_by_axis').show()

                # do some checks and set stops values
                self.settings.sigTreeStateChanged.disconnect()
                if param.name() == 'step_2d_axis1':
                    if param.value() < 0:
                        param.setValue(-param.value())

                if param.name() == 'step_2d_axis2':
                    if param.value() < 0:
                        param.setValue(-param.value())

                self.settings.child('scan2D_settings', 'stop_2d_axis1').setValue(
                    np.rint(self.settings.child(
                         'scan2D_settings', 'npts_by_axis').value() / 2) * np.abs(
                        self.settings.child('scan2D_settings', 'step_2d_axis1').value()))

                self.settings.child('scan2D_settings', 'stop_2d_axis2').setValue(
                    np.rint(self.settings.child(
                         'scan2D_settings', 'npts_by_axis').value() / 2) * np.abs(
                        self.settings.child('scan2D_settings', 'step_2d_axis2').value()))
                QtWidgets.QApplication.processEvents()
                self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)
            else:
                self.settings.child('scan2D_settings',
                                    'start_2d_axis1').setOpts(title='Start Ax1')
                self.settings.child('scan2D_settings',
                                    'start_2d_axis2').setOpts(title='Start Ax2')

                self.settings.child('scan2D_settings',
                                    'stop_2d_axis1').setOpts(title='Stop Ax1', readonly=False,
                                                             tip='Set the stop positions')
                self.settings.child('scan2D_settings',
                                    'stop_2d_axis2').setOpts(title='StopAx2', readonly=False,
                                                             tip='Set the stop positions')
                self.settings.child('scan2D_settings', 'npts_by_axis').hide()
        except Exception as e:
            raise ScannerException(str(e))


class TableModelTabular(gutils.TableModel):
    def __init__(self, data, axes_name=None, **kwargs):
        if axes_name is None:
            if 'header' in kwargs:  # when saved as XML the header will be saved and restored here
                axes_name = [h for h in kwargs['header']]
                kwargs.pop('header')
            else:
                raise Exception('Invalid header')

        header = [name for name in axes_name]
        editable = [True for name in axes_name]
        super().__init__(data, header, editable=editable, **kwargs)

    @pyqtSlot(int)
    def add_data(self, row, data=None):
        if data is not None:
            self.insert_data(row, [float(d) for d in data])
        else:
            self.insert_data(row, [0. for name in self.header])

    @pyqtSlot(int)
    def remove_data(self, row):
        self.remove_row(row)

    def load_txt(self):
        fname = gutils.select_file(start_path=None, save=False, ext='*')
        if fname is not None and fname != '':
            while self.rowCount(self.index(-1, -1)) > 0:
                self.remove_row(0)

            data = np.loadtxt(fname)
            if len(data.shape) == 1:
                data = data.reshape((data.size, 1))
            self.set_data_all(data)

    def save_txt(self):
        fname = gutils.select_file(start_path=None, save=True, ext='dat')
        if fname is not None and fname != '':
            np.savetxt(fname, self.get_data_all(), delimiter='\t')

    def __repr__(self):
        return f'{self.__class__.__name__} from module {self.__class__.__module__}'

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

        return True


class TableModelSequential(gutils.TableModel):
    def __init__(self, data, **kwargs):
        header = ['Actuator', 'Start', 'Stop', 'Step']
        if 'header' in kwargs:
            kwargs.pop('header')
        editable = [False, True, True, True]
        super().__init__(data, header, editable=editable, **kwargs)

    def __repr__(self):
        return f'{self.__class__.__name__} from module {self.__class__.__module__}'

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
        if col == 1:  # the start
            start = value
        elif col == 2:  # the stop
            stop = value
        else:  # the step
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


def set_scan_linear(starts, stops, steps, back_and_force=False, oversteps=10000):
    """
        Set a linear scan
    Parameters
    ----------
    starts
    stops
    steps
    back_and_force: (bool) if True insert between two steps a position back to start (to be used as a reference in the scan analysis)
    oversteps: (int) maximum number of calculated steps (stops the steps calculation if over the first power of 2 greater than oversteps)

    Returns
    -------
    positions (ndarray)

    See Also
    --------
    ScanParameters
    """
    starts = np.array(starts)
    stops = np.array(stops)
    steps = np.array(steps)

    if np.any(np.abs(steps) < 1e-12) or \
            np.any(np.sign(stops - starts) != np.sign(steps)) or \
            np.any(starts == stops):
        return np.array([starts])

    else:
        axis_1_unique = linspace_step(starts[0], stops[0], steps[0])
        len1 = len(axis_1_unique)

        axis_2_unique = linspace_step(starts[1], stops[1], steps[1])
        len2 = len(axis_2_unique)
        # if number of steps is over oversteps, reduce both axis in the same ratio
        if len1 * len2 > oversteps:
            axis_1_unique = axis_1_unique[:int(np.ceil(np.sqrt(oversteps * len1 / len2)))]
            axis_2_unique = axis_2_unique[:int(np.ceil(np.sqrt(oversteps * len2 / len1)))]

        positions = []
        for ind_x, pos1 in enumerate(axis_1_unique):
            if back_and_force:
                for ind_y, pos2 in enumerate(axis_2_unique):
                    if not odd_even(ind_x):
                        positions.append([pos1, pos2])
                    else:
                        positions.append([pos1, axis_2_unique[len(axis_2_unique) - ind_y - 1]])
            else:
                for ind_y, pos2 in enumerate(axis_2_unique):
                    positions.append([pos1, pos2])

        return np.array(positions)


def set_scan_random(starts, stops, steps, oversteps=10000):
    """

    Parameters
    ----------
    starts
    stops
    steps
    oversteps

    Returns
    -------

    """

    positions = set_scan_linear(starts, stops, steps, back_and_force=False, oversteps=oversteps)
    np.random.shuffle(positions)
    return positions


def set_scan_spiral(starts, rmaxs, rsteps, nsteps=None, oversteps=10000):
    """Calculate the positions to describe a spiral type scan, starting from a center position and spiraling out from it

    Parameters
    ----------
    starts: (sequence like) containing the center positions of the scan
    rmaxs: (sequence like) containing the maximum radius (ellipse axes) in each direction
    rsteps: (sequence like) containing the step size for each axis
    nsteps: (int) If not None, this is used together with rsteps to calculate rmaxs
    oversteps: (int) maximum number of calculated steps (stops the steps calculation if over the first power of 2 greater than oversteps)

    Returns
    -------
    ndarray of all positions for each axis

    See Also
    --------
    ScanParameters
    """
    if np.isscalar(rmaxs):
        rmaxs = np.ones(starts.shape) * rmaxs
    else:
        rmaxs = np.array(rmaxs)
    if np.isscalar(rsteps):
        rsteps = np.ones(starts.shape) * rsteps
    else:
        rsteps = np.array(rsteps)

    starts = np.array(starts)

    if nsteps is not None:
        rmaxs = np.rint(nsteps / 2) * rsteps

    if np.any(np.array(rmaxs) == 0) or np.any(np.abs(rmaxs) < 1e-12) or np.any(np.abs(rsteps) < 1e-12):
        positions = np.array([starts])
        return positions

    ind = 0
    flag = True
    oversteps = greater2n(oversteps)  # make sure the position matrix is still a square

    Nlin = np.trunc(rmaxs / rsteps)
    if not np.all(Nlin == Nlin[0]):
        raise ScannerException(f'For Spiral 2D scans both axis should have same length, here: {Nlin.shape}')
    else:
        Nlin = Nlin[0]

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

    positions = []
    for ind in range(len(axis_1_indexes)):
        positions.append(np.array([axis_1_indexes[ind] * rsteps[0] + starts[0],
                                   axis_2_indexes[ind] * rsteps[1] + starts[1]]))

    return np.array(positions)


def pos_above_stops(positions, steps, stops):
    state = []
    for pos, step, stop in zip(positions, steps, stops):
        if step >= 0:
            state.append(pos > stop)
        else:
            state.append(pos < stop)
    return state


def set_scan_sequential(starts, stops, steps):
    """
    Create a list of positions (one for each actuator == one for each element in starts list) that are sequential
    Parameters
    ----------
    starts: (sequence like)
            list of starts of all selected actuators
    stops: (sequence like)
                list of stops of all selected actuators
    steps: (sequence like)

    Returns
    -------
    positions: (ndarray)
    """

    all_positions = [starts[:]]
    positions = starts[:]
    state = pos_above_stops(positions, steps, stops)
    while not state[0]:
        if not np.any(np.array(state)):
            positions[-1] += steps[-1]

        else:
            indexes_true = np.where(np.array(state))
            positions[indexes_true[-1][0]] = starts[indexes_true[-1][0]]
            positions[indexes_true[-1][0] - 1] += steps[indexes_true[-1][0] - 1]

        state = pos_above_stops(positions, steps, stops)
        if not np.any(np.array(state)):
            all_positions.append(positions[:])

    return np.array(all_positions)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    from PyQt5.QtCore import QThread
    from pymodaq.daq_utils.gui_utils import DockArea
    from pyqtgraph.dockarea import Dock
    from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
    from pymodaq.daq_utils.plotting.navigator import Navigator
    from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer

    class UI:
        def __init__(self):
            pass

    class FakeDaqScan:
        def __init__(self, area):
            self.area = area
            self.detector_modules = None
            self.ui = UI()
            self.dock = Dock('2D scan', size=(500, 300), closable=False)

            form = QtWidgets.QWidget()
            self.ui.scan2D_graph = Viewer2D(form)
            self.dock.addWidget(form)
            self.area.addDock(self.dock)

    def get_scan_params(param):
        print(param)
        print(param.scan_info.positions)

    #
    # ####simple sequential scan test
    # prog = Scanner(actuators=['Xaxis', 'Yaxis', 'Theta Axis'])
    # prog.settings_tree.show()
    # #prog.actuators = ['xxx', 'yyy']
    # prog.scan_params_signal.connect(get_scan_params)

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

    fake.detector_modules = [prog, prog2]
    items = OrderedDict()
    items[prog.title] = dict(viewers=[view for view in prog.ui.viewers],
                             names=[view.title for view in prog.ui.viewers],
                             )
    items['Navigator'] = dict(viewers=[prog2.viewer],
                              names=['Navigator'])
    items["DaqScan"] = dict(viewers=[fake.ui.scan2D_graph],
                            names=["DaqScan"])

    prog = Scanner(items, actuators=['Xaxis', 'Yaxis'])
    prog.settings_tree.show()
    prog.scan_params_signal.connect(get_scan_params)
    win.show()
    sys.exit(app.exec_())
