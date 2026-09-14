from typing import Any

from serializall import SerializableFactory

from pymodaq_data import DataToExport, DataDim
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase
from pymodaq.extensions.sequencer.utilities.element_factory import ElementError


ser_factory = SerializableFactory()


@ChoiceModelFactory.register_choice()
class ThresholdChoiceModel(ChoiceModelBase):
    model_name = 'threshold'

    params = [
        {'title': 'Detectors', 'name': 'detectors', 'type': 'itemselect'},
        {'title': 'Probe Data', 'name': 'probe_data', 'type': 'action'},
        {'title': 'Threshold', 'name': 'threshold', 'type': 'float', 'value': 0},
        {'title': 'Direction', 'name': 'direction', 'type': 'list', 'value': 'Above',
         'limits': ['Above', 'Below']},
        {'title': 'Data0D', 'name': 'data_name', 'type': 'list',},]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings.child('probe_data').sigActivated.connect(self.probe_data)
        self.settings['detectors'] = dict(all_items=self.modules_manager.detectors_name,
                                          selected=self.modules_manager.detectors_name)

    def updated_module_manager(self):
        """ called whenever the parent modules manager is updated
        """
        self.settings['detectors'] = dict(all_items=self.modules_manager.detectors_name,
                                          selected=self.modules_manager.detectors_name)

    def probe_data(self):
        self.modules_manager.selected_detectors_name = self.settings['detectors']['selected']
        dte = self.modules_manager.get_det_data_list()
        data0D_names = dte.get_full_names(DataDim.Data0D)
        self.settings.child('data_name').setLimits(data0D_names)
        if len(data0D_names) > 0:
            self.settings['data_name'] = data0D_names[0]

    def execute(self, dte: DataToExport):
        if len(self.selected) > 0:
            self.modules_manager.selected_detectors_name = self.settings['detectors']['selected']
            self.modules_manager.connect_detectors()
            dte = self.modules_manager.grab_data()
            self.modules_manager.connect_detectors(False)
        else:
            dte = DataToExport('Grab')

        boolean_result = self.process_dte(dte)
        self.parent_elt.go_to_signal.emit(boolean_result)
        pass

    def process_dte(self, dte: DataToExport) -> bool:
        dwa = dte.get_data_from_full_name(self.settings['data_name'])
        if self.settings['direction'] == 'Above':
            return dwa.value() > self.settings['threshold']
        else:
            return dwa.value() < self.settings['threshold']

    def check_set_is_valid(self):
        """ Check if the current settings of this model are valid
        """
        if not self.parent_elt.dashboard.experiment_manager.entry_applied:
            raise ElementError('No Experiment has been applied in the DashBoard')
        if len(self.settings['detectors']['selected']) != 0:
            raise ElementError(f'Element {self.parent_elt} has no detector selected ')
        if (self.settings['detectors']['selected'] not in
                self.parent_elt.dashboard.modules_manager.detectors_name):
            raise ElementError(f'Element {self.parent_elt} : the selected detector is not existing in the DashBoard')
        if self.settings['data_name'] is None or self.settings['data_name'] == '':
            raise ElementError(f'Element {self.parent_elt} has no data name set')

    def to_dict(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this model params
        """
        return {'detectors': self.settings['detectors'],
                'threshold': self.settings['threshold'],
                'directions': self.settings.child('direction').opts['limits'],
                'direction': self.settings['direction'],
                'data_names': self.settings.child('data_name').opts['limits'],
                'data_name': self.settings['data_name'],
                }

    def from_dict(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods
        """
        self.settings['detectors'] = dict_config.pop('detectors')
        self.settings['threshold'] = dict_config.pop('threshold')
        self.settings.child('direction').setLimits(dict_config.pop('directions'))
        self.settings['direction'] = dict_config.pop('direction')
        self.settings.child('data_name').setLimits(dict_config.pop('data_names'))
        self.settings['data_name'] = dict_config.pop('data_name')