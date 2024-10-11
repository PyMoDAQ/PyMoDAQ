# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
import numpy as np
import pytest
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun, main,
                                                          DataActuatorType, check_units,
                                                          DataActuator)
from pymodaq_utils.utils import ThreadCommand


def test_check_units():

    dwa = DataActuator('myact', data=24., units='km')

    assert check_units(dwa, 'm') == dwa


def test_axis_list_legacy(qtbot):

    AXIS_NAMES = ['U', 'V']
    EPSILON = 0.001
    UNITS = 'µm'

    class HardwareWithList(DAQ_Move_base):
        _controller_units = UNITS
        # find available COM ports

        is_multiaxes = True
        axes_names = AXIS_NAMES.copy()
        _epsilon = EPSILON

        params = comon_parameters_fun(is_multiaxes, axes_names, epsilon=_epsilon)

    hardware = HardwareWithList()

    for ind, axis_name in enumerate(AXIS_NAMES):
        hardware.axis_name = axis_name

        assert hardware.axis_index_key == ind

        assert hardware.axis_names == AXIS_NAMES
        assert hardware.axis_name == axis_name
        assert hardware.axis_value == axis_name

        assert hardware.epsilon == pytest.approx(EPSILON)
        assert np.allclose(hardware.epsilons, [EPSILON for _ in range(len(AXIS_NAMES))])

        assert hardware.axis_unit == UNITS
        assert hardware.axis_units == [UNITS for _ in range(len(AXIS_NAMES))]



@pytest.mark.parametrize("AXIS_NAMES, EPSILONS, UNITS, error",
                         [(['a', 'b', 'c'], 0.1, 'mm', False),
                          (['a', 'b',], [0.1, 0.65], 'mm', False),
                          (['a', 'c'], 0.1, ['mm', '°'], False),
                          (['a', 'c'], [0.1, 0.001], ['mm', '°'], False),
                          (['a', 'b', 'c'], 0.1, ['mm', '°'], True),
                          (['a', 'c'], [0.1], ['mm', '°'], True),
                          (['a', 'b', 'c'], [0.1, 0.001], ['mm', '°', 's'], True),
                          ])
def test_axis_list(qtbot, AXIS_NAMES, EPSILONS, UNITS, error):

    class HardwareWithList(DAQ_Move_base):
        _axis_names = AXIS_NAMES
        _controller_units = UNITS
        _epsilons = EPSILONS

        params = comon_parameters_fun(axis_names=_axis_names)

    if error:
        with pytest.raises(ValueError):
            hardware = HardwareWithList()
    else:
        hardware = HardwareWithList()

        for ind, axis_name in enumerate(AXIS_NAMES):
            hardware.axis_name = axis_name

            assert hardware.axis_index_key == ind

            assert hardware.axis_names == AXIS_NAMES
            assert hardware.axis_name == axis_name
            assert hardware.axis_value == axis_name

            if not isinstance(EPSILONS, list):
                assert hardware.epsilon == pytest.approx(EPSILONS)
                assert np.allclose(hardware.epsilons, [EPSILONS for _ in range(len(AXIS_NAMES))])
            else:
                assert hardware.epsilon == pytest.approx(EPSILONS[ind])
                assert np.allclose(hardware.epsilons, EPSILONS)

            if not isinstance(UNITS, list):
                assert hardware.axis_unit == UNITS
                assert hardware.axis_units == [UNITS for _ in range(len(AXIS_NAMES))]
            else:
                assert hardware.axis_unit == UNITS[ind]
                assert hardware.axis_units == UNITS


@pytest.mark.parametrize("AXIS_NAMES, EPSILONS, UNITS, error",
                         [({'a': 0, 'b': 2, 'c': 5}, 0.1, 'mm', None),
                          ({'a': 0, 'b': 2}, [0.1, 0.65], 'mm', TypeError),
                          ({'a': 0, 'b': 2}, {'a': 0.1, 'b': 0.65}, 'mm', None),
                          ({'a': 0, 'b': 2}, 0.1, {'a': 'mm', 'b': '°'}, None),
                          ({'a': 0, 'b': 2}, {'a': 0.1, 'b': 0.65}, {'a': 'mm', 'b': '°'}, None),
                          ({'a': 0, 'b': 2}, {'a': 0.1,}, {'a': 'mm', 'b': '°'}, ValueError),
                          ({'a': 0, 'b': 2}, {'a': 0.1, 'b': 0.65}, {'b': '°'}, ValueError),
                          ])
def test_axis_dict(qtbot, AXIS_NAMES, EPSILONS, UNITS, error):

    class HardwareWithList(DAQ_Move_base):
        _axis_names = AXIS_NAMES
        _controller_units = UNITS
        _epsilons = EPSILONS

        params = comon_parameters_fun(axis_names=_axis_names)

    if error is not None:
        with pytest.raises(error):
            hardware = HardwareWithList()
    else:
        hardware = HardwareWithList()

        for axis_name, axis_value in AXIS_NAMES.items():
            hardware.axis_name = axis_name

            assert hardware.axis_index_key == axis_name

            assert hardware.axis_names == AXIS_NAMES
            assert hardware.axis_name == axis_name
            assert hardware.axis_value == axis_value

            if not isinstance(EPSILONS, dict):
                assert hardware.epsilon == pytest.approx(EPSILONS)
                assert np.allclose(list(hardware.epsilons.values()),
                                   [EPSILONS for _ in range(len(AXIS_NAMES))])
            else:
                assert hardware.epsilon == pytest.approx(EPSILONS[axis_name])
                assert hardware.epsilons == EPSILONS

            if not isinstance(UNITS, dict):
                assert hardware.axis_unit == UNITS
                assert list(hardware.axis_units.values()) == [UNITS for _ in range(len(AXIS_NAMES))]
            else:
                assert hardware.axis_unit == UNITS[axis_name]
                assert hardware.axis_units == UNITS
