from __future__ import annotations
from typing import List, Tuple, Union
import numpy as np
from collections import OrderedDict
from pymodaq_utils.utils import find_keys_from_val
from pymodaq_utils.serialize.factory import SerializableFactory, SerializableBase
from pymodaq_gui.parameter import ioxml

from pymodaq_gui.parameter import Parameter

ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
class ParameterWithPath(SerializableBase):
    """ holds together a Parameter object and its full path

    To be used when communicating between TCPIP to reconstruct properly the Parameter

    Attributes
    ----------
    parameter: Parameter
        a Parameter object
    path: full path of the parameter, if None it is constructed from the parameter parents
    """
    def __init__(self, parameter: Parameter, path: List[str] = None):
        super().__init__()
        self._parameter = parameter
        if path is None:
            path = get_param_path(parameter)
        self._path = path

    def __repr__(self):
        return f'Parameter {self.parameter.name()} with path {self.path}'

    def __eq__(self, other: 'ParameterWithPath'):
        return (self.path == other.path and
                compareParameters(self.parameter, other.parameter))

    @property
    def parameter(self) -> Parameter:
        return self._parameter

    @property
    def path(self) -> List[str]:
        return self._path

    def value(self):
        return self.parameter.value()

    @staticmethod
    def serialize(param: 'ParameterWithPath') -> bytes:
        """ """
        bytes_string = b''
        path = param.path
        param_as_xml = ioxml.parameter_to_xml_string(param.parameter)
        bytes_string += ser_factory.get_apply_serializer(path)
        bytes_string += ser_factory.get_apply_serializer(param_as_xml)
        return bytes_string

    @classmethod
    def deserialize(cls,
                    bytes_str: bytes) -> Union[ParameterWithPath,
                                               Tuple[ParameterWithPath, bytes]]:
        """Convert bytes into a ParameterWithPath object

        Returns
        -------
        ParameterWithPath: the decoded object
        bytes: the remaining bytes string if any
        """
        path, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        param_as_xml, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        param_dict = ioxml.xml_string_to_parameter_dict(param_as_xml)
        param_obj = Parameter.create(**param_dict)
        return ParameterWithPath(param_obj, path), remaining_bytes


def get_widget_from_tree(parameter_tree, widget_instance):
    widgets = []
    for item in parameter_tree.listAllItems():
        if hasattr(item, 'widget'):
            if item.widget.__class__.__name__ == widget_instance.__name__:
                widgets.append(item.widget)
    return widgets


def get_param_path(param: Parameter) -> List[str]:
    """ Get the parameter path from its highest parent down to the given parameter including its
    identifier (name)

    Parameters
    ----------
    param: Parameter
        The parameter object

    Returns
    -------
    List[str]: the path as a list of parameter identifiers
    """
    path = [param.name()]
    while param.parent() is not None:
        path.append(param.parent().name())
        param = param.parent()
    return path[::-1]


def getOpts(param:Parameter,) -> OrderedDict:
    """Return an OrderedDict with tree structures of all opts for all children of this parameter

        Parameters
        ----------
        param: Parameter

        Returns
        -------
        OrderedDict
    """
    vals = OrderedDict()
    for ch in param:
        vals[ch.name()] = (ch.opts, getOpts(ch))
    return vals

def getStruct(param:Parameter,) -> OrderedDict:
    """Return an OrderedDict with tree structures of all children of this parameter

        Parameters
        ----------
        param: Parameter

        Returns
        -------
        OrderedDict    
    """
    vals = OrderedDict()
    for ch in param:      
        vals[ch.name()] = (None, getStruct(ch))
    return vals 

def getValues(param:Parameter,) -> OrderedDict:
    """Return an OrderedDict with tree structures of all values for all children of this parameter

        Parameters
        ----------
        param: Parameter

        Returns
        -------
        OrderedDict    
    """    
    return param.getValues()


def compareParameters(param1:Parameter, param2:Parameter, with_self: bool = True)-> bool:
    """Compare the structure and the opts of two parameters with their children,
        return True if structure and all opts are identical.
        If with_self is False, only the children opts are compared.

        Parameters
        ----------
        param1: Parameter
        param2: Parameter
        with_self: bool

        Returns
        -------
        Bool
    """
    is_same = getOpts(param1) == getOpts(param2)
    if with_self:
        is_same = is_same and (param1.opts == param2.opts)
    return is_same
    
