Work in Progress Fluorescence measurements
==========================================

We add now a continuous wave laser which excites the sample. It passes through the cuvette at a right angle with respect to the path of the whitelight of the lamp to minimise scattering. However, during this experiment, the latter will remain switched off. Such arrangement can be used to measure a fluorescence spectrum. The laser shall be controlled by another binary DAQ_move like the shutter for the dark signal. Technically we implement it in fact as just another shutter.

.. image:: sketch-emission.png


.. code-block::
   :emphasize-lines: 4,5,8,12,16,17,20-30,36,37,39-

    class MockSpectrograph:
        ...
        light_level: float = 500
        fluorescence_level: float = 50
        excitation_fluctuation: float = 5
        ...
	absorption: float = 0.3
	shutter_names = ['dark', 'excitation']
        ...
        def __post_init__(self):
            self.with_sample = True
            self.fluorescence = False
        ...
        def calculate_base_data(self):
	    ...
	    self.luminescence = \
		np.exp(-((self.pixels - n_pix / 2) / (n_pix / 8))**2)
        ...
        def simulate_emission(self, shutter_open):
            data = np.random.normal(loc=self.dark_level * self.integration_time,
                                    scale=self.readout_noise, size=self.n_pixels)

            if shutter_open:
                light = self.luminescence * self.fluorescence_level \
                    * np.random.normal(1, self.excitation_fluctuation / 100) \
                    * self.integration_time * self.pe_per_lsb
                data += light
            max_adc = (1 << self.adc_bits) - 1
            data = np.where(data < max_adc, np.floor(data), max_adc)
            return data, time.time()

    ...
    if __name__ == '__main__':
        ...
        plt.plot(spectrograph.wavelengths, spectrograph.absorption)
        plt.plot(spectrograph.wavelengths, spectrograph.luminescence)
        plt.legend(['light spectrum', 'absorption', 'emission'])
        ...
        data, time_stamp = \
            spectrograph.simulate_emission(shutter_open=True)
        plt.plot(data)
        plt.title('Luminescence')
        plt.show()

The new parameters have to be declare in the plugin as well.

.. code-block::
   :emphasize-lines: 5-10,12-

    class DAQ_1DViewer_MockSpectro(DAQ_Viewer_base):
        ...
        params = comon_parameters+[
        ...
            {'title': 'Fluorescence level [LSB]', 'name': 'fluorescence_level',
             'type': 'float', 'min': 0, 'value': 32e3,
             'tip': 'Signal per second in LSB' },
            {'title': 'Excitation Fluctuation[%]', 'name': 'excitation_fluctuation',
             'type': 'float', 'min': 0, 'value': 5,
             'tip': 'Fluctuation of luminescence signal in %' },
        ...
            {'title': 'Fluorescence:', 'name': 'fluorescence',
             'type': 'bool', 'value': False, 'tip': 'Simulate Fluorescence' },
