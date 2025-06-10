from __future__ import annotations
from typing import Tuple, List, TYPE_CHECKING
from collections import OrderedDict

from qtpy.QtCore import QObject, Signal
from qtpy import QtWidgets

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import Config
import pymodaq_utils.utils as utils

from pymodaq_gui.managers.parameter_manager import ParameterManager, Parameter

from pymodaq.utils.scanner.scan_factory import ScannerFactory, ScannerBase
from pymodaq.utils.scanner.utils import ScanInfo
from pymodaq.utils.scanner.scan_selector import Selector
from pymodaq.utils.data import DataToExport, DataActuator

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move


logger = set_logger(get_module_name(__file__))
config = Config()
scanner_factory = ScannerFactory()


class Scanner(QObject, ParameterManager):
    """Main Object to define a PyMoDAQ scan and create a UI to set it

    Parameters
    ----------
    parent_widget: QtWidgets.QWidget
    scanner_items: list of GraphicItems
        used by ScanSelector for chosing scan area or linear traces
    actuators: List[DAQ_Move]
        list actuators names

    See Also
    --------
    ScanSelector, ScannerBase, TableModelSequential, TableModelTabular, pymodaq_types.TableViewCustom
    """
    scanner_updated_signal = Signal()
    settings_name = 'scanner'

    params = [
        {'title': 'Calculate positions:', 'name': 'calculate_positions', 'type': 'action'},
        {'title': 'N steps:', 'name': 'n_steps', 'type': 'int', 'value': 0, 'readonly': True},
        {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list',
         'limits': scanner_factory.scan_types()},
        {'title': 'Scan subtype:', 'name': 'scan_sub_type', 'type': 'list',
         'limits': scanner_factory.scan_sub_types(scanner_factory.scan_types()[0])},
    ]

    def __init__(self, parent_widget: QtWidgets.QWidget = None, scanner_items=OrderedDict([]),
                 actuators: List[DAQ_Move] = []):
        QObject.__init__(self)
        ParameterManager.__init__(self)
        if parent_widget is None:
            parent_widget = QtWidgets.QWidget()
        self.parent_widget = parent_widget
        self._scanner_settings_widget = None

        self.connect_things()
        self._scanner: ScannerBase = None

        self.setup_ui()
        self.actuators = actuators
        if self._scanner is not None:
            self.settings.child('n_steps').setValue(self._scanner.evaluate_steps())

    def setup_ui(self):
        self.parent_widget.setLayout(QtWidgets.QVBoxLayout())
        self.parent_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.parent_widget.layout().addWidget(self.settings_tree)
        self._scanner_settings_widget = QtWidgets.QWidget()
        self._scanner_settings_widget.setLayout(QtWidgets.QVBoxLayout())
        self._scanner_settings_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.parent_widget.layout().addWidget(self._scanner_settings_widget)
        self.settings_tree.setMinimumHeight(110)
        self.settings_tree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def set_scanner(self):
        try:
            self._scanner: ScannerBase = scanner_factory.get(self.settings['scan_type'],
                                                             self.settings['scan_sub_type'],
                                                             actuators=self.actuators)

            while True:
                child = self._scanner_settings_widget.layout().takeAt(0)
                if not child:
                    break
                child.widget().deleteLater()
                QtWidgets.QApplication.processEvents()

            self._scanner_settings_widget.layout().addWidget(self._scanner.settings_tree)
            self._scanner.settings.sigTreeStateChanged.connect(self._update_steps)

        except ValueError as e:
            pass

    @property
    def scanner(self) -> ScannerBase:
        return self._scanner

    def get_scanner_sub_settings(self):
        """Get the current ScannerBase implementation's settings"""
        return self._scanner.settings

    def value_changed(self, param: Parameter):
        if param.name() == 'scan_type':
            self.settings.child('scan_sub_type').setOpts(
                limits=scanner_factory.scan_sub_types(param.value()))
        if param.name() in ['scan_type', 'scan_sub_type']:
            self.set_scanner()
            self.settings.child('scan_type').setOpts(tip=self._scanner.__doc__)
            self.settings.child('scan_sub_type').setOpts(tip=self._scanner.__doc__)

        self.settings.child('n_steps').setValue(self._scanner.evaluate_steps())

    @property
    def actuators(self) -> list[DAQ_Move]:
        """list of str: Returns as a list the name of the selected actuators to describe the actual scan"""
        return self._actuators

    @actuators.setter
    def actuators(self, act_list):
        self._actuators = act_list
        self.set_scanner()

    def set_scan_type_and_subtypes(self, scan_type: str, scan_subtype: str):
        """Convenience function to set the main scan type

        Parameters
        ----------
        scan_type: str
            one of registered Scanner main identifier
        scan_subtype: list of str or None
            one of registered Scanner second identifier for a given main identifier

        See Also
        --------
        ScannerFactory
        """
        if scan_type in scanner_factory.scan_types():
            self.settings.child('scan_type').setValue(scan_type)

            if scan_subtype is not None:
                if scan_subtype in scanner_factory.scan_sub_types(scan_type):
                    self.settings.child('scan_sub_type').setValue(scan_subtype)

    def set_scan_from_settings(self, settings: Parameter, scanner_settings: Parameter):

        self.set_scan_type_and_subtypes(settings['scan_type'],
                                        settings['scan_sub_type'])
        self.settings.restoreState(settings.saveState())
        self._scanner.settings.restoreState(scanner_settings.saveState())

    @property
    def scan_type(self) -> str:
        return self.settings['scan_type']

    @property
    def scan_sub_type(self) -> str:
        return self.settings['scan_sub_type']

    def connect_things(self):
        self.settings.child('calculate_positions').sigActivated.connect(self.set_scan)
        self.scanner_updated_signal.connect(self.save_scanner_settings)

    def save_scanner_settings(self):
        self._scanner.save_scan_parameters()

    def get_scan_info(self) -> ScanInfo:
        """Get a summary of the configured scan as a ScanInfo object"""
        return ScanInfo(self._scanner.n_steps, positions=self._scanner.positions,
                        axes_indexes=self._scanner.axes_indexes, axes_unique=self._scanner.axes_unique,
                        selected_actuators=[act.title for act in self.actuators])

    def get_nav_axes(self):
        return self._scanner.get_nav_axes()

    def get_scan_shape(self):
        return self._scanner.get_scan_shape()

    def get_indexes_from_scan_index(self, scan_index: int) -> Tuple[int]:
        """To be reimplemented. Calculations of indexes within the scan"""
        return self._scanner.get_indexes_from_scan_index(scan_index)

    def _update_steps(self):
        self.settings.child('n_steps').setValue(self.n_steps)

    @property
    def n_steps(self):
        return self._scanner.evaluate_steps()

    @property
    def n_axes(self):
        return self._scanner.n_axes

    @property
    def positions(self):
        return self._scanner.positions

    def positions_at(self, index: int) -> DataToExport:
        """ Extract the actuators positions at a given index in the scan as a DataToExport of DataActuators"""
        dte = DataToExport('scanner')
        for ind, pos in enumerate(self.positions[index]):
            dte.append(DataActuator(self.actuators[ind].title, data=float(pos),
                                    units=self.actuators[ind].units))
        return dte

    @property
    def axes_indexes(self):
        return self._scanner.axes_indexes

    @property
    def axes_unique(self):
        return self._scanner.axes_unique

    @property
    def distribution(self):
        return self._scanner.distribution

    def set_scan(self):
        """Process the settings options to calculate the scan positions

        Returns
        -------
        bool: True if the processed number of steps if **higher** than the configured number of steps
        """
        oversteps = config('scan', 'steps_limit')
        if self._scanner.evaluate_steps() > oversteps:
            return True
        self._scanner.set_scan()
        self.settings.child('n_steps').setValue(self.n_steps)
        self.scanner_updated_signal.emit()
        return False

    def update_from_scan_selector(self, scan_selector: Selector):
        self._scanner.update_from_scan_selector(scan_selector)


