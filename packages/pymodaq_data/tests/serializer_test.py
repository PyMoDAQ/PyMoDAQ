import numpy as np
import pytest

from serializall import SerializableFactory
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



def _all_fields(dwa: data_mod.DataWithAxes) -> dict:
    """Every piece of information a DataWithAxes holds, as plain python objects"""
    fields = dict(
        name=dwa.name, source=dwa.source.name, dim=dwa.dim.name,
        distribution=dwa.distribution.name, units=dwa.units, labels=list(dwa.labels),
        origin=dwa.origin, nav_indexes=tuple(dwa.nav_indexes), timestamp=dwa.timestamp,
        data=[np.asarray(array).tolist() for array in dwa.data],
        errors=None if dwa.errors is None else [np.asarray(err).tolist() for err in dwa.errors],
        axes=[(axis.label, axis.units, axis.index, axis.spread_order,
               np.asarray(axis.get_data()).tolist()) for axis in dwa.axes],
        extra_attributes=list(dwa.extra_attributes),
    )
    for name in dwa.extra_attributes:
        value = getattr(dwa, name)
        fields[f'extra:{name}'] = value.tolist() if isinstance(value, np.ndarray) else value
    return fields


def _data_all_kinds():
    """DataWithAxes of each kind: 1D with errors, ND with nav axis, spread, calculated"""
    extras = dict(str_attr='an iri', int_attr=3, float_attr=2.5, bool_attr=True, list_attr=[1, 2],
                  tuple_attr=(1, 2), dict_attr={'a': [1, {'b': 2}]}, none_attr=None,
                  bytes_attr=b'ab', array_attr=np.arange(3), unicode_attr='é→µ')
    dat1d = data_mod.DataRaw('1d', data=[np.arange(10.), 2 * np.arange(10.)], labels=['a', 'b'],
                             units='V', origin='det1',
                             axes=[data_mod.Axis('x', 'nm', data=np.linspace(400, 700, 10),
                                                 index=0)],
                             errors=[0.1 * np.ones(10), 0.2 * np.ones(10)], **extras)
    datnd = data_mod.DataRaw('nd', data=[np.random.rand(4, 6)], nav_indexes=(0,),
                             axes=[data_mod.Axis('n', 's', data=np.arange(4.), index=0),
                                   data_mod.Axis('s', 'nm', data=np.arange(6.), index=1)],
                             errors=[np.random.rand(4, 6)], extra='nd')
    datspread = data_mod.DataRaw('spread', distribution='spread', data=[np.random.rand(5)],
                                 nav_indexes=(0,),
                                 axes=[data_mod.Axis('x', 'm', data=np.random.rand(5), index=0,
                                                     spread_order=0),
                                       data_mod.Axis('y', 'm', data=np.random.rand(5), index=0,
                                                     spread_order=1)])
    datcalc = data_mod.DataCalculated('calc', data=[np.arange(5.)], units='mm', origin='calc1',
                                      extra=1.5)
    return [dat1d, datnd, datspread, datcalc]


@pytest.mark.parametrize('dwa', _data_all_kinds(), ids=lambda dwa: dwa.name)
def test_dwa_serialization_keeps_every_field(dwa):
    """Name, source, dim, distribution, data, units, labels, origin, nav_indexes, axes, errors,
    timestamp and all extra attributes (names and values) survive a serialization round trip"""
    dwa_back = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(dwa))

    assert type(dwa_back) is type(dwa)
    assert _all_fields(dwa_back) == _all_fields(dwa)
    for key, value in _all_fields(dwa).items():
        if key.startswith('extra:'):
            assert type(getattr(dwa_back, key[len('extra:'):])) is type(getattr(dwa, key[len('extra:'):]))


def test_dwa_serialization_without_errors_and_extra_attributes():
    dwa = data_mod.DataRaw('plain', data=[np.arange(5.)])
    dwa_back = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(dwa))
    assert dwa_back.errors is None
    assert dwa_back.extra_attributes == []


def test_dte_serialization_keeps_extra_attributes_and_children():
    dte = data_mod.DataToExport('dte', data=_data_all_kinds(), dte_extra=[1, 'a'], other=2.5)
    dte_back = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(dte))

    assert dte_back.name == dte.name
    assert dte_back.timestamp == dte.timestamp
    assert dte_back.extra_attributes == ['dte_extra', 'other']
    assert dte_back.dte_extra == [1, 'a']
    assert dte_back.other == 2.5
    assert len(dte_back) == len(dte)
    for dwa, dwa_back in zip(dte, dte_back):
        assert type(dwa_back) is type(dwa)
        assert _all_fields(dwa_back) == _all_fields(dwa)


def test_axis_extra_attributes_serialization():
    axis = data_mod.Axis('x', 'nm', data=np.linspace(400, 700, 10), index=0,
                         quantity_kind='Wavelength')
    axis_back = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(axis))
    assert axis_back.extra_attributes == ['quantity_kind']
    assert axis_back.quantity_kind == 'Wavelength'


def test_axis_without_extra_attributes_serialization():
    axis = data_mod.Axis('x', 'nm', data=np.linspace(400, 700, 10), index=1)
    axis_back = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(axis))
    assert axis_back.extra_attributes == []
    assert axis_back.index == 1


def test_axes_extra_attributes_inside_data_serialization():
    axis = data_mod.Axis('x', 'nm', data=np.linspace(400, 700, 10), index=0, spread_order=0,
                         quantity_kind='Wavelength', unit_iri='http://qudt.org/vocab/unit/NanoM',
                         units_history='nm->eV')
    dwa = data_mod.DataRaw('d', data=[np.arange(10.)], axes=[axis])
    dwa_back = ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(dwa))
    axis_back = dwa_back.axes[0]
    assert sorted(axis_back.extra_attributes) == ['quantity_kind', 'unit_iri', 'units_history']
    assert axis_back.unit_iri == 'http://qudt.org/vocab/unit/NanoM'
    assert axis_back.units_history == 'nm->eV'
