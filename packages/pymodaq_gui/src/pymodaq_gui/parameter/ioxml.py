from __future__ import annotations

import copy

from typing import Union, Any
from pathlib import Path

import numpy as np

import importlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import OrderedDict

import numpy as np
from qtpy import QtGui
from qtpy.QtCore import QDateTime, QTime

from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.parameter import Parameter

from pyqtgraph.parametertree.Parameter import PARAM_TYPES, PARAM_NAMES


VALID_FOR_CONFIGURATION = 'valid_for_configuration'
logger = set_logger(get_module_name(__file__))

required_boolean_options = {'visible': True,
                            'removable': False,
                            'readonly': False,
                            'enabled': True,
                            'renamable': True,
                            'expanded': True,
                            'syncExpanded': True,
                            'showTop': False,
                            'strictNaming': False,
                            }

optional_boolean_options = {'show_pb': None,
                            VALID_FOR_CONFIGURATION: None,
                            'filetype': None,
                            }

optional_str_options = {'label': None,
                        'suffix': None,
                        }

optional_int_options = {}

optional_eval_options = {'addList': None,
                        'addText': None,
                        'detList': None,
                         'movelist': None,
                         }


def basic_serialization(param_val: Any, within_dict=False) -> str:
    if param_val is np.nan:
        text = f"np.nan"
    elif isinstance(param_val, str):
        if not within_dict:
            text = f"str({param_val!r})"  # Export repr() for handling non-printable characters
        else:
            text = param_val
    elif isinstance(param_val, int):
        text = f"int({param_val})"
    elif isinstance(param_val, float):
        text = f"float({param_val})"
    else:
        logger.exception(f"Serializing as xml the Parameter value: {param_val} as a simple string\n"
                         f"May not be reimportable...")
        text = str(param_val)
    return text


def walk_parameters_to_xml(parent_elt=None, param=None):
    """
        To convert a parameter object (and children) to xml data tree.

        =============== ================================ ==================================
        **Parameters**   **Type**                         **Description**

        *parent_elt*     XML element                      the root element
        *param*          instance of pyqtgraph parameter  Parameter object to be converted
        =============== ================================ ==================================

        Returns
        -------
        XML element : parent_elt
            XML element with subelements from Parameter object

        See Also
        --------
        add_text_to_elt, walk_parameters_to_xml, dict_from_param

    """

    if type(param) is None:
        raise TypeError('No valid param input')

    if parent_elt is None:
        opts = dict_from_param(param)
        parent_elt = ET.Element(param.name(), **opts)
        if 'value' in param.opts:
            add_text_to_elt(parent_elt, param)

    params_list = param.children()
    for param in params_list:
        opts = dict_from_param(param)
        elt = ET.Element(param.name(), **opts)
        if param.hasChildren():
            walk_parameters_to_xml(elt, param)
        if 'value' in param.opts:
            add_text_to_elt(elt, param)

        parent_elt.append(elt)

    return parent_elt


def add_text_to_elt(elt, param):
    """Add a text filed in a xml element corresponding to the parameter value

    Parameters
    ----------
    elt: XML elt
    param: Parameter

    See Also
    --------
    add_text_to_elt, walk_parameters_to_xml, dict_from_param
    """
    param_type = str(param.type())
    param_val = param.value()
    if 'bool' in param_type or 'led' in param_type:
        if param_val:
            text = '1'
        else:
            text = '0'
    elif param_type == 'itemselect':
        if param_val is not None:
            elt.set('all_items',
                    str(param_val['all_items']))  # use list(eval(val_str[1:-1])) to get back a list of strings
            text = str(param_val['selected'])  # use list(eval(val_str[1:-1])) to get back a list of strings
        else:
            text = str(None)
    elif param_type == 'color':
        text = str([param_val.red(), param_val.green(), param_val.blue(), param_val.alpha()])
    elif param_type == 'list':
        text = basic_serialization(param_val)
    elif param_type == 'int':
        if param_val is True:  # known bug is True should be clearly specified here
            val = 1
        else:
            val = param_val
        text = str(val)
    elif param_type == 'date_time':
        text = str(param_val.toMSecsSinceEpoch())
    elif param_type == 'date':
        text = str(QDateTime(param_val, QTime()).toMSecsSinceEpoch())
    elif param_type == 'progress':
        text = str(param_val)
    elif param_type == 'table_view':
        try:
            data = dict(classname=param_val.__class__.__name__,
                        module=param_val.__class__.__module__,
                        data=param_val.get_data_all(),
                        header=param_val.header)
            text = json.dumps(data)
        except Exception:
            text = ''
    else:
        text = str(param_val)
    elt.text = text


