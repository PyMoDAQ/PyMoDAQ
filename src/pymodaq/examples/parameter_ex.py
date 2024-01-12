"""
S Weber  2020
Examples of custome parameter types derived from pyqtgraph
"""
import sys

import pymodaq.utils.gui_utils.widgets.table
from qtpy import QtWidgets, QtCore
from pymodaq.utils.parameter import ParameterTree, Parameter
from collections import OrderedDict
from pymodaq.utils.managers.parameter_manager import ParameterManager


class ParameterEx(ParameterManager):
    params = [
        {'title': 'Groups:', 'name': 'groups', 'type': 'group', 'children': [
            {'title': 'A visible group:', 'name': 'agroup', 'type': 'group', 'children': []},
            {'title': 'An hidden group:', 'name': 'bgroup', 'type': 'group', 'children': [], 'visible': False},  # this
            # visible option is not available in usual pyqtgraph group
        ]},

        {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
            {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20., 'min': 1.,
             'tip': 'displays this text as a tooltip'},
            {'title': 'Linear Slide float', 'name': 'linearslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 0,
             'max': 123, 'subtype': 'linear'},
            {'title': 'Linear int Slide', 'name': 'linearslideint', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 0,
             'max': 123, 'subtype': 'linear', 'int': True},
            {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 1e-5,
             'max': 1e5, 'subtype': 'log'},
        ]},

        {'title': 'Booleans:', 'name': 'booleans', 'type': 'group', 'children': [
            {'title': 'Standard bool', 'name': 'abool', 'type': 'bool', 'value': True},
            {'title': 'bool push', 'name': 'aboolpush', 'type': 'bool_push', 'value': True, 'label': 'action'},
            {'title': 'A led', 'name': 'aled', 'type': 'led', 'value': False, 'tip': 'a led you cannot toggle'},
            {'title': 'A led', 'name': 'anotherled', 'type': 'led_push', 'value': True, 'tip': 'a led you can toggle'},
        ]},

        {'title': 'DateTime:', 'name': 'datetimes', 'type': 'group', 'children': [
            {'title': 'Time:', 'name': 'atime', 'type': 'time', 'value': QtCore.QTime.currentTime()},
            {'title': 'Date:', 'name': 'adate', 'type': 'date', 'value': QtCore.QDate.currentDate(),
             'format': 'dd/MM/yyyy'},
            {'title': 'DateTime:', 'name': 'adatetime', 'type': 'date_time',
             'value': QtCore.QDateTime(QtCore.QDate.currentDate(), QtCore.QTime.currentTime()),
             'format': 'MM/dd/yyyy hh:mm', 'tip': 'displays this text as a tooltip'},
        ]},
        {'title': 'An action', 'name': 'action', 'type': 'action'},  # action whose displayed text corresponds to title

        {'title': 'Lists:', 'name': 'lists', 'type': 'group', 'children': [
            {'title': 'Standard list:', 'name': 'alist', 'type': 'list', 'limits': ['a value', 'another one']},
            {'title': 'List with add:', 'name': 'anotherlist', 'type': 'list', 'limits': ['a value', 'another one'],
             'show_pb': True, 'tip': 'when using the "show_pb" option, displays a plus button to add elt to the list'},
            {'title': 'List defined from a dict:', 'name': 'dict_list', 'type': 'list',
             'limits': {'xaxis': 0, 'yaxis': [0, 1, 2]}, 'tip': 'Such a parameter display text that are keys of a dict while'
                                                        'values could be any object'
             },
        ]},
        {'title': 'Browsing files:', 'name': 'browser', 'type': 'group', 'children': [
            {'title': 'Look for a file:', 'name': 'afile', 'type': 'browsepath', 'value': '', 'filetype': True,
             'tip': 'If filetype is True select a file otherwise a directory'},
            {'title': 'Look for a dir:', 'name': 'adir', 'type': 'browsepath', 'value': '', 'filetype': False,
             'tip': 'If filetype is True select a file otherwise a directory'},

        ]},
        {'title': 'Selectable items:', 'name': 'itemss', 'type': 'group', 'children': [
            {'title': 'Selectable items', 'name': 'items', 'type': 'itemselect',
             'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
             'tip': 'Press Ctrl+click  to select items in any order'},
            {'title': 'Selectable items', 'name': 'itemsbis', 'type': 'itemselect',
             'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
             'tip': 'If show_pb is True, user can add items to the list', 'show_pb': True,},
            {'title': 'Removable items', 'name': 'itemsbisbis', 'type': 'itemselect',
             'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
             'tip': 'If show_mb is True, user can remove selected items from the list', 'show_mb': True,},            
            {'title': 'Checkable items', 'name': 'itemscheckable', 'type': 'itemselect',
             'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
             'tip': 'If checkbox is True, user can select item by checking/unchecking items. Remove items is still used with standard selections',
             'show_pb': True, 'checkbox': True, 'show_mb': True,},                        
            {'title': 'Dragable items', 'name': 'itemsdragablecheckable', 'type': 'itemselect',
             'value': dict(all_items=['item1', 'item2', 'item3'], selected=['item2']),
             'tip': 'If dragdrop is True, user can drag or drop items inside the list', 'checkbox': True, 'dragdrop': True}, 
        ]},  
        {'title': 'Plain text:', 'name': 'texts', 'type': 'group', 'children': [
            {'title': 'Standard str', 'name': 'atte', 'type': 'str', 'value': 'this is a string you can edit'},
            {'title': 'Plain text', 'name': 'text', 'type': 'text', 'value': 'this is some text'},
            {'title': 'Plain text', 'name': 'textpb', 'type': 'text_pb', 'value': 'this is some text',
             'tip': 'If text_pb type is used, user can add text to the parameter'},
        ]},

        {'title': 'Tables:', 'name': 'tables', 'type': 'group', 'children': [
            {'title': 'Table widget', 'name': 'tablewidget', 'type': 'table', 'value':
                OrderedDict(key1='data1', key2=24), 'header': ['keys', 'limits'], 'height': 100},
            {'title': 'Table view', 'name': 'tabular_table', 'type': 'table_view',
             'delegate': pymodaq.utils.gui_utils.widgets.table.SpinBoxDelegate, 'menu': True,
             'value': pymodaq.utils.gui_utils.widgets.table.TableModel([[0.1, 0.2, 0.3]], ['value1', 'value2', 'value3']),
             'tip': 'The advantage of the Table model lies in its modularity.\n For concrete examples see the'
                    'TableModelTabular and the TableModelSequential custom models in the'
                    ' pymodaq.utils.scanner module'},
        ]},  # The advantage of the Table model lies in its modularity for concrete examples see the
        # TableModelTabular and the TableModelSequential custom models in the pymodaq.utils.scanner module
    ]

    def __init__(self):
        super().__init__()

    def value_changed(self, param):
        """
        """
        print(f'The parameter {param.name()} changed its value to {param.value()}')


def main():
    app = QtWidgets.QApplication(sys.argv)
    ptree = ParameterEx()
    ptree.settings_tree.show()
    ptree.settings.child('itemss', 'itemsbis').setValue(dict(all_items=['item1', 'item2', 'item3'],
                                                             selected=['item3']))

    ptree.settings.child('itemss', 'itemsbis').setValue(dict(all_items=['item1', 'item2', 'item3'],
                                                             selected=['item1', 'item3']))
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
