import pytest

from pymodaq_gui.qt_utils import mkQApp

from pymodaq.utils.managers.overshoot.overshooter import Overshooter


@pytest.fixture
def dashboard():
    from pymodaq.dashboard import create_load_dashboard
    mkQApp('overshooter_test')
    shared_ui, dashboard = create_load_dashboard(show_dashboard=False)
    yield dashboard
    shared_ui.quit_fun()  # quits the dashboard too, as its Quit action
    for widget in (shared_ui.parent, dashboard.tree):
        widget.close()
        widget.deleteLater()


def test_experiment_applied_is_handled_once(dashboard, monkeypatch):
    """CustomExt connects do_things_after_experiment_set to the experiment manager: Overshooter must not do it again"""
    calls = []
    monkeypatch.setattr(Overshooter, 'do_things_after_experiment_set',
                        lambda self, experiment_name, *args, **kwargs: calls.append((id(self), experiment_name)))
    overshooter = Overshooter(dashboard)  # in addition to the one of the dashboard

    dashboard.experiment_manager.applied_entry.emit('an_experiment')

    assert [call for call in calls if call[0] == id(overshooter)] == [(id(overshooter), 'an_experiment')]
    overshooter.quit_fun()
