from pymodaq_data.config import Config

config = Config("data")

class TestHdf5BackendConfig:
    """Tests for hdf5_backend config special handling."""
    def test_backend_is_in_data_saving(self):
        """Verify backend list lives directly under data_saving."""
        data_saving_children = config('data_saving')
        assert 'backend' in data_saving_children

    def test_hdf5_backend_is_list(self):
        """Verify backend is stored as a list."""
        backends = config('data_saving', 'backend')
        assert isinstance(backends, list)
        assert len(backends) > 0

    def test_hdf5_backend_default_is_first(self):
        """Verify first element of backend is a valid backend string."""
        backends = config('data_saving', 'backend')
        assert isinstance(backends[0], str)
        assert backends[0] in ['tables', 'h5py', 'h5pyd']

    def test_hdf5_backend_contains_expected_values(self):
        """Verify backend list contains expected backends."""
        backends = config('data_saving', 'backend')
        assert 'tables' in backends or 'h5py' in backends

    def test_swmr_config_entries(self):
        """Verify SWMR-related config entries exist under data_saving.swmr."""
        swmr_children = config('data_saving', 'swmr')
        assert 'enabled' in swmr_children
        assert 'flush_interval' in swmr_children

    def test_swmr_enabled_is_bool(self):
        """Verify swmr enabled is a boolean."""
        swmr_enabled = config('data_saving', 'swmr', 'enabled')
        assert isinstance(swmr_enabled, bool)

    def test_swmr_flush_interval_is_int(self):
        """Verify swmr flush_interval is an integer."""
        flush_interval = config('data_saving', 'swmr', 'flush_interval')
        assert isinstance(flush_interval, int)
