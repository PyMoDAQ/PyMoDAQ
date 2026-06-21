from pymodaq.utils.caller import CallerBase


class TestCallerBase:
    def test_defaults(self):
        caller = CallerBase()
        assert caller.h5_file_path is None
        assert caller.node_name is None
        assert caller.origin is None

    def test_explicit_values(self):
        caller = CallerBase(h5_file_path='/tmp/data.h5', node_name='Scan001',
                            origin='DAQScan')
        assert caller.h5_file_path == '/tmp/data.h5'
        assert caller.node_name == 'Scan001'
        assert caller.origin == 'DAQScan'

    def test_equality(self):
        assert CallerBase(h5_file_path='/a.h5') == CallerBase(h5_file_path='/a.h5')
        assert CallerBase(h5_file_path='/a.h5') != CallerBase(h5_file_path='/b.h5')
