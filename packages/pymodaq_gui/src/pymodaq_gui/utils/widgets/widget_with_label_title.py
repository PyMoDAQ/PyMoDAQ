from qtpy import QtCore, QtWidgets
from .label import LabelWithFont
from .push import ToolButtonIcon
from pymodaq_gui.utils.styling import create_icon, theme


class WidgetWithLabelTitle(QtWidgets.QWidget):
    """ Create a Widget with a vertical layout containing a title and
    subwidgets

    Parameters
    ----------
    title: str
    subwidget: QWidget
    parent: QWidget
    closable: bool
        If True, add a close button in the title header emitting `sig_close`
        when clicked
    attachable: bool
        If True, add an attach/detach toggle button in the title header
        emitting `sig_attach_detach` when clicked
    """

    sig_close = QtCore.Signal()
    sig_attach_detach = QtCore.Signal(bool)  # True: detached (floating), False: attached (docked)

    def __init__(self, title: str, subwidget: QtWidgets.QWidget = None, parent=None,
                 closable: bool = False, attachable: bool = False,
                 **label_kwargs):
        super().__init__(parent)

        font_name = label_kwargs.pop('font_name', 'Tahoma')
        font_size = label_kwargs.pop('font_size', 14)
        isbold = label_kwargs.pop('isbold', True)
        isitalic = label_kwargs.pop('isitalic', True)

        self.setLayout(QtWidgets.QVBoxLayout())
        label = LabelWithFont(f'{title}', font_name=font_name,
                              font_size=font_size, isbold=isbold,
                              isitalic=isitalic)
        self.label = label

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(label)
        header_layout.addStretch()

        icon_size = QtCore.QSize(label.sizeHint().height(), label.sizeHint().height())

        self.attach_pb: QtWidgets.QToolButton = None
        if attachable:
            self.attach_pb = ToolButtonIcon('open_in_new', checkable=True,
                                            tip='Detach this widget from its dock',
                                            icon_size=icon_size)
            self.attach_pb.toggled.connect(self._update_attach_button)
            self.attach_pb.toggled.connect(self.sig_attach_detach.emit)
            header_layout.addWidget(self.attach_pb)

        self.close_pb: QtWidgets.QToolButton = None
        if closable:
            self.close_pb = ToolButtonIcon('cancel', tip='Close this widget',
                                           icon_color=theme.red, icon_size=icon_size)
            self.close_pb.clicked.connect(self.sig_close.emit)
            header_layout.addWidget(self.close_pb)

        self.layout().addLayout(header_layout)
        if subwidget is not None:
            self.layout().addWidget(subwidget)
        self.layout().addStretch()

    def _update_attach_button(self, detached: bool):
        self.attach_pb.setIcon(create_icon('back_to_tab' if detached else 'open_in_new'))
        self.attach_pb.setToolTip('Attach this widget to its dock' if detached else
                                  'Detach this widget from its dock')

    def set_attached(self, attached: bool):
        """ Programmatically set the attach/detach button state without emitting
        `sig_attach_detach` """
        if self.attach_pb is not None:
            self.attach_pb.blockSignals(True)
            self.attach_pb.setChecked(not attached)
            self._update_attach_button(not attached)
            self.attach_pb.blockSignals(False)

    def insert_widget(self, widget=None, ind=1):
        self.layout().insertWidget(ind, widget)

    def set_label_visible(self, visible=True):
        self.label.setVisible(visible)

    def set_title(self, title: str):
        self.label.setText(title)
