import sys

from PyQt6.QtWidgets import (QApplication, QGridLayout, QPushButton, QStyle,
                             QWidget, QVBoxLayout)
from PyQt6.QtGui import QIcon


class Icons():
    def __init__(self, widget: QWidget):
        super().__init__()
        self.widget = widget

        Ncol = 10

        icons_style = sorted([attr for attr in dir(QStyle.StandardPixmap) if (attr.startswith("SP_"))])

        icons_theme = sorted([icon_enum.name for icon_enum in QIcon.ThemeIcon])

        self.widget.setLayout(QVBoxLayout())

        layout_style = QGridLayout()
        for n, name in enumerate(icons_style):
            btn = QPushButton(name)

            pixmapi = getattr(QStyle.StandardPixmap, name)
            icon = self.widget.style().standardIcon(pixmapi)
            btn.setIcon(icon)
            layout_style.addWidget(btn, int(n/Ncol), int(n%Ncol))

        layout_theme = QGridLayout()
        for n, name in enumerate(icons_theme):
            icon = QIcon.fromTheme(getattr(QIcon.ThemeIcon, name))
            btn = QPushButton(name)
            btn.setIcon(icon)
            layout_theme.addWidget(btn, int(n/Ncol), int(n%Ncol))

        self.widget.layout().addLayout(layout_style)
        self.widget.layout().addLayout(layout_theme)

def main():
    app = QApplication(sys.argv)

    w = Icons(QWidget())
    w.widget.show()

    app.exec()

if __name__ == "__main__":
    main()