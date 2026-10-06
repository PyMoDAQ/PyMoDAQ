# Sequencer

The Sequencer builds an experiment *procedure* graphically, without code: a tree of elements (apply a state, move
actuators, grab detectors, wait, repeat, scan, choose where to go next...) executed one after the other on the actuators
and detectors of the Dashboard.

## Typical workflow

1. Define an experiment in the [Dashboard](https://pymodaq.cnrs.fr/en/latest/modules/DashBoard.html) and apply it with the Dashboard toolbar of the
   extension (some elements also need a state).
2. Build the sequence: add elements with the **Add Element** button at the end of each level of the tree, and
   double click on an element to configure it. Repeat and Scanner elements are containers executing their children.
   Drag and drop reorders the elements and each one has an **Execute** button to test it alone.
3. Optionally add other sequences (**Add Sequence**) that the main one calls with a *Sequence* element.
4. Check **Log** to save all the produced data in a h5 file (select it with the file toolbar), then press **Start**.
   The status bar shows the running element, **Pause** and **Stop** act at any time.
5. Save the sequences in a `.seq` file with **Save Sequence** to reuse them later.

## Good to know

- If some elements are not valid (module not available in the Dashboard, no experiment applied, missing Choice target...)
  the sequence does not start and the errors are written in the log.
- A paused sequence executes again, from its start, the element that was running when it is resumed.
- The `.seq` files are human readable and can be written or modified by hand.
- The logged data can be explored with the [H5Browser](https://pymodaq.cnrs.fr/en/latest/data_management/h5browser.html).

<!-- end of intro -->

## Full documentation

See the [Sequencer documentation](https://pymodaq.cnrs.fr/en/latest/extensions_folder/sequencer.html) for the description of each element and of the
`.seq` file format.
