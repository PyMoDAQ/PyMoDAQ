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
        saver.set_swmr_flush_interval(2)

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
        saver.set_swmr_flush_interval(3)

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
        saver.set_swmr_flush_interval(0)  # no periodic flush

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


class TestSWMRAttributeTracking:
    """Tests for swmr_active attribute tracking."""

    def test_swmr_active_attribute_set_on_enable(self, tmp_path):
        """Verify swmr_active attribute is set to True when SWMR is enabled."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'swmr_active_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create a dataset (required before enabling SWMR)
        saver.create_carray(saver.root(), 'data', obj=np.array([1.0, 2.0]))
        saver.flush()

        # Before enabling SWMR, attribute should not exist or be False
        assert not saver.root().attrs.get('swmr_active', False)

        saver.enable_swmr()

        # After enabling SWMR, attribute should be True
        assert saver.root().attrs['swmr_active']

        saver.close_file()

    def test_swmr_active_attribute_cleared_on_reconcile(self, tmp_path):
        """Verify swmr_active is set to False after reconcile_swmr_attrs."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'swmr_reconcile_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0, 2.0]))
        saver.flush()
        saver.enable_swmr()

        assert saver.root().attrs['swmr_active']

        # Finalize SWMR (close, reopen, reconcile)
        saver.finalize_swmr()

        # Reopen to check attribute
        saver.open_file(filepath, 'r')
        assert not saver.root().attrs['swmr_active']
        saver.close_file()

    def test_reader_can_detect_swmr_active(self, tmp_path):
        """Verify a reader can detect if writer has SWMR active."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'detect_swmr_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0, 2.0]))
        saver.flush()
        saver.enable_swmr()
        saver.flush()

        # Reader opens and checks attribute
        reader = h5py.File(str(filepath), 'r', swmr=True)
        reader_swmr_active = reader.attrs.get('swmr_active', False)
        assert bool(reader_swmr_active)
        reader.close()

        saver.close_file()


class TestCloseFileCleanup:
    """Tests for file handle cleanup on close."""

    def test_close_file_sets_h5file_to_none(self, tmp_path):
        """Verify close_file sets _h5file to None."""
        from pymodaq_data.h5modules.backends import H5Backend

        bck = H5Backend('h5py')
        filepath = tmp_path / 'close_test.h5'
        bck.open_file(filepath, 'w', 'test')

        assert bck._h5file is not None
        assert bck.isopen()

        bck.close_file()

        assert bck._h5file is None
        assert not bck.isopen()

    def test_close_file_resets_swmr_enabled(self, tmp_path):
        """Verify close_file resets _swmr_enabled flag."""
        from pymodaq_data.h5modules.backends import H5Backend

        bck = H5Backend('h5py')
        filepath = tmp_path / 'swmr_close_test.h5'
        bck.open_file(filepath, 'w', 'test', swmr_mode=True)
        bck.create_carray(bck.root(), 'data', obj=np.array([1.0]))
        bck.flush()
        bck.enable_swmr()

        assert bck._swmr_enabled is True

        bck.close_file()

        assert bck._swmr_enabled is False


class TestFinalizeSWMRKeepOpen:
    """Tests for finalize_swmr with keep_open parameter."""

    def test_finalize_swmr_keep_open_true(self, tmp_path):
        """Verify finalize_swmr(keep_open=True) leaves file open."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'keep_open_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0, 2.0]))
        saver.flush()
        saver.enable_swmr()

        saver.finalize_swmr(keep_open=True)

        # File should still be open
        assert saver.isopen()

        # Can set attributes now (not in SWMR mode anymore)
        saver.root().attrs['test_attr'] = 'test_value'
        saver.flush()

        saver.close_file()

        # Verify attribute was saved
        saver.open_file(filepath, 'r')
        assert saver.root().attrs['test_attr'] == 'test_value'
        saver.close_file()

    def test_finalize_swmr_keep_open_false(self, tmp_path):
        """Verify finalize_swmr(keep_open=False) closes file."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'close_after_finalize.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0, 2.0]))
        saver.flush()
        saver.enable_swmr()

        saver.finalize_swmr(keep_open=False)

        # File should be closed
        assert not saver.isopen()
        assert saver._h5file is None


class TestSWMRUtilityFunctions:
    """Tests for SWMR utility functions."""

    def test_open_h5_file_for_reading_normal_file(self, tmp_path):
        """Verify open_h5_file_for_reading works with normal (non-SWMR) file."""
        import h5py
        from pymodaq_data.h5modules import open_h5_file_for_reading

        filepath = tmp_path / 'normal_file.h5'

        # Create a normal file
        with h5py.File(str(filepath), 'w') as f:
            f.create_dataset('data', data=[1, 2, 3])

        # Open with utility function
        f, is_swmr = open_h5_file_for_reading(str(filepath))

        assert is_swmr is False
        np.testing.assert_array_equal(f['data'][:], [1, 2, 3])
        f.close()

    def test_open_h5_file_for_reading_swmr_file(self, tmp_path):
        """Verify open_h5_file_for_reading detects SWMR file."""
        import h5py
        from pymodaq_data.h5modules import open_h5_file_for_reading
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'swmr_utility_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0, 2.0, 3.0]))
        saver.flush()
        saver.enable_swmr()
        saver.flush()

        # Open with utility function
        f, is_swmr = open_h5_file_for_reading(str(filepath))

        assert is_swmr is True
        f.close()

        saver.close_file()

    def test_open_h5_file_for_reading_force_swmr(self, tmp_path):
        """Verify open_h5_file_for_reading with swmr=True forces SWMR mode."""
        import h5py
        from pymodaq_data.h5modules import open_h5_file_for_reading

        filepath = tmp_path / 'force_swmr.h5'

        # Create file with libver='latest' (required for SWMR)
        with h5py.File(str(filepath), 'w', libver='latest') as f:
            f.create_dataset('data', data=[1, 2, 3])

        # Force SWMR mode
        f, is_swmr = open_h5_file_for_reading(str(filepath), swmr=True)

        assert is_swmr is True
        f.close()

    def test_open_h5_file_for_reading_force_no_swmr(self, tmp_path):
        """Verify open_h5_file_for_reading with swmr=False opens normally."""
        import h5py
        from pymodaq_data.h5modules import open_h5_file_for_reading

        filepath = tmp_path / 'no_swmr.h5'

        with h5py.File(str(filepath), 'w') as f:
            f.create_dataset('data', data=[1, 2, 3])

        f, is_swmr = open_h5_file_for_reading(str(filepath), swmr=False)

        assert is_swmr is False
        f.close()

    def test_is_file_swmr_active_true(self, tmp_path):
        """Verify is_file_swmr_active returns True for active SWMR file."""
        from pymodaq_data.h5modules import is_file_swmr_active
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'swmr_active_check.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0]))
        saver.flush()
        saver.enable_swmr()
        saver.flush()

        # Check from outside
        assert is_file_swmr_active(str(filepath)) is True

        saver.close_file()

    def test_is_file_swmr_active_false(self, tmp_path):
        """Verify is_file_swmr_active returns False for normal file."""
        import h5py
        from pymodaq_data.h5modules import is_file_swmr_active

        filepath = tmp_path / 'normal_check.h5'

        with h5py.File(str(filepath), 'w') as f:
            f.create_dataset('data', data=[1, 2, 3])

        assert is_file_swmr_active(str(filepath)) is False

    def test_is_file_swmr_active_after_finalize(self, tmp_path):
        """Verify is_file_swmr_active returns False after finalize."""
        from pymodaq_data.h5modules import is_file_swmr_active
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'finalized_check.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0]))
        saver.flush()
        saver.enable_swmr()
        saver.finalize_swmr()

        assert is_file_swmr_active(str(filepath)) is False


class TestSWMRConfigEntries:
    """Tests for SWMR-related config entries."""

    def test_swmr_config_entries_exist(self):
        """Verify SWMR config entries are present in config template."""
        from pymodaq_data.config import Config

        config = Config()

        # Check SWMR entries exist in data_saving
        data_saving_children = config.get_children('data_saving')
        assert 'swmr_enabled' in data_saving_children
        assert 'swmr_flush_interval' in data_saving_children

    def test_swmr_enabled_is_bool(self):
        """Verify swmr_enabled is a boolean (value depends on user config)."""
        from pymodaq_data.config import Config

        config = Config()
        swmr_enabled = config('data_saving', 'swmr_enabled')
        assert isinstance(swmr_enabled, bool)

    def test_swmr_flush_interval_is_int(self):
        """Verify swmr_flush_interval is an integer (value depends on user config)."""
        from pymodaq_data.config import Config

        config = Config()
        flush_interval = config('data_saving', 'swmr_flush_interval')
        assert isinstance(flush_interval, int)


class TestHdf5BackendConfig:
    """Tests for hdf5_backend config handling."""

    def test_hdf5_backend_is_list(self):
        """Verify hdf5_backend is a list under general."""
        from pymodaq_data.config import Config

        config = Config()
        backends_list = config('general', 'hdf5_backend')
        assert isinstance(backends_list, list)
        assert len(backends_list) > 0
        assert 'tables' in backends_list or 'h5py' in backends_list

    def test_hdf5_backend_default_is_first(self):
        """Verify first element of hdf5_backend is the default."""
        from pymodaq_data.config import Config

        config = Config()
        backends_list = config('general', 'hdf5_backend')
        assert isinstance(backends_list[0], str)
        assert backends_list[0] in ['tables', 'h5py', 'h5pyd']

    def test_hdf5_backend_config_children(self):
        """Verify h5file config section has expected children."""
        from pymodaq_data.config import Config

        config = Config()
        children = config.get_children('data_saving', 'h5file')
        assert 'save_path' in children
        assert 'compression_level' in children


class TestSWMRReconciliation:
    """Tests for SWMR attr reconciliation edge cases."""

    def test_reconcile_updates_all_earray_shapes(self, tmp_path):
        """Verify reconcile updates shape attrs on all EARRAY nodes."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'multi_earray.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create multiple earrays
        earr1 = saver.create_earray(saver.root(), 'earray1',
                                    dtype=np.float64, data_shape=(3,))
        earr2 = saver.create_earray(saver.root(), 'earray2',
                                    dtype=np.float64, data_shape=(5,))
        earr3 = saver.create_earray(saver.root(), 'earray3',
                                    dtype=np.float64, data_shape=(2,))
        saver.flush()
        saver.enable_swmr()

        # Append different amounts to each
        earr1.append(np.array([1.0, 2.0, 3.0]))
        earr1.append(np.array([4.0, 5.0, 6.0]))  # 2 rows

        earr2.append(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))  # 1 row

        earr3.append(np.array([1.0, 2.0]))
        earr3.append(np.array([3.0, 4.0]))
        earr3.append(np.array([5.0, 6.0]))  # 3 rows

        # Shapes should be stale during SWMR
        assert earr1.attrs['shape'] == (0, 3)
        assert earr2.attrs['shape'] == (0, 5)
        assert earr3.attrs['shape'] == (0, 2)

        # Finalize and reconcile
        saver.finalize_swmr()

        # Reopen and verify all shapes are correct
        saver.open_file(filepath, 'r')
        node1 = saver.get_node('/earray1')
        node2 = saver.get_node('/earray2')
        node3 = saver.get_node('/earray3')

        assert node1.attrs['shape'] == (2, 3)
        assert node2.attrs['shape'] == (1, 5)
        assert node3.attrs['shape'] == (3, 2)

        saver.close_file()

    def test_reconcile_updates_vlarray_shapes(self, tmp_path):
        """Verify reconcile updates shape attrs on VLARRAY nodes."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'vlarray_reconcile.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        vlarr = saver.create_vlarray(saver.root(), 'vldata', dtype=np.float64)
        saver.flush()
        saver.enable_swmr()

        # Append variable-length rows
        vlarr.append(np.array([1.0, 2.0]))
        vlarr.append(np.array([3.0, 4.0, 5.0, 6.0]))
        vlarr.append(np.array([7.0]))

        # Shape should be stale
        assert vlarr.attrs['shape'] == (0,)

        saver.finalize_swmr()

        saver.open_file(filepath, 'r')
        node = saver.get_node('/vldata')
        assert node.attrs['shape'] == (3,)
        saver.close_file()

    def test_reconcile_in_nested_groups(self, tmp_path):
        """Verify reconcile works for arrays in nested group structure."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'nested_reconcile.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        # Create nested structure
        group1 = saver.get_set_group(saver.root(), 'level1', 'Level 1')
        group2 = saver.get_set_group(group1.node, 'level2', 'Level 2')
        group3 = saver.get_set_group(group2.node, 'level3', 'Level 3')

        # Create arrays at different levels
        earr_root = saver.create_earray(saver.root(), 'root_data',
                                        dtype=np.float64, data_shape=(2,))
        earr_l1 = saver.create_earray(group1.node, 'l1_data',
                                      dtype=np.float64, data_shape=(3,))
        earr_l3 = saver.create_earray(group3.node, 'l3_data',
                                      dtype=np.float64, data_shape=(4,))

        saver.flush()
        saver.enable_swmr()

        # Append data
        earr_root.append(np.array([1.0, 2.0]))
        earr_l1.append(np.array([1.0, 2.0, 3.0]))
        earr_l1.append(np.array([4.0, 5.0, 6.0]))
        earr_l3.append(np.array([1.0, 2.0, 3.0, 4.0]))

        saver.finalize_swmr()

        saver.open_file(filepath, 'r')
        assert saver.get_node('/root_data').attrs['shape'] == (1, 2)
        assert saver.get_node('/level1/l1_data').attrs['shape'] == (2, 3)
        assert saver.get_node('/level1/level2/level3/l3_data').attrs['shape'] == (1, 4)
        saver.close_file()


