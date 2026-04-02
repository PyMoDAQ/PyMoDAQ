from pymodaq.dashboard import DashBoard
from pymodaq_gui.managers.manager_base import ManagerBase


class ExtensionManager(ManagerBase) :

    def __init__(self, dashboard: 'DashBoard' = None):
        entry_type = 'extension'
        entry_extension = '.xml'
        # ext: Exten
        super.__init__(dashboard=dashboard)


