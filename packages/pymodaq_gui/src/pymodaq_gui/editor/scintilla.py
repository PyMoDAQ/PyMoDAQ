from enum import IntEnum
import sys

from pymodaq_gui.qt_utils import mkQApp

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.Qsci import QsciScintilla

from qt_themes import get_theme


class Symbols(IntEnum):
    GreenDot = 0
    RedDot = 1
    GreenArrow = 2
    RedArrow = 3


class CustomMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(CustomMainWindow, self).__init__()

        # Window setup
        # --------------

        # 1. Define the geometry of the main window
        self.setGeometry(300, 300, 800, 400)
        self.setWindowTitle("QScintilla Test")

        # 2. Create frame and layout
        self._frm = QtWidgets.QFrame(self)
        self._frm.setStyleSheet("QWidget { background-color: #ffeaeaea }")
        self._lyt = QtWidgets.QVBoxLayout()
        self._frm.setLayout(self._lyt)
        self.setCentralWidget(self._frm)
        self._myFont = QtGui.QFont()
        self._myFont.setPointSize(14)

        # 3. Place a button
        self._btn = QtWidgets.QPushButton("Qsci")
        self._btn.setFixedWidth(50)
        self._btn.setFixedHeight(50)
        self._btn.clicked.connect(self._btn_action)
        self._btn.setFont(self._myFont)
        self._lyt.addWidget(self._btn)

        # QScintilla editor setup
        # ------------------------

        # ! Make instance of QsciScintilla class!
        self._editor = QsciScintilla()
        self._editor.setText("This\n")  # Line 1
        self._editor.append("is\n")  # Line 2
        self._editor.append("a\n")  # Line 3
        self._editor.append("QScintilla\n")  # Line 4
        self._editor.append("test\n")  # Line 5
        self._editor.append("program\n")  # Line 6
        self._editor.append("to\n")  # Line 7
        self._editor.append("illustrate\n")  # Line 8
        self._editor.append("some\n")  # Line 9
        self._editor.append("basic\n")  # Line 10
        self._editor.append("functions.")  # Line 11
        self._editor.setLexer(None)
        self._editor.setUtf8(True)  # Set encoding to UTF-8
        self._editor.setFont(self._myFont)

        # ! Add editor to layout !
        self._lyt.addWidget(self._editor)

        self._editor.setWrapMode(QsciScintilla.WrapMode.WrapWord)
        self._editor.setCaretForegroundColor(get_theme().cyan)

        self._editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self._editor.setMarginWidth(0, "0000")
        self._editor.setMarginsForegroundColor(QtGui.QColor("#ff888888"))

        self._editor.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self._editor.setMarginWidth(1, "00000")

        sym_0 = QtGui.QImage(f"icons:{'greenLight2'}.png").scaled(QtCore.QSize(16, 16))
        sym_1 = QtGui.QImage(f"icons:{'red_light'}.png").scaled(QtCore.QSize(16, 16))
        sym_2 = QtGui.QImage(f"icons:{'go_to_1'}.png").scaled(QtCore.QSize(16, 16))
        sym_3 = QtGui.QImage(f"icons:{'go_to_2'}.png").scaled(QtCore.QSize(16, 16))

        self._editor.markerDefine(sym_0, 0)
        self._editor.markerDefine(sym_1, 1)
        self._editor.markerDefine(sym_2, 2)
        self._editor.markerDefine(sym_3, 3)

        self._editor.setMarginMarkerMask(1, 0b1111)

        self._editor.setMarginSensitivity(1, True)
        self._editor.marginClicked.connect(self.add_break_point)

    def add_break_point(self, margin_nr: int, line_nr: int, state: QtCore.Qt.Modifier):
        if margin_nr == 1:
            markers = format(self._editor.markersAtLine(line_nr), '05b')[::-1]
            if markers[Symbols.RedDot] == '0':
                self._editor.markerAdd(line_nr, Symbols.RedDot)
            else:
                self._editor.markerDelete(line_nr, Symbols.RedDot)

    def _btn_action(self):
        print("Hello World!")


if __name__ == '__main__':
    app = mkQApp('QScintilla')
    myGUI = CustomMainWindow()
    myGUI.show()
    sys.exit(app.exec_())