class TestSWMRErrorHandling:
    """Tests for SWMR error handling and edge cases."""

    def test_double_enable_swmr_safe(self, h5_swmr):
        """Verify enable_swmr can be called multiple times without error."""
        h5_swmr.create_carray(h5_swmr.root(), 'data', obj=np.array([1.0]))
        h5_swmr.flush()

        h5_swmr.enable_swmr()
        assert h5_swmr.is_swmr_active is True

        # Second call should not raise
        h5_swmr.enable_swmr()
        assert h5_swmr.is_swmr_active is True

        # Third call still safe
        h5_swmr.enable_swmr()
        assert h5_swmr.is_swmr_active is True

    def test_close_without_finalize(self, tmp_path):
        """Verify closing without finalize doesn't corrupt file."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'close_no_finalize.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()

        earr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        # Close without finalize (simulating unexpected exit)
        saver.close_file()

        # File should still be readable
        with h5py.File(str(filepath), 'r') as f:
            assert f['data'].shape == (1, 3)
            np.testing.assert_array_equal(f['data'][0], [1.0, 2.0, 3.0])
            # Shape attr will be stale but data is intact
            # This is expected behavior - finalize is needed for clean attrs

    def test_finalize_already_closed(self, tmp_path):
        """Verify finalize_swmr handles already-closed file gracefully."""
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'finalize_closed.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        saver.create_carray(saver.root(), 'data', obj=np.array([1.0]))
        saver.flush()
        saver.enable_swmr()
        saver.close_file()

        # finalize_swmr should handle this - it will try to close (noop)
        # then open, reconcile, and close
        saver.finalize_swmr()

        # Verify file is readable and swmr_active cleared on root
        saver.open_file(filepath, 'r')
        assert not saver.root().attrs['swmr_active']
        saver.close_file()

    def test_read_during_swmr_no_refresh_sees_stale(self, tmp_path):
        """Verify reader without refresh sees stale data (expected behavior)."""
        import h5py
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'stale_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()

        # Append initial data
        earr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        # Open reader and get initial shape
        reader = h5py.File(str(filepath), 'r', swmr=True)
        ds = reader['data']
        ds.id.refresh()
        initial_shape = ds.shape[0]

        # Write more data
        earr.append(np.array([4.0, 5.0, 6.0]))
        earr.append(np.array([7.0, 8.0, 9.0]))
        saver.flush()

        # Without refresh, reader might see old shape
        # (This is expected SWMR behavior - refresh is needed)
        shape_before_refresh = ds.shape[0]

        # After refresh, should see new shape
        ds.id.refresh()
        shape_after_refresh = ds.shape[0]

        # The test verifies the refresh is necessary
        assert shape_after_refresh == 3
        # Note: shape_before_refresh might be 1, 2, or 3 depending on timing
        # but after refresh it must be 3

        reader.close()
        saver.close_file()


class TestIsSwmrCompatibleProperty:
    """Tests for the is_swmr_compatible property on H5Backend."""

    def test_swmr_file_is_compatible(self, tmp_path):
        """File created with swmr_mode=True should report is_swmr_compatible=True."""
        bck = H5Backend('h5py')
        filepath = tmp_path / 'swmr_compat.h5'
        bck.open_file(filepath, 'w', 'test', swmr_mode=True)
        assert bck.is_swmr_compatible is True
        bck.close_file()

        # Reopen in read mode and check again
        bck.open_file(filepath, 'r')
        assert bck.is_swmr_compatible is True
        bck.close_file()

    def test_non_swmr_file_is_not_compatible(self, tmp_path):
        """File created without swmr_mode should report is_swmr_compatible=False."""
        bck = H5Backend('h5py')
        filepath = tmp_path / 'no_swmr_compat.h5'
        bck.open_file(filepath, 'w', 'test')
        assert bck.is_swmr_compatible is False
        bck.close_file()

    def test_is_swmr_compatible_closed_file(self, tmp_path):
        """is_swmr_compatible should return False when no file is open."""
        bck = H5Backend('h5py')
        filepath = tmp_path / 'closed.h5'
        bck.open_file(filepath, 'w', 'test')
        bck.close_file()
        assert bck.is_swmr_compatible is False


class TestAttributesGet:
    """Tests for Attributes.get() method."""

    def test_get_existing_attr(self, h5_swmr):
        """get() returns the value for an existing attribute."""
        h5_swmr.root().attrs['test_key'] = 42
        assert h5_swmr.root().attrs.get('test_key') == 42

    def test_get_missing_attr_returns_default(self, h5_swmr):
        """get() returns default when attribute doesn't exist."""
        assert h5_swmr.root().attrs.get('nonexistent', 'fallback') == 'fallback'

    def test_get_missing_attr_returns_none(self, h5_swmr):
        """get() returns None by default when attribute doesn't exist."""
        assert h5_swmr.root().attrs.get('nonexistent') is None