def main():
    from pymodaq.utils.parameter import ParameterTree
    app = QtWidgets.QApplication(sys.argv)

    class MoveMock:
        def __init__(self, ind: int = 0):
            self.title = f'act_{ind}'
            self.units = f'units_{ind}'

    actuators = [MoveMock(ind) for ind in range(3)]

    params = [{'title': 'Actuators', 'name': 'actuators', 'type': 'itemselect',
               'value': dict(all_items=[act.title for act in actuators], selected=[]),'checkbox':True},
              {'title': 'Set Scan', 'name': 'set_scan', 'type': 'action'},
              ]
    settings = Parameter.create(name='settings', type='group', children=params)
    settings_tree = ParameterTree()
    settings_tree.setParameters(settings)

    widget_main = QtWidgets.QWidget()
    widget_main.setLayout(QtWidgets.QVBoxLayout())
    #widget_main.layout().setContentsMargins(0, 0, 0, 0)
    widget_scanner = QtWidgets.QWidget()
    widget_main.layout().addWidget(settings_tree)
    widget_main.layout().addWidget(widget_scanner)
    scanner = Scanner(widget_scanner, actuators=actuators)

    def update_actuators(param):
        scanner.actuators = [utils.find_objects_in_list_from_attr_name_val(actuators, 'title', act_str,
                                                                           return_first=True)[0]
                             for act_str in param.value()['selected']]

    def print_info():
        print('info:')
        print(scanner.get_scan_info())
        print('positions:')
        print(scanner.positions)
        print('nav:')
        print(scanner.get_nav_axes())

    settings.child('actuators').sigValueChanged.connect(update_actuators)
    settings.child('set_scan').sigActivated.connect(scanner.set_scan)
    scanner.scanner_updated_signal.connect(print_info)
    widget_main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    import sys
    from qtpy import QtWidgets
    main()

