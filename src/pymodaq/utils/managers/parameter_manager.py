from pyqtgraph.parametertree import Parameter, ParameterTree


class ParameterManager:
    """Class dealing with Parameter and ParameterTree

    Attributes
    ----------
    params: list of dicts
        Defining the Parameter tree like structure
    settings: Parameter
        The higher level (parent) Parameter
    settings_tree: ParameterTree
    """

    params = []

    def __init__(self, settings_name='settings'):
        self.settings: Parameter = Parameter.create(name=settings_name, type='group', children=self.params)  # create a Parameter
        # object containing the settings defined in the preamble
        # # create a settings tree to be shown eventually in a dock
        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(150)
        self.settings_tree.setMinimumHeight(300)
        self.settings_tree.setParameters(self.settings, showTop=False)  # load the tree with this parameter object
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    def parameter_tree_changed(self, param, changes):
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                self.child_added(param, data)

            elif change == 'value':
                self.value_changed(param)

            elif change == 'parent':
                self.param_deleted(param)

    def value_changed(self, param):
        """Non mandatory method  to be subclassed for actions to perform (methods to call) when one of the param's
        value in self.settings is changed

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

    def child_added(self, param, data):
        """Non mandatory method to be subclassed for actions to perform when a param  has been added in self.settings

        Parameters
        ----------
        param: Parameter
            the parameter where child will be added
        data: Parameter
            the child parameter
        """
        pass

    def param_deleted(self, param):
        """Non mandatory method to be subclassed for actions to perform when one of the param in self.settings has been deleted

        Parameters
        ----------
        param: Parameter
            the parameter that has been deleted
        """
        pass