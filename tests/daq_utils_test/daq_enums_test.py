import numpy as np
import pytest

from pymodaq.daq_utils import daq_enums as enums


class Test_Items_Lockin_SR830:
    def test_item(self):

        x = np.random.randint(0, len(enums.Items_Lockin_SR830))
        item = enums.Items_Lockin_SR830(x)
        assert isinstance(item, enums.Items_Lockin_SR830)
        assert item.value == x

    def test_names(self):
        x = np.random.randint(0, len(enums.Items_Lockin_SR830))
        item = enums.Items_Lockin_SR830(x)
        assert item.names()
        assert item.name == item.names()[x]


class Test_Measurement_type:
    def test_item(self):
        x = np.random.randint(0, len(enums.Measurement_type))
        item = enums.Measurement_type(x)
        assert isinstance(item, enums.Measurement_type)
        assert item.value == x

    def test_names(self):
        x = np.random.randint(0, len(enums.Measurement_type))
        item = enums.Measurement_type(x)
        assert item.names()
        assert item.name == item.names()[x]

    def test_update_measurement_subtype(self):
        item = enums.Measurement_type(0)
        result = item.update_measurement_subtype(item.name)
        expected = [', ', '', ['sum', 'mean', 'std']]
        assert result == expected

        item = enums.Measurement_type(3)
        result = item.update_measurement_subtype(item.name)
        assert result[1]
        assert result[2] == result[0].split(', ')

        item = enums.Measurement_type(4)
        result = item.update_measurement_subtype(item.name)
        assert result[1]
        assert result[2] == result[0].split(', ')

        item = enums.Measurement_type(5)
        result = item.update_measurement_subtype(item.name)
        assert result[1]
        assert result[2] == result[0].split(', ')

    def test_gaussian_func(self):
        item = enums.Measurement_type(0)
        x = np.array([9.5, 9.7, 10.2, 11])
        amp = 1
        dx = 0.5
        x0 = 10
        offset = 0
        result = item.gaussian_func(x, amp, dx, x0, offset)
        expected = np.array([0.25, 0.60709744, 0.80106988, 0.00390625])
        for val1, val2 in zip(result, expected):
            assert pytest.approx(val1) == val2

        amp = 2
        result = item.gaussian_func(x, amp, dx, x0, offset)
        expected = 2 * expected
        for val1, val2 in zip(result, expected):
            assert pytest.approx(val1) == val2

        offset = 1
        result = item.gaussian_func(x, amp, dx, x0, offset)
        expected += 1
        for val1, val2 in zip(result, expected):
            assert pytest.approx(val1) == val2

    def test_laurentzian_func(self):
        item = enums.Measurement_type(0)
        x = np.array([9.5, 9.7, 10.2, 11])
        gamma = 1.5
        amp = 1
        dx = 0.5
        x0 = 10
        offset = 0
        result = item.laurentzian_func(x, gamma, amp, dx, x0, offset)
        expected = np.array([0.2938245, 0.3658734, 0.3962363, 0.1527887])
        for val1, val2 in zip(result, expected):
            assert pytest.approx(val1) == val2

    def test_decaying_func(self):
        item = enums.Measurement_type(0)
        x = np.array([9.5, 9.7, 10.2, 11])
        N0 = 1
        gamma = 0.1
        offset = 0
        result = item.decaying_func(x, N0, gamma, offset)
        expected = np.array([0.3867410, 0.3790830, 0.3605949, 0.3328710])
        for val1, val2 in zip(result, expected):
            assert pytest.approx(val1) == val2

    def test_update_measurement(self):
        item = enums.Measurement_type(0)
        xmin = 1
        xmax = 5
        xaxis = np.array([0, 1, 2, 3, 4, 5, 6, 7])
        data1D = np.array([7, 3, 4, 9, 10, 4, 3, 8])
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 0)
        assert result['value'] == 26
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 1)
        assert result['value'] == 6.5
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 2)
        assert result['value'] == pytest.approx(3.041381265)

        item = enums.Measurement_type(1)
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 0)
        assert result['value'] == 10

        item = enums.Measurement_type(2)
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 0)
        assert result['value'] == 3
        
        item = enums.Measurement_type(3)
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 0)
        expected = {'xaxis': xaxis[1:5], 'value': 8.026917, 'datafit': data1D[1:5]}
        assert np.array_equal(result['xaxis'], expected['xaxis'])
        assert result['value'] == pytest.approx(expected['value'])
        for val_1, val_2 in zip(result['datafit'], expected['datafit']):
            assert val_1 == pytest.approx(val_2)

        xmax = 6
        item = enums.Measurement_type(4)
        expected = {'xaxis': xaxis[1:6], 'value': 1.128095}
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 0)
        assert np.array_equal(result['xaxis'], expected['xaxis'])
        assert result['value'] == pytest.approx(expected['value'])
        assert len(result['xaxis']) == len(result['datafit'])

        result = item.update_measurement(xmin, xmax, xaxis, data1D, 4)
        assert result['value'] == pytest.approx(0.0321364)
        
        item = enums.Measurement_type(5)
        result = item.update_measurement(xmin, xmax, xaxis, data1D, 0)
        assert result['Status'] != None