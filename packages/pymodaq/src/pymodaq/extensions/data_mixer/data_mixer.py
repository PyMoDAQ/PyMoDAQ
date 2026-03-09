import sys

from qtpy import QtWidgets, QtCore
import numpy as np
from pathlib import Path

from typing import Optional

from pymodaq_gui import utils as gutils
from pymodaq_utils.config import ConfigError, GlobalConfig as Config
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import find_dict_in_list_from_key_val
from pymodaq_data.data import DataToExport, DataWithAxes

from pymodaq.extensions.custom_ext import CustomExt

from pymodaq_gui.plotting.data_viewers.viewer import ViewerDispatcher
from pymodaq_gui.utils.widgets.qled import QLED
from pymodaq_gui.parameter import utils as putils


from pymodaq.extensions.data_mixer.model import get_models, DataMixerModel
from pymodaq.extensions.data_mixer.utils import DataMixerConfig, find_key_in_nested_dict

logger = set_logger(get_module_name(__file__))

config = Config()

EXTENSION_NAME = 'Data Mixer'  # the name that will be displayed in the extension list in the
# dashboard
CLASS_NAME = 'DataMixer'  # this should be the name of your class defined below


class DataMixer(CustomExt):
    settings_name = 'DataMixerSettings'
    models = get_models()
    params = [
        {'title': 'Models', 'name': 'models', 'type': 'group', 'expanded': True, 'visible': True,
         'children': [
             {'title': 'Models class:', 'name': 'model_class', 'type': 'list',
              'limits': [d['name'] for d in models]},
             {'title': 'Ini Model', 'name': 'ini_model', 'type': 'action', },
             {'title': 'Model params:', 'name': 'model_params', 'type': 'group', 'children': []},

         ]}]

    dte_computed_signal = QtCore.Signal(DataToExport)

    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard)

        self.model_class: Optional[DataMixerModel] = None
        self.datamixer_config = DataMixerConfig()
        self.setup_ui()

        self.settings.child('models', 'ini_model').sigActivated.connect(
            self.get_action('ini_model').trigger)

    def get_set_model_params(self, model_name):
        self.settings.child('models', 'model_params').clearChildren()
        if len(self.models) > 0:
            model_class = find_dict_in_list_from_key_val(self.models, 'name', model_name)['class']
            params = getattr(model_class, 'params')
            self.settings.child('models', 'model_params').addChildren(params)


    def setup_docks(self):
        """Mandatory method to be subclassed to setup the docks layout

        """
        self.create_dashboard_toolbar()

        self.docks['settings'] = gutils.Dock('Settings')
        self.dockarea.addDock(self.docks['settings'])
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.docks['settings'].addWidget(splitter)
        splitter.addWidget(self.modules_manager.settings_tree)
        self.modules_manager.tree.header().setVisible(False)
        self.modules_manager.settings.child('actuators').hide()
        self.modules_manager.settings.child('probe_data').hide()
        self.modules_manager.settings.child('test_actuator').hide()

        splitter.addWidget(self.settings_tree)

        self.docks['computed'] = gutils.Dock('Computed data')
        self.dockarea.addDock(self.docks['computed'], 'right')

        self.area_computed = gutils.DockArea()
        self.docks['computed'].addWidget(self.area_computed)

        self.dte_computed_viewer = ViewerDispatcher(self.area_computed)

        if len(self.models) != 0:
            self.get_set_model_params(self.models[0]['name'])

    @property
    def config_path(self) -> Path:
        return self.datamixer_config.config_path

    def validate_config(self) -> bool:
        """ Read eventually saved settings from self.datamixer_config

        Example
        -------
        utility = find_key_in_nested_dict(self.datamixer_config.to_dict(), 'prediction')

        """
        return True

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory

        """
        combo_model = QtWidgets.QComboBox()
        combo_model.addItems([model['name'] for  model in self.models])
        self.add_widget('models', combo_model, tip='List of available models')
        self.add_action('ini_model', 'Init Model', 'ini')
        self.add_widget('model_led', QLED, toolbar=self.toolbar)
        self.add_action('snap', 'Snap Detectors', 'snap',
                        'Snap all selected detectors')
        self.add_action('create_computed_detectors', 'Create Computed Detectors', 'Add_Step',
                        tip='Create a DAQ_Viewer Control Module')

    def stop(self):
        """ Programmatic method to stop any action in the extension

        Irrelevant for the DataMixer as it doesn't do anything on the control modules
        """
        pass

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('models', self.update_model_settings_from_action, signal_name='currentTextChanged')
        self.connect_action('ini_model', self.ini_model)
        self.modules_manager.det_done_signal.connect(self.process_data)
        self.dte_computed_signal.connect(self.plot_computed_results)
        self.connect_action('snap', self.snap)
        self.modules_manager.detectors_changed.connect(self.update_connect_detectors)
        self.connect_action('create_computed_detectors', self.create_computed_detectors)

    def update_model_settings_from_action(self, model: str):
        self.settings.child('models', 'model_class').setValue(model)

    def process_data(self, dte: DataToExport):
        if self.model_class is not None:
            dte_computed = self.model_class.process_dte(dte)
            self.dte_computed_signal.emit(dte_computed)

    def snap(self):
        self.modules_manager.grab_data(check_do_override=False)

    def create_computed_detectors(self):
        try:
            self.dashboard.add_det_from_extension('DataMixer', 'DAQ0D', 'DataMixer', self)
            self.dashboard.modules_manager.get_mod_from_name(
                'DataMixer', 'det').settings.child('detector_settings', 'overridden_detectors').setOpts(
                limits=self.modules_manager.selected_detectors_name)
            self.set_action_enabled('create_computed_detectors', False)
            #self.dashboard.override_det_from_extension(self.modules_manager.selected_detectors_name)
        except Exception as e:
            logger.exception(str(e))
            pass

    def update_connect_detectors(self):
        try:
            self.connect_detectors(False)
        except :
            pass
        self.connect_detectors()

    def connect_detectors(self, connect=True):
        """Connect detectors to DAQ_Logging do_save_continuous method

        Parameters
        ----------
        connect: bool
            If True make the connection else disconnect
        """
        self.modules_manager.connect_detectors(connect=connect)

    def plot_computed_results(self, dte):
        self.dte_computed_viewer.show_data(dte)

    def ini_model(self):
        if self.model_class is None:
            self.set_model()

        self.get_action('model_led').set_as_true()
        self.set_action_enabled('ini_model', False)
        self.settings.child('models', 'ini_model').setValue(True)
        self.set_action_enabled('models', False)
        self.settings.child('models', 'model_class').setOpts(enabled=False)
        self.modules_manager.settings_tree.setEnabled(False)

        self.update_connect_detectors()

    def set_model(self):
        model_name = self.settings['models', 'model_class']
        self.model_class = find_dict_in_list_from_key_val(
            self.models, 'name', model_name)['class'](self)
        self.model_class.ini_model_base()

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        Examples
        --------
        >>>file_menu = self.mainwindow.menuBar().addMenu('File')
        >>>self.affect_to('load', file_menu)
        >>>self.affect_to('save', file_menu)

        >>>file_menu.addSeparator()
        >>>self.affect_to('quit', file_menu)

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        # todo create and populate menu using actions defined above in self.setup_actions
        pass

    def value_changed(self, param):
        """ Actions to perform when one of the param's value in self.settings is changed from the
        user interface

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        """
        if param.name() == 'model_class':
            self.get_set_model_params(param.value())
            self.get_action('models').setCurrentText(param.value())
        elif param.name() in putils.iter_children(self.settings.child('models', 'model_params'), []):
            if self.model_class is not None:
                self.model_class.update_settings(param)

    def quit_fun(self):
        self.dashboard.remove_modules(['DataMixer'])
        super().quit_fun()

def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import create_load_dashboard
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('Data Mixer')


    win, dashboard = create_load_dashboard()
    win.mainwindow.setVisible(False)

    win_ext, scan = create_extension(dashboard, DataMixer)
    win_ext.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
