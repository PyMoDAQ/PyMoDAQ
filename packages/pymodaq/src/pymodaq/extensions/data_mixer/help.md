# DataMixer

The DataMixer post-processes the data of the detectors of the Dashboard, even of unrelated ones, and can emulate a new
virtual detector producing the processed data, usable by any other extension (the DAQ_Scan for instance).

## Typical workflow

1. Define an experiment with the detectors to use in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) and apply it with the
   Dashboard toolbar of the extension.
2. Select a **model** (the post-processing to apply) and **initialize** it. Its own settings are then displayed. Two models
   are shipped: the *Equation* model, to write mathematical expressions between data, and a *Gaussian fit* model.
3. Select the detectors whose data you want to use and press **Get Data** to list the available data (raw or from
   regions of interest).
4. With the Equation model, copy the data names between curly brackets in the **Edit Formula** area (one operation per
   line, numpy functions are supported) and press the snap button to plot the results.
5. Press the **+** button to create a virtual DAQ_Viewer in the Dashboard grabbing the processed data.

## Good to know

- The processed data are displayed in dedicated viewers, one for each line of the formula.
- The virtual detector looks like any other detector for the extensions, so processed data can be plotted live during a scan.
- For another kind of processing, write your own model (a python class), see the *Example of code for a Model* section
  of the documentation.

<!-- end of intro -->

## Full documentation

See the [DataMixer documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/data_mixer.html) for the models and the way to write your own.
