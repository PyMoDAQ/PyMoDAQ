# -*- coding: utf-8 -*-
"""
Created the 22/10/2023

@author: Sebastien Weber
"""
import numbers

import numpy as np
import pytest

from pymodaq.utils import data as data_mod
from pymodaq.utils.data import Axis, DataToExport, DataWithAxes, DwaType
from pymodaq.utils.tcp_ip.serializer import Serializer, DeSerializer

LABEL = 'A Label'
UNITS = 'units'
OFFSET = -20.4
SCALING = 0.22
SIZE = 20
DATA = OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE)

DATA0D = np.array([2.7])
DATA1D = np.arange(0, 10)
DATA2D = np.arange(0, 5*6).reshape((5, 6))
DATAND = np.arange(0, 5 * 6 * 3).reshape((5, 6, 3))
Nn0 = 10
Nn1 = 5


def init_axis(data=None, index=0):
    if data is None:
        data = DATA
    return data_mod.Axis(label=LABEL, units=UNITS, data=data, index=index)


def init_data(data=None, Ndata=1, axes=[], name='myData', source=data_mod.DataSource['raw'],
              labels=None) -> data_mod.DataWithAxes:
    if data is None:
        data = DATA2D
    return data_mod.DataWithAxes(name, source, data=[data for ind in range(Ndata)],
                                 axes=axes, labels=labels)


@pytest.fixture()
def get_data():
    dat0D = init_data(DATA0D, 2, name='my0DData', source='raw')
    dat1D_calculated = init_data(DATA1D, 2, name='my1DDatacalculated', source='calculated')
    dat1D_raw = init_data(DATA1D, 2, name='my1DDataraw', source='raw')
    dat_act = data_mod.DataActuator(data=45)
    dte = data_mod.DataToExport(name='toexport', data=[dat0D, dat1D_calculated, dat1D_raw, dat_act])
    return dte


class TestStaticClassMethods:

    def test_int_to_bytes(self):

        afloat = 45.7
        a_negative_integer = -56
        for int_obj in [6, 678900786]:
            bytes_string = Serializer.int_to_bytes(int_obj)
            assert len(bytes_string) == 4
            assert bytes_string == int_obj.to_bytes(4, 'big')

            assert DeSerializer.bytes_to_int(bytes_string) == int_obj

        with pytest.raises(TypeError):
            Serializer.int_to_bytes(afloat)
        with pytest.raises(ValueError):
            Serializer.int_to_bytes(a_negative_integer)

    def test_str_to_bytes(self):
        MESSAGE = 'Hello World'
        ser = Serializer(MESSAGE)
        bytes_message = ser.str_to_bytes(MESSAGE)
        assert bytes_message == MESSAGE.encode()
        assert DeSerializer.bytes_to_string(bytes_message) == MESSAGE
        with pytest.raises(TypeError):
            ser.str_to_bytes(56)
        with pytest.raises(TypeError):
            ser.str_to_bytes(56,8)

    def test_str_len_to_bytes(self):

        MESSAGE = 'Hello World'
        ser = Serializer(MESSAGE)
        bytes_string, bytes_length = ser.str_len_to_bytes(MESSAGE)

        assert bytes_string == MESSAGE.encode()
        assert bytes_length == ser.int_to_bytes(len(MESSAGE))

        assert DeSerializer.bytes_to_string(bytes_string) == MESSAGE


def test_string_serialization_deserialization():

    string = 'Hello World'
    ser = Serializer(string)

    bytes_string = ser.string_serialization(string)
    assert len(bytes_string) == len(string) + 4
    deser = DeSerializer(bytes_string)
    assert deser.string_deserialization() == string
    assert ser.to_bytes() == bytes_string


def test_scalar_serialization_deserialization():
    scalars = [45.6, 67, -64, -56.8, 2+1j*56]

    for scalar in scalars:
        ser = Serializer(scalar)
        assert isinstance(ser.to_bytes(), bytes)
        assert DeSerializer(ser.to_bytes()).scalar_deserialization() == pytest.approx(scalar)
        pass


