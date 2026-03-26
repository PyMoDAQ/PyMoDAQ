import numpy as np
import pytest

from pymodaq_data import data as data_mod

xr = pytest.importorskip('xarray')


class TestXarrayConversion:
    """Tests for DataWithAxes.to_xarray / from_xarray and DataToExport.to_xarray / from_xarray."""


    def test_to_xarray_dims_coords(self):
        axis = data_mod.Axis('time', units='s', data=np.linspace(0, 9, 10), index=0)
        dwa = data_mod.DataRaw('mydata', data=[np.arange(10, dtype=float)], axes=[axis])
        ds = dwa.to_xarray()
        assert 'time' in ds.dims
        assert 'time' in ds.coords
        assert np.allclose(ds.coords['time'].values, axis.get_data())
        assert ds.coords['time'].attrs['units'] == 's'

    def test_to_xarray_data_vars(self):
        arr1 = np.arange(5, dtype=float)
        arr2 = np.arange(5, 10, dtype=float)
        dwa = data_mod.DataRaw('mydata', data=[arr1, arr2], labels=['ch0', 'ch1'])
        ds = dwa.to_xarray()
        assert 'ch0' in ds.data_vars
        assert 'ch1' in ds.data_vars
        assert np.allclose(ds['ch0'].values, arr1)
        assert np.allclose(ds['ch1'].values, arr2)

    def test_to_xarray_attrs(self):
        dwa = data_mod.DataRaw(
            'test', units='mm', data=[np.zeros((3, 4))],
            nav_indexes=(0,), origin='detector'
        )
        ds = dwa.to_xarray()
        assert ds.attrs['pymodaq_name'] == 'test'
        assert ds.attrs['pymodaq_units'] == 'mm'
        assert ds.attrs['pymodaq_source'] == 'raw'
        assert list(ds.attrs['pymodaq_nav_indexes']) == [0]

    def test_round_trip_1d(self):
        arr = np.linspace(1, 10, 20)
        axis = data_mod.Axis('x', units='nm', data=np.linspace(0, 19, 20), index=0)
        dwa = data_mod.DataRaw('signal', data=[arr], labels=['ch0'], axes=[axis])
        dwa2 = data_mod.DataWithAxes.from_xarray(dwa.to_xarray())
        assert dwa2.name == 'signal'
        assert np.allclose(dwa2[0], arr)
        axes = dwa2.get_axis_from_index(0)
        assert axes and axes[0].label == 'x'
        assert axes[0].units == 'nm'
        assert np.allclose(axes[0].get_data(), axis.get_data())

    def test_round_trip_2d_nav(self):
        arr = np.arange(12, dtype=float).reshape(3, 4)
        nav_axis = data_mod.Axis('nav', units='m', data=np.array([0., 1., 2.]), index=0)
        sig_axis = data_mod.Axis('sig', units='Hz', data=np.array([10., 20., 30., 40.]), index=1)
        dwa = data_mod.DataRaw(
            'nd', data=[arr], nav_indexes=(0,), axes=[nav_axis, sig_axis]
        )
        dwa2 = data_mod.DataWithAxes.from_xarray(dwa.to_xarray())
        assert tuple(dwa2.nav_indexes) == (0,)
        assert np.allclose(dwa2[0], arr)

    def test_round_trip_errors(self):
        arr = np.arange(5, dtype=float)
        err = arr * 0.1
        dwa = data_mod.DataRaw('errs', data=[arr], labels=['ch0'], errors=[err])
        ds = dwa.to_xarray()
        assert 'ch0_error' in ds.data_vars
        assert 'ch0' in ds.data_vars
        dwa2 = data_mod.DataWithAxes.from_xarray(ds)
        assert dwa2.errors is not None
        assert np.allclose(dwa2.errors[0], err)
        assert 'ch0_error' not in dwa2.labels

    def test_from_dataarray(self):
        da = xr.DataArray(
            np.arange(6, dtype=float),
            dims=['x'],
            coords={'x': np.arange(6, dtype=float)},
            name='myvar',
        )
        dwa = data_mod.DataWithAxes.from_xarray(da)
        assert dwa.name == 'from_xarray'
        assert np.allclose(dwa[0], da.values)

    def test_dte_to_datatree(self):
        dwa1 = data_mod.DataRaw('a', data=[np.zeros(5)])
        dwa2 = data_mod.DataRaw('b', data=[np.ones((3, 4))])
        dte = data_mod.DataToExport('myexp', data=[dwa1, dwa2])
        dt = dte.to_xarray()
        assert isinstance(dt, xr.DataTree)
        assert len(dt.children) == 2
        assert 'a' in dt.children
        assert 'b' in dt.children

    def test_dte_round_trip(self):
        dwa1 = data_mod.DataRaw('ch1', data=[np.arange(8, dtype=float)])
        dwa2 = data_mod.DataRaw('ch2', data=[np.arange(6, dtype=float).reshape(2, 3)])
        dte = data_mod.DataToExport('myexp', data=[dwa1, dwa2])
        dte2 = data_mod.DataToExport.from_xarray(dte.to_xarray())
        assert dte2.name == 'myexp'
        names = [dwa.name for dwa in dte2]
        assert 'ch1' in names
        assert 'ch2' in names
        ch1 = dte2.get_data_from_name('ch1')
        assert ch1.shape == (8,)
        ch2 = dte2.get_data_from_name('ch2')
        assert ch2.shape == (2, 3)