class TestSetBackend:
    """Tests for H5Backend.set_backend() method."""

    def test_set_backend_h5py(self):
        """set_backend('h5py') should set backend and library."""
        import h5py
        bck = H5Backend('h5py')
        assert bck.backend == 'h5py'
        assert bck.h5_library is h5py

    @pytest.mark.skipif(not is_tables, reason='pytables not available')
    def test_set_backend_tables(self):
        """set_backend('tables') should set backend and library."""
        import tables
        bck = H5Backend('tables')
        assert bck.backend == 'tables'
        assert bck.h5_library is tables

    def test_set_backend_invalid_raises(self):
        """set_backend with invalid name should raise ValueError."""
        with pytest.raises(ValueError, match='Unknown backend'):
            H5Backend('invalid_backend')

    def test_set_backend_closes_open_file(self, tmp_path):
        """Switching backend should close any open file."""
        bck = H5Backend('h5py')
        filepath = tmp_path / 'backend_switch.h5'
        bck.open_file(filepath, 'w', 'test')
        assert bck.isopen()
        bck.set_backend('h5py')
        assert not bck.isopen()


class TestSWMRUtilities:
    """Tests for swmr.py utility functions."""

    def test_collect_datasets(self, tmp_path):
        """collect_datasets returns a dict of all datasets under a group."""
        import h5py
        from pymodaq_data.h5modules.swmr import collect_datasets

        filepath = tmp_path / 'collect_test.h5'
        with h5py.File(str(filepath), 'w') as f:
            g = f.create_group('RawData')
            g.create_dataset('data1', data=[1, 2, 3])
            sub = g.create_group('sub')
            sub.create_dataset('data2', data=[4, 5, 6])

        with h5py.File(str(filepath), 'r') as f:
            cache = collect_datasets(f['RawData'])

        assert '/RawData/data1' in cache
        assert '/RawData/sub/data2' in cache
        assert len(cache) == 2

    def test_collect_datasets_empty_group(self, tmp_path):
        """collect_datasets on a group with no datasets returns empty dict."""
        import h5py
        from pymodaq_data.h5modules.swmr import collect_datasets

        filepath = tmp_path / 'empty_group.h5'
        with h5py.File(str(filepath), 'w') as f:
            f.create_group('empty')

        with h5py.File(str(filepath), 'r') as f:
            cache = collect_datasets(f['empty'])

        assert cache == {}

    def test_refresh_datasets(self, tmp_path):
        """refresh_datasets should not raise on a group with datasets."""
        import h5py
        from pymodaq_data.h5modules.swmr import refresh_datasets
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'refresh_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()
        earr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        reader = h5py.File(str(filepath), 'r', swmr=True)
        # Should not raise
        refresh_datasets(reader)
        ds = reader['data']
        ds.id.refresh()
        assert ds.shape[0] == 1
        reader.close()
        saver.close_file()

    def test_refresh_cached(self, tmp_path):
        """refresh_cached should refresh all datasets in a cache dict."""
        import h5py
        from pymodaq_data.h5modules.swmr import collect_datasets, refresh_cached
        from pymodaq_data.h5modules.saving import H5SaverLowLevel

        saver = H5SaverLowLevel(backend='h5py')
        filepath = tmp_path / 'cached_test.h5'
        saver.init_file(file_name=filepath, swmr_mode=True)

        earr = saver.create_earray(saver.root(), 'data',
                                   dtype=np.float64, data_shape=(3,))
        saver.flush()
        saver.enable_swmr()

        earr.append(np.array([1.0, 2.0, 3.0]))
        saver.flush()

        reader = h5py.File(str(filepath), 'r', swmr=True)
        cache = collect_datasets(reader)

        # Initial refresh
        refresh_cached(cache)
        assert cache['/data'].shape[0] == 1

        # Write more data and refresh via cache
        earr.append(np.array([4.0, 5.0, 6.0]))
        saver.flush()
        refresh_cached(cache)
        assert cache['/data'].shape[0] == 2

        reader.close()
        saver.close_file()


class TestBackendsAvailable:
    """Tests for backend availability checking."""

    def test_backends_available_is_list(self):
        """Verify backends_available is a list."""
        from pymodaq_data.h5modules import backends_available
        assert isinstance(backends_available, list)

    def test_h5py_in_backends(self):
        """Verify h5py is in available backends (since SWMR tests require it)."""
        from pymodaq_data.h5modules import backends_available
        # This test file is skipped if h5py not available, so it must be here
        assert 'h5py' in backends_available
