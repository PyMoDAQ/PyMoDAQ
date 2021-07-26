from pymodaq.daq_utils.parameter import utils

def test_is_name_in_dict():
    dict = {'name': 'test', 'parameter': 'gaussian', 'value': 5}
    assert utils.is_name_in_dict(dict, 'test')
    assert not utils.is_name_in_dict(dict, 'error')
