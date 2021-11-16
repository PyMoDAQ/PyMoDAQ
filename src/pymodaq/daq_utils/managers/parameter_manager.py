from pyqtgraph.parametertree import Parameter, ParameterTree


class ParameterManager:
    params = []

    def __init__(self):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)  # create a Parameter
        # object containing the settings defined in the preamble
        # # create a settings tree to be shown eventually in a dock
        self.settings_tree = ParameterTree()
        self.settings_tree.setParameters(self.settings, showTop=False)  # load the tree with this parameter object
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    def parameter_tree_changed(self, param, changes):
        for param, change, data in changes:
            if change == 'childAdded':
                self.child_added(param)

            elif change == 'value':
                self.value_changed(param)

            elif change == 'parent':
                self.param_deleted(param)

    def value_changed(self, param):
        """Non mandatory method  to be subclassed for actions to perform when one of the param's value in self.settings is changed

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        """
        pass

    def child_added(self, param):
        """Non mandatory method to be subclassed for actions to perform when a param  has been added in self.settings

        Parameters
        ----------
        param: (Parameter) the parameter that has been deleted
        """
        pass

    def param_deleted(self, param):
        """Non mandatory method to be subclassed for actions to perform when one of the param in self.settings has been deleted

        Parameters
        ----------
        param: (Parameter) the parameter that has been deleted
        """
        pass