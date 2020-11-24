from PyQt5 import QtWidgets
import sys
import os

import pymodaq.daq_utils.parameter.ioxml
from pyqtgraph.parametertree import Parameter, ParameterTree

from pymodaq.daq_utils.gui_utils import select_file

# check if overshoot_configurations directory exists on the drive
from pymodaq.daq_utils.daq_utils import get_set_roi_path

roi_path = get_set_roi_path()


class ROISaver:
    def __init__(self, msgbox=False, det_modules=[]):

        self.roi_presets = None
        self.detector_modules = det_modules

        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Overshoot Manager?")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == modify_button:
                path = select_file(start_path=roi_path, save=False, ext='xml')
                if path != '':
                    self.set_file_roi(str(path))
            else:  # cancel
                pass

    def set_file_roi(self, filename, show=True):
        """

        """

        children = pymodaq.daq_utils.parameter.ioxml.XML_file_to_parameter(filename)
        self.roi_presets = Parameter.create(title='roi', name='rois', type='group', children=children)

        det_children = [child for child in self.roi_presets.children() if 'det' in child.opts['name']]
        det_names = [child.child(('detname')).value() for child in self.roi_presets.children() if
                     'det' in child.opts['name']]
        det_module_names = [det.title for det in self.detector_modules]
        for ind_det, det_roi in enumerate(det_children):
            det_module = self.detector_modules[det_module_names.index(det_names[ind_det])]
            viewer_children = [child for child in det_roi.children() if 'viewer' in child.opts['name']]
            for ind_viewer, viewer in enumerate(det_module.ui.viewers):
                rois_params = [child for child in viewer_children[ind_viewer].children() if 'ROI' in child.opts['name']]
                if hasattr(viewer, 'roi_manager'):
                    # if hasattr(viewer.ui, 'roiBtn'):
                    #     viewer.ui.roiBtn.click()
                    # elif hasattr(viewer.ui, 'Do_math_pb'):
                    #     viewer.ui.Do_math_pb.click()

                    viewer.roi_manager.load_ROI(params=rois_params)
                    QtWidgets.QApplication.processEvents()

        if show:
            self.show_rois()

    def set_new_roi(self, file=None):
        if file is None:
            file = 'roi_default'

        self.roi_presets = Parameter.create(name='roi_settings', type='group', children=[
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': file}, ])

        for ind_det, det in enumerate(self.detector_modules):
            det_param = Parameter.create(name=f'det_{ind_det:03d}', type='group', children=[
                {'title': 'Det Name:', 'name': 'detname', 'type': 'str', 'value': det.title}, ])

            for ind_viewer, viewer in enumerate(det.ui.viewers):
                viewer_param = Parameter.create(name=f'viewer_{ind_viewer:03d}', type='group', children=[
                    {'title': 'Viewer:', 'name': 'viewername', 'type': 'str',
                     'value': det.ui.viewer_docks[ind_viewer].name()}, ])

                if hasattr(viewer, 'roi_manager'):
                    viewer_param.addChild({'title': 'ROI type:', 'name': 'roi_type', 'type': 'str',
                                           'value': viewer.roi_manager.settings.child(('ROIs')).roi_type})
                    viewer_param.addChildren(viewer.roi_manager.settings.child(('ROIs')).children())
                det_param.addChild(viewer_param)
            self.roi_presets.addChild(det_param)

        pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_file(self.roi_presets, os.path.join(roi_path, file))
        self.show_rois()

    def show_rois(self):
        """

        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        tree.setParameters(self.roi_presets, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this manager')
        res = dialog.exec()

        if res == dialog.Accepted:
            # save managers parameters in a xml file
            # start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            # start = os.path.join("..",'daq_scan')
            pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_file(self.roi_presets, os.path.join(roi_path,
                                                                                                   self.roi_presets.child(
                                                                                                       (
                                                                                                           'filename')).value()))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    prog = ROISaver(True, [])

    sys.exit(app.exec_())
