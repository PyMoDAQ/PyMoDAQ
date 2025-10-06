from pymodaq.extensions.data_mixer.model import DataMixerModel, np  # np will be used in method eval of the formula

from pymodaq_data.data import DataToExport, DataWithAxes
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.config_saver_loader import ConfigSaverLoader

from pymodaq.extensions.data_mixer.parser import (
    extract_data_names, split_formulae, replace_names_in_formula)

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class DataMixerModelEquation(DataMixerModel):
    params = [
        {'title': 'Get Data:', 'name': 'get_data', 'type': 'bool_push', 'value': False,
         'label': 'Get Data'},
        {'title': 'Edit Formula:', 'name': 'edit_formula', 'type': 'text', 'value': ''},
        {'title': 'Data0D:', 'name': 'data0D', 'type': 'itemselect',
         'value': dict(all_items=[], selected=[])},
        {'title': 'Data1D:', 'name': 'data1D', 'type': 'itemselect',
         'value': dict(all_items=[], selected=[])},
        {'title': 'Data2D:', 'name': 'data2D', 'type': 'itemselect',
         'value': dict(all_items=[], selected=[])},
        {'title': 'DataND:', 'name': 'dataND', 'type': 'itemselect',
         'value': dict(all_items=[], selected=[])},
    ]

    def ini_model(self):
        self.model_saver_loader = ConfigSaverLoader(self.settings, self.data_mixer.datamixer_config,
                                                    base_path=[self.__class__.__name__])
        self.show_data_list()
        self.model_saver_loader.load_config()

    def update_settings(self, param: Parameter):
        if param.name() == 'get_data':
            self.show_data_list()
        elif param.name() == 'edit_formula':
            self.model_saver_loader.save_config(param)

    def process_dte(self, dte: DataToExport):
        formulae = split_formulae(self.get_formulae())
        dte_processed = DataToExport('Computed')
        for ind, formula in enumerate(formulae):
            try:
                dwa = self.compute_formula(formula, dte,
                                           name=f'Formula_{ind:03.0f}')
                dte_processed.append(dwa)
            except Exception as e:
                logger.exception(f'{str(e)}')
        return dte_processed

    def get_formulae(self) -> str:
        """ Read the content of the formula QTextEdit widget"""
        return self.settings['edit_formula']

    def show_data_list(self):
        dte = self.modules_manager.get_det_data_list()

        data_list0D = dte.get_full_names('data0D')
        data_list1D = dte.get_full_names('data1D')
        data_list2D = dte.get_full_names('data2D')
        data_listND = dte.get_full_names('dataND')

        self.settings.child('data0D').setValue(dict(all_items=data_list0D, selected=[]))
        self.settings.child('data1D').setValue(dict(all_items=data_list1D, selected=[]))
        self.settings.child('data2D').setValue(dict(all_items=data_list2D, selected=[]))
        self.settings.child('dataND').setValue(dict(all_items=data_listND, selected=[]))


    def compute_formula(self, formula: str, dte: DataToExport,
                        name: str) -> DataWithAxes:
        """ Compute the operations in formula using data stored in dte

        Parameters
        ----------
        formula: str
            The mathematical formula using numpy and data fullnames within curly brackets
        dte: DataToExport
        name: str
            The name to give to the produced DataWithAxes

        Returns
        -------
        DataWithAxes: the results of the formula computation
        """
        formula_to_eval, names = replace_names_in_formula(formula)
        dwa = eval(formula_to_eval)
        dwa.name = name
        return dwa

