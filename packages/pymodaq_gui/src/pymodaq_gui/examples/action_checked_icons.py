
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_utils.config import Config

config = Config()
import sys
from qtpy import QtWidgets, QtCore, QtGui




class MyWidget(ActionManager):
    def __init__(self, parent):
        ActionManager.__init__(self)

        self.parent = parent

        self.setup_ui()
        self.setup_actions()

        self.parent.show()

    def setup_ui(self):
        self.parent.setLayout(QtWidgets.QVBoxLayout())
        self.add_toolbar('default')
        self.parent.layout().addWidget(self.get_toolbar('default'))

    def setup_actions(self):

        self.add_action('show', 'Show Icon', 'show', checkable=True, icon_checked='unshow',
                        toolbar='default')



def main():
    """Run the example application"""
    from pymodaq_gui.utils.utils import mkQApp


    app = mkQApp('Example')
    widget = QtWidgets.QWidget()
    mywidget = MyWidget(widget)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
