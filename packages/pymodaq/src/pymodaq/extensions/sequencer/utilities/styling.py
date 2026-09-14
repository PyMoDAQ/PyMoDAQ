import qt_themes
from PySide6.QtGui import QColor
from qtpy import QtWidgets, QtGui

from qt_themes import get_theme

def text_color(level: int):
    colors = ('text', 'subtext0', 'subtext1')
    level = level % 3
    return colors[level]

def alpha_color(level: int):
    return 0.5 + 0.5 * (1 - level / 5)

def color_to_rgba(color: QtGui.QColor, alpha: float = None):
    if alpha is None:
        alpha = color.alphaF()
    return f'rgb({color.red()}, {color.green()}, {color.blue()},{alpha})'

def button_style(level: int):

    return f"""
    QPushButton {{
        background-color: {color_to_rgba(color_from_depth(get_theme().mantle, level))};
        color: {color_to_rgba(get_theme().text)};
        border: 1px solid {color_to_rgba(get_theme().surface1)};
        border-radius: 6px;
        padding: 6px 24px 6px 12px; /* Plus d'espace à droite pour l'indicateur de menu */
        font-weight: bold;
    }}
    
    QPushButton:hover {{
        background-color: {color_to_rgba(get_theme().primary)};
        border: 1px solid {color_to_rgba(get_theme().surface2)};
    }}
    
    QPushButton:pressed {{
        background-color: {color_to_rgba(get_theme().primary)};
    }}
    
    QPushButton::menu-indicator {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        right: 8px;
        width: 10px;
        height: 10px;
    }}
    """

def menu_style(level: int):
    return f"""
    QMenu {{
        background-color: {color_to_rgba(get_theme().mantle)};
        color: {color_to_rgba(get_theme().text)};
        border: 1px solid {color_to_rgba(get_theme().surface0)};
        padding: 4px 0px;
    }}

    QMenu::item {{
        background-color: transparent;
        padding: 6px 28px 6px 24px;
        margin: 2px 4px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {color_to_rgba(get_theme().primary)};
        color: {color_to_rgba(get_theme().base)};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {color_to_rgba(get_theme().surface0)};
        margin: 4px 10px;
    }}

    QMenu::indicator {{
        width: 14px;
        height: 14px;
        left: 6px;
    }}
    """


if __name__ == '__main__':
    from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory
    from pymodaq_gui.utils.menu_utils import MenuButton
    from pymodaq_gui.utils.utils import mkQApp

    app = mkQApp('Button')

    container = QtWidgets.QWidget()
    #container.setStyleSheet("background-color: transparent;")
    layout = QtWidgets.QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    buttons = []
    themes = ['monokai', 'atom_one', 'catppuccin_frappe', 'nord']
    for ind in range(4):
        qt_themes.set_theme(themes[ind])
        button = MenuButton('Add', add_menu_entries=SeqEltFactory().elements)
        button.setFixedHeight(30)
        button.setStyleSheet(button_style(ind))
        button.menu.setStyleSheet(menu_style(0))
        layout.addWidget(button)
        buttons.append(button)

    container.show()

    app.exec()


def color_from_depth(color: QColor, depth: int) -> QColor:
    # Generate a distinct tint step per level
    # Dark themes: Stepwise lightening | Light themes: Stepwise darkening
    if get_theme().is_dark_theme():
        # Dark theme adjustment (e.g., Nord, Monokai)
        level_color = color.lighter(100 + (depth * 15))
    else:
        # Light theme adjustment (e.g., Catppuccin Latte)
        level_color = color.darker(100 + (depth * 10))
    return level_color
