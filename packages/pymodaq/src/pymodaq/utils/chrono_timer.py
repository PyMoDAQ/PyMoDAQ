import time
from datetime import timedelta
import sys

from qtpy import QtGui, QtWidgets
from qtpy.QtCore import Qt, QObject, QTimer


from pymodaq_gui.utils.dock import DockArea, Dock


class PushButtonShortcut(QtWidgets.QPushButton):

    def __init__(self, *args, shortcut=None, shortcut_widget=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.shortcut = None
        if shortcut_widget is None:
            shortcut_widget = self
        if shortcut is not None:
            self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), shortcut_widget)
            self.shortcut.activated.connect(self.click_button)

    def click_button(self):
        self.click()


class ChronoTimer(QObject):

    def __init__(self, parent, duration=None):
        """

        :param parent:
        :param Nteams:
        :param duration: (dict) containing optional keys : days, minutes, seconds, hours, weeks, milliseconds, microseconds
        """
        super().__init__()
        self.area = parent
        if duration is None:
            self.type = 'chrono'
            self.duration = timedelta()
        else:
            self.type = 'timer'
            self.duration = timedelta(**duration)  # seconds
        self.displayed_time = 0  # in seconds
        self.started = False
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.display_time)

        self.setup_ui()

    def setup_ui(self):

        self.dock_chrono_timer = Dock(self.type.capitalize())
        self.area.addDock(self.dock_chrono_timer)
        self.dock_chrono_timer.float()

        widget_chrono_timer = QtWidgets.QWidget()
        self.dock_chrono_timer.addWidget(widget_chrono_timer)

        self.layout_lcd = QtWidgets.QVBoxLayout()
        widget_chrono_timer.setLayout(self.layout_lcd)

        self.dock_chrono_timer.setAutoFillBackground(True)
        palette = self.dock_chrono_timer.palette()
        palette.setColor(palette.Window, QtGui.QColor(0, 0, 0))
        self.dock_chrono_timer.setPalette(palette)

        self.time_lcd = QtWidgets.QLCDNumber(8)
        self.set_lcd_color(self.time_lcd, 'red')
        self.layout_lcd.addWidget(self.time_lcd)

        hours, minutes, seconds = self.get_times(self.duration)

        self.time_lcd.display(
            '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds))

        self.dock_controls = Dock('Chrono/Timer Controls')
        self.area.addDock(self.dock_controls)
        self.dock_controls.setOrientation('vertical', True)
        self.dock_controls.setMaximumHeight(150)

        self.widget_controls = QtWidgets.QWidget()
        self.controls_layout = QtWidgets.QVBoxLayout()
        self.widget_controls.setLayout(self.controls_layout)

        hor_layout = QtWidgets.QHBoxLayout()
        hor_widget = QtWidgets.QWidget()
        hor_widget.setLayout(hor_layout)

        self.controls_layout.addWidget(hor_widget)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("icons:run2.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
        self.start_pb = PushButtonShortcut(icon, 'Start',
                                           shortcut='Home', shortcut_widget=self.area)
        self.start_pb.clicked.connect(self.start)
        self.start_pb.setToolTip('home ("début") key shorcut')

        hor_layout.addWidget(self.start_pb)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("icons:pause.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
        self.pause_pb = PushButtonShortcut(icon, 'Pause',
                                           shortcut='Ctrl+p', shortcut_widget=self.area)
        self.pause_pb.setCheckable(True)
        self.pause_pb.setToolTip("Ctrl+p key shortcut")
        self.pause_pb.clicked.connect(self.pause)
        hor_layout.addWidget(self.pause_pb)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("icons:Refresh2.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
        self.reset_pb = PushButtonShortcut(icon, 'Reset',
                                           shortcut='F5', shortcut_widget=self.area)
        self.reset_pb.setToolTip('F5 key shortcut')
        self.reset_pb.clicked.connect(self.reset)
        hor_layout.addWidget(self.reset_pb)

        self.dock_controls.addWidget(self.widget_controls)

    def get_times(self, duration):
        seconds = int(duration.total_seconds() % 60)
        total_minutes = duration.total_seconds() // 60
        minutes = int(total_minutes % 60)
        hours = int(total_minutes // 60)

        return hours, minutes, seconds

    def get_elapsed_time(self):
        return time.perf_counter() - self.ini_time

    def display_time(self):
        elapsed_time = self.get_elapsed_time()
        if self.type == 'timer':
            display_timedelta = self.duration - timedelta(seconds=elapsed_time)
        else:
            display_timedelta = self.duration + timedelta(seconds=elapsed_time)

        self.displayed_time = display_timedelta.total_seconds()
        if display_timedelta.total_seconds() <= 0:
            self.reset()
            return
        else:
            hours, minutes, seconds = self.get_times(display_timedelta)

            self.time_lcd.display(
                '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds))
            QtWidgets.QApplication.processEvents()

    def start(self):
        self.ini_time = time.perf_counter()
        self.timer.start()
        self.started = True
        self.start_pb.setEnabled(False)

    def pause(self):
        if self.pause_pb.isChecked():
            self.started = False
            self.timer.stop()
            self.paused_time = time.perf_counter()
        else:
            elapsed_pause_time = time.perf_counter() - self.paused_time
            self.ini_time += elapsed_pause_time
            self.timer.start()
            self.started = True

    def reset(self):
        if self.pause_pb.isChecked():
            self.pause_pb.setChecked(False)
            QtWidgets.QApplication.processEvents()
        self.timer.stop()
        self.start_pb.setEnabled(True)
        self.started = False
        hours, minutes, seconds = self.get_times(self.duration)
        self.time_lcd.display(
            '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds))

    def set_lcd_color(self, lcd, color):
        palette = lcd.palette()
        # lcd.setPalette(QtGui.QPalette(Qt.red))
        if hasattr(Qt, color):
            palette.setBrush(palette.WindowText, getattr(Qt, color))
            palette.setColor(palette.Window, QtGui.QColor(0, 0, 0))
        lcd.setPalette(palette)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    form = QtWidgets.QWidget()
    win = QtWidgets.QMainWindow()
    win.setVisible(False)
    area = DockArea()
    win.setCentralWidget(area)
    win.setWindowTitle('Chrono Timer')

    # prog = ChronoTimer(area, dict(hours=1, minutes=0, seconds=0))
    prog = ChronoTimer(area)
    win.show()
    sys.exit(app.exec_())
