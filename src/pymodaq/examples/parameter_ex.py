"""
S Weber  2020
Examples of custome parameter types derived from pyqtgraph
"""
import sys
from PyQt5 import QtWidgets, QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
from collections import OrderedDict
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from pymodaq.resources.QtDesigner_Ressources import QtDesigner_ressources_rc


class ParameterEx:
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
            {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 1e-5,
             'max': 1e5, 'subtype': 'log'},
        ]},

        {'title': 'Booleans:', 'name': 'booleans', 'type': 'group', 'children': [
            {'title': 'Standard bool', 'name': 'abool', 'type': 'bool', 'value': True},
            {'title': 'bool push', 'name': 'aboolpush', 'type': 'bool_push', 'value': True, 'label': 'action'},
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
            {'title': 'Standard list:', 'name': 'alist', 'type': 'list', 'values': ['a value', 'another one']},
            {'title': 'List with add:', 'name': 'anotherlist', 'type': 'list', 'values': ['a value', 'another one'],
             'show_pb': True, 'tip': 'when using the "show_pb" option, displays a plus button to add elt to the list'},
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
             'tip': 'If show_pb is True, user can add items to the list', 'show_pb': True},
        ]},
        {'title': 'Plain text:', 'name': 'texts', 'type': 'group', 'children': [
            {'title': 'Plain text', 'name': 'text', 'type': 'text', 'value': 'this is some text'},
            {'title': 'Plain text', 'name': 'textpb', 'type': 'text_pb', 'value': 'this is some text',
             'tip': 'If text_pb type is used, user can add text to the parameter'},
        ]},

        {'title': 'Tables:', 'name': 'tables', 'type': 'group', 'children': [
            {'title': 'Table widget', 'name': 'tablewidget', 'type': 'table', 'value':
                OrderedDict(key1='data1', key2=24), 'header': ['keys', 'values'], 'height': 100},
            {'title': 'Table view', 'name': 'tabular_table', 'type': 'table_view',
             'delegate': gutils.SpinBoxDelegate, 'menu': True,
             'value': gutils.TableModel([[0.1, 0.2, 0.3]], ['value1', 'value2', 'value3']),
             'tip': 'The advantage of the Table model lies in its modularity.\n For concrete examples see the'
                    'TableModelTabular and the TableModelSequential custom models in the'
                    ' pymodaq.daq_utils.scanner module'},
        ]},  # The advantage of the Table model lies in its modularity for concrete examples see the
        # TableModelTabular and the TableModelSequential custom models in the pymodaq.daq_utils.scanner module
    ]

    def __init__(self, tree):
        self.parameter_tree = tree

        self.settings = Parameter.create(name='settings', type='group', children=self.params)
        self.parameter_tree.setParameters(self.settings, showTop=False)

        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    def parameter_tree_changed(self, param, changes):
        """
        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                pass  # Triggered when parameter is added to the tree

            elif change == 'value':
                print(f'The parameter {param.name()} changed its value to {data}')

            elif change == 'parent':
                pass  # triggered when a param is removed from the tree


def main():
    app = QtWidgets.QApplication(sys.argv)

    parametertree = ParameterTree()
    ptree = ParameterEx(parametertree)
    parametertree.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
