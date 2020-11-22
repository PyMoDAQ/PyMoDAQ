import sys
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDateTime, pyqtSignal, QPointF, QObject
import numpy as np
import pyqtgraph as pg
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_basic import ImageWidget
from pymodaq.daq_utils.managers.roi_manager import ROIBrushable

from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

pos = []
colors = []
for ticks in Gradients['thermal']['ticks']:
    pos.append(ticks[0])
    colors.append(ticks[1])
cmap = pg.ColorMap(pos, colors, Gradients['thermal']['mode'])


def setTicksLabels(values):
    strings = []
    for v in values:
        d = QDateTime()
        d = d.fromSecsSinceEpoch(v * 30 * 60)
        vstr = d.toString('HH:mm dd/MM/yy')
        strings.append(vstr)
    return strings


class AxisItemDate(pg.AxisItem):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        if self.logMode:
            return self.logTickStrings(values, scale, spacing)

        places = max(0, np.ceil(-np.log10(spacing * scale)))
        strings = setTicksLabels(values)
        return strings


class GanttROI(ROIBrushable):
    index_signal = pyqtSignal(int)

    def __init__(self, task='No task', index=0, start=0, stop=1, brush=None, *args, **kwargs):
        super().__init__(pos=[start, index], size=[stop - start, 1], brush=brush, pen=brush, snapSize=1, scaleSnap=True,
                         translateSnap=True, *args, **kwargs)  # )
        self.h1 = self.addScaleHandle([1, 0.5], [0, 0.5])
        self.h2 = self.addScaleHandle([0, 0.5], [1, 0.5])

        self.task = task
        self.setToolTip(task)
        self.index = index
        self.sigRegionChangeFinished.connect(self.emit_index_signal)
        self.sigRegionChangeFinished.connect(self.update_tooltip)
        self.update_tooltip()

    def update_tooltip(self):
        self.h2.setToolTip(setTicksLabels([self.pos()[0]])[0])
        self.h1.setToolTip(setTicksLabels([self.pos()[0] + self.size()[0]])[0])

    def center(self):
        return QPointF(self.pos().x() + self.size().x() / 2, self.pos().y() + self.size().y() / 2)

    def emit_index_signal(self):
        self.index_signal.emit(self.index)


class GanttTask(QObject):
    alpha = 255

    def __init__(self, task_dict):
        super().__init__()

        self.task_dict = task_dict  # taskdict=dict(name=  ,idnumber=  ,task_type=int(0 to 12), time_start=, time_end=)
        qc = cmap.mapToQColor(task_dict['task_type'] / 12)
        qc.setAlpha(self.alpha)
        self.roi_item = GanttROI(task_dict['name'], task_dict['idnumber'], start=task_dict['time_start'],
                                 stop=task_dict['time_end'], brush=qc)
        self.roi_item.sigRegionChangeFinished.connect(self.show_hide_move_text())
        self.roi_item.setZValue(-1000)
        self.text_item = pg.TextItem(task_dict['name'])
        self.text_item.setPos(task_dict['time_start'], task_dict['idnumber'])
        self.roi_item.setZValue(-500)

    def show_hide_move_text(self):
        pass


class GanttChart(QObject):
    def __init__(self):
        super().__init__()
        self.setupUI()
        self.tasks = []

    def setupUI(self):
        axis = AxisItemDate(orientation='bottom')
        axis_top = AxisItemDate(orientation='top')

        self.widget = ImageWidget(axisItems=dict(bottom=axis, top=axis_top))
        self.widget.plotitem.showAxis('top')
        self.widget.plotitem.vb.setAspectLocked(lock=False)
        self.widget.view.invertY(True)
        self.widget.view.setLimits(yMin=0)

    def add_task(self, task_dict):
        self.tasks.append(GanttTask(task_dict))
        self.widget.plotItem.addItem(self.tasks[-1].roi_item)
        self.widget.plotItem.addItem(self.tasks[-1].text_item)


# # create GUI
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    gchart = GanttChart()
    gchart.widget.show()

    gchart.add_task(
        dict(name='This is task 1, the best of all the tasks!yeeah baby', idnumber=1, task_type=1, time_start=5,
             time_end=7))

    sys.exit(app.exec_())
