from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.parameter import ioxml

def test_empty_string():

    param_list = [{'name': 'strname', 'type': 'str', 'value': ''}]

    settings = Parameter.create(name='settings', type='group', children=param_list)
    xml_string = ioxml.parameter_to_xml_string(settings)
    settings_back = ioxml.XML_string_to_pobject(xml_string)
    #
    assert settings_back['strname'] == ''
    pass