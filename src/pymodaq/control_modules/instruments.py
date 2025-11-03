from pyqtgraph.parametertree import Parameter

from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_utils.enums import BaseEnum

from pymodaq_utils.utils import find_dict_in_list_from_key_val, find_dicts_in_list_from_key_val
from pymodaq.utils.exceptions import DetectorError, ActuatorError

from pymodaq import CONTROL_MODULES


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



class DAQTypesEnum(BaseEnum):
    """enum relating a given DAQType and a viewer type
    See Also
    --------
    pymodaq.utils.plotting.data_viewers.viewer.ViewersEnum
    """
    DAQ0D = 'Viewer0D'
    DAQ1D = 'Viewer1D'
    DAQ2D = 'Viewer2D'
    DAQND = 'ViewerND'

    def to_data_type(self):
        return ViewersEnum[self.value].value

    def to_viewer_type(self):
        return self.value

    def to_daq_type(self):
        return self.name

    def increase_dim(self, ndim: int):
        dim = self.get_dim()
        if dim != 'N':
            dim_as_int = int(dim) + ndim
            if dim_as_int > 2:
                dim = 'N'
            else:
                dim = str(dim_as_int)
        else:
            dim = 'N'
        return DAQTypesEnum(f'Viewer{dim}D')

    def get_dim(self):
        return self.value.split('Viewer')[1].split('D')[0]


def get_viewer_plugins(daq_type, det_name):
    parent_module = find_dict_in_list_from_key_val(DET_TYPES[daq_type], 'name', det_name)
    match_name = daq_type.lower()
    match_name = f'{match_name[0:3]}_{match_name[3:].upper()}viewer_'
    obj = getattr(getattr(parent_module['module'], match_name + det_name),
                  f'{match_name[0:7].upper()}{match_name[7:]}{det_name}')
    params = getattr(obj, 'params')
    det_params = Parameter.create(name='Det Settings', type='group', children=params)
    return det_params, obj
