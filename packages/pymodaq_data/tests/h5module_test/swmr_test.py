# -*- coding: utf-8 -*-
"""Tests for SWMR (Single Writer Multiple Reader) support in the h5py backend."""

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from pymodaq_data.h5modules import backends
from pymodaq_data.h5modules.backends import H5Backend, is_h5py, is_tables

pytestmark = pytest.mark.skipif(not is_h5py, reason='h5py not available')


@pytest.fixture()
def h5_swmr(tmp_path):
    """Create an h5py backend file opened with swmr_mode=True."""
    bck = H5Backend('h5py')
    filepath = tmp_path / 'swmr_test.h5'
    bck.open_file(filepath, 'w', 'SWMR test file', swmr_mode=True)
    yield bck
    if bck.isopen():
        bck.close_file()


@pytest.fixture()
def h5_no_swmr(tmp_path):
    """Create an h5py backend file opened without swmr_mode."""
    bck = H5Backend('h5py')
    filepath = tmp_path / 'no_swmr_test.h5'
    bck.open_file(filepath, 'w', 'No SWMR test file')
    yield bck
    if bck.isopen():
        bck.close_file()


class TestSWMRBackend:

    def test_open_file_with_swmr_libver(self, tmp_path):
        """When swmr_mode=True and backend is h5py, file should be opened with libver='latest'."""
        import h5py
        bck = H5Backend('h5py')
        filepath = tmp_path / 'libver_test.h5'
        bck.open_file(filepath, 'w', 'test', swmr_mode=True)
        # h5py files opened with libver='latest' use the latest file format version
        # We can verify by checking the file's libver_bounds or driver info
        assert bck._swmr_mode is True
        assert bck._swmr_enabled is False
        # The file should be valid and open
        assert bck.isopen()
        bck.close_file()

        # Verify the file can be reopened with swmr=True (only possible if libver='latest' was used)
        f = h5py.File(str(filepath), 'r', swmr=True)
        f.close()

    def test_open_file_without_swmr(self, h5_no_swmr):
        """When swmr_mode is not set, _swmr_mode should be False."""
        assert h5_no_swmr._swmr_mode is False
        assert h5_no_swmr._swmr_enabled is False

    def test_enable_swmr_activates(self, h5_swmr):
        """enable_swmr() should set swmr_mode on the h5py file and update flag."""
        # Create a dataset first (required before enabling SWMR)
        h5_swmr.create_carray(h5_swmr.root(), 'test_data',
                              obj=np.array([1.0, 2.0, 3.0]))
        h5_swmr.flush()
        h5_swmr.enable_swmr()
        assert h5_swmr._swmr_enabled is True
        assert h5_swmr.is_swmr_active is True
        assert h5_swmr._h5file.swmr_mode is True

    def test_enable_swmr_idempotent(self, h5_swmr):
        """Calling enable_swmr() twice should not raise."""
        h5_swmr.create_carray(h5_swmr.root(), 'test_data',
                              obj=np.array([1.0, 2.0, 3.0]))
        h5_swmr.flush()
        h5_swmr.enable_swmr()
        h5_swmr.enable_swmr()  # should not raise
        assert h5_swmr.is_swmr_active is True

    @pytest.mark.skipif(not is_tables, reason='pytables not available')
    def test_enable_swmr_non_h5py_raises(self, tmp_path):
        """enable_swmr() should raise RuntimeError for non-h5py backends."""
        bck = H5Backend('tables')
        filepath = tmp_path / 'tables_test.h5'
        bck.open_file(filepath, 'w', 'test')
        with pytest.raises(RuntimeError, match='only supported with the h5py backend'):
            bck.enable_swmr()
        bck.close_file()

    def test_enable_swmr_without_swmr_mode_raises(self, h5_no_swmr):
        """enable_swmr() should raise if file was not opened with swmr_mode=True."""
        with pytest.raises(RuntimeError, match='not opened with swmr_mode=True'):
            h5_no_swmr.enable_swmr()

    def test_close_file_resets_swmr_enabled(self, h5_swmr):
        """close_file() should reset _swmr_enabled to False."""
        h5_swmr.create_carray(h5_swmr.root(), 'test_data',
                              obj=np.array([1.0, 2.0, 3.0]))
        h5_swmr.flush()
        h5_swmr.enable_swmr()
        assert h5_swmr._swmr_enabled is True
        h5_swmr.close_file()
        assert h5_swmr._swmr_enabled is False

    def test_carray_write_in_swmr(self, h5_swmr):
        """Writing to existing CARRAY datasets should work in SWMR mode."""
        data = np.array([1.0, 2.0, 3.0])
        arr = h5_swmr.create_carray(h5_swmr.root(), 'test_data', obj=data)
        h5_swmr.flush()
        h5_swmr.enable_swmr()

        # Write new data to existing array
        arr[0] = 99.0
        h5_swmr.flush()

        assert arr[0] == 99.0

    def test_earray_append_skips_attrs_in_swmr(self, h5_swmr):
        """EARRAY.append() should skip attrs['shape'] update in SWMR mode."""
        arr = h5_swmr.create_earray(h5_swmr.root(), 'test_earray',
                                    dtype=np.float64, data_shape=(3,))
        h5_swmr.flush()

        # Shape attr starts at (0, 3)
        initial_shape = arr.attrs['shape']
        assert initial_shape == (0, 3)

        h5_swmr.enable_swmr()

        # Append data in SWMR mode
        arr.append(np.array([1.0, 2.0, 3.0]))

        # Shape attr should NOT be updated (still (0, 3)) because SWMR forbids attr writes
        assert arr.attrs['shape'] == (0, 3)

        # But the actual data should be there (the dataset itself was resized)
        assert arr.node.shape[0] == 1

    def test_vlarray_append_skips_attrs_in_swmr(self, h5_swmr):
        """VLARRAY.append() should skip attrs['shape'] update in SWMR mode."""
        arr = h5_swmr.create_vlarray(h5_swmr.root(), 'test_vlarray',
                                     dtype=np.float64)
        h5_swmr.flush()

        initial_shape = arr.attrs['shape']
        assert initial_shape == (0,)

        h5_swmr.enable_swmr()

        # Append data in SWMR mode
        arr.append(np.array([1.0, 2.0, 3.0]))

        # Shape attr should NOT be updated
        assert arr.attrs['shape'] == (0,)

        # But the actual data should be there
        assert arr.node.shape[0] == 1

    def test_reconcile_swmr_attrs(self, tmp_path):
        """reconcile_swmr_attrs() should fix deferred shape attrs after SWMR ends."""
        bck = H5Backend('h5py')
        filepath = tmp_path / 'reconcile_test.h5'
        bck.open_file(filepath, 'w', 'test', swmr_mode=True)

        # Create arrays and append some data before SWMR
        earr = bck.create_earray(bck.root(), 'test_earray',
                                 dtype=np.float64, data_shape=(3,))
        bck.flush()
        bck.enable_swmr()

        # Append in SWMR mode (shape attr deferred)
        earr.append(np.array([1.0, 2.0, 3.0]))
        earr.append(np.array([4.0, 5.0, 6.0]))

        # Close to end SWMR
        bck.close_file()

        # Reopen and reconcile
        bck.open_file(filepath, 'a')
        bck.reconcile_swmr_attrs()

        # Shape should now be correct
        node = bck.get_node('/test_earray')
        assert node.attrs['shape'] == (2, 3)

        bck.close_file()

    def test_is_swmr_active_property(self, h5_swmr):
        """is_swmr_active should reflect the SWMR state."""
        assert h5_swmr.is_swmr_active is False
        h5_swmr.create_carray(h5_swmr.root(), 'dummy', obj=np.array([0.0]))
        h5_swmr.flush()
        h5_swmr.enable_swmr()
        assert h5_swmr.is_swmr_active is True


