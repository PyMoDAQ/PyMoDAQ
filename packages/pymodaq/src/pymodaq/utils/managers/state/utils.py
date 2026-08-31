from pathlib import Path
from typing import Union, Any

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.parameter import Parameter

from serializall import SerializableFactory

from pymodaq.utils.managers.modules import ModuleType

from pymodaq_gui.managers.settings.subentries import  SubEntryHandlerFactory, SubEntry

logger = set_logger(get_module_name(__file__))
ser_factory = SerializableFactory()
special_entry_factory = SubEntryHandlerFactory()



def get_module_index_from_param(param: ParameterWithPath) -> Union[int, None]:
    if ModuleType.Actuator in param.path or 'Moves' in param.path:
        try:
            index = param.path[::-1].index(ModuleType.Actuator)
        except ValueError:
            index = param.path[::-1].index('Moves')  #backcompat with old style experiment
    elif 'Detectors' in param.path or ModuleType.Detector in param.path:
        try:
            index = param.path[::-1].index(ModuleType.Detector)
        except ValueError:
            index = param.path[::-1].index('Detectors')  #backcompat with old style experiment
    else:
        return None
    return len(param.path) - index


def get_module_from_param(param: ParameterWithPath) -> Union[tuple[str, ModuleType], None]:
    index = get_module_index_from_param(param)
    if index is None:
        return None
    if ModuleType.Actuator in param.path or 'Moves' in param.path:
        module_type = ModuleType.Actuator
    elif 'Detectors' in param.path or ModuleType.Detector in param.path:
        module_type = ModuleType.Detector
    else:
        return None
    index = len(param.path) - index
    param_module = param.parameter
    for _ in range(index-1):
        param_module = param_module.parent()
    module = param_module.child('name').value()
    return module, module_type


def state_subentries_from_path(fname: Path) -> list[SubEntry]:
    if not fname.exists():
        return []
    with open(fname, 'rb') as file:
        lines = file.readlines()
    all_lines = b''
    for line in lines:
        all_lines += line
    data = []
    while len(all_lines) > 0:
        entry, all_lines = SubEntry.deserialize(all_lines)
        data.append(entry)
    return data


mock_list = ['elt1', 'elt2', 'elt3']
mock_entry = SubEntry('settings',
                      'Photodiode',
                      ParameterWithPath(
                          parameter=Parameter.create(title='mytitle', name='myname',
                                                     type='list', value=mock_list[0],
                                                     limits=mock_list)))

