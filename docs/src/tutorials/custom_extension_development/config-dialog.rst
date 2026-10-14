Work in Progress Configuring Devices and Data
=============================================

Until here, the names of the employed devices were hard coded into the extension. In principle, this is fine as long as there aren't any choices to be made and the extension runs in the way of a custom application as it was the case so far in this tutorial. However, this does not use the full power of the dashboard which potentially gives access to any device hooked up to the computer. This chapter demonstrates how to make use of this funktionality. In a first step we'll build an auto-configure mechanism which chooses the first available and suitable spectrometer device. In a second step we will build a configuration dialog which allows the user to make choices out of lists of suitable devices and data sets.

The idea for probing potential device candidates is as follows: temporarily assign a 1Dim detector found in the dashboard's experiment configuration, perform a single acquisition and analyse the result. If it contains what could be intensity and wavelength data, add it to the list of devices. Similarly, a list of potential shutter devices is built. The auto config mechanism will simpy choose the first entry in both lists.

.. code-block::
   :emphasize-lines: 4-

    def __init__(self, parent: gutils.DockArea, dashboard):
        ...
        self.read_settings(self.qt_settings)
        self.auto_config()
   
The lines with hard coded device names are simply removed.

.. code-block::

     def do_things_after_experiment_set(self, experiment_name: str):
        self.modules_manager.detectors_all = \
            self.dashboard.modules_manager.detectors_all
        self.modules_manager.actuators_all = \
            self.dashboard.modules_manager.actuators_all
        # end of procedure

And some new functions are defined.

.. code-block::

    def auto_config(self):
        """Select first existing spectrometer and shutter and probe spectrometer
        for data."""

        self.shutter_name = self.modules_manager.actuators_all[0].title
        self.spectrometer_name = self.modules_manager.detectors_all[0].title
        self.probe_detector = \
            self.modules_manager.get_mod_from_name(self.spectrometer_name,
                                                   ModuleType.Detector)
        self.probe_detector.grab_done_signal.connect(self.take_auto_probe_data)
        self.probe_detector.snap()

    def take_auto_probe_data(self, data: DataToExport):
        print("got auto config probe")
        intensity_name, wavelength_name, axis_data = self.take_probe_data(data)
        self.set_config(self.spectrometer_name, self.shutter_name,
                        intensity_name, axis_data)

    def take_probe_data(self, data: DataToExport):
        """Analyze probe data from spectrometer.
        If there is more than one 1dim data item, the names of both are returned
        as list for the user to chose or the first one to pick in auto config.
        If there is only one, the axis data from that one is taken. In case that
        the data doesn't contain an axis, a generic axis containing pixel nubers
        is generated.
        """
        self.probe_detector.grab_done_signal.disconnect()
        data1D = data.get_data_from_dim('Data1D')
        if len(data1D) > 1:
            intensity_names = [d.name for d in data1D]
            wavelength_names = [d.name for d in data1D]
        elif len(data1D) == 1:
            intensity_names = [data1D[0].name]
            if data1D[0].n_axes:
                wavelength_names = [f'--{data1D[0].name} axis--']
                axis_data = data1D[0].axes[0].data
            else:
                wavelength_names = [f'--{data1D[0].name} pixels--']
                l = len(data1D[0].data)
                axis_data = np.linspace(0, l - 1, l)
        else:
            raise RuntimeError("Spectrometer didn't send 1Dim data")

        return intensity_names[0], wavelength_names[0], axis_data

    def set_config(self, spectrometer_name, shutter_name, intensity_name,
                   axis_data):
        if hasattr(self, 'detector'):
            self.detector.grab_done_signal.disconnect()
        self.detector = \
            self.modules_manager.get_mod_from_name(spectrometer_name,
                                                   ModuleType.Detector)
        self.detector.grab_done_signal.connect(self.take_data)

        if hasattr(self, 'dark_shutter'):
            self.dark_shutter.move_done_signal.disconnect()
        self.dark_shutter = \
            self.modules_manager.get_mod_from_name(shutter_name,
                                                   ModuleType.Actuator)
        self.dark_shutter.move_done_signal.connect(self.shutter_ready)

        self.x_axis = \
            Axis(label='Wavelength', units='nm', data=axis_data, index=0)
        print("done")
