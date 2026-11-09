import qt_themes
from qtpy import QtWidgets

from pymodaq_gui import qt_utils
from pymodaq_gui.qt_utils import mkQApp, STYLED_PROPERTY


def test_mkqapp_styles_once(qtbot, monkeypatch):
    app = QtWidgets.QApplication.instance()  # created by pytest-qt, maybe already styled by another test
    app.setProperty(STYLED_PROPERTY, None)

    calls = []
    original = qt_utils.apply_styling_rules
    monkeypatch.setattr(qt_utils, 'apply_styling_rules', lambda a: (calls.append(a), original(a)))

    assert mkQApp('first') is app
    assert len(calls) == 1
    assert qt_themes.get_theme() is not None
    style = app.style()

    for _ in range(3):
        assert mkQApp('again') is app
    assert len(calls) == 1  # the theme is not applied again...
    assert app.style() is style  # ...and the application style is not replaced


def test_apply_styling_rules_does_not_nest_proxies(qtbot, monkeypatch):
    app = mkQApp('nested')
    monkeypatch.setattr(qt_themes, 'set_theme', lambda **kwargs: None)  # as with an empty style: no style reset
    monkeypatch.setattr(qt_themes.Theme, 'is_dark_theme', lambda self: True)
    for _ in range(3):
        qt_utils.apply_styling_rules(app)
    style = app.style()
    assert isinstance(style, qt_utils.WhiteCheckboxStyle)
    assert not isinstance(style.baseStyle(), qt_utils.WhiteCheckboxStyle)
