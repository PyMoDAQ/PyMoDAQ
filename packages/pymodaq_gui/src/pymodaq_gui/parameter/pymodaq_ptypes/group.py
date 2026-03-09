from qtpy import QtWidgets
from pyqtgraph.parametertree.parameterTypes.basetypes import GroupParameter, GroupParameterItem
from pymodaq_gui.utils.menu_utils import build_menu_from_iterable


class GroupParameterItem(GroupParameterItem):
    """
    Group parameters are used mainly as a generic parent item that holds (and groups!) a set
    of child parameters. It also provides a simple mechanism for displaying a button or combo
    that can be used to add new parameters to the group.
    """

    def __init__(self, param, depth):
        if 'addMenu' in param.opts:
            param.opts.pop('addList', None)
        super().__init__(param, depth)

        if 'addMenu' in param.opts:
            # Disconnect signal from previous init
            self.addWidget.clicked.disconnect(self.addClicked)
            # Create the nested menu
            self.addMenu = QtWidgets.QMenu(self.addWidget)
            self.addWidget.setMenu(self.addMenu)
            # Populate the nested menu structure
            self.updateAddMenu()

        self.optsChanged(self.param, self.param.opts)

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)

        if 'addMenu' in opts and hasattr(self, 'addMenu'):
            self.updateAddMenu()

    def updateAddMenu(self):
        self.addWidget.blockSignals(True)
        try:
            self.addMenu.clear()
            addMenu = self.param.opts.get('addMenu', [])
            build_menu_from_iterable(self.addMenu, addMenu, self.addMenuItemSelected)
        finally:
            self.addWidget.blockSignals(False)

    def addMenuItemSelected(self, name, path_tuple):
        """Called when a menu item is selected from the nested add menu.
        The parameter MUST have an 'addNew' method defined.
        """
        self.param.addNew(path_tuple)

        if hasattr(self.param.opts, 'addText'):
            self.addWidget.setText(self.param.opts['addText'])

class GroupParameter(GroupParameter):
    
    itemClass = GroupParameterItem

    def __init__(self, **opts):
        super().__init__(**opts)
   