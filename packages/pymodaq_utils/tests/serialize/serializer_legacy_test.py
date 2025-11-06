# -*- coding: utf-8 -*-
"""
Created the 22/10/2023

@author: Sebastien Weber
"""

import numpy as np
import pytest


from pymodaq_data import data as data_mod
from pymodaq_data.data import Axis, DataToExport, DwaType
from pymodaq_utils.serialize.serializer_legacy import Serializer, DeSerializer


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
    dat1D_raw = init_data(DATA1D, 2, name='my1DDataraw', klass=data_mod.DataRaw,
                          errors=False)
    dte = data_mod.DataToExport(name='toexport', data=[dat0D, dat1D_calculated, dat1D_raw])
    return dte


def test_string_serialization_deserialization():

    string = 'Hello World'
    ser = Serializer(string)

    bytes_string = ser.string_serialization(string)
    assert len(bytes_string) == len(string) + 4 + 4 + len('str') + 4
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
        assert ser.object_type_serialization(obj)[11:].decode() == obj.__class__.__name__


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


class TestObjectSerializationDeSerialization:

    @pytest.mark.parametrize("obj, serialized", (
        (True, b'\x00\x00\x00\x14\x00\x00\x00\x04bool\x00\x00\x00\x03|b1\x00\x00\x00\x01\x01'),
        # (123, b'\x00\x00\x00\x06scalar\x00\x00\x00\x03<i4\x00\x00\x00\x04{\x00\x00\x00'),  # it varies on different test machines
        (10.45, b'\x00\x00\x00\x1c\x00\x00\x00\x05float\x00\x00\x00\x03<f8\x00\x00\x00\x08fffff\xe6$@'),
        (1 + 2j, b"\x00\x00\x00'\x00\x00\x00\x07complex\x00\x00\x00\x04<c16\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@"),
        ('hello world', b'\x00\x00\x00\x16\x00\x00\x00\x03str\x00\x00\x00\x0bhello world'),
        (b'hello binary world', b'\x00\x00\x00\x1f\x00\x00\x00\x05bytes\x00\x00\x00\x12hello binary world'),
    ))
    def test_serialization(self, obj, serialized):
        assert Serializer().type_and_object_serialization(obj) == serialized
        assert Serializer(obj).type_and_object_serialization() == serialized
        assert DeSerializer(serialized).type_and_object_deserialization() == obj

    def test_array(self):
        obj = np.array([[0.1, 0.5], [5, 7], [8, 9]])
        serialized = (b'\x00\x00\x00R\x00\x00\x00\x07ndarray\x00\x00\x00\x03<f8\x00\x00\x000\x00'
                      b'\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x02\x9a\x99\x99\x99\x99\x99\xb9?'
                      b'\x00\x00\x00\x00\x00\x00\xe0?\x00\x00\x00\x00\x00\x00\x14@\x00\x00\x00\x00'
                      b'\x00\x00\x1c@\x00\x00\x00\x00\x00\x00 @\x00\x00\x00\x00\x00\x00"@')

        assert Serializer().type_and_object_serialization(obj) == serialized
        assert Serializer(obj).type_and_object_serialization() == serialized
        assert np.allclose(DeSerializer(serialized).type_and_object_deserialization(), obj)

    def test_dwa(self, get_data):
        dte = get_data
        for obj in dte:
            assert (DeSerializer(Serializer().type_and_object_serialization(obj)).
                    type_and_object_deserialization() == obj)

    def test_axis(self, get_data):
        dte = get_data
        for dwa in dte:
            for obj in dwa.axes:
                assert (DeSerializer(Serializer().type_and_object_serialization(obj)).
                        type_and_object_deserialization() == obj)

    def test_list(self, get_data):
        dte = get_data
        obj = [True, 12.4, dte[0], [False, 78]]

        assert (DeSerializer(Serializer().type_and_object_serialization(obj)).
                type_and_object_deserialization() == obj)

    def test_dte(self, get_data):
        dte_in = get_data

        serialized = Serializer().type_and_object_serialization(dte_in)
        dte_out = DeSerializer(serialized).type_and_object_deserialization()

        for dwa_name in dte_in.get_full_names():
            assert dte_in.get_data_from_full_name(dwa_name) == dte_out.get_data_from_full_name(dwa_name)