class TestSWMRSaving:
    """Tests for SWMR integration with the saving layer."""

    def test_init_file_with_swmr(self, tmp_path):
        """H5SaverLowLevel.init_file should pass swmr_mode through."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel
        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'saver_swmr.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)
        assert saver._swmr_mode is True
        saver.close_file()

    def test_finalize_swmr(self, tmp_path):
        """finalize_swmr() should close, reopen, reconcile, and close."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel
        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'finalize_swmr.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create structure
        earr = saver.create_earray(saver.root(), 'test_earray',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()

        # Append data (shape attr deferred)
        earr.append(np.array([1.0, 2.0, 3.0]))
        earr.append(np.array([4.0, 5.0, 6.0]))

        # Finalize
        saver.finalize_swmr()

        # Verify: reopen and check
        saver.open_file(filepath, 'r')
        node = saver.get_node('/test_earray')
        assert node.attrs['shape'] == (2, 3)
        saver.close_file()


class TestSWMRExtendedSaver:
    """Tests for SWMR with DataToExportExtendedSaver."""

    def test_extended_saver_swmr_lifecycle(self, tmp_path):
        """Full lifecycle: create file, add structure, enable SWMR, add data, finalize."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel
        from pymodaq_data.h5modules.data_saving import DataToExportExtendedSaver
        from pymodaq_data.data import DataWithAxes, DataSource, DataToExport, Axis

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'extended_swmr.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        scan_shape = (5,)
        ext_saver = DataToExportExtendedSaver(saver, extended_shape=scan_shape)
        ext_saver.set_swmr_flush_interval(2)

        # Create test data
        data_array = np.random.rand(10)
        dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                           axes=[Axis('x', 'um', data=np.arange(10), index=0)])
        dte = DataToExport('scan_data', data=[dwa])

        nav_axes = [Axis('scan_axis', 'mm', data=np.arange(5), index=0)]
        ext_saver.add_nav_axes(saver.raw_group, nav_axes)

        # First data point creates structure then activates SWMR
        ext_saver.add_data(saver.raw_group, dte, indexes=[0])
        assert saver.is_swmr_active is True
        assert ext_saver._swmr_activated is True

        # Subsequent data points
        for i in range(1, 5):
            data_array = np.random.rand(10)
            dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                               axes=[Axis('x', 'um', data=np.arange(10), index=0)])
            dte = DataToExport('scan_data', data=[dwa])
            ext_saver.add_data(saver.raw_group, dte, indexes=[i])

        # Finalize
        saver.finalize_swmr()

        # Verify data integrity
        saver.open_file(filepath, 'r')
        # Check that all shape attrs are reconciled
        for node in saver.walk_nodes('/'):
            if 'CLASS' in node.attrs:
                node_class = node.attrs['CLASS']
                if node_class in ('EARRAY', 'VLARRAY'):
                    assert node.attrs['shape'] == node.node.shape
        saver.close_file()

    def test_flush_interval(self, tmp_path):
        """Verify flush is called at the correct intervals."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel
        from pymodaq_data.h5modules.data_saving import DataToExportExtendedSaver
        from pymodaq_data.data import DataWithAxes, DataSource, DataToExport, Axis

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'flush_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        scan_shape = (10,)
        ext_saver = DataToExportExtendedSaver(saver, extended_shape=scan_shape)
        ext_saver.set_swmr_flush_interval(3)

        nav_axes = [Axis('scan_axis', 'mm', data=np.arange(10), index=0)]
        ext_saver.add_nav_axes(saver.raw_group, nav_axes)

        flush_call_count = 0
        original_flush = saver.flush

        def counting_flush():
            nonlocal flush_call_count
            flush_call_count += 1
            original_flush()

        # First call to create structure and activate SWMR
        data_array = np.random.rand(5)
        dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                           axes=[Axis('x', 'um', data=np.arange(5), index=0)])
        dte = DataToExport('scan_data', data=[dwa])
        ext_saver.add_data(saver.raw_group, dte, indexes=[0])

        # Now patch flush to count calls
        saver.flush = counting_flush
        flush_call_count = 0

        # Add 9 more data points (indexes 1-9)
        for i in range(1, 10):
            data_array = np.random.rand(5)
            dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                               axes=[Axis('x', 'um', data=np.arange(5), index=0)])
            dte = DataToExport('scan_data', data=[dwa])
            ext_saver.add_data(saver.raw_group, dte, indexes=[i])

        # With interval=3 and 9 writes (write_count 1-9), flush at 3,6,9 => 3 flushes
        assert flush_call_count == 3

        saver.flush = original_flush
        saver.close_file()

    def test_concurrent_read(self, tmp_path):
        """Verify a reader can see data after writer flush in SWMR mode."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'concurrent_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create structure
        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()

        # Append data and flush
        earr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        # Open as concurrent reader
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['data']
        ds.id.refresh()
        assert ds.shape[0] == 1
        np.testing.assert_array_equal(ds[0], [1.0, 2.0, 3.0])

        # Write more data
        earr.append(np.array([4.0, 5.0, 6.0]))
        saver.flush()

        # Reader should see new data after refresh
        ds.id.refresh()
        assert ds.shape[0] == 2
        np.testing.assert_array_equal(ds[1], [4.0, 5.0, 6.0])

        reader.close()
        saver.close_file()

    def test_concurrent_read_refresh_updates_view(self, tmp_path):
        """Verify that reader sees updated data after calling refresh."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'refresh_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create structure and initial data
        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()

        # Append initial data and flush
        earr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        # Open as concurrent reader
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['data']
        ds.id.refresh()
        initial_shape = ds.shape[0]
        assert initial_shape == 1  # Reader sees first row
        np.testing.assert_array_equal(ds[0], [1.0, 2.0, 3.0])

        # Write more data and flush
        earr.append(np.array([4.0, 5.0, 6.0]))
        saver.flush()

        # After refresh, reader should see new data
        ds.id.refresh()
        assert ds.shape[0] == 2
        np.testing.assert_array_equal(ds[1], [4.0, 5.0, 6.0])

        # Write even more and verify
        earr.append(np.array([7.0, 8.0, 9.0]))
        saver.flush()
        ds.id.refresh()
        assert ds.shape[0] == 3
        np.testing.assert_array_equal(ds[2], [7.0, 8.0, 9.0])

        reader.close()
        saver.close_file()

    def test_concurrent_read_multiple_datasets(self, tmp_path):
        """Verify reader can access multiple datasets simultaneously during SWMR."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'multi_dataset_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create multiple datasets
        earr1 = saver.create_earray(saver.root(), 'data1',
                                    dtype=np.float64, data_shape=(3,))
        earr2 = saver.create_earray(saver.root(), 'data2',
                                    dtype=np.float32, data_shape=(5,))
        carr = saver.create_carray(saver.root(), 'static_data',
                                   obj=np.array([100.0, 200.0, 300.0]))
        saver.flush()
        saver.enable_swmr()

        # Append data
        earr1.append(np.array([1.0, 2.0, 3.0]))
        earr2.append(np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float32))
        saver.flush()

        # Reader accesses all datasets
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds1 = reader['data1']
        ds2 = reader['data2']
        ds_static = reader['static_data']

        ds1.id.refresh()
        ds2.id.refresh()

        assert ds1.shape[0] == 1
        assert ds2.shape[0] == 1
        np.testing.assert_array_equal(ds1[0], [1.0, 2.0, 3.0])
        np.testing.assert_array_almost_equal(ds2[0], [10.0, 20.0, 30.0, 40.0, 50.0])
        np.testing.assert_array_equal(ds_static[:], [100.0, 200.0, 300.0])

        # Write more to both earrays
        earr1.append(np.array([4.0, 5.0, 6.0]))
        earr2.append(np.array([60.0, 70.0, 80.0, 90.0, 100.0], dtype=np.float32))
        saver.flush()

        ds1.id.refresh()
        ds2.id.refresh()

        assert ds1.shape[0] == 2
        assert ds2.shape[0] == 2

        reader.close()
        saver.close_file()

    def test_concurrent_read_vlarray(self, tmp_path):
        """Verify reader can read VLARRAY data during SWMR mode."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'vlarray_concurrent_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create vlarray
        vlarr = saver.create_vlarray(saver.root(), 'vldata', dtype=np.float64)
        saver.flush()
        saver.enable_swmr()

        # Append variable-length data
        vlarr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        # Reader opens and reads
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['vldata']
        ds.id.refresh()

        assert ds.shape[0] == 1
        np.testing.assert_array_equal(ds[0], [1.0, 2.0, 3.0])

        # Append more variable-length data (different sizes)
        vlarr.append(np.array([4.0, 5.0, 6.0, 7.0, 8.0]))
        saver.flush()

        ds.id.refresh()
        assert ds.shape[0] == 2
        np.testing.assert_array_equal(ds[1], [4.0, 5.0, 6.0, 7.0, 8.0])

        reader.close()
        saver.close_file()

    def test_concurrent_read_large_data(self, tmp_path):
        """Verify SWMR handles larger datasets correctly."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'large_data_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create array for large data
        data_shape = (1000,)  # 1000 elements per row
        earr = saver.create_earray(saver.root(), 'large_data',
                                   dtype=np.float64, data_shape=data_shape)
        saver.flush()
        saver.enable_swmr()

        # Open reader
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['large_data']

        # Write and verify multiple large rows
        num_rows = 10
        for i in range(num_rows):
            row_data = np.arange(1000, dtype=np.float64) + i * 1000
            earr.append(row_data)
            saver.flush()

            ds.id.refresh()
            assert ds.shape[0] == i + 1
            np.testing.assert_array_equal(ds[i], row_data)

        reader.close()
        saver.close_file()

    def test_concurrent_read_group_structure(self, tmp_path):
        """Verify reader can navigate group structure during SWMR."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'group_structure_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create group structure
        group1 = saver.get_set_group(saver.root(), 'group1', 'First Group')
        group2 = saver.get_set_group(saver.root(), 'group2', 'Second Group')
        subgroup = saver.get_set_group(group1, 'subgroup', 'Nested Group')

        # Create arrays in different groups
        earr1 = saver.create_earray(group1.node, 'data',
                                    dtype=np.float64, data_shape=(3,))
        earr2 = saver.create_earray(subgroup.node, 'nested_data',
                                    dtype=np.float64, data_shape=(2,))

        saver.flush()
        saver.enable_swmr()

        # Write data
        earr1.append(np.array([1.0, 2.0, 3.0]))
        earr2.append(np.array([10.0, 20.0]))
        saver.flush()

        # Reader navigates structure
        reader = h5py.File(str(filepath), 'r', swmr=True)

        # Check groups exist
        assert 'group1' in reader
        assert 'group2' in reader
        assert 'subgroup' in reader['group1']

        # Access nested data
        ds1 = reader['group1/data']
        ds2 = reader['group1/subgroup/nested_data']

        ds1.id.refresh()
        ds2.id.refresh()

        np.testing.assert_array_equal(ds1[0], [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(ds2[0], [10.0, 20.0])

        reader.close()
        saver.close_file()

    def test_concurrent_multiple_readers(self, tmp_path):
        """Verify multiple readers can access the file simultaneously."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'multi_reader_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create array
        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()

        # Write initial data
        earr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        # Open multiple readers
        reader1 = h5py.File(str(filepath), 'r', swmr=True)
        reader2 = h5py.File(str(filepath), 'r', swmr=True)
        reader3 = h5py.File(str(filepath), 'r', swmr=True)

        ds1 = reader1['data']
        ds2 = reader2['data']
        ds3 = reader3['data']

        # All readers refresh and verify they see the same data
        ds1.id.refresh()
        ds2.id.refresh()
        ds3.id.refresh()

        np.testing.assert_array_equal(ds1[0], [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(ds2[0], [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(ds3[0], [1.0, 2.0, 3.0])

        # Write more data
        earr.append(np.array([4.0, 5.0, 6.0]))
        saver.flush()

        # All readers refresh and see new data
        ds1.id.refresh()
        ds2.id.refresh()
        ds3.id.refresh()

        assert ds1.shape[0] == 2
        assert ds2.shape[0] == 2
        assert ds3.shape[0] == 2

        np.testing.assert_array_equal(ds1[1], [4.0, 5.0, 6.0])
        np.testing.assert_array_equal(ds2[1], [4.0, 5.0, 6.0])
        np.testing.assert_array_equal(ds3[1], [4.0, 5.0, 6.0])

        # Write even more and verify all readers can independently refresh
        earr.append(np.array([7.0, 8.0, 9.0]))
        saver.flush()

        ds1.id.refresh()
        ds2.id.refresh()
        ds3.id.refresh()

        assert ds1.shape[0] == 3
        np.testing.assert_array_equal(ds1[2], [7.0, 8.0, 9.0])
        np.testing.assert_array_equal(ds2[2], [7.0, 8.0, 9.0])
        np.testing.assert_array_equal(ds3[2], [7.0, 8.0, 9.0])

        reader1.close()
        reader2.close()
        reader3.close()
        saver.close_file()

    def test_concurrent_read_rapid_writes(self, tmp_path):
        """Verify reader handles rapid successive writes correctly."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'rapid_write_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create array
        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(10,))
        saver.flush()
        saver.enable_swmr()

        # Open reader
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['data']

        # Rapid writes with single flush at end
        num_rapid_writes = 50
        for i in range(num_rapid_writes):
            earr.append(np.arange(10, dtype=np.float64) + i * 10)
        saver.flush()

        # Reader should see all data after single refresh
        ds.id.refresh()
        assert ds.shape[0] == num_rapid_writes

        # Verify data integrity
        for i in range(num_rapid_writes):
            expected = np.arange(10, dtype=np.float64) + i * 10
            np.testing.assert_array_equal(ds[i], expected)

        reader.close()
        saver.close_file()

    def test_concurrent_read_2d_data(self, tmp_path):
        """Verify SWMR works correctly with 2D data."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / '2d_data_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create 2D array (each row is a 10x10 image)
        data_shape = (10, 10)
        earr = saver.create_earray(saver.root(), 'images',
                                   dtype=np.float64, data_shape=data_shape)
        saver.flush()
        saver.enable_swmr()

        # Open reader
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['images']

        # Write 2D frames
        for i in range(5):
            frame = np.ones((10, 10), dtype=np.float64) * (i + 1)
            earr.append(frame)
            saver.flush()

            ds.id.refresh()
            assert ds.shape == (i + 1, 10, 10)
            np.testing.assert_array_equal(ds[i], frame)

        reader.close()
        saver.close_file()

    def test_flush_interval_zero(self, tmp_path):
        """With flush_interval=0, no periodic flushes should happen."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel
        from pymodaq_data.h5modules.data_saving import DataToExportExtendedSaver
        from pymodaq_data.data import DataWithAxes, DataSource, DataToExport, Axis

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'no_flush_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        scan_shape = (5,)
        ext_saver = DataToExportExtendedSaver(saver, extended_shape=scan_shape)
        ext_saver.set_swmr_flush_interval(0)  # no periodic flush

        nav_axes = [Axis('scan_axis', 'mm', data=np.arange(5), index=0)]
        ext_saver.add_nav_axes(saver.raw_group, nav_axes)

        # First data point
        data_array = np.random.rand(5)
        dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                           axes=[Axis('x', 'um', data=np.arange(5), index=0)])
        dte = DataToExport('scan_data', data=[dwa])
        ext_saver.add_data(saver.raw_group, dte, indexes=[0])

        # Count flushes for remaining data points
        flush_count = 0
        original_flush = saver.flush

        def counting_flush():
            nonlocal flush_count
            flush_count += 1
            original_flush()

        saver.flush = counting_flush

        for i in range(1, 5):
            data_array = np.random.rand(5)
            dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                               axes=[Axis('x', 'um', data=np.arange(5), index=0)])
            dte = DataToExport('scan_data', data=[dwa])
            ext_saver.add_data(saver.raw_group, dte, indexes=[i])

        assert flush_count == 0  # no periodic flushes with interval=0

        saver.flush = original_flush
        saver.close_file()


