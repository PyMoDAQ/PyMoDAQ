.. _extensions:

Dashboard Extensions
====================

The DashBoard module can load extensions to perform dedicated tasks, such as automated data acquisition.

.. _extensions_closing:

Closing an extension
--------------------

An extension can be started from the Dashboard, from the command line (``dashboard -x EXPERIMENT -e EXTENSION``) or
from a script: in all cases the Dashboard knows it. Closing an extension closes only that extension and shows the Dashboard
again, unless the extension refuses to quit (for instance because an acquisition is running). Closing the Dashboard closes
all its extensions, and stays open if one of them refuses.

To close everything at once when an extension is closed, set ``extension_close_all = true`` in the ``[extensions]``
section of the *pymodaq* configuration file (see :ref:`configfile`). The default is ``false``. Closing an extension then
closes the Dashboard and all the other extensions, with the same refusal rule: nothing is closed if one extension
cannot quit.

.. code-block:: toml

    [extensions]
    extension_close_all = false  # if true, closing an extension will close the DashBoard and all the other extensions

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   /extensions_folder/daq_scan/daq_scan
   /extensions_folder/daq_logger
   /extensions_folder/pid_module
   /extensions_folder/bayesian
   /extensions_folder/adaptive
   /extensions_folder/ramping
   /extensions_folder/data_mixer
   /extensions_folder/sequencer
   /extensions_folder/console
