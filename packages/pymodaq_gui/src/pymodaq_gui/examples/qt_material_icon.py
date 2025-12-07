from qtpy import QtGui
from pymodaq_gui.resources.qt_material_icons import MaterialIcon

# Create a QIcon object
icon = MaterialIcon('search')

# Set a color
color = QtGui.QColor('red')
icon.set_color(color)

# Set a color for a state, for example when a button is checked
icon.set_color(color, state=QtGui.QIcon.State.On)

# Set a different icon for a state, for example when a button is checked
toggle_icon = MaterialIcon('toggle_off')
toggle_icon_on = MaterialIcon('toggle_on')
toggle_icon.set_icon(toggle_icon_on, state=QtGui.QIcon.State.On)
