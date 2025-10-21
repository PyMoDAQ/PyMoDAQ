
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QStyle

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml


from pymodaq.utils.managers.configurator.utils import (ConfiguratorParameterTree, ConfiguratorModel,
                                                       ConfiguratorEntry, ConfiguratorTableView,
                                                       get_module_from_param, )


logger = set_logger(get_module_name(__file__))


class Configurator:
    def __init__(self):
        self._actuators: list[str] = None
        self.control_modules_settings: Parameter = None


    def populate_from_settings(self, settings: Parameter):
        self.control_modules_settings = settings
        self.set_drag_mode_recursive(self.control_modules_settings, movable=True, drop_enabled=True)
        self._actuators = [
            param.opts['title'] for param in self.control_modules_settings.child('Actuators').children()]
        self.show_configurator()

    def populate_from_file(self, file_path: Path):

        children = ioxml.XML_file_to_parameter(file_path)
        self.control_modules_settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children
        )
        self.set_drag_mode_recursive(self.control_modules_settings, movable=True, drop_enabled=True)
        self._actuators = [
            param.child('name').value() for param in self.control_modules_settings.child('Moves').children()]
        self.show_configurator()

    def show_configurator(self):

        self.tree_in = ConfiguratorParameterTree()
        self.tree_in.setParameters(self.control_modules_settings, showTop=False)
        self.tree_in.setDragEnabled(True)
        self.tree_in.setAcceptDrops(False)
        self.tree_in.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)

        self.table_out = ConfiguratorTableView(True)
        self.table_out.horizontalHeader().ResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_out.horizontalHeader().setStretchLastSection(True)
        self.table_out.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_out.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.table_out.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)

        self.config_model = ConfiguratorModel(actuators=self._actuators)
        self.table_out.setModel(self.config_model)
        self.table_out.add_data_signal[int].connect(self.config_model.add_data)
        self.table_out.remove_row_signal[int].connect(self.config_model.remove_data)
        self.table_out.load_data_signal.connect(self.config_model.load)
        self.table_out.save_data_signal.connect(self.config_model.save)

        self.main_widget = QtWidgets.QWidget()

        vlayout = QtWidgets.QVBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)


        widget_buttons = QtWidgets.QWidget()
        widget_buttons.setLayout(QtWidgets.QVBoxLayout())

        add_button = QtWidgets.QPushButton('Add')
        pixmapi = getattr(QStyle.StandardPixmap, 'SP_ArrowRight')
        icon = widget_buttons.style().standardIcon(pixmapi)
        add_button.setIcon(icon)
        add_button.clicked.connect(self.add_setting)

        remove_button = QtWidgets.QPushButton('Remove')
        pixmapi = getattr(QStyle.StandardPixmap, 'SP_ArrowLeft')
        icon = widget_buttons.style().standardIcon(pixmapi)
        remove_button.setIcon(icon)
        remove_button.clicked.connect(self.remove_setting)

        widget_buttons.layout().addStretch()
        widget_buttons.layout().addWidget(add_button)
        widget_buttons.layout().addWidget(remove_button)
        widget_buttons.layout().addStretch()

        vlayout.addWidget(hwidget)
        hlayout.addWidget(self.tree_in)
        hlayout.addWidget(widget_buttons)
        hlayout.addWidget(self.table_out)

        self.main_widget.setLayout(vlayout)

        self.main_widget.setWindowTitle("Fill in information about this manager")
        self.main_widget.show()

    def set_drag_mode_recursive(self, param: Parameter, movable=True, drop_enabled=True):
        param.setOpts(movable=movable, dropEnabled=drop_enabled)
        for child in param.children():
            self.set_drag_mode_recursive(child, movable, drop_enabled)


    def add_setting(self):
        current_setting = self.tree_in.currentItem().param
        module = get_module_from_param(ParameterWithPath(current_setting))
        entry = ConfiguratorEntry(module, ParameterWithPath(current_setting))
        self.config_model.add_data(self.config_model.rowCount(), entry)

    def remove_setting(self):
        current_index = self.table_out.currentIndex()
        self.config_model.remove_data(current_index.row())

if __name__ == "__main__":

    from pymodaq.utils.config import get_set_preset_path

    preset_path = get_set_preset_path().joinpath('preset_default.xml')

    app = QtWidgets.QApplication(sys.argv)


    prog = Configurator()
    prog.populate_from_file(preset_path)

    sys.exit(app.exec_())
