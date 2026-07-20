from qtpy import QtWidgets
from .label import LabelWithFont

class WidgetWithLabelTitle(QtWidgets.QWidget):
    """ Create a Widget with a vertical layout containing a title and
    subwidgets
    """

    def __init__(self, title:str, subwidget:QtWidgets.QWidget = None, parent=None,
                 **label_kwargs):
        super().__init__(parent)

        self.setLayout(QtWidgets.QVBoxLayout())
        label = LabelWithFont(f'{title}', **label_kwargs)
        self.label = label
        self.layout().addWidget(label)
        if subwidget is not None:
            self.layout().addWidget(subwidget)
        self.layout().addStretch()

    def insert_widget(self, widget=QtWidgets.QWidget, ind=1):
        self.layout().insertWidget(ind, widget)

    def set_label_visible(self, visible=True):
        self.label.setVisible(visible)