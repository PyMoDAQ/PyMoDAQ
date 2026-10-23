import os
from unittest.mock import MagicMock
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx
import qt_themes
from pymodaq_data.data import DataToExport, DataRaw
from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
from pymodaq.utils.gui_utils.loader_utils import create_load_daq_viewer
from pymodaq_gui.utils.dock import DockArea

from pymodaq.control_modules import daq_viewer as daqvm
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.viewer_utility_classes import HW_SETTINGS_KEY as DETECTOR_SETTINGS_KEY
from pymodaq.control_modules.utils import ControlModule
from pymodaq.control_modules.instruments import DET_TYPES, get_viewer_plugins
from pymodaq.control_modules.enums import DAQTypesEnum
from pymodaq.utils.conftests import qtbotskip, main_modules_skip
from pymodaq.utils.config import GlobalConfig

from pymodaq_gui.parameter import utils as putils


config = GlobalConfig()

config_viewer = config['pymodaq', 'viewer']
config_viewer['viewer_in_thread'] = True


@fixture
def init_qt(qtbot):
    return qtbot


@fixture
def ini_daq_viewer_without_ui(init_qt):
    qtbot = init_qt
    prog = daqvm.DAQ_Viewer()
    yield prog, qtbot
    prog.quit_fun()
    QtWidgets.QApplication.processEvents()


@fixture
def ini_daq_viewer_ui(init_qt):
    qtbot = init_qt
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    shared_ui, prog = create_load_daq_viewer()
    shared_ui.show()

    qtbot.addWidget(shared_ui.mainwindow)


    yield prog, qtbot, shared_ui.mainwindow
    shared_ui.quit_fun()  # quits prog too, as the Quit action of the standalone module
    QtWidgets.QApplication.processEvents()


class TestMethods:
    def test_overriden(self):
        assert ControlModule.stop_grab != DAQ_Viewer.stop_grab
        assert ControlModule.grab != DAQ_Viewer.grab
        assert ControlModule.quit_fun != DAQ_Viewer.quit_fun
        assert ControlModule.init_hardware != DAQ_Viewer.init_hardware


