"""Continuous saving, shared by DAQ_Viewer and DAQ_Move through ParameterControlModule"""
import numpy as np
import pytest

from pymodaq.control_modules import utils as control_module_utils
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.thread_commands import UiToMainSaving
from pymodaq.utils.data import DataToExport
from pymodaq_data.data import DataRaw
from pymodaq_utils.utils import ThreadCommand


@pytest.fixture(params=[DAQ_Viewer, DAQ_Move], ids=['DAQ_Viewer', 'DAQ_Move'])
def module_saving_in_tmp_path(request, qtbot, tmp_path, monkeypatch):
    """A control module (no UI) whose continuous-save H5Saver writes into tmp_path.

    Yields (module, init_file_calls), the latter recording each init_file call so
    tests can count files opened even when two land on the same second-resolution name.
    """
    init_file_calls = []
    real_h5saver_class = control_module_utils.H5Saver

    def h5saver_in_tmp_path(*args, **kwargs):
        h5saver = real_h5saver_class(*args, **kwargs)
        h5saver.settings.child('base_path').setValue(str(tmp_path))
        real_init_file = h5saver.init_file

        def counting_init_file(*a, **k):
            init_file_calls.append(k)
            return real_init_file(*a, **k)

        h5saver.init_file = counting_init_file
        return h5saver

    monkeypatch.setattr(control_module_utils, 'H5Saver', h5saver_in_tmp_path)
    module = request.param()
    yield module, init_file_calls
    if module._h5saver_continuous is not None:
        module._h5saver_continuous.close_file()
    module.quit_fun()


def make_dte():
    return DataToExport('data', data=[DataRaw('ch0', data=[np.array([1., 2., 3.])])])


def test_one_file_per_enable(module_saving_in_tmp_path, tmp_path):
    """Each enable opens exactly one file and disabling none, across several cycles.

    Previously DAQ_Viewer made a second, stray file on the first enable (the generic
    scan-typed self.h5saver created as a side effect) and DAQ_Move made one more file per
    re-enable (_init_continuous_save reconnected each time), plus one on each disable."""
    module, init_file_calls = module_saving_in_tmp_path
    do_save = module.settings.child('saver_settings', 'do_save')

    for cycle in range(3):
        do_save.setValue(True)
        assert len(init_file_calls) == cycle + 1
        assert module._h5saver_continuous.isopen()
        do_save.setValue(False)
        assert len(init_file_calls) == cycle + 1
        assert not module._h5saver_continuous.isopen()

    assert module._h5saver is None, "the generic scan-typed h5saver must never be created"
    assert module._h5saver_continuous.settings['save_type'] == module._continuous_save_type
    created = list(tmp_path.rglob('*.h5'))
    assert created and all(path.name.startswith('Data_') for path in created)


def test_append_data(module_saving_in_tmp_path):
    module, _ = module_saving_in_tmp_path
    module.settings.child('saver_settings', 'do_save').setValue(True)
    for _ in range(3):
        module.append_data(make_dte())
    assert module.settings['saver_settings', 'N_saved'] == 3

    h5saver = module._h5saver_continuous
    assert h5saver.get_node_from_title(h5saver.raw_group, module.title) is not None


def test_toolbar_commands(module_saving_in_tmp_path):
    """process_ui_cmds handles the Continuous Save toolbar group commands"""
    module, init_file_calls = module_saving_in_tmp_path

    # New file / Browse file are safe no-ops while continuous saving is off
    module.process_ui_cmds(ThreadCommand(UiToMainSaving.SAVE_NEW))
    module.process_ui_cmds(ThreadCommand(UiToMainSaving.OPEN))
    assert init_file_calls == []

    module.process_ui_cmds(ThreadCommand(UiToMainSaving.DO_SAVE, True))
    assert module.settings['saver_settings', 'do_save'] is True
    assert module._h5saver_continuous.isopen()

    module.settings.child('saver_settings', 'N_saved').setValue(3)
    module.process_ui_cmds(ThreadCommand(UiToMainSaving.SAVE_NEW))
    assert len(init_file_calls) == 2
    assert module._h5saver_continuous.isopen()
    assert module.settings['saver_settings', 'N_saved'] == 0

    module.process_ui_cmds(ThreadCommand(UiToMainSaving.DO_SAVE, False))
    assert module.settings['saver_settings', 'do_save'] is False
    assert not module._h5saver_continuous.isopen()


def test_current_file_shown(module_saving_in_tmp_path, tmp_path):
    """The file being written is shown in the 'h5file:' settings entry while saving"""
    module, _ = module_saving_in_tmp_path
    current_h5_file = module.settings.child('saver_settings', 'current_h5_file')
    assert current_h5_file.opts.get('visible', True)
    assert current_h5_file.value() == ''

    module.settings.child('saver_settings', 'do_save').setValue(True)
    assert current_h5_file.value().startswith(str(tmp_path))

    module.settings.child('saver_settings', 'do_save').setValue(False)
    assert current_h5_file.value() == ''


def test_redundant_saver_settings_hidden(module_saving_in_tmp_path):
    module, _ = module_saving_in_tmp_path
    for name in module._hidden_saver_params:
        assert module.settings.child('saver_settings', name).opts['visible'] is False


def test_swmr_options_visible_and_forwarded(module_saving_in_tmp_path):
    """swmr_options stay hidden on the saver_settings display clone unless shown
    explicitly, and edits made there must reach the H5Saver actually saving, including
    flush_interval being applied when a file is opened."""
    module, _ = module_saving_in_tmp_path
    swmr_options = module.settings.child('saver_settings', 'backend', 'swmr_options')
    assert swmr_options.opts['visible'] is True

    module.setup_continuous_saving(init=True)
    swmr_options.child('enable_swmr').setValue(True)
    swmr_options.child('flush_interval').setValue(2)
    h5saver = module._h5saver_continuous
    assert h5saver.settings['backend', 'swmr_options', 'enable_swmr'] is True
    assert h5saver.settings['backend', 'swmr_options', 'flush_interval'] == 2

    module.settings.child('saver_settings', 'do_save').setValue(True)
    assert h5saver._flush_interval == 2


def test_swmr_active_on_each_new_file(module_saving_in_tmp_path):
    """SWMR turns on once data is written, including in a file started with New file:
    the module saver keeps per-file SWMR state, so it must not be carried over."""
    module, _ = module_saving_in_tmp_path
    module.setup_continuous_saving(init=True)
    module.settings.child('saver_settings', 'backend', 'swmr_options', 'enable_swmr').setValue(True)
    module.settings.child('saver_settings', 'do_save').setValue(True)
    h5saver = module._h5saver_continuous

    module.append_data(make_dte())
    assert h5saver.is_swmr_active

    module.new_continuous_save_file()
    assert not h5saver.is_swmr_active
    module.append_data(make_dte())
    assert h5saver.is_swmr_active
