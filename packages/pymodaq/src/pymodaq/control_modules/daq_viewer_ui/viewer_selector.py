from dataclasses import dataclass, field

from qtpy import QtCore
from pymodaq.control_modules.instruments import DAQTypesEnum
from ..control_module_selector import ModuleSelector

@dataclass
class SelectedModule:
    daq_type: DAQTypesEnum = field(default_factory=lambda: DAQTypesEnum.DAQ0D)
    module_name: str = 'Mock'

    def __post_init__(self):
        if not isinstance(self.daq_type, DAQTypesEnum):
            if isinstance(self.daq_type, str):
                self.daq_type = DAQTypesEnum[self.daq_type]

    def __repr__(self):
        return f'{self.daq_type.name}/{self.module_name}'

class ViewerSelector(ModuleSelector):

    module_changed = QtCore.Signal(SelectedModule)

    def __init__(self, *args, **kwargs):
        super().__init__(str(SelectedModule()), *args, **kwargs)

        self._selected_module: SelectedModule = SelectedModule()

    @property
    def selected_module(self):
        return self._selected_module

    @selected_module.setter
    def selected_module(self, value: SelectedModule):
        self._selected_module = value
        self.add_widget.setText(str(value))
        self.module_changed.emit(value)

    def _add_menu_item_selected(self, name, path_tuple):
        """Called when a menu item is selected from the nested add menu

        To be subclassed for particular signal emission

        """
        # Call the parameter's addNew method with the selected type
        self.add_widget.setText('/'.join((path_tuple[0], path_tuple[-1])))
        self.add_widget.adjustSize()
        self.selected_module = SelectedModule(DAQTypesEnum[path_tuple[0]], path_tuple[-1], )
        self.module_changed.emit(self.selected_module)