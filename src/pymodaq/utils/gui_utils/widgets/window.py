from qtpy.QtWidgets import QMainWindow
from qtpy.QtCore import Qt
from pymodaq_gui.utils import DockArea


def make_window(
    area:DockArea=None,
    win:QMainWindow=None,
    title="Module",
    flags=(
        Qt.WindowType.Window
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowMaximizeButtonHint
    ),
):
    """
    Create and configure a QMainWindow with a DockArea as its central widget.

    Args:
        area (DockArea): DockArea widget to use as central widget.
                                   Defaults to a new DockArea instance.
        win (QMainWindow): Main window object to configure.
                                     Defaults to a new QMainWindow instance.
        title (str, optional): Window title text. Defaults to "Module".
        flags (Qt.WindowFlags, optional): Combined window flags that control
                                         window behavior and appearance.
                                         Defaults to a standard window with
                                         title bar and min/max buttons.

    Returns:
        tuple: (win, area) - The configured QMainWindow and DockArea objects.
    """
    # Check if area parameter was provided, create new one if None
    if area is None:
        area = DockArea()

    # Check if win parameter was provided, create new one if None
    if win is None:
        win = QMainWindow()

    # Apply the window flags (controls titlebar, buttons, window type)
    win.setWindowFlags(flags)

    # Set the DockArea as the main content widget of the window
    win.setCentralWidget(area)

    # Set the text displayed in the window's title bar
    win.setWindowTitle(title)

    # Return both objects for further use
    return win, area