class TestWithoutUI:
    def test_instanciation(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui

        assert prog.viewers is None
        assert prog.viewer_docks is None


    @pytest.mark.parametrize("det", [det_dict['name'] for det_dict in DET_TYPES['DAQ0D']])
    def test_detector_changed(self, ini_daq_viewer_without_ui, det):
        prog, qtbot = ini_daq_viewer_without_ui
        daq_type = 'DAQ0D'
        prog.detector = SelectedModule(DAQTypesEnum[daq_type], det)
        det_params, _class = get_viewer_plugins(prog.detector.daq_type.name, prog.detector.module_name)
        assert putils.iter_children(prog.settings.child(DETECTOR_SETTINGS_KEY), []) == \
            putils.iter_children(det_params, [])

    def test_main_settings_recall_detector(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.detector = SelectedModule(DAQTypesEnum['DAQ1D'], 'Mock')
        assert prog.settings['main_settings', 'DAQ_type'] == 'DAQ1D'
        assert prog.settings['main_settings', 'detector_type'] == 'Mock'

    def test_removed_main_settings(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        main_settings = prog.settings.child('main_settings')
        assert 'overshoot' not in main_settings.names
        assert 'axes' not in main_settings.names


#@pytest.mark.skip
class TestWithUI:

    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_daq_type_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.daq_type = daq_type
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'


    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_detector_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.detector = SelectedModule(DAQTypesEnum[daq_type], 'Mock')
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'


    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_detector_name_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.daq_type = daq_type
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.detector = 'Mock'
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'

def test_viewers_roi_select_and_crosshair_forwarding(ini_daq_viewer_ui):
    """ROIselect and crosshair of each viewer are forwarded to the plugin with the right viewer index"""
    from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
    from pymodaq_gui.plotting.items.roi import RoiInfo, RectROI
    from pymodaq.control_modules.thread_commands import ControlToHardwareViewer

    prog, qtbot, win = ini_daq_viewer_ui
    # the parents are kept alive and deleted explicitly at the end: temporaries are deleted in an arbitrary order
    # and may leave items of the viewers (crosshair lines) in a scene without their ViewBox
    forms = [QtWidgets.QWidget() for _ in range(3)]
    viewers = [Viewer2D(form) for form in forms]
    commands = []
    prog.command_hardware.connect(commands.append)

    prog.viewers = viewers[:2]
    roi_info = RoiInfo((1., 2.), (3., 4.), roi_class=RectROI)
    viewers[1].roi_select_signal.emit(roi_info)
    viewers[0].crosshair_dragged.emit(5., 6.)

    roi_cmds = [cmd for cmd in commands if cmd.command == ControlToHardwareViewer.ROI_SELECT]
    cross_cmds = [cmd for cmd in commands if cmd.command == ControlToHardwareViewer.CROSSHAIR]
    assert roi_cmds[-1].attribute == dict(roi_info=roi_info, ind_viewer=1)
    assert cross_cmds[-1].attribute == dict(crosshair_info=(5., 6.), ind_viewer=0)

    # after a change of viewers, the old ones are no more forwarded
    prog.viewers = viewers[2:]
    commands.clear()
    viewers[1].roi_select_signal.emit(roi_info)
    viewers[0].crosshair_dragged.emit(5., 6.)
    assert len(commands) == 0
    viewers[2].crosshair_dragged.emit(7., 8.)
    assert commands[-1].attribute == dict(crosshair_info=(7., 8.), ind_viewer=0)

    for form in forms:
        form.close()
        form.deleteLater()
    QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


class TestAveragingStatistics:
    def test_standard_error_of_the_mean(self):
        n_spectra = 25
        rng = np.random.default_rng(1)
        spectra = rng.normal(loc=3., scale=0.5, size=(n_spectra, 40))
        statistics = daqvm.AveragingStatistics()
        for spectrum in spectra:
            statistics.add(DataToExport('acquisition', data=[DataRaw('raw', data=[spectrum])]))

        expected_error = np.std(spectra, axis=0, ddof=1) / np.sqrt(n_spectra)
        assert statistics.n_data == n_spectra
        assert statistics.standard_errors()[0][0] == approx(expected_error)

    def test_errors_are_only_set_from_two_acquisitions(self):
        statistics = daqvm.AveragingStatistics()
        data = DataToExport('acquisition', data=[DataRaw('raw', data=[np.array([1., 2.])])])
        statistics.add(data)
        statistics.set_errors(data)
        assert data[0].errors is None
        with pytest.raises(ValueError):
            statistics.standard_errors()

        statistics.add(DataToExport('acquisition', data=[DataRaw('raw', data=[np.array([3., 2.])])]))
        statistics.set_errors(data)
        assert data[0].errors[0] == approx(np.array([1., 0.]))

    def test_reset(self):
        statistics = daqvm.AveragingStatistics()
        statistics.add(DataToExport('acquisition', data=[DataRaw('raw', data=[np.array([1.])])]))
        statistics.reset()
        assert statistics.n_data == 0


class TestSoftwareAveraging:
    def test_errors_of_the_averaged_data(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        n_average = 10
        prog.detector = SelectedModule(DAQTypesEnum['DAQ1D'], 'Mock')
        with qtbot.waitSignal(prog.init_signal, timeout=10000):
            prog.init_hardware(True)
        prog.settings.child('main_settings', 'Naverage').setValue(n_average)

        with qtbot.waitSignal(prog.grab_done_signal, timeout=20000) as blocker:
            prog.snap()

        averaged_data = blocker.args[0]
        assert averaged_data[0].n_averaged == n_average
        assert averaged_data[0].errors is not None
        assert averaged_data[0].errors[0].shape == averaged_data[0].data[0].shape
        assert np.all(averaged_data[0].errors[0] >= 0)

    def test_no_errors_without_averaging(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.detector = SelectedModule(DAQTypesEnum['DAQ1D'], 'Mock')
        with qtbot.waitSignal(prog.init_signal, timeout=10000):
            prog.init_hardware(True)

        with qtbot.waitSignal(prog.grab_done_signal, timeout=20000) as blocker:
            prog.snap()

        assert blocker.args[0][0].errors is None


class TestErrorsReplacedWarning:
    @pytest.mark.parametrize('with_errors', [True, False])
    def test_warning_only_if_the_plugin_provides_errors(self, with_errors):
        worker = MagicMock()
        worker.Naverage = 5
        errors = [np.array([0.1, 0.1])] if with_errors else None
        data = DataToExport('acquisition', data=[DataRaw('raw', data=[np.array([1., 2.])], errors=errors)])

        daqvm.DetectorWorker._warn_if_errors_replaced(worker, data)

        assert worker.logger.warning.called == with_errors
        assert worker.status_sig.emit.called == with_errors