def dict_from_param(param: Parameter):
    """Get Parameter properties as a dictionary

    Parameters
    ----------
    param: Parameter

    Returns
    -------
    opts: dict

    See Also
    --------
    add_text_to_elt, walk_parameters_to_xml, dict_from_param
    """
    opts = dict([])

    param_opts = param.opts

    opts['type'] = str(param_opts.get('type'))
    title = param_opts.get('title', None)
    opts['title'] = title if title is not None else param.name()

    for option_str, default in required_boolean_options.items():
        opt_as_str = '1' if param_opts.get(option_str, default) else '0'
        opts[option_str] = opt_as_str

    for option_str in optional_boolean_options:
        if option_str in param_opts:
            opt_as_str = '1' if param_opts.get(option_str) else '0'
            opts[option_str] = opt_as_str

    for option_str in optional_str_options:
        if option_str in param_opts:
            opts[option_str] = param_opts.get(option_str)

    for option_int in optional_int_options:
        if option_int in param_opts:
            opts[option_int] = f'{param_opts.get(option_int)}'

    for eval_option in optional_eval_options:
        if eval_option in param_opts:
            opts[eval_option] = str(param_opts.get(eval_option))

    if 'limits' in param_opts:
        limits_opt = param_opts.get('limits')
        if isinstance(limits_opt, dict):
            limits = {}
            for key in limits_opt:
                limits[key] = basic_serialization(limits_opt[key], within_dict=True)
        else:
            limits = str(limits_opt)
        opts.update(dict(limits=limits))

    return opts


def elt_to_dict(el):
    """Convert xml element attributes to a dictionnary

    Parameters
    ----------
    el

    Returns
    -------

    """
    param = dict([])

    # name=el.tag, title=title, type=param_type, value=param_value, values=[param_value],
    #              visible=visible, removable=removable, readonly=readonly, show_pb=show_pb)
    param.update(dict(name=el.tag))
    param_type = el.get('type')
    param.update(dict(type=param_type))

    for attribute in el.attrib.keys():
        if attribute in required_boolean_options or attribute in optional_boolean_options:
            param[attribute] = bool(int(el.get(attribute)))

        elif attribute in optional_int_options:
            param[attribute] = int(el.get(attribute))

        elif attribute in optional_str_options:
            param[attribute] = str(el.get(attribute))

        elif attribute in optional_eval_options:
            try:
                param[attribute] = eval(el.get(attribute))
            except Exception as e:
                logger.warning(f'could not restore setting option {attribute}')

    if 'limits' in el.attrib.keys():
        try:
            limits = eval(el.get('limits'))
            if isinstance(limits, dict):
                for key, val in limits.items():
                    try:
                        limits[key] = eval(val)
                    except NameError:
                        limits[key] = val
            param.update(dict(limits=limits))
        except Exception as e:
            logger.exception(e)

    return param


def parameter_to_xml_string(param):
    """ Convert  a Parameter to a XML string.

    Parameters
    ----------
    param: Parameter

    Returns
    -------
    str: XMl string

    See Also
    --------
    add_text_to_elt, walk_parameters_to_xml, dict_from_param

    Examples
    --------
    >>> from pyqtgraph.parametertree import Parameter
    >>>    #Create an instance of Parameter
    >>> settings=Parameter(name='settings')
    >>> converted_xml=parameter_to_xml_string(settings)
    >>>    # The converted Parameter
    >>> print(converted_xml)
    b'<settings title="settings" type="None" />'
    """
    xml_elt = walk_parameters_to_xml(param=param)
    return ET.tostring(xml_elt)


def parameter_to_xml_file(param, filename: Union[str, Path], overwrite=True):
    """
        Convert the given parameter to XML element and update the given XML file.

        =============== ================================= ================================
        **Parameters**    **Type**                          **Description**
        *param*           instance of pyqtgraph parameter   the parameter to be added
        *filename*        string                            the filename of the XML file
        *overwrite*       boolean                           raise Error is False and file exists
        =============== ================================= ================================

        See Also
        --------
        walk_parameters_to_xml

        Examples
        --------
    """
    if not isinstance(filename, Path):
        filename = Path(filename)
    parent = filename.parent
    filename = filename.stem
    fname = parent.joinpath(filename + ".xml")  # forcing the right extension on the filename
    xml_elt = walk_parameters_to_xml(param=param)
    tree = ET.ElementTree(xml_elt)
    if not overwrite and fname.exists() and fname.is_file():
        raise FileExistsError
    tree.write(str(fname))


def walk_xml_to_parameter(params=[], XML_elt=None):
    """ To convert an XML element (and children) to list of dict enabling creation of parameter object.

        =============== ================== =======================================
        **Parameters**   **Type**            **Description**

        *params*         dictionnary list    the list to create parameter object
        *XML_elt*        XML object          the XML object to be converted
        =============== ================== =======================================

        Returns
        -------
        params : dictionnary list
            list of dict to create parameter object

        Examples
        -------
        >>> from pyqtgraph.parametertree import Parameter, ParameterItem
        >>> import xml.etree.ElementTree as ET
        >>> tree = ET.parse('text_bis.xml')
        >>> root = tree.getroot()
        >>> params=walk_xml_to_parameter(XML_elt=root)
        >>> settings_xml=Parameter.create(name='Settings XML', type='group', children=params)
        >>> settings=Parameter.create(name='Settings', type='group', children=params)

        See Also
        --------
        walk_parameters_to_xml
    """
    try:
        if type(XML_elt) is not ET.Element:
            raise TypeError('not valid XML element')

        if len(XML_elt) == 0:
            param_dict = set_dict_from_el(XML_elt)
            params.append(param_dict)

        for el in XML_elt:
            param_dict = set_dict_from_el(el)           
            if param_dict['type'] not in PARAM_TYPES:
                param_dict['type'] = 'group'  # in case the custom group has been defined somewhere but not
                # registered again in this session
            if len(el) == 0:
                children = []
            else:
                subparams = []
                children = walk_xml_to_parameter(subparams, el)
            param_dict['children'] = children            
            params.append(param_dict)

    except Exception as e:  # to be able to debug when there's an issue
        raise e
    return params


