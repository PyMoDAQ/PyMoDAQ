# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
import pytest
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.scanner.scan_factory import ScannerFactory, ScannerBase, SCANNER_SETTINGS_NAME
from pymodaq.utils.parameter import utils as putils

scanner_factory = ScannerFactory()


class MainScanner(ParameterManager):
    params = [
        {'title': 'N steps:', 'name': 'n_steps', 'type': 'int', 'value': 0, 'readonly': True},
        {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list',
         'limits': scanner_factory.scan_types()},
        {'title': 'Scan subtype:', 'name': 'scan_sub_type', 'type': 'list',
         'limits': scanner_factory.scan_sub_types(scanner_factory.scan_types()[0])},
        {'title': 'Settings', 'name': SCANNER_SETTINGS_NAME, 'type': 'group'}
    ]

    def __init__(self):
        super().__init__()

        self._scanner: ScannerBase = None

        self.set_scanner()
        self.settings.child('n_steps').setValue(self._scanner.evaluate_steps())

    def set_scanner(self):
        try:
            self._scanner: ScannerBase = scanner_factory.get(self.settings['scan_type'],
                                                             self.settings['scan_sub_type'])

            self._scanner.settings.sigTreeStateChanged.connect(self.update_local_settings)

            while len(self.settings.child(SCANNER_SETTINGS_NAME).children()) > 0:
                self.settings.child(SCANNER_SETTINGS_NAME).removeChild(self.settings.child(SCANNER_SETTINGS_NAME).children()[0])

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


if __name__ == '__main__':
    import sys
    from qtpy import QtWidgets
    app = QtWidgets.QApplication(sys.argv)
    prog = MainScanner()
    prog.settings_tree.show()
    sys.exit(app.exec_())


class TestSettings:
    pass

