from pymodaq_utils.help import get_help_text

from pymodaq.extensions.scan.daq_scan import DAQScan


def test_daq_scan_help():
    text = get_help_text(DAQScan)
    assert text is not None
    assert text.startswith('# DAQ_Scan')
    assert '<!-- end of intro -->' in text
