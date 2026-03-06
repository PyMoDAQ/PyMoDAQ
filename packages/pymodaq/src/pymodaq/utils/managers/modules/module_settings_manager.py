from typing import TYPE_CHECKING, Type
from importlib import import_module


from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION

from pymodaq.utils.managers.modules.utils import ModuleType
from pymodaq.control_modules.instruments import (DET_TYPES, ACTUATOR_TYPES, find_dict_in_list_from_key_val,
                                                 find_dicts_in_list_from_key_val)
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer

if TYPE_CHECKING:
    from pymodaq.control_modules.utils import ParameterControlModule


class SettingsManager:
    """ Manage the settings from a list of Control Modules either actual instances or as defined in a preset file"""


    def create_settings_all(self,
                            actuators: list[Parameter] | list[DAQ_Move],
                            detectors: list[Parameter] | list[DAQ_Viewer],):
        settings = Parameter.create(
            title="Control Modules Settings",
            name="control_modules_settings",
            type="group",
            children=[{'title': 'Actuators:', 'name': ModuleType.Actuator.value, 'type': 'group',
                       VALID_FOR_CONFIGURATION: True},
                      {'title': 'Detectors:', 'name': ModuleType.Detector.value, 'type': 'group',
                       VALID_FOR_CONFIGURATION: True},],
        )
        if len(actuators) > 0:
            if isinstance(actuators[0], Parameter):
                self.add_settings_from_modules_in_preset(settings, actuators, ModuleType.Actuator)
            else:
                self.add_settings_from_modules_instances(settings, actuators, ModuleType.Actuator)
        if len(detectors) > 0:
            if isinstance(detectors[0], Parameter):
                self.add_settings_from_modules_in_preset(settings, detectors, ModuleType.Detector)
            else:
                self.add_settings_from_modules_instances(settings, detectors, ModuleType.Detector)

        return settings

    def add_settings_from_modules_instances(self,
            settings: Parameter,
            modules: list['ParameterControlModule'],
            module_type: ModuleType = ModuleType.Actuator):
        """ Adds to a given Parameter children based from the current value of their settings

        Settings are grouped by module type: 'Actuator' or 'Detector'
        """
        modules_titles = [mod.title for mod in modules]
        for ind, module in enumerate(modules):
            module_settings = self.get_settings_from_instance(module, module_type)

            self._add_settings_from_settings(settings, module_type=module_type,
                                             name=f'{module_type}_{ind:03.0f}', title=modules_titles[ind],
                                             module_settings=module_settings)

    def add_settings_from_modules_in_preset(self,
                                            settings: Parameter,
                                            preset_settings: list[Parameter],
                                            module_type: ModuleType = ModuleType.Actuator
                                            ):
        """ Adds to a given Parameter children based from the current value of their settings

        Settings are grouped by module type: 'Actuator' or 'Detector'
        """
        modules_titles = [param['name'] for param in preset_settings]

        for ind, param_info in enumerate(preset_settings):

            module_settings = self.get_settings_from_class(
                self.get_module_class_from_preset(param_info, module_type),
            module_type)

            self._add_settings_from_settings(settings, module_type=module_type,
                                            name=f'{module_type}_{ind:03.0f}', title=modules_titles[ind],
                                            module_settings=module_settings)


    @staticmethod
    def _add_settings_from_settings(settings: Parameter, module_type, name: str, title: str, module_settings):
        settings.child(module_type).addChild(
            {'title': title, 'name': name, 'type': 'group',
             'children': [
                 {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': title,
                  VALID_FOR_CONFIGURATION: False}
             ]},
        )
        settings.child(module_type, name).addChildren(module_settings.children())

    @staticmethod
    def get_settings_from_instance(module: 'ParameterControlModule', module_type: ModuleType) -> Parameter:
        module_settings = Parameter.create(name='settings', type='group', children=[])
        module_settings.restoreState(module.settings.saveState())
        return module_settings

    @staticmethod
    def get_settings_from_class(module: Type['ParameterControlModule'], module_type: ModuleType) -> Parameter:

        if module_type == ModuleType.Actuator:
            params = DAQ_Move.params
            params_actuator = find_dict_in_list_from_key_val(params, 'name', 'move_settings')
            params_actuator['children'] = module.params
        elif module_type == ModuleType.Detector:
            params = DAQ_Viewer.params
            params_actuator = find_dict_in_list_from_key_val(params, 'name', 'detector_settings')
            params_actuator['children'] = module.params
        else:
            params = []

        return Parameter.create(name='settings', type='group', children=params)

    @staticmethod
    def get_module_class_from_preset(preset_subentry: Parameter, module_type: ModuleType)\
            -> Type['ParameterControlModule']:

        if module_type == ModuleType.Actuator:
            act_dict = find_dict_in_list_from_key_val(ACTUATOR_TYPES, 'name', preset_subentry['info', 'type'])
            module_module = getattr(act_dict['module'], f"daq_move_{act_dict['name']}")
            return getattr(module_module, f"DAQ_Move_{act_dict['name']}")

        elif module_type == ModuleType.Detector:

            det_dicts_dim = DET_TYPES[preset_subentry['info', 'dim']]
            det_dict = find_dict_in_list_from_key_val(det_dicts_dim, 'name', preset_subentry['info', 'type'])
            module_module = getattr(det_dict['module'], f"{det_dict['type']}_{det_dict['name']}")
            return getattr(module_module, f"DAQ{det_dict['type'][3:6]}Viewer_{det_dict['name']}")

        else:
            raise TypeError(f'Module type {module_type} not supported')
