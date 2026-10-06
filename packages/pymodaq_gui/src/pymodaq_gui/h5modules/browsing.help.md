# H5Browser

The H5Browser explores PyMoDAQ h5 files: it displays their tree of groups and nodes, the data they hold and their
metadata (scan settings, settings of the modules at the time of saving...).

## Typical workflow

1. Start the H5Browser with the `h5browser` command and select an h5 file, or give it directly with
   `h5browser --input my_file.h5`.
2. Select a node of the tree: its metadata are displayed.
3. Double click on a data node to plot it in the viewer.
4. Right click on a node for more actions: export the data to another file format, add a comment to the node, plot a
   node or the nodes of a same channel, with or without background subtraction.

## Good to know

- The h5 files written by DAQ_Scan, DAQ_Logger and the other extensions can all be explored with it.
- The data viewer displays data up to 4 dimensions.
- The H5Browser can be associated with the `.h5` files so that double clicking on a file opens it directly.

<!-- end of intro -->

## Full documentation

See the [H5Browser documentation](https://pymodaq.cnrs.fr/en/latest/data_management/h5browser.html).
