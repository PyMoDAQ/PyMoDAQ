
from typing import Union, TYPE_CHECKING

from qtpy import QtCore, QtWidgets

from pymodaq_utils.config import GlobalConfig
from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq_gui.utils import CustomApp, DockArea

from pymodaq.utils.managers.modules.modules_manager import ModulesManager
from pymodaq.utils.dashboard_mixin import DashboardMixin, DashBoardToolbarActions  # noqa: F401
from pymodaq.utils.h5modules.module_saving import ModuleSaver
from pymodaq_utils.utils import ThreadCommand

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

config = GlobalConfig()


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
        super().__init__(parent, **kwargs)

        self.init_dashboard(dashboard, module_manager_class)
        # an experiment already applied (extension opened from the Dashboard) is handled at the end of setup_ui:
        # do_things_after_experiment_set may use the actions and widgets, which do not exist yet
        self.connect_experiment_manager(apply_now=False)

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

    def setup_ui(self):
        """ Set up the UI (see CustomApp), then call do_things_after_experiment_set if an experiment is already
        applied in the dashboard"""
        super().setup_ui()
        if self.dashboard is not None:
            # opening the extension does not change the visibility of the dashboard
            self.apply_current_experiment(show_dashboard=self.dashboard.mainwindow.isVisible())

    def stop(self):
        """ Programmatic method to stop any action in the extension

        To be reimplemented
        """
        raise NotImplementedError

    def quit_fun(self, external_call=False) -> bool:
        """Quit the extension, unless :meth:`_quit_fun` refuses it

        This method should not be reimplemented: reimplement :meth:`_quit_fun` to define what has to be done
        (and checked) before quitting. If it returns True, the quit proceeds (``CustomApp.quit_fun``), otherwise
        nothing is closed and False is returned.

        Parameters
        ----------
        external_call: bool
            Is True when the quit_fun is called from an external object, ie the DashBoard
        """

        if not external_call and config('pymodaq', 'extensions', 'extension_close_all') and self.dashboard is not None:
            return self.dashboard.quit_fun()
        else:
            if self._quit_fun():
                res = super().quit_fun()

                if self.dashboard is not None:
                    self.dashboard.extension_manager.unregister_extension(self)
                    self.show_dashboard(True)  #make sure to show it if it was hidden
                return res
            else:
                return False

    def _quit_fun(self) -> bool:
        """ To be reimplemented in order to properly quit your application

        Return True to let the quit proceed: the base class quit_fun method will then be called. The default
        returns False: an extension that does not reimplement it cannot be quit (see the PMQ338 rule).
        """
        return False

    def get_app_toolbars(self) -> list[QtWidgets.QToolBar]:
        """ Get the main toolbars widget to be eventually added in the main window toolbararea

        Default is the default toolbar. To be reimplemented if needed
        """
        return [self.toolbar]
