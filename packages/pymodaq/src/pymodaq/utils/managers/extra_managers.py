"""Managers installed by other packages, discovered through the entry point group ``pymodaq.managers``.

A package declares, in its ``pyproject.toml``::

    [project.entry-points."pymodaq.managers"]
    ontology = "pymodaq_ontology.manager:OntologyManager"

The entry point value must be a subclass of
:class:`~pymodaq_gui.managers.manager_base.ManagerBase` instantiated by the Dashboard as
``manager_class(dashboard=dashboard)``. The entry point name identifies the manager.

At the first discovery of a manager, the preference ``managers/<name>/show_toolbar`` (true) is created in the
PyMoDAQ configuration file: the user can set it to false to stop the Dashboard from adding the toolbar of the manager
(its menu is always added).
"""
from pymodaq_utils.utils import get_entrypoints
from pymodaq_utils.config import GlobalConfig, ConfigError
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.managers.manager_base import ManagerBase

logger = set_logger(get_module_name(__file__))

GROUP = 'pymodaq.managers'


def get_extra_managers() -> dict[str, type[ManagerBase]]:
    """Get the manager classes declared by installed packages in the ``pymodaq.managers`` entry point group

    A manager that fails to import or that is not a ManagerBase subclass is logged and skipped,
    so that a broken package cannot prevent the Dashboard from starting.

    Returns
    -------
    dict
        manager name (the entry point name) -> manager class
    """
    managers = {}
    for entry_point in get_entrypoints(group=GROUP):
        try:
            manager_class = entry_point.load()
        except Exception as e:
            logger.exception(f'Could not load the manager {entry_point.name} ({entry_point.value}): {e}')
            continue
        if not (isinstance(manager_class, type) and issubclass(manager_class, ManagerBase)):
            logger.error(f'The manager {entry_point.name} ({entry_point.value}) is not a ManagerBase subclass')
            continue
        managers[entry_point.name] = manager_class
    return managers


def show_toolbar_in_dashboard(name: str) -> bool:
    """Whether the toolbar of the manager ``name`` should be added to the Dashboard (its menu is always added)

    The preference ``managers/<name>/show_toolbar`` of the PyMoDAQ configuration is created (true) at the first call
    for a manager.
    """
    config = GlobalConfig()
    try:
        return bool(config('pymodaq', 'managers', name, 'show_toolbar'))
    except (ConfigError, KeyError):
        config['pymodaq', 'managers', name, 'show_toolbar'] = True
        return True
