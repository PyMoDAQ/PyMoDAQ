from pymodaq.utils.caller import CallerInfo


class TestCallerInfo:
    def test_defaults(self):
        caller = CallerInfo()
        assert caller.h5_file_path is None
        assert caller.node_name is None
        assert caller.origin is None

    def test_explicit_values(self):
        caller = CallerInfo(h5_file_path='/tmp/data.h5', node_name='Scan001',
                            origin='DAQScan')
        assert caller.h5_file_path == '/tmp/data.h5'
        assert caller.node_name == 'Scan001'
        assert caller.origin == 'DAQScan'

    def test_equality(self):
        assert CallerInfo(h5_file_path='/a.h5') == CallerInfo(h5_file_path='/a.h5')
        assert CallerInfo(h5_file_path='/a.h5') != CallerInfo(h5_file_path='/b.h5')
