# Bayesian Optimisation

The Bayesian Optimisation extension finds the actuators positions that optimize a value measured by your detectors, by
building a probabilistic model of the experiment from the points already tested. It needs far fewer measurements than
a grid or random search with the DAQ_Scan.

## Typical workflow

1. Define an experiment in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) and apply it with the Dashboard toolbar of the
   extension.
2. In the **Settings** panel, select the actuators and detectors that take part in the optimization and set the search
   bounds of each actuator.
3. Select a **model**, which converts the data of the detectors into the single value to optimize. The default model
   only needs you to choose one 0D data as the target.
4. Press the first **Init** button to initialize the model, set the algorithm parameters (acquisition function, number of
   iterations, stopping criteria...), then press the second **Init** button to initialize the algorithm.
5. Press **Run**: the best target and its actuators values (*Observable*) and all the tested points (*Probed Data*) are
   updated at each iteration. **Pause**, **Restart** and **Stop** act on the algorithm.
6. Once paused (or converged), press **Go to best** to move the actuators to the best positions found.

## Good to know

- The algorithm stops after the given number of iterations, or earlier with the *Predict* or *Best* stopping criteria.
- To initialize again, press the Init button twice (changing some parameters in between if needed).
- With the **Goto** action active, a double click in the *Probed Data* viewer moves the actuators to the clicked position.
- To optimize a combination of data (a ratio of two regions of interest...), write your own model or produce a 0D data
  with the [DataMixer](https://pymodaq.cnrs.fr/en/latest/extensions_folder/data_mixer.html).

<!-- end of intro -->

## Full documentation

See the [Bayesian Optimisation documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/bayesian.html) for the settings and the models.
