from qtpy import QtGui, QtWidgets
from pymodaq_gui.resources.qt_material_icons import MaterialIcon


class WidgetWithMaterialIcons:
    def __init__(self):

        self.setup_ui()

    def setup_ui(self):

        self.setup_icons()

        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(QtWidgets.QHBoxLayout())

        self.widget.layout().addWidget(self.search_button)
        self.widget.layout().addWidget(self.toggle_button)
        self.widget.show()

    def setup_icons(self):
        # Create a QIcon object
        self.search_icon = MaterialIcon('search', fill=False,
                                        size=40)

        # Set a color for a state, for example when a button is checked
        self.search_icon.set_color(QtGui.QColor('green'), state=QtGui.QIcon.State.On)
        self.search_icon.set_color(QtGui.QColor('red'), state=QtGui.QIcon.State.Off)

        self.search_button = QtWidgets.QPushButton('Search')
        self.search_button.setIcon(self.search_icon)
        self.search_button.setCheckable(True)

        # Set a different icon for a state, for example when a button is checked
        self.toggle_icon_off = MaterialIcon('toggle_off', fill=False)
        self.toggle_icon_on = MaterialIcon('toggle_on', fill=False)
        self.toggle_icon_off.set_icon(self.toggle_icon_on, state=QtGui.QIcon.State.On)

        self.toggle_button = QtWidgets.QPushButton('Toggle')
        self.toggle_button.setIcon(self.toggle_icon_off)
        self.toggle_button.setCheckable(True)

if __name__ == '__main__':

    from pymodaq_gui.utils.utils import mkQApp

    # Create application and main window
    app = mkQApp('Dashboard')

    myapp = WidgetWithMaterialIcons()

    app.exec_()