class TestSWMRIndexedArrays:
    """Tests for SWMR with pre-allocated indexed arrays (DAQ_Scan workflow)."""

    def test_preallocated_carray_indexed_write(self, tmp_path):
        """Verify SWMR works with pre-allocated CARRAY using indexed writes."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'indexed_carray.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Pre-allocate array with scan shape (simulating a 5-point 1D scan with 10-element data)
        scan_shape = (5,)
        data_shape = (10,)
        full_shape = scan_shape + data_shape

        # Create pre-allocated array (like DAQ_Scan does)
        carr = saver.create_carray(saver.root(), 'scan_data',
                                   obj=np.zeros(full_shape, dtype=np.float64))
        saver.flush()
        saver.enable_swmr()

        # Open reader
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['scan_data']
        ds.id.refresh()

        # Write data at specific indices (simulating scan points)
        for scan_idx in range(5):
            data = np.arange(10, dtype=np.float64) + scan_idx * 100
            carr[scan_idx] = data
            saver.flush()

            # Reader should see the data after refresh
            ds.id.refresh()
            np.testing.assert_array_equal(ds[scan_idx], data)

        reader.close()
        saver.close_file()

    def test_preallocated_2d_scan_indexed_write(self, tmp_path):
        """Verify SWMR works with 2D scan shape (e.g., XY scan)."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'indexed_2d_scan.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Pre-allocate array with 2D scan shape (3x4 scan with 8-element data)
        scan_shape = (3, 4)
        data_shape = (8,)
        full_shape = scan_shape + data_shape

        carr = saver.create_carray(saver.root(), 'scan_data',
                                   obj=np.zeros(full_shape, dtype=np.float64))
        saver.flush()
        saver.enable_swmr()

        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['scan_data']

        # Write data at 2D indices
        for i in range(3):
            for j in range(4):
                data = np.arange(8, dtype=np.float64) + i * 100 + j * 10
                carr[i, j] = data
                saver.flush()

                ds.id.refresh()
                np.testing.assert_array_equal(ds[i, j], data)

        reader.close()
        saver.close_file()

    def test_preallocated_2d_image_data(self, tmp_path):
        """Verify SWMR works with 2D image data at each scan point."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'indexed_image_scan.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Pre-allocate: 5 scan points, each with a 10x10 image
        scan_shape = (5,)
        image_shape = (10, 10)
        full_shape = scan_shape + image_shape

        carr = saver.create_carray(saver.root(), 'images',
                                   obj=np.zeros(full_shape, dtype=np.float64))
        saver.flush()
        saver.enable_swmr()

        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['images']

        for scan_idx in range(5):
            image = np.ones(image_shape, dtype=np.float64) * (scan_idx + 1)
            carr[scan_idx] = image
            saver.flush()

            ds.id.refresh()
            np.testing.assert_array_equal(ds[scan_idx], image)

        reader.close()
        saver.close_file()

    def test_extended_saver_indexed_workflow(self, tmp_path):
        """Test DataToExportExtendedSaver with SWMR using indexed writes."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel
        from pymodaq_data.h5modules.data_saving import DataToExportExtendedSaver
        from pymodaq_data.data import DataWithAxes, DataSource, DataToExport, Axis
        from pymodaq_data.h5modules.backends import CARRAY
        import h5py

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'extended_indexed.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Simulate a 5-point 1D scan
        scan_shape = (5,)
        ext_saver = DataToExportExtendedSaver(saver, extended_shape=scan_shape)

        # Add navigation axes before first data
        nav_axes = [Axis('scan_axis', 'mm', data=np.linspace(0, 4, 5), index=0)]
        ext_saver.add_nav_axes(saver.raw_group, nav_axes)

        # First data point creates the structure
        data_array = np.random.rand(10)
        dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                           axes=[Axis('x', 'um', data=np.arange(10), index=0)])
        dte = DataToExport('scan_data', data=[dwa])
        ext_saver.add_data(saver.raw_group, dte, indexes=[0])

        # SWMR should now be active
        assert saver.is_swmr_active is True

        # Open reader
        reader = h5py.File(str(filepath), 'r', swmr=True)

        # Add remaining data points with indexed writes
        for i in range(1, 5):
            data_array = np.arange(10, dtype=np.float64) + i * 10
            dwa = DataWithAxes('test', source=DataSource(0), data=[data_array],
                               axes=[Axis('x', 'um', data=np.arange(10), index=0)])
            dte = DataToExport('scan_data', data=[dwa])
            ext_saver.add_data(saver.raw_group, dte, indexes=[i])
            saver.flush()

        # Find the data node by walking the structure
        data_path = None
        for node in saver.walk_nodes('/'):
            if isinstance(node, CARRAY) and 'data_type' in node.attrs:
                if node.attrs['data_type'] == 'data':
                    data_path = node.path
                    break

        assert data_path is not None, "Could not find data node"

        # Verify reader can see the data
        ds = reader[data_path]
        ds.id.refresh()
        assert ds.shape[0] == 5  # 5 scan points

        reader.close()
        saver.finalize_swmr()

        # Verify data integrity after finalization
        saver.open_file(filepath, 'r')
        node = saver.get_node(data_path)
        assert node.attrs['shape'][0] == 5
        saver.close_file()

    def test_concurrent_read_indexed_non_sequential(self, tmp_path):
        """Verify reader sees data when scan points are written non-sequentially."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'non_sequential.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Pre-allocate 10-point scan
        scan_shape = (10,)
        data_shape = (5,)
        full_shape = scan_shape + data_shape

        carr = saver.create_carray(saver.root(), 'scan_data',
                                   obj=np.zeros(full_shape, dtype=np.float64))
        saver.flush()
        saver.enable_swmr()

        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['scan_data']

        # Write data in non-sequential order (simulating snake scan or random access)
        write_order = [0, 9, 5, 2, 7, 1, 8, 4, 3, 6]
        for scan_idx in write_order:
            data = np.arange(5, dtype=np.float64) + scan_idx * 10
            carr[scan_idx] = data
            saver.flush()

            ds.id.refresh()
            np.testing.assert_array_equal(ds[scan_idx], data)

        # Verify all data after complete scan
        ds.id.refresh()
        for scan_idx in range(10):
            expected = np.arange(5, dtype=np.float64) + scan_idx * 10
            np.testing.assert_array_equal(ds[scan_idx], expected)

        reader.close()
        saver.close_file()

    def test_multiple_datasets_indexed(self, tmp_path):
        """Verify SWMR with multiple pre-allocated datasets (like multiple detectors)."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'multi_detector.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        scan_shape = (5,)

        # Create multiple detector data arrays
        det1_group = saver.get_set_group(saver.root(), 'Detector1', 'First Detector')
        det2_group = saver.get_set_group(saver.root(), 'Detector2', 'Second Detector')

        carr1 = saver.create_carray(det1_group.node, 'data',
                                    obj=np.zeros(scan_shape + (10,), dtype=np.float64))
        carr2 = saver.create_carray(det2_group.node, 'data',
                                    obj=np.zeros(scan_shape + (20,), dtype=np.float32))

        saver.flush()
        saver.enable_swmr()

        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds1 = reader['Detector1/data']
        ds2 = reader['Detector2/data']

        # Write to both detectors at each scan point
        for scan_idx in range(5):
            data1 = np.arange(10, dtype=np.float64) + scan_idx * 100
            data2 = np.arange(20, dtype=np.float32) + scan_idx * 50

            carr1[scan_idx] = data1
            carr2[scan_idx] = data2
            saver.flush()

            ds1.id.refresh()
            ds2.id.refresh()

            np.testing.assert_array_equal(ds1[scan_idx], data1)
            np.testing.assert_array_almost_equal(ds2[scan_idx], data2)

        reader.close()
        saver.close_file()

    def test_reader_partial_scan(self, tmp_path):
        """Verify reader correctly sees partially completed scan."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'partial_scan.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Pre-allocate for 10-point scan
        scan_shape = (10,)
        data_shape = (8,)
        full_shape = scan_shape + data_shape

        # Initialize with NaN to distinguish written vs unwritten
        init_data = np.full(full_shape, np.nan, dtype=np.float64)
        carr = saver.create_carray(saver.root(), 'scan_data', obj=init_data)
        saver.flush()
        saver.enable_swmr()

        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['scan_data']

        # Write only first 3 points
        for scan_idx in range(3):
            data = np.arange(8, dtype=np.float64) + scan_idx * 10
            carr[scan_idx] = data
        saver.flush()

        ds.id.refresh()

        # Reader sees written data
        for scan_idx in range(3):
            expected = np.arange(8, dtype=np.float64) + scan_idx * 10
            np.testing.assert_array_equal(ds[scan_idx], expected)

        # Unwritten points still have NaN
        assert np.all(np.isnan(ds[5]))

        # Continue writing
        for scan_idx in range(3, 10):
            data = np.arange(8, dtype=np.float64) + scan_idx * 10
            carr[scan_idx] = data
        saver.flush()

        ds.id.refresh()

        # Now all data should be valid
        for scan_idx in range(10):
            expected = np.arange(8, dtype=np.float64) + scan_idx * 10
            np.testing.assert_array_equal(ds[scan_idx], expected)

        reader.close()
        saver.close_file()
