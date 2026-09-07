# extending the h5_manager from pymodaq_gui

from typing import TYPE_CHECKING

from pymodaq_gui.managers.h5manager import H5Manager
from pymodaq.utils.h5modules.module_saving import ModuleSaver

if TYPE_CHECKING:
    from pymodaq.utils.custom_ext import CustomExt


class H5ManagerExt(H5Manager):

    def __init__(self, app: 'CustomExt'):
        super().__init__(app)

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
        self._module_and_data_saver.h5saver = self.h5saver