def set_dict_from_el(el):
    """Convert an element into a dict
    ----------
    el: xml element
    param_dict: dictionnary from which the parameter will be constructed
    """
    param_dict = elt_to_dict(el)
    set_txt_from_elt(el, param_dict)  
    return param_dict          

def set_txt_from_elt(el, param_dict):
    """
    get the value of the parameter from the text value of the xml element
    Parameters
    ----------
    el: xml element
    param_dict: dictionnary from which the parameter will be constructed

    """
    val_text = el.text
    param_type = param_dict['type']
    # param_type = el.get('type') # Redundancy (param_dict already has this attribute)
    if val_text is not None:
        if param_type == 'float':
            param_value = float(val_text)
        elif param_type == 'int':
            param_value = int(float(val_text))
        elif param_type == 'slide':
            param_value = float(val_text)
        elif param_type == 'itemselect':
            if val_text == 'None':
                param_value = dict(all_items=[], selected=[])
            else:
                param_value = dict(all_items=eval(el.get('all_items', val_text)), selected=eval(val_text))
        elif 'bool' in param_type or 'led' in param_type:  # covers 'bool' 'bool_push',  'led' and 'led_push'types
            param_value = bool(int(val_text))
        elif param_type == 'date_time':
            param_value = QDateTime.fromMSecsSinceEpoch(int(val_text))
        elif param_type == 'date':
            param_value = QDateTime.fromMSecsSinceEpoch(int(val_text)).date()
        elif param_type == 'table':
            param_value = eval(val_text)
        elif param_type == 'color':
            param_value = QtGui.QColor(*eval(val_text))
        elif param_type == 'list':
            try:
                param_value = eval(val_text)
            except Exception:
                param_value = val_text  # for back compatibility
        elif param_type == 'progress':
            param_value = int(val_text)
        elif param_type == 'table_view':
            data_dict = json.loads(val_text)
            mod = importlib.import_module(data_dict['module'])
            _cls = getattr(mod, data_dict['classname'])
            param_value = _cls(data_dict['data'], header=data_dict['header'])
        elif param_type == 'action':
            if val_text == 'None':
                param_value = None
            else:
                param_value = eval(val_text)
        else:
            param_value = val_text
        param_dict.update(dict(value=param_value))
    else:
        if param_type == 'str':
            param_dict.update(dict(value=''))


def XML_file_to_parameter(file_name: Union[str, Path]) -> list:
    """ Convert a xml file into pyqtgraph parameter object.

    Returns
    -------
    params : list of dictionary
        a list of dictionary defining a Parameter object and its children

    See Also
    --------
    walk_parameters_to_xml

    Examples
    --------
    """
    tree = ET.parse(str(file_name))

    root = tree.getroot()
    params = walk_xml_to_parameter(params=[], XML_elt=root)
    return params

def xml_file_to_parameter_dict(file_name: Union[str, Path]) -> dict:
    tree = ET.parse(str(file_name))
    root = tree.getroot()
    param_dict = set_dict_from_el(root)
    if len(root) > 0:
        param_dict['children'] = walk_xml_to_parameter(params=[], XML_elt=root)

    return param_dict


def XML_string_to_parameter(xml_string):
    """ Convert a xml string into a list of dict for initialize pyqtgraph parameter object.
    """
    root = ET.fromstring(xml_string)
    params = walk_xml_to_parameter(params=[], XML_elt=root)
    return params


def xml_string_to_parameter_dict(xml_string) -> dict:
    """
        Convert a xml string into a dict to initialize pyqtgraph parameter object.
    """
    root = ET.fromstring(xml_string)
    tree = ET.ElementTree(root)

    param_dict = set_dict_from_el(root)
    if len(root) > 0:
        param_dict['children'] = walk_xml_to_parameter(params=[], XML_elt=root)

    return param_dict

def xml_string_to_parameter(xml_string) -> Parameter:
    return Parameter.create(**xml_string_to_parameter_dict(xml_string))


def XML_string_to_pobject(xml_string) -> Parameter:
    """
    return a Parameter object from its deserialized version from a XML string

    Deprecated as not symetric with parameter_to_xml_string

    Parameters
    ----------
    xml_string: (str) string representation of a Parameter Object

    """
    return Parameter.create(name='settings', type='group',
                            children=XML_string_to_parameter(xml_string))



