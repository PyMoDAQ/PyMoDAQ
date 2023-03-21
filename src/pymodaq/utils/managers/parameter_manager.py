from pathlib import Path
from typing import List, Union, Dict
from pymodaq.utils.parameter import Parameter, ParameterTree, ioxml


class ParameterManager:
    """Class dealing with Parameter and ParameterTree

    Attributes
    ----------
    params: list of dicts
        Defining the Parameter tree like structure
    settings_name: str
        The particular name to give to the object parent Parameter (self.settings)
    settings: Parameter
        The higher level (parent) Parameter
    settings_tree: ParameterTree
    """
    settings_name = 'custom_settings'
    params = []

    def __init__(self, settings_name: str = None):
        if settings_name is None:
            settings_name = self.settings_name
        # create a settings tree to be shown eventually in a dock
        self.settings_tree: ParameterTree = ParameterTree()
        self.settings_tree.setMinimumWidth(150)
        self.settings_tree.setMinimumHeight(300)

        self.settings: Parameter = Parameter.create(name=settings_name, type='group', children=self.params)  # create a Parameter
        # object containing the settings defined in the preamble

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, settings: Union[Parameter, List[Dict[str, str]], Path]):
        settings = self.create_parameter(settings)
        self._settings = settings
        self.settings_tree.setParameters(self._settings, showTop=False)  # load the tree with this parameter object
        self._settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    @staticmethod
    def create_parameter(settings: Union[Parameter, List[Dict[str, str]], Path]) -> Parameter:

        if isinstance(settings, List):
            _settings = Parameter.create(title='Settings', name='settings', type='group', children=settings)
        elif isinstance(settings, Path) or isinstance(settings, str):
            settings = Path(settings)
            _settings = Parameter.create(title='Settings', name='settings',
                                        type='group', children=ioxml.XML_file_to_parameter(str(settings)))
        elif isinstance(settings, Parameter):
            _settings = Parameter.create(title='Settings', name=settings.name(), type='group')
            _settings.restoreState(settings.saveState())
        else:
            raise TypeError(f'Cannot create Parameter object from {settings}')
        return _settings

    def parameter_tree_changed(self, param, changes):
        for param, change, data in changes:
            path = self._settings.childPath(param)
            if change == 'childAdded':
                self.child_added(param, data)

            elif change == 'value':
                self.value_changed(param)

            elif change == 'parent':
                self.param_deleted(param)

    def value_changed(self, param):
        """Non-mandatory method  to be subclassed for actions to perform (methods to call) when one of the param's
        value in self._settings is changed

        Parameters
        ----------
        param: Parameter
            the parameter whose value just changed

        Examples
        --------
        >>> if param.name() == 'do_something':
        >>>     if param.value():
        >>>         print('Do something')
        >>>         self.settings.child('main_settings', 'something_done').setValue(False)
        """
        ...

    def child_added(self, param, data):
        """Non-mandatory method to be subclassed for actions to perform when a param  has been added in self.settings

        Parameters
        ----------
        param: Parameter
            the parameter where child will be added
        data: Parameter
            the child parameter
        """
        pass

    def param_deleted(self, param):
        """Non-mandatory method to be subclassed for actions to perform when one of the param in self.settings has been deleted

        Parameters
        ----------
        param: Parameter
            the parameter that has been deleted
        """
        pass