from typing import TYPE_CHECKING, Type
from pymodaq_gui.parameter import Parameter

from pymodaq_utils.utils import find_dict_in_list_from_key_val, find_dicts_in_list_from_key_val
from pymodaq.utils.exceptions import DetectorError, ActuatorError
from .enums import DAQTypesEnum  # noqa for backcompatibility
from pymodaq import CONTROL_MODULES


if TYPE_CHECKING:
    from pymodaq.control_modules.move_utility_classes import DAQ_Move_base

DET_TYPES = {'DAQ0D': find_dicts_in_list_from_key_val(CONTROL_MODULES, 'type', 'daq_0Dviewer'),
             'DAQ1D': find_dicts_in_list_from_key_val(CONTROL_MODULES, 'type', 'daq_1Dviewer'),
             'DAQ2D': find_dicts_in_list_from_key_val(CONTROL_MODULES, 'type', 'daq_2Dviewer'),
             'DAQND': find_dicts_in_list_from_key_val(CONTROL_MODULES, 'type', 'daq_NDviewer'),
             }
if len(DET_TYPES['DAQ0D']) == 0:
    raise DetectorError('No installed Detector')

ACTUATOR_TYPES = find_dicts_in_list_from_key_val(CONTROL_MODULES, 'type', 'daq_move')
ACTUATOR_NAMES = [mov["name"] for mov in ACTUATOR_TYPES]
if len(ACTUATOR_TYPES) == 0:
    raise ActuatorError("No installed Actuator")


def find_actuator_class_from_name(actuator_name: str) -> Type['DAQ_Move_base']:
    parent_module = find_dict_in_list_from_key_val(
        ACTUATOR_TYPES, "name", actuator_name
    )
    class_ = getattr(
        getattr(parent_module["module"], "daq_move_" + actuator_name),
        "DAQ_Move_" + actuator_name,
    )
    return class_


def get_viewer_plugins(daq_type, det_name):
    parent_module = find_dict_in_list_from_key_val(DET_TYPES[daq_type], 'name', det_name)
    match_name = daq_type.lower()
    match_name = f'{match_name[0:3]}_{match_name[3:].upper()}viewer_'
    obj = getattr(getattr(parent_module['module'], match_name + det_name),
                  f'{match_name[0:7].upper()}{match_name[7:]}{det_name}')
    params = getattr(obj, 'params')
    det_params = Parameter.create(name='Det Settings', type='group', children=params)
    return det_params, obj
