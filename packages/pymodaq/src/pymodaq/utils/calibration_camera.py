import os
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Qt, QObject

from pymodaq_utils.config import get_set_local_dir

from pymodaq_gui.parameter import ioxml
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq_gui.h5modules.browsing import browse_data

from pymodaq.post_treatment.daq_measurement.daq_measurement_main import DAQ_Measurement


local_path = get_set_local_dir()
calib_path = os.path.join(local_path, 'camera_calibrations')
if not os.path.isdir(calib_path):
    os.makedirs(calib_path)


class CalibrationCamera(QtWidgets.QWidget, QObject):
    def __init__(self, parent=None, h5filepath=None):

        
        super(CalibrationCamera, self).__init__()
        if parent is None:
            parent = QtWidgets.QWidget()

        self.parent = parent
        self.setupUI()
        self.fname = None
        self.node_path = None

        self.viewer2D.get_action('histo').trigger()
        self.viewer2D.get_action('roi').trigger()

        self.meas_module.ui.measurement_type_combo.setCurrentText('Sinus')
        QtWidgets.QApplication.processEvents()
        self.meas_module.ui.measure_subtype_combo.setCurrentText('dx')

    def setupUI(self):

        params = [{'title': 'Load data:', 'name': 'Load data', 'type': 'action', },
                  {'title': 'Set Measurement:', 'name': 'Do measurement', 'type': 'action', },
                  {'title': 'Calib from:', 'name': 'calib_from', 'type': 'list', 'limits': ['Hlineout', 'Vlineout'], },
                  {'title': 'X axis:', 'name': 'xaxis', 'type': 'group', 'children': [
                      {'title': 'Units:', 'name': 'xunits', 'type': 'str', 'value': "µm"},
                      {'title': 'dx (units):', 'name': 'dx_units', 'type': 'float', 'value': 0, },
                      {'title': 'dx from fit:', 'name': 'dx_fit', 'type': 'float', 'value': 0, },
                      {'title': 'x Offset:', 'name': 'xoffset', 'type': 'float', 'value': 0., 'readonly': False}, ]},
                  {'title': 'Y axis:', 'name': 'yaxis', 'type': 'group', 'children': [
                      {'title': 'Units:', 'name': 'yunits', 'type': 'str', 'value': "µm"},
                      {'title': 'dy (units):', 'name': 'dy_units', 'type': 'float', 'value': 0., },
                      {'title': 'dy from fit:', 'name': 'dy_fit', 'type': 'float', 'value': 0., },
                      {'title': 'y Offset:', 'name': 'yoffset', 'type': 'float', 'value': 0., 'readonly': False}, ]},
                  {'title': 'Save calib:', 'name': 'Save data', 'type': 'action', },
                  {'title': 'Data Saved:', 'name': 'data_saved', 'type': 'led', 'value': False, 'readonly': True},
                  {'title': 'File path:', 'name': 'filepath', 'type': 'text', 'value': '', 'readonly': True},
                  ]

        layout = QtWidgets.QHBoxLayout()
        self.parent.setLayout(layout)

        splitter_H = QtWidgets.QSplitter(Qt.Horizontal)

        splitter = QtWidgets.QSplitter(Qt.Vertical)

        widg2D = QtWidgets.QWidget()
        self.viewer2D = Viewer2D(widg2D)
        self.viewer2D.title = 'calib'
        self.viewer2D.get_action('autolevels').trigger()

        splitter.addWidget(widg2D)

        widg_meas = QtWidgets.QWidget()
        self.meas_module = DAQ_Measurement(widg_meas)
        splitter.addWidget(widg_meas)

        self.settings_tree = ParameterTree()
        self.settings = Parameter.create(name='Settings', type='group', children=params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        self.settings.child(('Load data')).sigActivated.connect(self.load_data)
        self.settings.child(('Save data')).sigActivated.connect(self.save_data)
        self.settings.child(('Do measurement')).sigActivated.connect(self.update_data_meas)

        splitter_H.addWidget(self.settings_tree)
        splitter_H.addWidget(splitter)

        layout.addWidget(splitter_H)

    def update_data_meas(self):
        if self.settings.child(('calib_from')).value() == 'Hlineout':
            xdata = self.viewer2D.data_to_export['data1D']['calib_Hlineout_ROI_00']['x_axis']
            ydata = self.viewer2D.data_to_export['data1D']['calib_Hlineout_ROI_00']['data']
        else:
            xdata = self.viewer2D.data_to_export['data1D']['calib_Vlineout_ROI_00']['x_axis']
            ydata = self.viewer2D.data_to_export['data1D']['calib_Vlineout_ROI_00']['data']

        self.meas_module.update_data(xdata, ydata)

    def load_data(self):
        self.data, self.fname, self.node_path = browse_data(ret_all=True)
        if self.data is not None:
            self.settings.child('xaxis', 'xoffset').setValue((-self.data.shape[1] / 2))
            self.settings.child('yaxis', 'yoffset').setValue((-self.data.shape[0] / 2))
            self.viewer2D.setImage(self.data)
            self.viewer2D.get_action('histo').trigger()
            self.viewer2D.get_action('roi').trigger()
            QtWidgets.QApplication.processEvents()

    def save_data(self):
        params = [{'title': 'Axis options:', 'name': 'axes', 'type': 'group', 'visible': False, 'expanded': False,
                   'children': [
                       {'title': 'X axis:', 'name': 'xaxis', 'type': 'group', 'children': [
                           {'title': 'Label:', 'name': 'xlabel', 'type': 'str', 'value': "x axis"},
                           {'title': 'Units:', 'name': 'xunits', 'type': 'str',
                            'value': self.settings.child('xaxis', 'xunits').value()},
                           {'title': 'Offset:', 'name': 'xoffset', 'type': 'float', 'default': 0.,
                            'value': self.settings.child('xaxis', 'xoffset').value()},

                           {'title': 'Scaling', 'name': 'xscaling', 'type': 'float', 'default': 1.,
                            'value': self.settings.child('xaxis', 'dx_units').value() / self.settings.child('xaxis',
                                                                                                            'dx_fit').value()},
                       ]},
                       {'title': 'Y axis:', 'name': 'yaxis', 'type': 'group', 'children': [
                           {'title': 'Label:', 'name': 'ylabel', 'type': 'str', 'value': "x axis"},
                           {'title': 'Units:', 'name': 'yunits', 'type': 'str',
                            'value': self.settings.child('yaxis', 'yunits').value()},
                           {'title': 'Offset:', 'name': 'yoffset', 'type': 'float', 'default': 0.,
                            'value': self.settings.child('yaxis', 'yoffset').value()},
                           {'title': 'Scaling', 'name': 'yscaling', 'type': 'float', 'default': 1.,
                            'value': self.settings.child('yaxis', 'dy_units').value() / self.settings.child('yaxis',
                                                                                                            'dy_fit').value()},
                       ]},
                   ]}, ]
        param_obj = Parameter.create(name='Axes_Settings', type='group', children=params)
        ioxml.parameter_to_xml_file(param_obj,
                                    os.path.join(calib_path, os.path.split(self.fname)[1]))
        self.settings.child(('data_saved')).setValue(True)
        self.settings.child(('filepath')).setValue(os.path.join(calib_path, os.path.split(self.fname)[1]))

    def parameter_tree_changed(self, param, changes):
        """

        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'calib_from':
                    self.update_data_meas()
                elif param.name() == 'dx_fit':
                    scaling = self.settings.child('xaxis', 'dx_units').value() / param.value()
                    self.settings.child('xaxis', 'xoffset').setValue(-scaling * self.data.shape[1] / 2)
                elif param.name() == 'dy_fit':
                    scaling = self.settings.child('yaxis', 'dy_units').value() / param.value()
                    self.settings.child('yaxis', 'yoffset').setValue(-scaling * self.data.shape[0] / 2)

                self.settings.child(('data_saved')).setValue(False)

            elif change == 'parent':
                pass


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QWidget()
    prog = CalibrationCamera(win)
    win.show()
    sys.exit(app.exec_())
