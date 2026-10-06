
from qtpy import QtWidgets, QtCore

from pymodaq_gui.managers.action_manager import QAction, addaction, ActionManager
from pymodaq_gui.utils.styling import Font


class WidgetWithToolbar(QtWidgets.QWidget, ActionManager):
    """ Create a Widget with a vertical layout containing a title and
    subwidgets
    """

    def __init__(self, subwidget:QtWidgets.QWidget = None, parent=None,
                 **label_kwargs):
        QtWidgets.QWidget.__init__(self, parent)

        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar(self))
        self.font = Font(**label_kwargs)

        self.top_widget = QtWidgets.QWidget()
        self.top_widget.setLayout(QtWidgets.QHBoxLayout())

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.top_widget)

        self.top_widget.layout().addWidget(self.toolbar)
        self.top_widget.layout().addStretch()

        self._widget_with_focus: QtWidgets.QWidget = None

        if subwidget is not None:
            self.layout().addWidget(subwidget)

    def give_focus_to(self, widget: QtWidgets.QWidget):
        self._widget_with_focus = widget

    @property
    def top_layout(self) -> QtWidgets.QHBoxLayout:
        return self.top_widget.layout()

    def add_widget_top(self, widget: QtWidgets.QWidget):
        ind = self.top_layout.count()
        ind = ind - 2 if ind > 1 else 0  # -2 is for the toolbar and the stretch
        self.top_layout.insertWidget(ind, widget)

    def insert_widget(self, widget=QtWidgets.QWidget, ind=1):
        self.layout().insertWidget(ind, widget)

    def showEvent(self, event, /):
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self.set_focus)

    def set_focus(self,):
        if self._widget_with_focus is not None:
            self._widget_with_focus.setFocus()
            if hasattr(self._widget_with_focus, 'selectAll'):
                self._widget_with_focus.selectAll()


if __name__ == '__main__':
    from pymodaq_gui.utils.utils import mkQApp
    from qt_themes import get_theme
    app = mkQApp('WidgetToolbar')
    widget = WidgetWithToolbar(123, 'State')

    widget.add_action('quit', 'Quit', icon_name="cancel",
                        tip="Quit PyMoDAQ", icon_color=get_theme().red)
    widget.connect_action('quit', widget.close)
    widget.show()

    app.exec()