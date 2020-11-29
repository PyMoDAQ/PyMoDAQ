  .. _section_installation:

Installation
============

.. contents::
   :depth: 1
   :local:
   :backlinks: none

.. highlight:: console

Preamble
--------
PyMoDAQ is written in `Python`__ and uses Python 3.5+. It uses the `PyQt5`__ library and the excellent `pyqtgraph`__ package
for its user interface. For PyMoDAQ to run smoothly, you need a Python distribution to be installed. Here are some advices.

__ https://docs.python-guide.org/
__ http://doc.qt.io/qt-5/qt5-intro.html
__ http://www.pyqtgraph.org/

On all platforms **Windows**, **MacOS** or **Linux**, `Anaconda`__ or `Miniconda`__ is the advised distribution/package
manager. Environments can be created to deal with different version of packages and isolate the code from other
programs. Anaconda comes with a full set of installed scientific python packages while *Miniconda* is a very
light package manager.

__ https://www.anaconda.com/download/
__ https://docs.conda.io/en/latest/miniconda.html

Setting up a new environment
----------------------------

* Download and install Miniconda3.
* Open a console, and cd to the location of the *condabin* folder, for instance: ``C:\Miniconda3\condabin``
* Create a new environment: ``conda create -n my_env python=3.7``, where my_env is your new environment name, could be *pymodaq16*
  if you plan to install PyMoDAQ version 1.6.0 for instance.. This will create the environment with python version 3.7
  that is currently the recommended one.
* Activate your environment so that only packages installed within this environment will be *seen* by Python:
  ``conda activate my_env``
* Install, using conda manager, some mandatory packages: ``conda install pyqt``

Installing PyMoDAQ
------------------

Easiest part: in your newly created and activated environment enter: ``pip install pymodaq``. This will install the
latest PyMoDAQ available version and all its dependencies. For a specific version enter:  ``pip install pymodaq==x.y.z``.

  .. _shortcut_section:


Creating shortcuts on **Windows**
---------------------------------

Python packages can easily be started from the command line (see :ref:`section_how_to_start`). However, Windows users
will probably prefer using shortcuts on the desktop. Here is how to do it (Thanks to Christophe Halgand for the procedure):

* First create a shortcut (see :numref:`shortcut_create`) on your desktop (pointing to any file or program, it doesn't matter)
* Right click on it and open its properties (see :numref:`shortcut_prop`)
* On the *Start in* field ("Démarrer dans" in french and in the figure), enter the path to the condabin folder of your miniconda or
  anaconda distribution, for instance: ``C:\Miniconda3\condabin``
* On the *Target* field, ("Cible" in french and in the figure), enter this string:
  ``C:\Windows\System32\cmd.exe /k conda activate my_env & python -m pymodaq.dashboard``. This means that
  your shortcut will open the windows's command line, then execute your environment activation (*conda activate my_env* bit),
  then finally execute and start **Python**, opening the correct pymodaq file (here *dashboard.py*,
  starting the Dashboard module, *python -m pymodaq.dashboard* bit)
* You're done!
* Do it again for each PyMoDAQ's module you want (to get the correct python file and it's path, see :ref:`run_module`).



   .. _shortcut_create:

.. figure:: /image/installation/shortcut_creation.png
   :alt: shortcut

   Create a shortcut on your desktop

   .. _shortcut_prop:

.. figure:: /image/installation/shortcut_prop.PNG
   :alt: shortcut properties

   Shortcut properties


   .. _PluginManager:

Plugin Manager
--------------

The complete list of available plugins is maintained on this GitHub `repository`__.

While you can install them manually (for instance using ``pip install plugin_name``), from PyMoDAQ 2.2.2 a plugin
manager is available. You can open it from the **Dashboard** in the help section or directly using the command
line: ``python -m pymodaq_plugin_manager.manager`` or directly ``plugin_manager``

This will open the Plugin Manager User Interface as shown on figure :numref:`fig_plug_manager` listing the available
plugins packages that can be either *installed*, *updated* or *removed*. It includes a description of the content of
each package and the instruments it interfaces. For instance, on figure :numref:`fig_plug_manager`, the selected *Andor*
plugin package is selected and includes two plugins: a Viewer1D to interface Andor Shamrock spectrometers and a Viewer2D
to interface Andor CCD camera.

   .. _fig_plug_manager:

.. figure:: /image/installation/plugin_manager.png
   :alt: plugin_manager

   Plugin Manager interface


__ https://github.com/CEMES-CNRS/pymodaq_plugin_manager/blob/main/pymodaq_plugin_manager/doc/PluginList.md

