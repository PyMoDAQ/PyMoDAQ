"""Managers that need the DashBoard (and its modules manager)."""
from pymodaq_gui.managers.manager_base import ManagerBase

from pymodaq.utils.dashboard_mixin import DashboardMixin


class ManagerWithDashboard(DashboardMixin, ManagerBase):
    """ A ManagerBase working on a DashBoard (given as the ``dashboard`` keyword argument)

    The base :class:`~pymodaq_gui.managers.manager_base.ManagerBase` knows nothing about the
    dashboard (``pymodaq_gui`` cannot import ``pymodaq``), this class adds it with the same mixin
    as the extensions (:class:`~pymodaq.utils.custom_ext.CustomExt`). Entries can only be executed
    if a dashboard has been given.
    """

    def can_execute_entry(self) -> bool:
        return self.dashboard is not None
