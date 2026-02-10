from pymodaq_data.config import Config

config = Config("data")

class TestHdf5BackendConfig:
    """Tests for hdf5_backend config special handling."""
    def test_hdf5_backend_in_general(self):
        """Verify hdf5_backend is in general section of pymodaq_data config."""
        general_children = config('general')
        assert 'hdf5_backend' in general_children

    def test_hdf5_backend_is_list(self):
        """Verify hdf5_backend is stored as a list."""
        backends = config('general', 'hdf5_backend')
        assert isinstance(backends, list)
        assert len(backends) > 0

    def test_hdf5_backend_default_is_first(self):
        """Verify first element of hdf5_backend is the default (string)."""
        backends = config('general', 'hdf5_backend')
        assert isinstance(backends[0], str)
        assert backends[0] in ['tables', 'h5py', 'h5pyd']

    def test_hdf5_backend_contains_expected_values(self):
        """Verify hdf5_backend list contains expected backends."""
        backends = config('general', 'hdf5_backend')
        # Should contain at least tables and h5py
        assert 'tables' in backends or 'h5py' in backends

    def test_swmr_config_entries(self):
        """Verify SWMR-related config entries exist under data_saving."""
        data_saving_children = config.get_children('data_saving')
        assert 'swmr_enabled' in data_saving_children
        assert 'swmr_flush_interval' in data_saving_children

    def test_swmr_enabled_is_bool(self):
        """Verify swmr_enabled is a boolean."""
        swmr_enabled = config('data_saving', 'swmr_enabled')
        assert isinstance(swmr_enabled, bool)

    def test_swmr_flush_interval_is_int(self):
        """Verify swmr_flush_interval is an integer."""
        flush_interval = config('data_saving', 'swmr_flush_interval')
        assert isinstance(flush_interval, int)
