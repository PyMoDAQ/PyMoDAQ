New Tree items
++++++++++++++

Documentation on the added or modified ParameterItem types compared to ``pyqtgraph.parametertree.parameterTypes`` module.

``WidgetParameterItem`` and ``SimpleParameter`` have been subclassed to define more options:

* ``int`` and ``float``: represented by a custom ``Spinbox``, see :py:class:`~pymodaq.utils.gui_utils.widgets.spinbox.Spinbox`
* ``bool``, ``led``, ``bool_push`` are represented respectively by a :py:class:`~qtpy.QtWidgets.QCheckBox`,
  a :py:class:`~pymodaq.utils.gui_utils.widgets.qled.QLED`, :py:class:`~qtpy.QtWidgets.QPushButton`
* ``str`` displays a QLineEdit widget
* ``date_time`` displays a QDateTime widget
* ``date`` displays a QDate widget
* ``time`` displays a :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.date.QTimeCustom` widget
* ``pixmap`` displays a QPixmap in a QLabel
* ``pixmap_check`` displays a custom :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.pixmap.PixmapCheckWidget` widget


Other widgets for ParameterTree have been introduced:

* ``group``: subclassed group parameter, see :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.GroupParameterCustom`
  and :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.GroupParameterItemCustom`
* ``slide``: displays a custom ``Spinbox`` and a QSlider to set floats and ints,
  see :py:class:`~.pymodaq.utils.parameter.pymodaq_ptypes.slide.SliderSpinBox`
* ``list``: subclassed pyqtgraph ``list`` that displays a list and a pushbutton to let the user add entries in the list,
  see :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.list.ListParameter` and
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.list.ListParameterItem` and
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.list.Combo_pb`
* ``table``: subclassed pyqtgraph ``table``, see :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.table.TableParameterItem`,
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.table.TableParameter` and
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.table.TableWidget`
* ``table_view`` : displaying a QTableView with custom model to be user defined, see Qt5 documentation, see
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.tableview.TableViewParameterItem`,
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.tableview.TableViewCustom` and
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.tableview.TableViewParameter`
* ``ìtemselect``: displays a QListWidget with selectable elements, see
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.itemselect.ItemSelectParameterItem`,
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.itemselect.ItemSelect_pb`,
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.itemselect.ItemSelect` and
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.itemselect.ItemSelectParameter`
* ``browsepath``: displays an edit line and a push button to select files or folders, see
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.filedir.FileDirParameterItem`,
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.filedir.FileDirWidget` and
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.filedir.FileDirParameter`
* ``text```: subclassed plain text area ``text`` from pyqtgraph with limited height, see
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.text.TextParameterItemCustom` and
  :py:class:`~pymodaq.utils.parameter.pymodaq_ptypes.text.TextParameter`
* ``text_pb``: displays a plain text area and a visible button to add data into it, see
  :py:class:`~pymodaq.utils.custom_parameter_tree.PlainTextParameterItem`,
  :py:class:`~pymodaq.utils.custom_parameter_tree.PlainTextWidget` and
  :py:class:`~pymodaq.utils.custom_parameter_tree.PlainTextPbParameter`



.. automodule:: pymodaq.utils.parameter.pymodaq_ptypes
   :members:

