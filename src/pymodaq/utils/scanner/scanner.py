import sys
from collections import OrderedDict
import numpy as np

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QObject, Signal, Slot

from pymodaq.utils.parameter import ioxml
from pymodaq.utils.scanner.scan_factory import ScannerFactory, ScannerBase, SCANNER_SETTINGS_NAME
from pymodaq.utils.plotting.scan_selector import ScanSelector
from pymodaq.utils.managers.parameter_manager import ParameterManager

import pymodaq.utils.daq_utils as utils
import pymodaq.utils.gui_utils as gutils
import pymodaq.utils.math_utils as mutils
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.plotting.utils.plot_utils import QVector


from .utils import ScanParameters, ScanInfo, ScanType, SCAN_SUBTYPES, ScannerException

logger = set_logger(get_module_name(__file__))
config = Config()
scanner_factory = ScannerFactory()


class MainScanner(ParameterManager):
    """Main Object to define a PyMoDAQ scan and create a UI to set it

    Parameters
    ----------
    scanner_items: (items used by ScanSelector for chosing scan area or linear traces)
    actuators: list of actuators names

    Attributes
    ----------
    table_model: TableModelSequential or TableModelTabular
    table_view: pymodaq_types.TableViewCustom
    scan_selector: ScanSelector

    See Also
    --------
    ScanSelector, TableModelSequential, TableModelTabular, pymodaq_types.TableViewCustom
    """
    scan_params_signal = Signal(ScanParameters)

    params = [
        {'title': 'Calculate positions:', 'name': 'calculate_positions', 'type': 'action'},
        {'title': 'N steps:', 'name': 'Nsteps', 'type': 'int', 'value': 0, 'readonly': True},
        {'title': 'Settings', 'name': SCANNER_SETTINGS_NAME, 'type': 'group'},
    ]

    def __init__(self, scanner_items=OrderedDict([]), actuators=[]):
        super().__init__()

        self.connect_things()
        self._scanner: ScannerBase = None

        self.set_scanner()
        self.settings.child('n_steps').setValue(self._scanner.evaluate_steps())

        # self.scan_selector = ScanSelector(scanner_items, scan_type)
        # self.scan_selector.scan_select_signal.connect(self.update_scan_2D_positions)
        # self.scan_selector.scan_select_signal.connect(lambda: self.update_tabular_positions())
        # self.scan_selector.widget.setVisible(False)
        # self.scan_selector.show_scan_selector(visible=False)

        # self.settings.child('tabular_settings', 'tabular_roi_module').setOpts(
        #     limits=self.scan_selector.sources_names)
        # self.settings.child('scan2D_settings', 'scan2D_roi_module').setOpts(
        #     limits=self.scan_selector.sources_names)
        # self.table_model = None

        self.actuators = actuators

    def set_scanner(self):
        try:
            self._scanner: ScannerBase = scanner_factory.get(self.settings['scan_type'],
                                                             self.settings['scan_sub_type'])

            self._scanner.settings.sigTreeStateChanged.connect(self.update_local_settings)

            while len(self.settings.child(SCANNER_SETTINGS_NAME).children()) > 0:
                self.settings.child(SCANNER_SETTINGS_NAME).removeChild(
                    self.settings.child(SCANNER_SETTINGS_NAME).children()[0])

            self.settings.child(SCANNER_SETTINGS_NAME).restoreState(self._scanner.settings.saveState())
        except ValueError:
            pass

    def update_local_settings(self, param, changes):
        """Apply a change from the settings in the Scanner object to the local settings"""
        for param, change, data in changes:
            if change == 'value':
                self.settings.child(*putils.get_param_path(param)).setValue(data)

    def value_changed(self, param):
        if param.name() == 'scan_type':
            self.settings.child('scan_sub_type').setOpts(
                limits=scanner_factory.scan_sub_types(param.value()))

        if param.name() in ['scan_type', 'scan_sub_type']:
            self.set_scanner()

        if param.name() in putils.iter_children(self.settings.child(SCANNER_SETTINGS_NAME), []):
            self._scanner.settings.child(*putils.get_param_path(param)[2:]).setValue(param.value())

        self.settings.child('n_steps').setValue(self._scanner.evaluate_steps())

    @property
    def actuators(self):
        """list of str: Returns as a list the name of the selected actuators to describe the actual scan"""
        return self._actuators

    @actuators.setter
    def actuators(self, act_list):
        self._actuators = act_list
        self.update_model()

    def update_model(self, init_data=None):
        """Update the model of the Sequential or Tabular view according to the selected actuators

        Parameters
        ----------
        init_data: list of float (optional)
            The initial values for the associated table
        """
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
        """Add 2D viewer objects where one can plot ROI or Polylines to define a Scan using the ScanSelector

        Parameters
        ----------
        items: list of Viewer2D

        See Also
        --------
        Viewer2D, ScanSelector
        """
        self.scan_selector.remove_scan_selector()
        self.scan_selector.viewers_items = items
        self.settings.child('tabular_settings', 'tabular_roi_module').setOpts(
            limits=self.scan_selector.sources_names)
        self.settings.child('scan2D_settings', 'scan2D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)

    def set_scan_type_and_subtypes(self, scan_type: str, scan_subtype=None):
        """Convenience function to set the main scan type

        Parameters
        ----------
        scan_type: str
            one of ScanType
        scan_subtype: list of str or None
            one list of SCAN_SUBTYPES
        """
        if scan_type in ScanType.names():
            self.settings.child('scan_type').setValue(scan_type)

            if scan_subtype is not None:
                if scan_subtype in SCAN_SUBTYPES[scan_type]['limits']:
                    self.settings.child(*SCAN_SUBTYPES[scan_type]['subpath']).setValue(scan_subtype)

    def parameter_tree_changed(self, param, changes):
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

    def connect_things(self):
        self.settings.child('calculate_positions').sigActivated.connect(self.set_scan)


    def set_scan(self):
        """Process the settings options to calculate the scan positions

        Returns
        -------
        ScanParameters
        """
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

    def update_tabular_positions(self, positions: np.ndarray = None):
        """Convenience function to write positions directly into the tabular table

        Parameters
        ----------
        positions: ndarray
            a 2D ndarray with as many columns as selected actuators
        """
        try:
            if self.settings.child('scan_type').value() == 'Tabular':
                if positions is None:
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
                elif isinstance(positions, np.ndarray):
                    self.update_model(init_data=positions)
                else:
                    pass
            else:
                self.update_model()
        except Exception as e:
            logger.exception(str(e))

    def update_scan_2D_positions(self):
        """Compute scan positions from the ROI set with the scan_selector"""
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
        """Update the 2D scan type from the given parameter.
        """
        try:
            self.settings.child('scan2D_settings', 'step_2d_axis1').show()
            self.settings.child('scan2D_settings', 'step_2d_axis2').show()
            scan_subtype = self.settings.child('scan2D_settings', 'scan2D_type').value()
            self.settings.child('scan2D_settings', 'scan2D_loss').show(scan_subtype == 'Adaptive')
            if scan_subtype == 'Adaptive':
                if self.settings.child('scan2D_settings', 'scan2D_loss').value() == 'resolution':
                    title = 'Minimal feature (%):'
                    if self.settings.child('scan2D_settings', 'step_2d_axis1').opts['title'] != title:
                        self.settings.child('scan2D_settings', 'step_2d_axis1').setValue(1)
                        self.settings.child('scan2D_settings', 'step_2d_axis2').setValue(100)

                    self.settings.child('scan2D_settings', 'step_2d_axis1').setOpts(
                        limits=[0, 100], title=title, visible=True,
                        tip='Features smaller than this will not be probed first. In percent of maximal scanned area'
                            ' length',
                        )
                    self.settings.child('scan2D_settings', 'step_2d_axis2').setOpts(
                        limits=[0, 100], title='Maximal feature (%):', visible=True,
                        tip='Features bigger than this will be probed first. In percent of maximal scanned area length',
                        )

                else:
                    self.settings.child('scan2D_settings', 'step_2d_axis1').hide()
                    self.settings.child('scan2D_settings', 'step_2d_axis2').hide()
            else:
                self.settings.child('scan2D_settings',
                                    'step_2d_axis1').setOpts(title='Step Ax1:',
                                                             tip='Step size for ax1 in actuator units')
                self.settings.child('scan2D_settings',
                                    'step_2d_axis2').setOpts(title='Step Ax2:',
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



class Scanner(QObject):
    """Main Object to define a PyMoDAQ scan and create a UI to set it

    Parameters
    ----------
    scanner_items: (items used by ScanSelector for chosing scan area or linear traces)
    scan_type: type of scan selector
    actuators: list of actuators names
    adaptive_losses

    Attributes
    ----------
    table_model: TableModelSequential or TableModelTabular
    table_view: pymodaq_types.TableViewCustom
    scan_selector: ScanSelector

    See Also
    --------
    ScanSelector, TableModelSequential, TableModelTabular, pymodaq_types.TableViewCustom
    """
    scan_params_signal = Signal(ScanParameters)

    params = [#{'title': 'Scanner settings', 'name': 'scan_options', 'type': 'group', 'children': [
        {'title': 'Calculate positions:', 'name': 'calculate_positions', 'type': 'action'},
        {'title': 'N steps:', 'name': 'Nsteps', 'type': 'int', 'value': 0, 'readonly': True},

        {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'limits': ScanType.names(),
         'value': config('scan', 'default')},
        {'title': 'Scan1D settings', 'name': 'scan1D_settings', 'type': 'group', 'children': [
            {'title': 'Scan subtype:', 'name': 'scan1D_type', 'type': 'list',
             'limits': SCAN_SUBTYPES['Scan1D']['limits'], 'value': config('scan', 'scan1D', 'type'),
             'tip': 'For adaptive, an algo will '
                    'determine the positions to check within the scan bounds. The defined step will be set as the'
                    'biggest feature size the algo should reach.'},
            {'title': 'Loss type', 'name': 'scan1D_loss', 'type': 'list',
             'limits': [], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Start:', 'name': 'start_1D', 'type': 'float', 'value': config('scan', 'scan1D', 'start')},
            {'title': 'stop:', 'name': 'stop_1D', 'type': 'float', 'value': config('scan', 'scan1D', 'stop')},
            {'title': 'Step:', 'name': 'step_1D', 'type': 'float', 'value': config('scan', 'scan1D', 'step')}
        ]},
        {'title': 'Scan2D settings', 'name': 'scan2D_settings', 'type': 'group', 'visible': False, 'children': [
            {'title': 'Scan subtype:', 'name': 'scan2D_type', 'type': 'list',
             'limits': SCAN_SUBTYPES['Scan2D']['limits'], 'value': config('scan', 'scan2D', 'type'),
             'tip': 'For adaptive, an algo will '
                    'determine the positions to check within the scan bounds. The defined step will be set as the'
                    'biggest feature size the algo should reach.'},
            {'title': 'Loss type', 'name': 'scan2D_loss', 'type': 'list',
             'limits': [], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Selection:', 'name': 'scan2D_selection', 'type': 'list', 'limits': ['Manual', 'FromROI']},
            {'title': 'From module:', 'name': 'scan2D_roi_module', 'type': 'list', 'limits': [], 'visible': False},
            {'title': 'Start Ax1:', 'name': 'start_2d_axis1', 'type': 'float',
             'value': config('scan', 'scan2D', 'start1'), 'visible': True},
            {'title': 'Start Ax2:', 'name': 'start_2d_axis2', 'type': 'float',
             'value': config('scan', 'scan2D', 'start2'), 'visible': True},
            {'title': 'Step Ax1:', 'name': 'step_2d_axis1', 'type': 'float',
             'value': config('scan', 'scan2D', 'step1'), 'visible': True},
            {'title': 'Step Ax2:', 'name': 'step_2d_axis2', 'type': 'float',
             'value': config('scan', 'scan2D', 'step2'), 'visible': True},
            {'title': 'Npts/axis', 'name': 'npts_by_axis', 'type': 'int', 'min': 1,
             'value': config('scan', 'scan2D', 'npts'),
             'visible': True},
            {'title': 'Stop Ax1:', 'name': 'stop_2d_axis1', 'type': 'float',
             'value': config('scan', 'scan2D', 'stop1'), 'visible': True,
             'readonly': True, },
            {'title': 'Stop Ax2:', 'name': 'stop_2d_axis2', 'type': 'float',
             'value': config('scan', 'scan2D', 'stop2'), 'visible': True,
             'readonly': True, },

        ]},
        {'title': 'Sequential settings', 'name': 'seq_settings', 'type': 'group', 'visible': False, 'children': [
            {'title': 'Scan subtype:', 'name': 'scanseq_type', 'type': 'list',
             'limits': SCAN_SUBTYPES['Sequential']['limits'], 'value': SCAN_SUBTYPES['Sequential']['limits'][0], },
            {'title': 'Sequences', 'name': 'seq_table', 'type': 'table_view',
             'delegate': gutils.SpinBoxDelegate},
        ]},
        {'title': 'Tabular settings', 'name': 'tabular_settings', 'type': 'group', 'visible': False, 'children': [
            {'title': 'Scan subtype:', 'name': 'tabular_subtype', 'type': 'list',
             'limits': SCAN_SUBTYPES['Tabular']['limits'], 'value': config('scan', 'tabular', 'type'),
             'tip': 'For adaptive, an algo will '
                    'determine the positions to check within the scan bounds. The defined step will be set as the'
                    'biggest feature size the algo should reach.'},
            {'title': 'Loss type', 'name': 'tabular_loss', 'type': 'list',
             'limits': [], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Selection:', 'name': 'tabular_selection', 'type': 'list',
             'limits': ['Manual', 'Polylines']},
            {'title': 'From module:', 'name': 'tabular_roi_module', 'type': 'list', 'limits': [],
             'visible': False},
            {'title': 'Curvilinear Step:', 'name': 'tabular_step', 'type': 'float',
             'value': config('scan', 'tabular', 'curvilinear')},
            {'title': 'Positions', 'name': 'tabular_table', 'type': 'table_view',
             'delegate': gutils.SpinBoxDelegate, 'menu': True},
        ]},
        {'title': 'Load settings', 'name': 'load_xml', 'type': 'action'},
        {'title': 'Save settings', 'name': 'save_xml', 'type': 'action'},
    ]#}]

    def __init__(self, scanner_items=OrderedDict([]), scan_type='Scan1D', actuators=[], adaptive_losses=None):
        super().__init__()

        self.settings_tree = None
        self.setupUI()

        self.scan_selector = ScanSelector(scanner_items, scan_type)
        self.settings.child('scan_type').setValue(scan_type)
        # self.scan_selector.settings.child('scan_options', 'scan_type').hide()
        self.scan_selector.scan_select_signal.connect(self.update_scan_2D_positions)
        self.scan_selector.scan_select_signal.connect(lambda: self.update_tabular_positions())

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

        self.actuators = actuators
        # if actuators != []:
        #     self.actuators = actuators
        # else:
        #     stypes = ScanType[:]
        #     stypes.pop(stypes.index('Sequential'))
        #     self.settings.child('scan_type').setLimits(stypes)
        #     self.settings.child('scan_type').setValue(stypes[0])

        self.scan_selector.widget.setVisible(False)
        self.scan_selector.show_scan_selector(visible=False)
        self.settings.child('load_xml').sigActivated.connect(self.load_xml)
        self.settings.child('save_xml').sigActivated.connect(self.save_xml)

        self.set_scan()
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    def load_xml(self):
        """Load settings, previously saved, from a xml file

        See Also
        --------
        save_xml
        """
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
        """Save current settings to a xml file

        See Also
        --------
        load_xml
        """
        fname = gutils.select_file(start_path=None, save=True, ext='xml')
        if fname is not None and fname != '':
            ioxml.parameter_to_xml_file(self.settings, fname)

    def set_config(self):
        """Set the scanner settings according to configuration file

        See Also
        --------
        :ref:`configfile`
        """
        scan_type = config['scan']['default']
        self.settings.child('scan_type').setValue(scan_type)

        self.settings.child('scan1D_settings', 'scan1D_type').setValue(config('scan', 'scan1D', 'type'))
        self.settings.child('scan1D_settings', 'start_1D').setValue(config('scan', 'scan1D', 'start'))
        self.settings.child('scan1D_settings', 'stop_1D').setValue(config('scan', 'scan1D', 'stop'))
        self.settings.child('scan1D_settings', 'step_1D').setValue(config('scan', 'scan1D', 'step'))

        self.settings.child('scan2D_settings', 'scan2D_type').setValue(config('scan', 'scan2D', 'type'))
        self.settings.child('scan2D_settings', 'start_2d_axis1').setValue(
            config('scan', 'scan2D', 'start1'))
        self.settings.child('scan2D_settings', 'start_2d_axis2').setValue(
            config('scan', 'scan2D', 'start2'))
        self.settings.child('scan2D_settings', 'step_2d_axis2').setValue(
            config('scan', 'scan2D', 'step1'))
        self.settings.child('scan2D_settings', 'step_2d_axis2').setValue(
            config('scan', 'scan2D', 'step2'))
        self.settings.child('scan2D_settings', 'npts_by_axis').setValue(
            config('scan', 'scan2D', 'npts'))
        self.settings.child('scan2D_settings', 'stop_2d_axis1').setValue(
            config('scan', 'scan2D', 'stop1'))
        self.settings.child('scan2D_settings', 'stop_2d_axis2').setValue(
            config('scan', 'scan2D', 'stop2'))

        self.settings.child('tabular_settings', 'tabular_subtype').setValue(
            config('scan', 'tabular', 'type'))
        self.settings.child('tabular_settings', 'tabular_step').setValue(
            config('scan', 'tabular', 'curvilinear'))

    @property
    def actuators(self):
        """list of str: Returns as a list the name of the selected actuators to describe the actual scan"""
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
        """Update the model of the Sequential or Tabular view according to the selected actuators

        Parameters
        ----------
        init_data: list of float (optional)
            The initial values for the associated table
        """
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
        """Add 2D viewer objects where one can plot ROI or Polylines to define a Scan using the ScanSelector

        Parameters
        ----------
        items: list of Viewer2D

        See Also
        --------
        Viewer2D, ScanSelector
        """
        self.scan_selector.remove_scan_selector()
        self.scan_selector.viewers_items = items
        self.settings.child('tabular_settings', 'tabular_roi_module').setOpts(
            limits=self.scan_selector.sources_names)
        self.settings.child('scan2D_settings', 'scan2D_roi_module').setOpts(
            limits=self.scan_selector.sources_names)

    def set_scan_type_and_subtypes(self, scan_type: str, scan_subtype=None):
        """Convenience function to set the main scan type

        Parameters
        ----------
        scan_type: str
            one of ScanType
        scan_subtype: list of str or None
            one list of SCAN_SUBTYPES
        """
        if scan_type in ScanType.names():
            self.settings.child('scan_type').setValue(scan_type)

            if scan_subtype is not None:
                if scan_subtype in SCAN_SUBTYPES[scan_type]['limits']:
                    self.settings.child(*SCAN_SUBTYPES[scan_type]['subpath']).setValue(scan_subtype)

    def parameter_tree_changed(self, param, changes):
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
        """Process the settings options to calculate the scan positions

        Returns
        -------
        ScanParameters
        """
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

    def update_tabular_positions(self, positions: np.ndarray = None):
        """Convenience function to write positions directly into the tabular table

        Parameters
        ----------
        positions: ndarray
            a 2D ndarray with as many columns as selected actuators
        """
        try:
            if self.settings.child('scan_type').value() == 'Tabular':
                if positions is None:
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
                elif isinstance(positions, np.ndarray):
                    self.update_model(init_data=positions)
                else:
                    pass
            else:
                self.update_model()
        except Exception as e:
            logger.exception(str(e))

    def update_scan_2D_positions(self):
        """Compute scan positions from the ROI set with the scan_selector"""
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
        """Update the 2D scan type from the given parameter.
        """
        try:
            self.settings.child('scan2D_settings', 'step_2d_axis1').show()
            self.settings.child('scan2D_settings', 'step_2d_axis2').show()
            scan_subtype = self.settings.child('scan2D_settings', 'scan2D_type').value()
            self.settings.child('scan2D_settings', 'scan2D_loss').show(scan_subtype == 'Adaptive')
            if scan_subtype == 'Adaptive':
                if self.settings.child('scan2D_settings', 'scan2D_loss').value() == 'resolution':
                    title = 'Minimal feature (%):'
                    if self.settings.child('scan2D_settings', 'step_2d_axis1').opts['title'] != title:
                        self.settings.child('scan2D_settings', 'step_2d_axis1').setValue(1)
                        self.settings.child('scan2D_settings', 'step_2d_axis2').setValue(100)

                    self.settings.child('scan2D_settings', 'step_2d_axis1').setOpts(
                        limits=[0, 100], title=title, visible=True,
                        tip='Features smaller than this will not be probed first. In percent of maximal scanned area'
                            ' length',
                        )
                    self.settings.child('scan2D_settings', 'step_2d_axis2').setOpts(
                        limits=[0, 100], title='Maximal feature (%):', visible=True,
                        tip='Features bigger than this will be probed first. In percent of maximal scanned area length',
                        )

                else:
                    self.settings.child('scan2D_settings', 'step_2d_axis1').hide()
                    self.settings.child('scan2D_settings', 'step_2d_axis2').hide()
            else:
                self.settings.child('scan2D_settings',
                                    'step_2d_axis1').setOpts(title='Step Ax1:',
                                                             tip='Step size for ax1 in actuator units')
                self.settings.child('scan2D_settings',
                                    'step_2d_axis2').setOpts(title='Step Ax2:',
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
    """Table Model for the Model/View Qt framework dedicated to the Tabular scan mode"""
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

    @Slot(int)
    def add_data(self, row, data=None):
        if data is not None:
            self.insert_data(row, [float(d) for d in data])
        else:
            self.insert_data(row, [0. for name in self.header])

    @Slot(int)
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





if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    from qtpy.QtCore import QThread
    from pymodaq.utils.gui_utils import DockArea
    from pyqtgraph.dockarea import Dock
    from pymodaq.utils.plotting.data_viewers.viewer2D import Viewer2D
    from pymodaq.utils.plotting.navigator import Navigator
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

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
