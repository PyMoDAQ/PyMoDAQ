# Adaptive Scanning

Adaptive scanning samples the parameter space intelligently: instead of a predetermined grid, the next actuators
positions are chosen from the data already measured, finely where the signal varies quickly and roughly where it is
constant. It is based on the python-adaptive package.

## Typical workflow

1. Define an experiment in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) and apply it with the Dashboard toolbar of the
   extension.
2. In the **Settings** panel, select the actuators (their number sets the type of loss function: 1D, 2D or ND) and the
   detectors, and set the bounds of each actuator.
3. Select a **model** and the **observable**, the 0D data used by the algorithm to learn (raw from a detector, from a
   region of interest or computed with the [DataMixer](https://pymodaq.cnrs.fr/en/latest/extensions_folder/data_mixer.html)).
4. Initialize the model, set the loss function and the stopping criteria, then initialize the algorithm.
5. Press **Run** to start the sampling, the sampled points and the data are plotted live. **Pause**, **Restart** and
   **Stop** act on the algorithm.

## Good to know

- The interface and the workflow are the same as the [Bayesian Optimisation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/bayesian.html) extension.
- The parameter space is probed in an irregular order, a parameter can jump a lot between two steps: it can be a problem
  for an actuator with hysteresis or backlash.
- The observable should not be too noisy as the algorithm learns from its variations, and the gain is small if it
  varies very slowly.
- The algorithm stops after the given number of iterations, or earlier with a stopping criterion.

<!-- end of intro -->

## Full documentation

See the [Adaptive Scanning documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/adaptive.html).
