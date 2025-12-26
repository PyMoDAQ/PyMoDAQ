from qtpy import QtGui, QtWidgets
from pymodaq_gui.resources.material_icons import MaterialIcon
from pymodaq_gui.managers.action_manager import resource_path_exists
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_utils.config import Config

config = Config()


class WidgetWithMaterialIcons(CustomApp):
    def __init__(self, parent):
        super().__init__(parent)

        self.setup_ui()

    def setup_docks(self):

        self.setup_icons()

        self.widget = QtWidgets.QWidget()
        self.parent.setCentralWidget(self.widget)

        self.widget.setLayout(QtWidgets.QHBoxLayout())

        self.widget.layout().addWidget(self.search_button)
        self.widget.layout().addWidget(self.toggle_button)
        self.widget.show()

    def setup_icons(self):
        # Create a QIcon object
        self.search_icon = MaterialIcon(
            'search',
            style=MaterialIcon.Style(config('style', 'icons', 'style')[0]),
            fill=config('style', 'icons', 'fill')[0],
            size=config('style', 'icons', 'size')[0])

        # Set a color for a state, for example when a button is checked
        self.search_icon.set_color(QtGui.QColor('green'), state=QtGui.QIcon.State.On)
        self.search_icon.set_color(QtGui.QColor('red'), state=QtGui.QIcon.State.Off)

        self.search_button = QtWidgets.QPushButton('Search')
        self.search_button.setIcon(self.search_icon)
        self.search_button.setCheckable(True)

        # Set a different icon for a state, for example when a button is checked
        self.toggle_icon_off = MaterialIcon(
            'toggle_off',
            style=MaterialIcon.Style(config('style', 'icons', 'style')[0]),
            fill=config('style', 'icons', 'fill')[0],
            size=config('style', 'icons', 'size')[0])
        self.toggle_icon_on = MaterialIcon(
            'toggle_on',
            style=MaterialIcon.Style(config('style', 'icons', 'style')[0]),
            fill=config('style', 'icons', 'fill')[0],
            size=config('style', 'icons', 'size')[0])
        self.toggle_icon_off.set_icon(self.toggle_icon_on, state=QtGui.QIcon.State.On)

        self.toggle_button = QtWidgets.QPushButton('Toggle')
        self.toggle_button.setIcon(self.toggle_icon_off)
        self.toggle_button.setCheckable(True)

    def setup_actions(self):
        self.add_action('search', 'Search Action', 'search',
                        checkable=True,
                        icon_color='green',
                        icon_checked_color='red')
        self.add_action('toggle', 'Toggle Action', 'toggle_off', icon_checked='toggle_on',
                        icon_color='red', icon_checked_color='green')
        self.add_action('visibility', 'Visibility Action', 'visibility', icon_checked='visibility_off',
                        icon_color='red', icon_checked_color='green')

    def connect_things(self):
        pass


if __name__ == '__main__':

    from pymodaq_gui.utils.utils import mkQApp

    # Create application and main window
    app = mkQApp('Qt Material Icons and theme')
    parent = QtWidgets.QMainWindow()
    myapp = WidgetWithMaterialIcons(parent)

    parent.show()
    app.exec_()

