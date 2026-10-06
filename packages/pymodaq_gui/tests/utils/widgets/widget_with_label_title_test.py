import pytest
from qtpy import QtWidgets
from pymodaq_gui.utils.widgets.widget_with_label_title import WidgetWithLabelTitle


class TestWidgetWithLabelTitle:

    def test_no_buttons_by_default(self, qtbot):
        widget = WidgetWithLabelTitle('title')
        qtbot.addWidget(widget)

        assert widget.close_pb is None
        assert widget.attach_pb is None

    def test_close_button_emits_signal(self, qtbot):
        widget = WidgetWithLabelTitle('title', closable=True)
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.sig_close, timeout=1000):
            widget.close_pb.click()

    def test_attach_button_emits_signal(self, qtbot):
        widget = WidgetWithLabelTitle('title', attachable=True)
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.sig_attach_detach) as blocker:
            widget.attach_pb.click()
        assert blocker.args[0] is True  # now detached

        with qtbot.waitSignal(widget.sig_attach_detach) as blocker:
            widget.attach_pb.click()
        assert blocker.args[0] is False  # attached again

    def test_set_attached_does_not_emit_signal(self, qtbot):
        widget = WidgetWithLabelTitle('title', attachable=True)
        qtbot.addWidget(widget)

        received = []
        widget.sig_attach_detach.connect(received.append)

        widget.set_attached(False)
        assert widget.attach_pb.isChecked() is True
        assert received == []

    def test_set_title_updates_label(self, qtbot):
        widget = WidgetWithLabelTitle('title')
        qtbot.addWidget(widget)

        widget.set_title('new title')
        assert widget.label.text() == 'new title'


@pytest.mark.parametrize('expand, use_insert', [(False, False), (True, False), (True, True)])
def test_expand_subwidget(qtbot, expand, use_insert):
    tree = QtWidgets.QTreeWidget()
    tree.setMinimumHeight(10)
    if use_insert:
        widget = WidgetWithLabelTitle('title', expand_subwidget=expand)
        widget.insert_widget(tree)
    else:
        widget = WidgetWithLabelTitle('title', tree, expand_subwidget=expand)
    qtbot.addWidget(widget)
    widget.resize(300, 1000)
    widget.show()
    qtbot.waitExposed(widget)
    if expand:
        assert tree.height() > 800  # fills the available height
    else:
        assert tree.height() < 600  # shares the height with the stretch below it
