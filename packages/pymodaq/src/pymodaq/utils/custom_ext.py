
from typing import Union, TYPE_CHECKING

from qtpy import QtCore, QtWidgets

from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq_gui.utils import CustomApp, DockArea

from pymodaq.utils.managers.modules.modules_manager import ModulesManager
from pymodaq.utils.dashboard_mixin import DashboardMixin, DashBoardToolbarActions  # noqa: F401
from pymodaq.utils.h5modules.module_saving import ModuleSaver
from pymodaq_utils.utils import ThreadCommand

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


class CustomExt(DashboardMixin, CustomApp):
    status_sig = QtCore.Signal(ThreadCommand)
    status_signal = QtCore.Signal(str)  # signal to be used to emit info
    config_changed = QtCore.Signal()  # will be emitted when the user changed anything in the configuration files (emitted from SharedUI)

    icon_name = 'extension' # change this icon name if needed

    def __init__(self,
                 parent: Union[DockArea, QtWidgets.QWidget, QtWidgets.QMainWindow],
                 dashboard: 'DashBoard',
                 module_manager_class=ModulesManager,
                 **kwargs):
        super().__init__(parent, dashboard=dashboard,
                         module_manager_class=module_manager_class, **kwargs)

        self._module_and_data_saver: ModuleSaver = None  # to use only if you want to save data with
        #ordered with groups and with control modules, then call self.module_and_data_saver property
        # a bit complex to use but properly save things from control modules

    @property
    def module_and_data_saver(self):
        """ Complex but Standardized way to save data from the CustomExt and
        especially from the ControlModules"""
        if (self._module_and_data_saver.h5saver is None
                or not self._module_and_data_saver.h5saver.isopen()):
            self._module_and_data_saver.h5saver = self.h5saver
        return self._module_and_data_saver

    @module_and_data_saver.setter
    def module_and_data_saver(self, mod: ModuleSaver):
        self._module_and_data_saver = mod
        if self.h5saver is not None:
            self._module_and_data_saver.h5saver = self.h5saver

    def stop(self):
        """ Programmatic method to stop any action in the extension

        To be reimplemented
        """
        raise NotImplementedError

    def quit_fun(self) -> bool:
        """Method to be subclassed in order to define a custom quit function
        if returned True, one can proceed with other quit mechanisms otherwise do not quit
        """
        if self._quit_fun():
            res = super().quit_fun()

            if self.dashboard is not None:
                self.show_dashboard(True)  #make sure to show it if it was hidden
            return res
        else:
            return False

    def _quit_fun(self) -> bool:
        """ to be reimplemented in order to properly quit your application

        Then the base class quit_fun method will be called

        """
        pass

    def get_app_toolbars(self) -> list[QtWidgets.QToolBar]:
        """ Get the main toolbars widget to be eventually added in the main window toolbararea

        Default is the default toolbar. To be reimplemented if needed
        """
        return [self.toolbar]
