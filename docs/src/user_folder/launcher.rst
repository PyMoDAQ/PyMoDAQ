Launcher
=========

This module is a home page for PyMoDAQ, it will:

* Launch empty:
    * Dashboard
    * DAQ Viewer
    * DAQ Move
    * H5Browser
* Restore a dashboard with experiment and state
* Load extensions
* See informations about the latest experiments:
    * Date and hour
    * Which experiment and state used
    * Actuators and Detectors used for selected experiment
* Navigate in the configurations history by navigation arrows or by date
* Change experiment and state to restore on the fly

.. _launcher_cli_arguments_note:

.. note::

    This module can be started from a terminal, using the command ``pymodaq`` in an activated environment where
    PyMoDAQ is installed.

Introduction
------------

This module has one main window, the launcher (:numref:`launcher`) where two spaces : a shortcuts part and a restoration part, separate by a vertical spacer.
The first, contains PyMoDAQ's extensions launch shortcuts.
In this second space, the header allows you to navigate in the history entries, change configuration and load a dashboard with an experiment and a state.
Finally, under the header, there is a material tree, who expose actuators and detectors used for selected experiment.

  .. _launcher:

.. figure:: /image/launcher/launcher_home_page.png
   :alt: launcher

   Launcher user interface containing shortcuts and experiment informations.

.. :download:`png <launcher_home_page.png>`

PyMoDAQ's shorcuts
------------

This part is very basically and allows you to launch an empty interface with different buttons, linked to PyMoDAQ's shortcuts.

  .. _launcher_shortcuts:

.. figure:: /image/launcher/launcher_shortcuts.png
   :alt: launcher_shortcuts

   Launcher graphical shortcuts.

.. :download: `png <launcher_shortcuts.png>`

There are 4 shortcuts:

* :ref:`Dashboard <Dashboard_module>` to launch an empty dashboard without loaded experiment, it's similar to run `dashboard` command in a PyMoDAQ's folder.
.. _launcher_default_dashboard_note:

.. note::

    If you want to launch a ``default`` dashboard with default experiment and state, you can refer to the `Restore an experiment`_ section.
* :ref:`DAQ_Viewer_module` to launch an empty Viewer, it's similar to run ``daq_viewer`` command in a PyMoDAQ's folder.
* :ref:`DAQ_Move_module` to launch an empty DAQ Move, it's similar to run ``daq_move`` command in a PyMoDAQ's folder.
* :ref:`H5Browser <H5Browser_module>`  to launch an empty H5Browser, it's similar to run ``h5browser`` command in a PyMoDAQ's folder.

For all shortcuts, please refer you to appropriate section for more details on how it works.

Extensions launch
------------

To load an extension, select one in the combo box widget and click to arrow button.
Multiple extensions can be launched simultaneously. Extensions run in separate process from each other, as well as from the launcher and dashboard.
So, if an extension encounter an issue, other modules are not affected.

  .. _launcher_extensions:

.. figure:: /image/launcher/launcher_extensions.png
   :alt: launcher_extensions

   Launcher graphical extensions.

.. :download: `png <launcher_extensions.png>`



.. _restore_configuration:

Restore an experiment
------------


To restore an experiment click on |open_in_new| ``Launch`` button. The launcher will load a dashboard with selected experiment and state.
You can modify experiment or state before restore an experiment, for exemple if the last time PyMoDAQ used an experiment and a state, the launcher suggests that but you can just modify state.
If the experiment that you want load is not suggest directly by the launcher or in :ref:`history <launcher_history>`, you can select any experiment and state, to use passive launcher experience.

.. note::

   If you want to load a dashboard with ``default`` experiment and state, the right method is to choose ``default`` experiment and click on |open_in_new| ``Launch``.
   This method is faster than open an empty dashboard and load manually ``default`` experiment.

.. |open_in_new| image:: /image/launcher/open_in_new.png
   :height: 1em
   :align: middle

Navigate through the history
------------

.. _launcher_history:

By default, the launcher  display the last configuration used to make the dashboard restoration as quick as possible. But, you can navigate in the configurations history,
who store date, hour, experiment and state used. The are two method to navigate in the history entries :

* By ``navigation arrows``:
   To navigate to the previous configuration, click on |left_arrow| icon and to navigate to the next one click on |right_arrow| icon.

* By ``date``:
   To navigate by date, click on date combo box to display all history entries and select one (:numref:`launcher_date_combo_box`).

History entries are sorted by descendant order date. When the right configuration is set, you can change the state before to restore the dashboard (see :ref:`restore_configuration` section).

.. _launcher_date_combo_box:

.. figure:: /image/launcher/launcher_date_combo_box.png
   :alt: launcher_date_combo_box

   Navigate through the configurations history by date.

.. :download: `png <launcher_date_combo_box.png>`


.. |right_arrow| image:: /image/launcher/keyboard_arrow_right.png
   :height: 1em
   :align: middle

.. |left_arrow| image:: /image/launcher/keyboard_arrow_left.png
   :height: 1em
   :align: middle

Change history configuration
------------

By default in the launcher, the history size is fixed at 20 items and does not keep duplicates entries. So, if you choose a configuration (experiment + state) and
this configurations already exists at an other date (or hour), the first entry is overwrite by the newest. Yo can change this comportment in the settings !

   #. First, select ``Tools`` and ``Preferences`` at the top of application (on any interface, not only the launcher).

   #. Next, go to ``Pymodaq`` > ``Launcher`` (:numref:`launcher_settings`)
Here, you can change the maximum history size and if the launcher keep duplicates.

.. warning::

   If the new maximum history size is smaller than the previous, old entries will be deleted !

.. warning::

   If ``keep_duplicates`` settings is set to ``on`` and you switch it to ``off``, old duplicates will be deleted !



.. _launcher_settings:

.. figure:: /image/launcher/launcher_settings.png
   :alt: launcher_date_combo_box

   Launcher settings.

.. :download: `png <launcher_settings.png>`