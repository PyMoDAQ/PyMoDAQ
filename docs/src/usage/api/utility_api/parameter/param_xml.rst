Parameter and XML
+++++++++++++++++

Within PyMoDAQ, Parameter state are often saved or transferred (for instance when using TCP/IP) as a XML string whose
Tree structure is well adapted to represent the Parameter tree structure. Below are all the functions used to convert
from a Parameter to a XML string (or file) and vice-versa.

.. automodule:: pymodaq.utils.parameter.ioxml
   :members: walk_parameters_to_xml, walk_xml_to_parameter, add_text_to_elt, set_txt_from_elt,
             dict_from_param, elt_to_dict, parameter_to_xml_string, parameter_to_xml_file, XML_file_to_parameter,
             XML_string_to_parameter,