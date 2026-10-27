import datetime
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
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from easydict import EasyDict as edict
from pymodaq_gui.parameter import Parameter
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

    def test_activation_of_an_action_reaches_the_plugin(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.detector = SelectedModule(DAQTypesEnum['DAQ1D'], 'Mock')
        hw_settings = prog.settings.child(DETECTOR_SETTINGS_KEY)
        hw_settings.addChild({'title': 'Go', 'name': 'go', 'type': 'action_led', 'value': 'false'})
        sent = []
        prog._update_settings_signal.connect(sent.append)

        hw_settings.child('go').activate()

        assert [(item['path'], item['change']) for item in sent] == [([DETECTOR_SETTINGS_KEY, 'go'], 'activated')]

    def test_activation_received_by_the_plugin_emits_sigactivated(self):
        class Plugin(DAQ_Viewer_base):
            def ini_detector(self, controller=None):
                return '', True

            def close(self):
                pass

        plugin = Plugin()
        plugin.settings.addChild({'title': 'Go', 'name': 'go', 'type': 'action_led', 'value': 'false'})
        activated = []
        plugin.settings.child('go').sigActivated.connect(activated.append)
        gui_param = Parameter.create(name='go', type='action_led', value='false')

        plugin.update_settings(edict(path=[DETECTOR_SETTINGS_KEY, 'go'], param=gui_param, change='activated'))

        assert len(activated) == 1

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


class TestLiveAveraging:
    def test_errors_of_the_live_averaged_data(self, ini_daq_viewer_ui):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        n_acquisitions = 6
        rng = np.random.default_rng(7)
        acquisitions = rng.normal(loc=1., scale=0.2, size=(n_acquisitions, 9))
        prog.settings.child('main_settings', 'show_data').setValue(False)
        prog.settings.child('main_settings', 'live_averaging').setValue(True)

        for acquisition in acquisitions:
            prog.show_data(DataToExport('acquisition', data=[DataRaw('raw', data=[acquisition])]))

        live_averaged = prog.current_data[0]
        assert live_averaged.n_averaged == n_acquisitions
        assert live_averaged.data[0] == approx(acquisitions.mean(axis=0))
        assert live_averaged.errors[0] == approx(acquisitions.std(axis=0, ddof=1) / np.sqrt(n_acquisitions))

    def test_errors_replaced_message(self):
        data = DataToExport('acquisition', data=[DataRaw('raw', data=[np.array([1., 2.])])])
        assert daqvm.errors_replaced_message(data, 'live averaging') is None
        data[0].errors = [np.array([0.1, 0.1])]
        assert 'live averaging' in daqvm.errors_replaced_message(data, 'live averaging')


def test_continuous_save_toolbar_group_structure(ini_daq_viewer_ui):
    """The toolbar exposes one grouped button for continuous saving: the (now hidden)
    settings-tree entries are replaced by a single toolbar entry point."""
    prog, qtbot, dockarea = ini_daq_viewer_ui
    ui = prog.ui

    for name in ('do_save', 'new_file', 'show_file', 'custom_name'):
        assert prog.settings.child('saver_settings', name).opts['visible'] is False

    button = next(child for child in ui.toolbar.findChildren(QtWidgets.QToolButton)
                  if child.defaultAction() is ui.get_action('continuous_save'))
    assert [a.text() for a in button.menu().actions()] == [
        'Save Current Data', 'New file', 'Browse file']

    # Same icons H5Manager uses for these exact actions everywhere else in the app
    assert not ui.get_action('new_file').icon().isNull()
    assert not ui.get_action('browse_file').icon().isNull()


def test_background_toolbar_group_structure(ini_daq_viewer_ui):
    """background_snap/background_subtract are now one grouped toolbar button, with
    unchanged short names so existing wiring (DO_BKG/TAKE_BKG) keeps working as-is."""
    prog, qtbot, dockarea = ini_daq_viewer_ui
    ui = prog.ui

    button = next(child for child in ui.toolbar.findChildren(QtWidgets.QToolButton)
                  if child.defaultAction() is ui.get_action('background_subtract'))
    assert [a.text() for a in button.menu().actions()] == ['Snap Background']



def test_save_current_defaults_to_dated_folder_with_prefilled_name(
        ini_daq_viewer_without_ui, tmp_path, monkeypatch):
    """save_current's dialog should default into today's dataset folder (not the bare
    base path), with a timestamped .h5 name already filled in and the extension enforced."""
    prog, qtbot = ini_daq_viewer_without_ui
    prog._data_to_save_export = None

    config['data', 'data_saving', 'h5file', 'save_path'] = str(tmp_path)

    captured = {}

    def fake_select_file(start_path=None, save=True, ext=None, filter=None,
                         force_save_extension=False):
        captured.update(start_path=start_path, filter=filter,
                        force_save_extension=force_save_extension)
        return ''  # simulate the user cancelling, so no actual save/grab is attempted

    monkeypatch.setattr(daqvm, 'select_file', fake_select_file)

    prog.save_current()

    today = datetime.date.today()
    expected_dir = tmp_path / str(today.year) / today.strftime('%Y%m%d')
    assert captured['start_path'].parent == expected_dir
    assert captured['start_path'].name.startswith('Data_')
    assert captured['start_path'].suffix == '.h5'
    assert captured['filter'] == 'HDF5 files (*.h5)'
    assert captured['force_save_extension'] is True
    assert expected_dir.is_dir()

    # Cancelling must not leave save-in-progress state set
    assert prog._do_save_data is False


def test_save_current_during_continuous_save(ini_daq_viewer_without_ui, tmp_path):
    """A one-shot save must not replace the continuous-saving module saver: it used to,
    so continuous saving then kept appending into the closed one-shot file."""
    from pymodaq_data.data import DataRaw
    from pymodaq.utils.data import DataToExport
    from pymodaq.utils.h5modules.module_saving import DetectorTimeSaver

    prog, qtbot = ini_daq_viewer_without_ui
    dte = DataToExport('data', data=[DataRaw('ch0', data=[np.array([1., 2., 3.])])])

    prog.setup_continuous_saving(init=True)
    prog._h5saver_continuous.settings.child('base_path').setValue(str(tmp_path))
    prog.settings.child('saver_settings', 'do_save').setValue(True)
    prog.append_data(dte)

    prog._save_data(tmp_path.joinpath('one_shot.h5'), dte)
    assert tmp_path.joinpath('one_shot.h5').is_file()

    assert isinstance(prog.module_and_data_saver, DetectorTimeSaver)
    assert prog.module_and_data_saver.h5saver is prog._h5saver_continuous
    prog.append_data(dte)
    assert prog.settings['saver_settings', 'N_saved'] == 2

    prog.settings.child('saver_settings', 'do_save').setValue(False)
