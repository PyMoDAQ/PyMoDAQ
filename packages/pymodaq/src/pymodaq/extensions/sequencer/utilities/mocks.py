from pymodaq.utils.managers.modules import ModulesManager


class DAQ_Viewer:
    def __init__(self, title: str):
        self.title = title


class DAQ_Move:
    def __init__(self, title: str):
        self.title = title

class DashBoard:
    def __init__(self, title: str,
                 actuators: list[DAQ_Move],
                 detectors: list[DAQ_Viewer],):
        self.title = title

        self.modules_manager = ModulesManager(actuators=actuators, detectors=detectors)