def test_ndarray_serialization_deserialization():

    ndarrays = [np.array([12, 56, 78,]),
                np.array([-12.8, 56, 78, ]),
                np.array([12]),
                np.array([[12, 56, 78, ],
                          [12, 56, 78, ],
                          [12, 56, 78, ]])]

    for ndarray in ndarrays:
        ser = Serializer(ndarray)
        assert isinstance(ser.to_bytes(), bytes)
        assert np.allclose(DeSerializer(ser.to_bytes()).ndarray_deserialization(), ndarray)


def test_object_type_serialization(get_data):
    dte = get_data
    ser = Serializer()
    objects = [dwa for dwa in dte]
    objects.append(dte)
    objects.extend(dte.get_data_from_dim('Data1D')[0].axes)

    for obj in objects:
        assert ser.object_type_serialization(obj)[4:].decode() == obj.__class__.__name__


def test_axis_serialization_deserialization():

    axis = init_axis()

    ser = Serializer(axis)
    assert isinstance(ser.to_bytes(), bytes)

    axis_deser = DeSerializer(ser.to_bytes()).axis_deserialization()
    assert isinstance(axis_deser, Axis)
    assert axis_deser.label == axis.label
    assert axis_deser.units == axis.units
    assert np.allclose(axis_deser.get_data(), axis.get_data())

    ser = Serializer('bjkdbjk')
    with pytest.raises(TypeError):
        ser.axis_serialization()
    with pytest.raises(TypeError):
        DeSerializer(ser.string_serialization()).axis_deserialization()


@pytest.mark.parametrize('obj_list', (['hjk', 'jkgjg', 'lkhlkhl'],  # homogeneous string
                                      [21, 34, -56, 56.7, 1+1j*99],  # homogeneous numbers
                                      [np.array([45, 67, 87654]), np.array([[45, 67, 87654],
                                                                            [-45, -67, -87654]])],  # homogeneous ndarrays
                                      [init_axis(), init_axis()],  # homogeneous axis
                                      [init_data(), init_data(), init_data()],  # homogeneous dwa
                                      ['hjk', 34, np.array([45, 67, 87654]), init_data(), init_axis()]))  # inhomogeneous
