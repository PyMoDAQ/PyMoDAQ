"""The manager inside a real Dashboard (with the mock instruments of the default experiment)"""
import pytest
import qt_themes

from pymodaq.dashboard import create_load_dashboard
from pymodaq_utils.config import GlobalConfig

from pymodaq_ontology import manager as manager_module
from pymodaq_ontology.manager import OntologyManager
from pymodaq_ontology.terms import ACTUATOR, DETECTOR

FIELD = 'http://example.org/moke#MagneticField'


@pytest.fixture
def dashboard(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(manager_module, 'get_set_config_dir', lambda name, user=False: tmp_path / name)
    (tmp_path / 'ontology').mkdir()
    config = GlobalConfig()
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0], style=config('gui', 'style', 'style')[0])
    shared_ui, dashboard = create_load_dashboard()
    qtbot.addWidget(shared_ui.mainwindow)
    shared_ui.show()
    yield dashboard
    shared_ui.quit_fun()


def test_the_dashboard_creates_the_manager_from_the_entry_point(dashboard):
    assert isinstance(dashboard.extra_managers['ontology'], OntologyManager)


def test_channels_of_the_loaded_instruments_and_probe(qtbot, dashboard, source):
    manager: OntologyManager = dashboard.extra_managers['ontology']
    manager.set_source(source)

    dashboard.experiment_manager.execute_entry()
    qtbot.waitUntil(lambda: dashboard.get_menu('manager_ontology').isEnabled(), timeout=60000)  # experiment loaded

    actuators = [c for c in manager.channels if c.kind == ACTUATOR]
    assert [c.module for c in actuators] == [a.title for a in dashboard.modules_manager.actuators_all]

    manager.probe()
    detectors = [c for c in manager.channels if c.kind == DETECTOR]
    assert detectors
    assert {c.module for c in detectors} <= {d.title for d in dashboard.modules_manager.detectors_all}

    if actuators:
        manager.assign(actuators[0].key, FIELD)
        assert manager.entry_filepath.is_file()
