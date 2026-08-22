from pymodaq.utils.caller import CallerInfo


class TestCallerInfo:
    def test_defaults(self):
        caller = CallerInfo()
        assert caller.h5_file_path is None
        assert caller.node_name is None
        assert caller.caller_name is None
        assert caller.caller_type == 'CallerInfo'

    def test_explicit_values(self):
        caller = CallerInfo(h5_file_path='/tmp/data.h5', node_name='Scan001',
                            caller_name='DAQScan')
        assert caller.h5_file_path == '/tmp/data.h5'
        assert caller.node_name == 'Scan001'
        assert caller.caller_name == 'DAQScan'
        assert caller.caller_type == 'CallerInfo'

    def test_caller_type_can_be_overridden(self):
        caller = CallerInfo(caller_type='CustomCaller')
        assert caller.caller_type == 'CustomCaller'

    def test_equality(self):
        assert CallerInfo(h5_file_path='/a.h5') == CallerInfo(h5_file_path='/a.h5')
        assert CallerInfo(h5_file_path='/a.h5') != CallerInfo(h5_file_path='/b.h5')
