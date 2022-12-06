# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
import pytest
from qtpy import QtWidgets, QtCore
from pymodaq.utils.managers.parameter_manager import ParameterManager, Parameter, ParameterTree
from pymodaq.utils.scanner.scan_factory import ScannerFactory, ScannerBase, SCANNER_SETTINGS_NAME
from pymodaq.utils.parameter import utils as putils

scanner_factory = ScannerFactory()
config_scanner = dict(actuators=['act1', 'act2'])


class MainScanner(ParameterManager):
    params = [
        {'title': 'N steps:', 'name': 'n_steps', 'type': 'int', 'value': 0, 'readonly': True},
        {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list',
         'limits': scanner_factory.scan_types()},
        {'title': 'Scan subtype:', 'name': 'scan_sub_type', 'type': 'list',
         'limits': scanner_factory.scan_sub_types(scanner_factory.scan_types()[0])},
    ]

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__()

        self.parent_widget = parent_widget
        self._scanner: ScannerBase = None
        self.setup_ui()
        self.set_scanner()
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
                                                             **config_scanner)
            while 1:
                child = self._scanner_settings_widget.layout().takeAt(0)
                if not child:
                    break
                child.widget().deleteLater()
                QtWidgets.QApplication.processEvents()

            self._scanner_settings_widget.layout().addWidget(self._scanner.settings_tree)

        except ValueError:
            pass

    def value_changed(self, param):
        if param.name() == 'scan_type':
            self.settings.child('scan_sub_type').setOpts(
                limits=scanner_factory.scan_sub_types(param.value()))

        if param.name() in ['scan_type', 'scan_sub_type']:
            self.set_scanner()

        self.settings.child('n_steps').setValue(self._scanner.evaluate_steps())


if __name__ == '__main__':
    import sys
    from qtpy import QtWidgets
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = MainScanner(widget)
    widget.show()
    sys.exit(app.exec_())


class TestSettings:
    def test_factory_interface(self, qtbot):
        for scan_type in scanner_factory.scan_types():
            for scan_sub_type in scanner_factory.scan_sub_types(scan_type):
                scanner = scanner_factory.get(scan_type, scan_sub_type, **config_scanner)
                scanner.evaluate_steps()
                scanner.set_scan()
                assert hasattr(scanner,  'axes_unique')
                assert hasattr(scanner,  'axes_indexes')
                assert hasattr(scanner,  'positions')
                assert hasattr(scanner, 'n_steps')