def compareStructureParameter(param1:Parameter, param2: Parameter,)-> bool:
    """Compare the structure of two parameters with their children, return True if structure is identical

        Parameters
        ----------
        param1: Parameter
        param2: Parameter   
        
        Returns
        -------
        Bool    
    """    
    return getStruct(param1) == getStruct(param2)


def compareValuesParameter(param1:Parameter, param2: Parameter, with_self: bool = True)-> bool:
    """Compare the structure and the values of two parameters with their children, return True if structures and values
        are identical.
        If with_self is False, only the children opts are compared.

        Parameters
        ----------
        param1: Parameter
        param2: Parameter
        with_self: bool

        Returns
        -------
        Bool
    """
    is_same = getValues(param1) == getValues(param2)
    if with_self:        
        is_same = is_same and (param1.value == param2.value)        
    return is_same


def iter_children(param, childlist: list = [], filter_type=(), filter_name=(), select_filter=False)-> list:
    """
    Get a list of parameters' name under a given Parameter (see iter_children_params)

    Returns
    -------
    list
        The list of the children name from the given node.       
    """
    return iter_children_params(param, childlist=childlist, output_type='name',
                                filter_type=(), filter_name=(), select_filter=False)


def iter_children_params(param, childlist: list = [], output_type=None,
                         filter_type=(), filter_name=(), select_filter=False)-> list:
    """
    Get a list of parameters under a given Parameter.

    Parameters
    ----------
    param : Parameter (pyqtgraph)
        the root node to be coursed
    childlist: list
        the child/output list
    output_type: str
        the attribute of parameter that will be added to the output list
    filter_type: list
        filter children sharing those types
    filter_name: list
        filter children sharing those names
    select_filter: bool
        if True, add filtered parameters to output list. 
        if False (default), add non-filtered parameter to output list.

    Returns
    -------
    list
        The list of the children from the given node.    
    """
    for child in param.children():
        # XNOR Gate        
        is_filtered = child.type() in filter_type or child.name() in filter_name
        add_selected_child = select_filter and is_filtered
        add_notselected_child = not select_filter and not is_filtered
        if add_selected_child or add_notselected_child:            
            if output_type is not None:            
                try:
                    output = getattr(child,output_type)()
                except Exception as e:
                    print(str(e))
            else:                    
                output = child
            childlist.append(output)
        if child.hasChildren():
             childlist.extend(iter_children_params(child, [], output_type, filter_type, filter_name, select_filter))
    return childlist


def get_param_from_name(parent: Parameter, name) -> Parameter:
    """Get Parameter under parent whose name is name

    Parameters
    ----------
    parent: Parameter
    name: str

    Returns
    -------
    Parameter
    """
    for child in parent.children():
        if child.name() == name:
            return child
        if child.hasChildren():
            ch = get_param_from_name(child, name)
            if ch is not None:
                return ch


def is_name_in_dict(dict_tmp, name):
    if 'name' in dict_tmp:
        if dict_tmp['name'] == name:
            return True
    return False


def get_param_dict_from_name(parent_list, name, pop=False):
    """Get dict under parent whose name is name. The parent_list structure is the one used to init a Parameter object

    Parameters
    ----------
    parent_list: (list of dicts) as defined to init Parameter object
    name: (str) value to find for the key: name
    pop: (bool) if True remove the matched dict from parent

    Returns
    -------
    dict the matched dict
    """
    for index, parent_dict in enumerate(parent_list):
        if is_name_in_dict(parent_dict, name):
            if pop:
                return parent_list.pop(index)
            else:
                return parent_dict

        elif 'children' in parent_dict:
            ch = get_param_dict_from_name(parent_dict['children'], name, pop)
            if ch is not None:
                return ch


