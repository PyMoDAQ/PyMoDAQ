from typing import TYPE_CHECKING

from qtpy import QtWidgets

from pymodaq_utils.config import GlobalConfig

from pymodaq.extensions.custom_ext import CustomExt
from pymodaq_gui.utils import DockArea, Dock
from pymodaq_gui.utils.widgets.window import make_window

from pymodaq.utils.shared_ui import SharedUI


if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.dashboard import DashBoard

config = GlobalConfig()


def create_load_daq_move(title="DAQ_Move") -> tuple[SharedUI, 'DAQ_Move']:
    from pymodaq.control_modules.daq_move import DAQ_Move

    win, area = make_window(area=False, title='DAQ_Move')
    widget = QtWidgets.QWidget()
    daq_move = DAQ_Move(widget, title=title)

    area = DockArea()

    settings_dock = Dock('Settings')
    controls_dock = Dock('Controls')
    area.addDock(settings_dock)
    area.addDock(controls_dock, 'right', settings_dock)
    settings_dock.setVisible(False)
    controls_dock.setVisible(False)

    daq_move = DAQ_Move(widget, title=title,
                        settings_dock=settings_dock,
                        controls_dock=controls_dock,
                        )
    widget.layout().addWidget(area)
    win.setCentralWidget(widget)
    shared_ui = SharedUI(win)
    shared_ui.affect_application(daq_move.ui)

    shared_ui.add_toolbar('move_toolbar', 'Move', win,
                          toolbar=daq_move.ui.toolbar,
                          add_break=False)

    return shared_ui, daq_move


def create_load_daq_viewer(title='DAQ_Viewer') -> tuple[SharedUI, 'DAQ_Viewer']:
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer, Dock
    win, area = make_window(area=False, title='DAQ_Viewer')
    widget = QtWidgets.QWidget()
    win.setCentralWidget(widget)

    area = DockArea()

    settings_dock = Dock('Settings')
    rois_dock = Dock('ROIs')

    area.addDock(settings_dock, 'right')
    area.addDock(rois_dock, 'right', settings_dock)
    settings_dock.setVisible(False)
    rois_dock.setVisible(False)

    daq_viewer = DAQ_Viewer(widget, title=title,
                            area=area,
                            settings_dock=settings_dock,
                            rois_dock=rois_dock,)

    shared_ui = SharedUI(win)
    shared_ui.affect_application(daq_viewer.ui)
    shared_ui.add_toolbar('viewer', 'Viewer', win,
                          toolbar=daq_viewer.ui.toolbar, add_break=False)

    return shared_ui, daq_viewer


def create_extension(dashboard: 'DashBoard',
                     extension_class: type[CustomExt],
                     *ext_args,
                     window: QtWidgets.QMainWindow = None,
                     add_toolbarbreak=True,
                     show_extension=True,
                     **ext_kwargs) -> tuple[SharedUI, CustomExt]:

    from pymodaq_gui.utils.dock import DockArea
    if window is None:
        window, dockarea = make_window(win=window, title=extension_class.__name__)
    else:
        dockarea = window.centralWidget()
    if not isinstance(dockarea, DockArea):
        dockarea = DockArea()
        window.setCentralWidget(dockarea)

    shared_ui = SharedUI(window, show=show_extension)
    extension = extension_class(dockarea, dashboard, *ext_args, **ext_kwargs)

    shared_ui.affect_application(extension)

    if add_toolbarbreak:
        shared_ui.mainwindow.addToolBarBreak()
    toolbars = extension.get_app_toolbars()
    if not isinstance(toolbars, list):
        toolbars = [toolbars]
    for toolbar in toolbars:
        shared_ui.mainwindow.addToolBar(toolbar)
    return shared_ui, extension