from pymodaq.extensions.scan.daq_scan import DAQScanCaller
from pymodaq.utils.caller import CallerBase


class TestDAQScanCaller:
    def test_is_a_caller_base(self):
        assert isinstance(DAQScanCaller(), CallerBase)

    def test_defaults(self):
        caller = DAQScanCaller()
        assert caller.origin == 'DAQScan'
        assert caller.ind_scan == 0
        assert caller.ind_average == 0
        assert caller.h5_file_path is None
        assert caller.node_name is None

    def test_explicit_values(self):
        caller = DAQScanCaller(ind_scan=3, ind_average=1, node_name='Scan001',
                               h5_file_path='/tmp/data.h5')
        assert caller.ind_scan == 3
        assert caller.ind_average == 1
        assert caller.node_name == 'Scan001'
        assert caller.h5_file_path == '/tmp/data.h5'
        assert caller.origin == 'DAQScan'
