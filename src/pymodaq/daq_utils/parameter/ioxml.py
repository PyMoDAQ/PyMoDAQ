import importlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import OrderedDict
from PyQt5 import QtGui
from PyQt5.QtCore import QDateTime


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
        param_type = str(param.type())
        if 'group' not in param_type:  # covers 'group', custom 'groupmove', 'groupai' ...
            add_text_to_elt(parent_elt, param)

    params_list = param.children()
    for param in params_list:

        opts = dict_from_param(param)
        elt = ET.Element(param.name(), **opts)
        param_type = str(param.type())
        if 'group' not in param_type:  # covers 'group', custom 'groupmove'...
            add_text_to_elt(elt, param)
        else:
            walk_parameters_to_xml(elt, param)

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
    if 'bool' in param_type or 'led' in param_type:
        if param.value():
            text = '1'
        else:
            text = '0'
    elif param_type == 'itemselect':
        if param.value() is not None:
            elt.set('all_items',
                    str(param.value()['all_items']))  # use list(eval(val_str[1:-1])) to get back a list of strings
            text = str(param.value()['selected'])  # use list(eval(val_str[1:-1])) to get back a list of strings
        else:
            text = str(None)
    elif param_type == 'color':
        text = str([param.value().red(), param.value().green(), param.value().blue(), param.value().alpha()])
    elif param_type == 'list':
        if isinstance(param.value(), str):
            text = "str('{}')".format(param.value())
        elif isinstance(param.value(), int):
            text = 'int({})'.format(param.value())
        elif isinstance(param.value(), float):
            text = 'float({})'.format(param.value())
        else:
            str(param.value())
    elif param_type == 'int':
        if param.value() is True:  # known bug is True should be clearly specified here
            val = 1
        else:
            val = param.value()
        text = str(val)
    elif param_type == 'date_time':
        text = str(param.value().toSecsSinceEpoch())
    elif param_type == 'date':
        text = str(QDateTime(param.value()).toSecsSinceEpoch())
    elif param_type == 'table_view':
        try:
            data = dict(classname=param.value().__class__.__name__,
                        module=param.value().__class__.__module__,
                        data=param.value().get_data_all(),
                        header=param.value().header)
            text = json.dumps(data)
        except Exception:
            text = ''
    else:
        text = str(param.value())
    elt.text = text


def dict_from_param(param):
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
    param_type = str(param.type())
    opts.update(dict(type=param_type))
    title = param.opts['title']
    if title is None:
        title = param.name()
    opts.update(dict(title=title))

    visible = '1'
    if 'visible' in param.opts:
        if param.opts['visible']:
            visible = '1'
        else:
            visible = '0'

    opts.update(dict(visible=visible))

    removable = '1'
    if 'removable' in param.opts:
        if param.opts['removable']:
            removable = '1'
        else:
            removable = '0'
    opts.update(dict(removable=removable))

    readonly = '0'
    if 'readonly' in param.opts:
        if param.opts['readonly']:
            readonly = '1'
        else:
            readonly = '0'
    opts.update(dict(readonly=readonly))

    if 'values' in param.opts:
        values = str(param.opts['values'])
        opts.update(dict(values=values))

    if 'limits' in param.opts:
        limits = str(param.opts['limits'])
        opts.update(dict(limits=limits))
        opts.update(dict(values=limits))

    if 'addList' in param.opts:
        addList = str(param.opts['addList'])
        opts.update(dict(addList=addList))

    if 'detlist' in param.opts:
        detlist = str(param.opts['detlist'])
        opts.update(dict(detlist=detlist))

    if 'movelist' in param.opts:
        movelist = str(param.opts['movelist'])
        opts.update(dict(movelist=movelist))

    if 'show_pb' in param.opts:
        if param.opts['show_pb']:
            show_pb = '1'
        else:
            show_pb = '0'
        opts.update(dict(show_pb=show_pb))

    if 'filetype' in param.opts:
        if param.opts['filetype']:
            filetype = '1'
        else:
            filetype = '0'
        opts.update(dict(filetype=filetype))

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

    title = el.get('title')
    if title == 'None':
        title = el.tag
    param.update(dict(title=title))

    if 'visible' not in el.attrib.keys():
        visible = True
    else:
        visible = bool(int(el.get('visible')))
    param.update(dict(visible=visible))

    if 'removable' not in el.attrib.keys():
        removable = False
    else:
        removable = bool(int(el.get('removable')))
    param.update(dict(removable=removable))

    if 'readonly' not in el.attrib.keys():
        readonly = False
    else:
        readonly = bool(int(el.get('readonly')))
    param.update(dict(readonly=readonly))

    if 'show_pb' in el.attrib.keys():
        show_pb = bool(int(el.get('show_pb')))
    else:
        show_pb = False
    param.update(dict(show_pb=show_pb))

    if 'filetype' in el.attrib.keys():
        filetype = bool(int(el.get('filetype')))
        param.update(dict(filetype=filetype))

    if 'detlist' in el.attrib.keys():
        detlist = eval(el.get('detlist'))
        param.update(dict(detlist=detlist))

    if 'movelist' in el.attrib.keys():
        movelist = eval(el.get('movelist'))
        param.update(dict(movelist=movelist))

    if 'addList' in el.attrib.keys():
        addList = eval(el.get('addList'))
        param.update(dict(addList=addList))

    if 'values' in el.attrib.keys():
        values = list(eval(el.get('values')))  # make sure the evaluated values are returned as list (in case another
        # iterator type has been used)
        param.update(dict(values=values))

    if 'limits' in el.attrib.keys():
        limits = eval(el.get('limits'))
        param.update(dict(limits=limits))

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


