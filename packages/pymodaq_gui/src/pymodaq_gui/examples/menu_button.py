from typing import Iterable

from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.menu_utils import MenuButton

if __name__ == '__main__':
    app = mkQApp('MenuButton')

    def print_path(path: Iterable[str]) -> None:
        print(path)

    add_menu = ['level-0-0', 'level-0-1',
                {'level-0-2': ['level-1-0', 'level-1-1',
                               {'level-1-2': ['level-2-0', 'level-2-1']}]}]

    menu_button = MenuButton('My button', add_menu)

    menu_button.show()

    menu_button.triggered.connect(print_path)


    app.exec()