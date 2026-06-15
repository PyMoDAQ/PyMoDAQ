"""Demo of StickyMenu with three configurations:

* Default (checkable-only): menu stays open only when a checkable action is clicked.
* sticky_all=True: menu stays open for every click, checkable or not.
* sticky_predicate: custom rule — here, only actions whose text starts with '[pin]' stay open.
"""
import sys

from qtpy import QtWidgets

from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.dock import Dock
from pymodaq_gui.utils.utils import mkQApp
from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_gui.utils.menu_utils import StickyMenu


class StickyMenuDemo(CustomApp):

    params = []

    def __init__(self, dockarea):
        super().__init__(dockarea)
        self.setup_ui()

    def setup_docks_and_widgets(self):
        dock = Dock('Log', size=(600, 300))
        self.dockarea.addDock(dock)
        self._log = QtWidgets.QPlainTextEdit()
        self._log.setReadOnly(True)
        dock.addWidget(self._log)

    def setup_menus_and_toolbars(self, menubar=None):
        # 1. Default StickyMenu — stays open only for checkable actions
        self.add_menu('checkable', 'Checkable-only (default)',
                      self.menubar, menu=StickyMenu())

        # 2. sticky_all=True — stays open for every click
        self.add_menu('all', 'All-sticky',
                      self.menubar, menu=StickyMenu(sticky_all=True))

        # 3. Custom predicate — stays open when action text starts with '[pin]'
        self.add_menu('custom', 'Custom predicate',
                      self.menubar,
                      menu=StickyMenu(sticky_predicate=lambda a: a.text().startswith('[pin]')))

    def setup_actions(self):
        # --- Checkable-only menu ---
        self.add_action('ch_toggle1', 'Toggle A', checkable=True, menu='checkable')
        self.add_action('ch_toggle2', 'Toggle B', checkable=True, menu='checkable')
        self.add_action('ch_normal', 'Normal action (closes menu)', menu='checkable')

        # --- All-sticky menu ---
        self.add_action('all_toggle', 'Toggle', checkable=True, menu='all')
        self.add_action('all_normal', 'Normal action (stays open)', menu='all')

        # --- Custom predicate menu ---
        self.add_action('pin_a', '[pin] Pinned action A', menu='custom')
        self.add_action('pin_b', '[pin] Pinned action B', checkable=True, menu='custom')
        self.add_action('unpin_c', 'Unpinned action C (closes menu)', menu='custom')

    def connect_things(self):
        for name in ('ch_toggle1', 'ch_toggle2', 'ch_normal',
                     'all_toggle', 'all_normal',
                     'pin_a', 'pin_b', 'unpin_c'):
            self.connect_action(name, lambda checked=False, n=name: self._log_action(n))

    def _log_action(self, name):
        self._log.appendPlainText(f'triggered: {name}')


def main():
    app = mkQApp('StickyMenuDemo')
    win, area = make_window(title='StickyMenu Demo')
    prog = StickyMenuDemo(area)

    from pymodaq_gui.utils.shared_ui import SharedUI
    shared_ui = SharedUI(win)
    shared_ui.affect_application(prog)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