def parameter_to_xml_file(param, filename):
    """
        Convert the given parameter to XML element and update the given XML file.

        =============== ================================= ================================
        **Parameters**    **Type**                          **Description**
        *param*           instance of pyqtgraph parameter   the parameter to be added
        *filename*        string                            the filename of the XML file
        =============== ================================= ================================

        See Also
        --------
        walk_parameters_to_xml

        Examples
        --------
    """
    fname = Path(filename)
    parent = fname.parent
    filename = fname.stem
    fname = parent.joinpath(filename + ".xml")  # forcing the right extension on the filename
    xml_elt = walk_parameters_to_xml(param=param)
    tree = ET.ElementTree(xml_elt)
    tree.write(str(fname))


def walk_xml_to_parameter(params=[], XML_elt=None):
    """ To convert an XML element (and children) to dict enabling creation of parameter object.

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

        elts = XML_elt.getchildren()
        if len(elts) == 0:
            param_dict = elt_to_dict(XML_elt)
            param_type = XML_elt.get('type')

            if 'group' not in param_type:  # covers 'group', custom 'groupmove'...
                set_txt_from_elt(XML_elt, param_dict)
            params.append(param_dict)

        for el in elts:
            param_dict = elt_to_dict(el)
            param_type = el.get('type')

            if 'group' not in param_type:  # covers 'group', custom 'groupmove'...
                set_txt_from_elt(el, param_dict)
            else:
                subparams = []
                param_dict.update(dict(children=walk_xml_to_parameter(subparams, el)))

                param_dict.update(dict(name=el.tag))

            params.append(param_dict)
    except Exception as e:  # to be able to debug when there's an issue
        raise e
    return params


def set_txt_from_elt(el, param_dict):
    """
    get the value of the parameter from the text value of the xml element
    Parameters
    ----------
    el: xml element
    param_dict: dictionnary from which the parameter will be constructed

    """
    val_text = el.text
    param_type = el.get('type')
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
        elif 'bool' in param_type or 'led' in param_type: # covers 'bool' 'bool_push',  'led' and 'led_push'types
            param_value = bool(int(val_text))
        elif param_type == 'date_time':
            param_value = QDateTime.fromSecsSinceEpoch(int(val_text))
        elif param_type == 'date':
            param_value = QDateTime.fromSecsSinceEpoch(int(val_text)).date()
        elif param_type == 'table':
            param_value = eval(val_text)
        elif param_type == 'color':
            param_value = QtGui.QColor(*eval(val_text))
        elif param_type == 'list':
            try:
                param_value = eval(val_text)
            except Exception:
                param_value = val_text  # for back compatibility
        elif param_type == 'table_view':
            data_dict = json.loads(val_text)
            mod = importlib.import_module(data_dict['module'])
            _cls = getattr(mod, data_dict['classname'])
            param_value = _cls(data_dict['data'], header=data_dict['header'])
        else:
            param_value = val_text
        param_dict.update(dict(value=param_value))


def XML_file_to_parameter(file_name):
    """
        Convert a xml file into pyqtgraph parameter object.

        =============== =========== ================================================
        **Parameters**   **Type**    **Description**

        *file_name*     string      the file name of the XML file to be converted
        =============== =========== ================================================

        Returns
        -------
        params : dictionnary list
            a parameter list of dictionnary to init a parameter

        See Also
        --------
        walk_parameters_to_xml

        Examples
        --------
    """
    tree = ET.parse(file_name)

    root = tree.getroot()
    params = walk_xml_to_parameter(params=[], XML_elt=root)
    return params


def XML_string_to_parameter(xml_string):
    """
        Convert a xml string into pyqtgraph parameter object.

        =============== =========== ================================
        **Parameters**   **Type**    **Description**

        xml_string       string      the xml string to be converted
        =============== =========== ================================

        Returns
        -------
        params: a parameter list of dict to init a parameter

        See Also
        --------
        walk_parameters_to_xml

        Examples
        --------
    """
    root = ET.fromstring(xml_string)
    tree = ET.ElementTree(root)

    # tree.write('test.xml')
    params = walk_xml_to_parameter(params=[], XML_elt=root)

    return params
