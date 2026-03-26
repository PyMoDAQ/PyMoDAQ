from typing import Any, TYPE_CHECKING

from pathlib import Path
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMessageBox, QMainWindow


from pymodaq.utils.gui_utils import DockArea
from pymodaq.utils.config import get_set_preset_path
from pymodaq.extensions.custom_ext import CustomExt
from pymodaq.utils.gui_utils.widgets.window import make_window

from pymodaq.utils.shared_ui import SharedUI


if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.dashboard import DashBoard


def create_load_daq_move(ui_identifier='Original') -> tuple[SharedUI, 'DAQ_Move']:
    from pymodaq.control_modules.daq_move import DAQ_Move

    widget = QtWidgets.QWidget()
    daq_move = DAQ_Move(widget, title="test",
                        ui_identifier=ui_identifier)

    shared_ui = SharedUI(widget)
    shared_ui.affect_application(daq_move)
    shared_ui.add_toolbar('move_toolbar', 'Move', toolbar=daq_move.ui.move_toolbar,
                          add_break=True)
    daq_move.settings_tree.setVisible(False)
    widget.layout().addWidget(daq_move.ui.control_widget)
    widget.layout().addWidget(daq_move.settings_tree)
    widget.layout().addWidget(daq_move.ui.graph_widget)

    return shared_ui, daq_move


def create_load_daq_viewer() -> tuple[SharedUI, 'DAQ_Viewer']:
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

    widget = QtWidgets.QWidget()
    daq_viewer = DAQ_Viewer(widget, title="test")

    shared_ui = SharedUI(widget)
    shared_ui.affect_application(daq_viewer)
    shared_ui.add_toolbar('viewer', 'Viewer', toolbar=daq_viewer.ui.toolbar, add_break=True)

    return shared_ui, daq_viewer


def create_extension(dashboard: 'DashBoard',
                     extension_class: type[CustomExt],
                     *ext_args,
                     window: QtWidgets.QMainWindow = None,
                     add_toolbarbreak=True,
                     **ext_kwargs) -> tuple[SharedUI, CustomExt]:

    from pymodaq_gui.utils.dock import DockArea
    if window is None:
        window, dockarea = make_window(win=window, title=extension_class.__name__)
    else:
        dockarea = window.centralWidget()
    if not isinstance(dockarea, DockArea):
        dockarea = DockArea()
        window.setCentralWidget(dockarea)

    extension = extension_class(dockarea, dashboard, *ext_args, **ext_kwargs)

    shared_ui = SharedUI(window)
    shared_ui.affect_application(extension)
    shared_ui.mainwindow.addToolBar(extension.get_toolbar('dashboard'))
    if add_toolbarbreak:
        shared_ui.mainwindow.addToolBarBreak()
    shared_ui.mainwindow.addToolBar(extension.get_main_toolbar())
    return shared_ui, extension