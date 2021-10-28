New Tree items
++++++++++++++

Documentation on the added or modified ParameterItem types compared to ``pyqtgraph.parametertree.parameterTypes`` module.

``WidgetParameterItem`` and ``SimpleParameter`` have been subclassed to define more options:

* ``int`` and ``float``: represented by a custom ``Spinbox``, see :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.SpinBoxCustom`
* ``bool``, ``led``, ``bool_push`` are represented respectively by a :py:meth:`~qtpy.QtWidgets.QCheckBox`,
  a :py:meth:`~pymodaq.daq_utils.plotting.QLED.qled.QLED`, :py:meth:`~qtpy.QtWidgets.QPushButton`
* ``str`` displays a QLineEdit widget
* ``date_time`` displays a QDateTime widget
* ``date`` displays a QDate widget
* ``time`` displays a :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.QTimeCustom` widget
* ``pixmap`` displays a QPixmap in a QLabel
* ``pixmap_check`` displays a custom :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.Pixmap_check` widget


Other widgets for ParameterTree have been introduced:

* ``group``: subclassed group parameter, see :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.GroupParameterCustom` and :py:meth:`~GroupParameterItemCustom`
* ``slide``: displays a custom ``Spinbox`` and a QSlider to set floats and ints, see :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.SliderSpinBox`
* ``list``: subclassed pyqtgraph ``list`` that displays a list and a pushbutton to let the user add entries in the list,
  see :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.ListParameter_custom` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.ListParameterItem_custom` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.Combo_pb`
* ``table``: subclassed pyqtgraph ``table``, see :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.TableParameterItem`,
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.TableParameter` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.Table_custom`
* ``table_view`` : displaying a QTableView with custom model to be user defined, see Qt5 documentation, see
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.TableViewParameterItem`,
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.TableViewCustom` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.TableViewParameter`
* ``ìtemselect``: displays a QListWidget with selectable elements, see
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.ItemSelectParameterItem`,
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.ItemSelect_pb`,
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.ItemSelect` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.ItemSelectParameter`
* ``browsepath``: displays an edit line and a push button to select files or folders, see
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.file_browserParameterItem`,
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.file_browser` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.file_browserParameter`
* ``text```: subclassed plain text area ``text`` from pyqtgraph with limited height, see
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.TextParameterItemCustom` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.TextParameter`
* ``text_pb``: displays a plain text area and a visible button to add data into it, see
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.Plain_text_pbParameterItem`,
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.Plain_text_pb` and
  :py:meth:`~pymodaq.daq_utils.custom_parameter_tree.Plain_text_pbParameter`



.. automodule:: pymodaq.daq_utils.parameter.pymodaq_ptypes
   :members: GroupParameterItemCustom, GroupParameterCustom, SpinBoxCustom, Pixmap_check, QTimeCustom,
             SliderParameterItem, SliderParameter, SliderSpinBox,
             ListParameter_custom, ListParameterItem_custom, Combo_pb, TableParameterItem, TableParameter, Table_custom,
             TableViewParameterItem, TableViewCustom, TableViewParameter, pymodaq.daq_utils.plotting.QLED.qled.QLED,
             ItemSelectParameterItem, ItemSelect_pb, ItemSelect, ItemSelectParameter, file_browser, file_browserParameterItem,
             file_browserParameter, Plain_text_pbParameterItem, Plain_text_pb, Plain_text_pbParameter, TextParameterItemCustom,
             TextParameter