def test_list_serialization_deserialization(get_data, obj_list):
    ser = Serializer(obj_list)
    list_back = DeSerializer(ser.to_bytes()).list_deserialization()
    assert isinstance(list_back, list)
    for ind in range(len(obj_list)):
        if isinstance(obj_list[ind], np.ndarray):
            assert np.allclose(obj_list[ind], list_back[ind])
        else:
            assert obj_list[ind] == list_back[ind]


    #     """ Convert a list of objects into a bytes message together with the info to convert it back
    #
    #     Parameters
    #     ----------
    #     list_object: list
    #         the list could contains either scalars, strings or ndarrays or Axis objects or DataWithAxis objects
    #         module
    #
    #     Returns
    #     -------
    #     bytes: the total bytes message to serialize the list of objects
    #
    #     Notes
    #     -----
    #
    #     The bytes sequence is constructed as:
    #     * the length of the list
    #     * get data type as a string
    #     * reshape array as 1D array and get the array dimensionality (len of array's shape)
    #     * convert Data array as bytes
    #     * serialize data type
    #     * serialize data length
    #     * serialize data shape length
    #     * serialize all values of the shape as integers converted to bytes
    #     * serialize array as bytes
    #     """
    #     if not isinstance(list_object, list):
    #         raise TypeError(f'{list_object} should be a list, not a {type(list_object)}')
    #
    #     bytes_string = b''
    #
    #     bytes_string += self.int_to_bytes(len(list_object))
    #     for obj in list_object:
    #         if isinstance(obj, DataWithAxes):
    #             bytes_string += self.string_serialization('dwa')
    #             bytes_string += self.dwa_serialization(obj)
    #
    #         elif isinstance(obj, Axis):
    #             bytes_string += self.string_serialization('axis')
    #             bytes_string += self.axis_serialization(obj)
    #
    #         elif isinstance(obj, np.ndarray):
    #             bytes_string += self.string_serialization('array')
    #             bytes_string += self.ndarray_serialization(obj)
    #
    #         elif isinstance(obj, str):
    #             bytes_string += self.string_serialization('string')
    #             bytes_string += self.string_serialization(obj)
    #
    #         elif isinstance(obj, numbers.Number):
    #             bytes_string += self.string_serialization('scalar')
    #             bytes_string += self.scalar_serialization(obj)
    #
    #         else:
    #             raise TypeError(f'the element {obj} type cannot be serialized into bytes, only numpy arrays'
    #                             f', strings, or scalars (int or float)')
    #     self._bytes_string += bytes_string
    #     return bytes_string
    #
    # def dwa_serialization(self, dwa: DataWithAxes) -> bytes:
    #     """ Convert a DataWithAxes into a bytes string
    #
    #     Parameters
    #     ----------
    #     dwa: DataWithAxes
    #
    #     Returns
    #     -------
    #     bytes: the total bytes message to serialize the DataWithAxes
    #
    #     Notes
    #     -----
    #     The bytes sequence is constructed as:
    #
    #     * serialize the string type: 'DataWithAxis'
    #     * serialize the timestamp: float
    #     * serialize the name
    #     * serialize the source enum as a string
    #     * serialize the dim enum as a string
    #     * serialize the distribution enum as a string
    #     * serialize the list of numpy arrays
    #     * serialize the list of labels
    #     * serialize the origin
    #     * serialize the nav_index tuple as a list of int
    #     * serialize the list of axis
    #     """
    #     if not isinstance(dwa, DataWithAxes):
    #         raise TypeError(f'{dwa} should be a DataWithAxes, not a {type(dwa)}')
    #
    #     bytes_string = b''
    #     bytes_string += self.object_type_serialization(dwa)
    #     bytes_string += self.scalar_serialization(dwa.timestamp)
    #     bytes_string += self.string_serialization(dwa.name)
    #     bytes_string += self.string_serialization(dwa.source.name)
    #     bytes_string += self.string_serialization(dwa.dim.name)
    #     bytes_string += self.string_serialization(dwa.distribution.name)
    #     bytes_string += self.list_serialization(dwa.data)
    #     bytes_string += self.list_serialization(dwa.labels)
    #     bytes_string += self.string_serialization(dwa.origin)
    #     bytes_string += self.list_serialization(list(dwa.nav_indexes))
    #     bytes_string += self.list_serialization(dwa.axes)
    #     self._bytes_string += bytes_string
    #     return bytes_string
    #
    # def dte_serialization(self, dte: DataToExport) -> bytes:
    #     """ Convert a DataToExport into a bytes string
    #
    #     Parameters
    #     ----------
    #     dte: DataToExport
    #
    #     Returns
    #     -------
    #     bytes: the total bytes message to serialize the DataToExport
    #
    #     Notes
    #     -----
    #     The bytes sequence is constructed as:
    #
    #     * serialize the string type: 'DataToExport'
    #     * serialize the timestamp: float
    #     * serialize the name
    #     * serialize the list of DataWithAxes
    #     """
    #     if not isinstance(dte, DataToExport):
    #         raise TypeError(f'{dte} should be a DataToExport, not a {type(dte)}')
    #
    #     bytes_string = b''
    #     bytes_string += self.object_type_serialization(dte)
    #     bytes_string += self.scalar_serialization(dte.timestamp)
    #     bytes_string += self.string_serialization(dte.name)
    #     bytes_string += self.list_serialization(dte.data)
    #     self._bytes_string += bytes_string
    #     return bytes_string
    #
