from qtpy import QtWidgets

from pymodaq_gui.utils.utils import mkQApp
from pymodaq_gui.utils.widgets.label import LabelWithFont
from pymodaq_gui.managers.action_manager import ActionManager


class WidgetWithTitleInToolbar(QtWidgets.QWidget, ActionManager):
    """ Create a Widget with a vertical layout containing a title and
    subwidgets
    """

    def __init__(self, title:str, subwidget:QtWidgets.QWidget = None, parent=None,
                 **label_kwargs):
        ActionManager.__init__(self)
        QtWidgets.QWidget.__init__(self, parent)


        font_name = label_kwargs.pop('font_name', 'Tahoma')
        font_size = label_kwargs.pop('font_size', 14)
        isbold = label_kwargs.pop('isbold', True)
        isitalic = label_kwargs.pop('isitalic', True)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.add_toolbar('top', 'TopToolbar', parent=self)
        self.layout().addWidget(self.toolbar)
        self.label = LabelWithFont(f'{title}', font_name=font_name,
                              font_size=font_size, isbold=isbold,
                              isitalic=isitalic)

        self.add_widget('label', self.label)

        if subwidget is not None:
            self.layout().addWidget(subwidget)
        self.layout().addStretch()

    def insert_widget(self, widget=QtWidgets.QWidget, ind=1):
        self.layout().insertWidget(ind, widget)

    def set_label_visible(self, visible=True):
        self.label.setVisible(visible)

    def set_title(self, title: str):
        self.label.setText(title)


if __name__ == '__main__':
    from qt_themes import get_theme
    app = mkQApp('WidgetToolbar')
    widget = WidgetWithTitleInToolbar('AToolbar')

    widget.add_action('quit', 'Quit', icon_name="cancel",
                        tip="Quit PyMoDAQ", icon_color=get_theme().red)
    widget.connect_action('quit', widget.close)
    widget.show()

    app.exec()