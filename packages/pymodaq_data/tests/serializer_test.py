import numpy as np
import pytest

from pymodaq_utils.serialize.factory import SerializableFactory
from pymodaq_data import data as data_mod


ser_factory = SerializableFactory()


LABEL = 'A Label'
UNITS = 'mm'
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


class DataFromPlugins(data_mod.DataRaw):
    """ Inheriting class for test purpose"""
    pass


def init_axis(data=None, index=0):
    if data is None:
        data = DATA
    return data_mod.Axis(label=LABEL, units=UNITS, data=data, index=index)


def init_data(data=None, Ndata=1, axes=[], name='myData', source=data_mod.DataSource['raw'],
              labels=None, klass=data_mod.DataWithAxes,
              errors=True, units='ms') -> data_mod.DataWithAxes:
    if data is None:
        data = DATA2D
    if errors:
        errors = [np.random.random_sample(data.shape) for _ in range(Ndata)]
    else:
        errors = None
    return klass(name, source=source, data=[data for _ in range(Ndata)],
                 axes=axes, labels=labels, errors=errors,
                 extra1=True, extra2=[1, 2, 3], units=units)


@pytest.fixture()
def get_data():
    dat0D = init_data(DATA0D, 2, name='my0DData', source='raw', errors=True)
    dat1D_calculated = init_data(DATA1D, 2, name='my1DDatacalculated',
                                 klass=data_mod.DataCalculated, errors=True)
    dat1D_plugin = init_data(DATA1D, 2, name='my1DDataraw', klass=DataFromPlugins,
                          errors=False)
    dte = data_mod.DataToExport(name='toexport', data=[dat0D, dat1D_calculated, dat1D_plugin])
    return dte


def test_axis_serialization_deserialization():

    axis = init_axis()

    ser = axis.serialize(axis)
    assert isinstance(ser, bytes)

    axis_deser = axis.deserialize(ser)[0]
    assert axis_deser == axis

    axis_back = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(axis))
    assert axis_back == axis


def test_dwa_serialization_deserialization(get_data):
    dte = get_data

    for dwa in dte:
        dwa.extra_attributes = ['extra1', 'extra2']
        dwa.extra1 = True
        dwa.extra2 = 12.4
        ser = ser_factory.get_apply_serializer(dwa)
        assert isinstance(ser, bytes)
        dwa_back = ser_factory.get_apply_deserializer(ser)

        assert dwa_back == dwa
        assert dwa_back.__class__.__name__ == dwa.__class__.__name__
        assert dwa == dwa_back
        assert dwa.extra_attributes == dwa_back.extra_attributes
        for attr in dwa.extra_attributes:
            assert getattr(dwa, attr) == getattr(dwa_back, attr)

    for dwa in dte:
        assert ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(dwa)) == dwa


def test_dte_serialization(get_data):
    dte = get_data

    ser = ser_factory.get_apply_serializer(dte)
    assert isinstance(ser, bytes)
    dte_back = ser_factory.get_apply_deserializer(ser)

    assert dte_back.name == dte.name
    assert dte_back.timestamp == dte.timestamp
    for dwa in dte_back:
        assert dwa == dte.get_data_from_full_name(dwa.get_full_name())

    dte_back_factory = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(dte))
    assert dte_back_factory.name == dte.name
    assert dte_back_factory.timestamp == dte.timestamp
    for dwa in dte_back_factory:
        assert dwa == dte.get_data_from_full_name(dwa.get_full_name())

