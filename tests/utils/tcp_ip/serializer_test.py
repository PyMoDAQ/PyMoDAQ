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
              labels=None, klass=data_mod.DataWithAxes, errors=True) -> data_mod.DataWithAxes:
    if data is None:
        data = DATA2D
    if errors:
        errors = [np.random.random_sample(data.shape) for _ in range(Ndata)]
    else:
        errors = None
    return klass(name, source=source, data=[data for _ in range(Ndata)],
                 axes=axes, labels=labels, errors=errors,
                 extra1=True, extra2=[1, 2, 3])


@pytest.fixture()
def get_data():
    dat0D = init_data(DATA0D, 2, name='my0DData', source='raw', errors=True)
    dat1D_calculated = init_data(DATA1D, 2, name='my1DDatacalculated',
                                 klass=data_mod.DataCalculated, errors=True)
    dat1D_raw = init_data(DATA1D, 2, name='my1DDataraw', klass=data_mod.DataFromPlugins,
                          errors=False)
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
                                      ['hjk', 34, np.array([45, 67, 87654]), init_data(),
                                       init_axis(), True, 23, False]))  # inhomogeneous
def test_list_serialization_deserialization(get_data, obj_list):
    ser = Serializer(obj_list)
    list_back = DeSerializer(ser.to_bytes()).list_deserialization()
    assert isinstance(list_back, list)
    for ind in range(len(obj_list)):
        if isinstance(obj_list[ind], np.ndarray):
            assert np.allclose(obj_list[ind], list_back[ind])
        else:
            assert obj_list[ind] == list_back[ind]


def test_dwa_serialization_deserialization(get_data):
    dte = get_data

    for dwa in dte:
        dwa.extra_attributes = ['extra1', 'extra2']
        dwa.extra1 = True
        dwa.extra2 = 12.4
        ser = Serializer(dwa)
        assert isinstance(ser.to_bytes(), bytes)
        dwa_back = DeSerializer(ser.to_bytes()).dwa_deserialization()

        assert dwa_back.__class__.__name__ in DwaType.names()
        assert dwa_back.__class__.__name__ == dwa.__class__.__name__
        assert dwa == dwa_back
        assert dwa.extra_attributes == dwa_back.extra_attributes
        for attr in dwa.extra_attributes:
            assert getattr(dwa, attr) == getattr(dwa_back, attr)


def test_dte_serialization(get_data):
    dte = get_data

    ser = Serializer(dte)
    assert isinstance(ser.to_bytes(), bytes)
    dte_back = DeSerializer(ser.to_bytes()).dte_deserialization()

    assert dte_back.name == dte.name
    assert dte_back.timestamp == dte.timestamp
    for dwa in dte_back:
        assert dwa == dte.get_data_from_full_name(dwa.get_full_name())


def test_base_64_de_serialization(get_data: DataToExport):
    dte = get_data
    ser = Serializer(dte)
    serialized_string = ser.to_b64_string()
    assert isinstance(serialized_string, str)
    deser: DeSerializer = DeSerializer.from_b64_string(serialized_string)
    dte_back = deser.dte_deserialization()

    assert dte_back.name == dte.name
    assert dte_back.timestamp == dte.timestamp
    for dwa in dte_back:
        assert dwa == dte.get_data_from_full_name(dwa.get_full_name())
