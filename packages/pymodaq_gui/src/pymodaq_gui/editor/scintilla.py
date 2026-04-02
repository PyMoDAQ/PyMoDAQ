from enum import IntEnum
import sys

from pymodaq.utils.gui_utils.widgets.window import make_window
from pymodaq_gui.qt_utils import mkQApp

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.Qsci import QsciScintilla, QsciLexerPython

from qt_themes import get_theme

from pymodaq_gui.utils.custom_app import CustomApp


class Symbols(IntEnum):
    GreenDot = 0
    RedDot = 1
    GreenArrow = 2
    RedArrow = 3


class Editor(CustomApp):
    def __init__(self, parent: QtWidgets.QMainWindow):
        super().__init__(parent)
        self._editor: QsciScintilla = None

        self.setup_ui()

    def do_things_after_ui_setup(self):
        self.setup_editor()

    def setup_docks(self):

        # 2. Create frame and layout
        self._frm = QtWidgets.QFrame()
        self.mainwindow.setCentralWidget(self._frm)
        self._lyt = QtWidgets.QVBoxLayout()
        self._frm.setLayout(self._lyt)

    def setup_editor(self):
        # ! Make instance of QsciScintilla class!
        self._editor = QsciScintilla()
        self._lexer = QsciLexerPython(self._editor)
        self._editor.setLexer(self._lexer)
        self._editor.setUtf8(True)  # Set encoding to UTF-8
        # self._editor.setFont(self._myFont)

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

    def setup_actions(self):
        pass

    def connect_things(self):
        pass



if __name__ == '__main__':
    app = mkQApp('QScintilla')
    from pymodaq.utils.shared_ui import SharedUI

    win, area = make_window(area=False, title="QScintilla Example")

    editor = Editor(win)

    shared_ui = SharedUI(win)

    shared_ui.affect_application(editor)

    shared_ui.show()

    sys.exit(app.exec_())

