import pytest
from pymodaq.daq_utils.config import load_config, Config


class TestGeneral:
    def test_load_config(self):
        config = load_config()
        config = Config()
        config('style', 'darkstyle')
        assert config('style', 'darkstyle') == config['style']['darkstyle']