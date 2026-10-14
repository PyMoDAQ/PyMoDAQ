Interlude I: Using the state manager
====================================

This section covers the use of the state manager. It can be used to trigger actions on actuators and to change parameter values on plugins. We'll use it here to close and open the shutter for background acquisition. Since we want to keep the already working extension in place, let's create a new file :file:`state_absorption_extension.py` and fill it with the following

.. code-block::

    from pymodaq_utils.logger import set_logger, get_module_name
    from pymodaq_utils.config import Config, ConfigError
    from pymodaq.utils.managers.modules.utils import ModuleType
    from pymodaq.utils.data import DataFromPlugins, Axis
    from pymodaq_plugins_tutorial_extension.utils import Config as PluginConfig
    from pymodaq_plugins_tutorial_extension.extensions.absorption_extension \
        import AbsorptionExtension

    logger = set_logger(get_module_name(__file__))

    main_config = Config()
    plugin_config = PluginConfig()

    EXTENSION_NAME = 'StateManagerAbsorption'
    CLASS_NAME = 'StateManagerAbsorptionExtension'

    class StateManagerAbsorptionExtension(AbsorptionExtension):

        def start_background(self):
            self.data_valid = False
            self.n_average = self.settings['back_averaging']
            self.n_samples = 0
            self.adjust_actions()
            self.state_manager.entry = 'background'
            self.state_manager.execute_entry()
            if self.state_manager.entry_applied:
                self.acquisition_mode = 'background'
                self.detector.grab()
                self.data_valid = True

        def take_background(self, mean, error):
            self.background = mean
            self.error_background = error
            self.have_background = True
            dfp = DataFromPlugins(name='Spectrograph',
                                  data=[self.background, self.error_background],
                                  dim='Data1D', labels=['background', 'error'],
                                  axes=[self.x_axis])
            self.spectrum_viewer.show_data(dfp)
            self.background_viewer.show_data(dfp)
            self.state_manager.entry = 'spectrum'
            self.state_manager.execute_entry()
            if self.state_manager.entry_applied:
                self.acquisition_mode = 'idle'
                self.adjust_actions()

The code of :code:`take_background` is slightly longer than the version it overloads. However, the method :code:`shutter_ready` will not be used any more because :code:`StateManager.execute_entry()` only returns once the actions asked for in the state configuration have all completed.

Launch the dashboard, load the :file:`absorption` experiment and the :file:`StateManagerAbsorption` extension. The state manager permits now to create sets of configuration operations. Click on the New item on top of the right panel and enter :file:`background` as name. Upon a right click into the configuration area below select :file:`Add Special Configuration -> Actuator value`. Choose the dark shutter here and set the actuator value to zero. Activate the configuration once to get it saved (that's a bug-like trap!). Repeat the same for a state :file:`spectrum` which should set the dark shutter value to one. Note that the names given to the configuration have to literally match the corresponding names in the code above. 

In terms of functionality, the program has not changed. Using the state manager instead of steering the actuators directly just changes the way things are 'wired' together. However, used together with a sequencer, this can be turned into a quite powerful tool to work on complex sequences.

:code:`-> branch state-manager`
