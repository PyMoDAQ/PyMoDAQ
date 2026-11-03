"""Settings stored in xml (files, hdf5 attributes, messages) must never run code when read back.

The payloads below are inert: they only try to compute something that cannot be the result of reading
plain data (the version of python).
"""
import json
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml
from pymodaq_utils.utils import UnsafeExpressionError

PAYLOAD = "[__import__('sys').version]"


def craft_xml(param_type: str, text: str = '', **attributes) -> str:
    """xml of a single parameter, as a foreign file could contain it"""
    elt = ET.Element('p', type=param_type, title='p', **attributes)
    elt.text = text
    return ET.tostring(elt, encoding='unicode')


@pytest.mark.parametrize('param_type, text, attributes', [
    ('table', PAYLOAD, {}),
    ('color', PAYLOAD, {}),
    ('itemselect', PAYLOAD, {}),
    ('itemselect', '[]', {'all_items': PAYLOAD}),
    ('action', PAYLOAD, {}),
    ('str', 'a text', {'addList': PAYLOAD}),
    ('str', 'a text', {'detlist': PAYLOAD}),
    ('str', 'a text', {'movelist': PAYLOAD}),
])
def test_unsafe_content_is_refused(param_type, text, attributes):
    with pytest.raises(UnsafeExpressionError):
        ioxml.xml_string_to_parameter_dict(craft_xml(param_type, text, **attributes))


def test_unsafe_list_value_is_kept_as_text():
    param_dict = ioxml.xml_string_to_parameter_dict(craft_xml('list', PAYLOAD))

    assert param_dict['value'] == PAYLOAD


def test_unsafe_limits_are_ignored():
    param_dict = ioxml.xml_string_to_parameter_dict(craft_xml('list', 'a', limits=PAYLOAD))

    assert 'limits' not in param_dict


def test_unsafe_table_view_class_is_refused():
    data = json.dumps(dict(module='builtins', classname='dict', data={'a': 1}, header=['b']))

    with pytest.raises(UnsafeExpressionError):
        ioxml.xml_string_to_parameter_dict(craft_xml('table_view', data))


def test_table_view_round_trip(qtbot):
    from pymodaq_gui.utils.widgets.table import TableModel
    model = TableModel([[1, 2.5], [3, 4.5]], header=['a', 'b'])

    param_dict = round_trip(type='table_view', value=model, title='p')

    assert isinstance(param_dict['value'], TableModel)
    assert param_dict['value'].get_data_all() == [[1, 2.5], [3, 4.5]]
    assert param_dict['value'].header == ['a', 'b']


def round_trip(**opts) -> dict:
    param = Parameter.create(name='p', **opts)
    return ioxml.xml_string_to_parameter_dict(ioxml.parameter_to_xml_string(param))


def test_list_with_list_limits_round_trip():
    param_dict = round_trip(type='list', limits=['a', 'b', 'c'], value='b')

    assert param_dict['limits'] == ['a', 'b', 'c']
    assert param_dict['value'] == 'b'


def test_list_with_dict_limits_round_trip():
    limits = {'a_nan': np.nan, 'an_int': 21, 'a_float': 1.5, 'a_str': 'astr'}
    param_dict = round_trip(type='list', limits=limits, value=21)

    assert param_dict['value'] == 21
    assert param_dict['limits']['an_int'] == 21
    assert param_dict['limits']['a_float'] == 1.5
    assert param_dict['limits']['a_str'] == 'astr'
    assert param_dict['limits']['a_nan'] is np.nan or np.isnan(param_dict['limits']['a_nan'])


def test_itemselect_round_trip():
    value = dict(all_items=['a', 'b', 'c'], selected=['b'])
    assert round_trip(type='itemselect', value=value)['value'] == value


def test_table_round_trip():
    value = [[1, 'a'], [2.5, 'b']]
    assert round_trip(type='table', value=value)['value'] == value


def test_table_of_ordered_dict_round_trip():
    from collections import OrderedDict
    value = OrderedDict([('key1', 'data1'), ('key2', 24.0)])
    result = round_trip(type='table', value=value)['value']

    assert result == value
    assert isinstance(result, OrderedDict)


def test_optional_options_round_trip():
    param_dict = round_trip(type='str', value='a', addList=['x', 'y'], movelist=['z'])

    assert param_dict['addList'] == ['x', 'y']
    assert param_dict['movelist'] == ['z']