def set_param_from_param(param_old, param_new):
    """
        Walk through parameters children and set values using new parameter values.
    """
    for child_old in param_old.children():
        # try:
        path = param_old.childPath(child_old)
        child_new = param_new.child(*path)
        param_type = child_old.type()

        if 'group' not in param_type:  # covers 'group', custom 'groupmove'...
            # try:
            if 'list' in param_type:  # check if the value is in the limits of the old params
                # (limits are usually set at initialization) but carefull as such paramater limits can be a list or a
                # dict object
                if isinstance(child_old.opts['limits'], list):
                    if child_new.value() not in child_old.opts['limits']:
                        new_limits = child_old.opts['limits'].copy()
                        new_limits.append(child_new.value())
                        child_old.setLimits(new_limits)
                        
                elif isinstance(child_old.opts['limits'], dict):
                    if child_new.value() not in child_old.opts['limits'].values():
                        child_new_key = find_keys_from_val(child_new.opts['limits'], child_new.value())[0]
                        new_limits = child_old.opts['limits'].copy()
                        new_limits.update({child_new_key: child_new.value()})
                        child_old.setLimits(new_limits)

                child_old.setValue(child_new.value())
            elif 'str' in param_type or 'browsepath' in param_type or 'text' in param_type:
                if child_new.value() != "":  # to make sure one doesnt overwrite something
                    child_old.setValue(child_new.value())
            else:
                child_old.setValue(child_new.value())
            # except Exception as e:
            #    print(str(e))
        else:
            set_param_from_param(child_old, child_new)
        # except Exception as e:
        #    print(str(e))

def filter_parameter_tree(param:Parameter, search_text:str = "") -> bool:
    """
    Filter parameter tree based on search text.
    Returns True if this parameter or any of its children match the search.
    """
    if not search_text:
        # If search is empty, show everything
        param.show()
        for child in param.children():
            filter_parameter_tree(child, search_text)
        return True

    search_lower = search_text.lower()
    param_name_lower = param.title().lower()

    # Check if current parameter matches
    current_matches = search_lower in param_name_lower

    # If this is a group and it matches, show all children
    if param.hasChildren() and current_matches:
        param.setOpts(expanded=True)        
        param.show()
        for child in param.children():
            child.show()
            # Recursively show all descendants
            change_visibility_all_descendants(child, visible=True)
        return True

    # Check if any children match (recursively)
    # Each child is evaluated independently
    any_child_matches = False
    for child in param.children():
        child_matches = filter_parameter_tree(child, search_text)
        any_child_matches = any_child_matches or child_matches

    # Show this parameter only if it matches OR any of its children match
    should_show = current_matches or any_child_matches

    if should_show:
        param.show()
        # If children match, expand this parent to show them
        if any_child_matches and param.hasChildren():
            items = param.items
            if items:
                for item in items:
                    item.setExpanded(True)
            param.setOpts(expanded=True)        
    else:
        param.hide()

    return should_show

def change_visibility_all_descendants(param: Parameter, visible: bool = True):
    """Recursively show all descendants of a parameter"""
    if param.hasChildren():
        param.setOpts(expanded=True)
    for child in param.children():
        if visible:
            child.show()
        else:
            child.hide()
        change_visibility_all_descendants(child, visible)


        
def scroll_log(scroll_val, min_val, max_val):
    """
    Convert a scroll value [0-100] to a log scale between min_val and max_val

    Parameters
    ----------
    scroll
    min_val
    max_val

    Returns
    -------
    the scaled value
    """
    assert scroll_val >= 0
    assert scroll_val <= 100
    value = scroll_val * (np.log10(max_val) - np.log10(min_val)) / 100 + np.log10(min_val)
    return 10 ** value


def scroll_linear(scroll_val, min_val, max_val):
    """
    Convert a scroll value [0-100] to a linear scale between min_val and max_val

    Parameters
    ----------
    scroll
    min_val
    max_val

    Returns
    -------
    the scaled value
    """
    assert scroll_val >= 0
    assert scroll_val <= 100
    value = scroll_val * (max_val - min_val) / 100 + min_val
    return value




if __name__ == '__main__':              # pragma: no cover
    parent = [
        {'title': 'Spectro Settings:', 'name': 'spectro_settings', 'type': 'group', 'expanded': True,
            'children': [
                {'title': 'Home Wavelength (nm):', 'name': 'spectro_wl_home', 'type': 'float', 'value': 600, 'min': 0,
                 'readonly': False},
                {'title': 'Grating Settings:', 'name': 'grating_settings', 'type': 'group', 'expanded': True,
                    'children': [
                        {'title': 'Grating:', 'name': 'grating', 'type': 'list'},
                        {'title': 'Lines (/mm):', 'name': 'lines', 'type': 'int', 'readonly': True},
                        {'title': 'Blaze WL (nm):', 'name': 'blaze', 'type': 'str', 'readonly': True},
                    ]},
            ]
         },
    ]

    d = get_param_dict_from_name(parent, 'lines')

    d['readonly'] = False
    print(parent[0]['children'][1]['children'])

