import numpy as np

from pymodaq.utils.data import DataToExport, DataRaw, DataActuator

from pymodaq_ontology.channels import Channel, actuator_channels, detector_channels
from pymodaq_ontology.terms import ACTUATOR, DETECTOR


def test_detector_channels_one_per_array():
    dwa = DataRaw('diodes', data=[np.array([1.82]), np.array([1.79])], labels=['diode_A', 'diode_B'],
                  units='V', origin='Balanced detector')
    spectrum = DataRaw('spectrum', data=[np.arange(5.)], origin='Camera')

    channels = detector_channels(DataToExport('probe', data=[dwa, spectrum]).data)

    assert [c.key for c in channels] == ['Balanced detector/diodes/diode_A', 'Balanced detector/diodes/diode_B',
                                         'Camera/spectrum/CH00']
    assert channels[0].kind == DETECTOR
    assert channels[0].last_value == '1.82'
    assert channels[2].last_value == ''  # an array is not a value


def test_actuator_is_its_own_channel():
    class Move:
        title = 'Magnet'
        units = 'mT'
        _current_value = DataActuator('Magnet', data=[np.array([12.5])])

    channel, = actuator_channels([Move()])
    assert channel == Channel('Magnet', ACTUATOR, units='mT', last_value='12.5')
    assert channel.key == 'Magnet'
    assert channel.name == 'Magnet'
