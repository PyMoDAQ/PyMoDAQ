.. _quick_start:

Quick Start
===========

PyMoDAQ installation on Windows is done in a few steps. We just need an internet connexion.

Python installation
-------------------

We first need to download the `Miniforge <https://github.com/conda-forge/miniforge/>`_ installer by
clicking (on the miniforge webpage) on one of the links highlighted in red in the following figure.

.. figure:: /image/quick_start/mini_forge_installer_link.png

   Click on one of these links to start the download of *Miniforge*’s installer.

Let’s execute the installer and keep the default choices.

.. note::

   It will actually install in particular:

   * an :term:`environment` manager: :term:`mamba`. Mamba is a :term:`CLI` to manage environments just like
     :term:`conda`. However conda has restrictions in terms of licencing hence the use of mamba as of now)
   * a Python interpreter (a *python.exe* file) in a *base* environment
   * :term:`pip <pip & PyPI>`


.. _section_installation:

Set up a new Python environment
-------------------------------

From the Windows *Start* menu, execute the *Miniforge Prompt*.

.. figure:: /image/quick_start/miniforge_prompt.png

   The Miniforge Prompt. The name in brackets at the beginning of the line indicates the *Python environment* that is
   currently activated. (base) indicates that we are in the default environment of *mamba*.

In order to have a clean installation of PyMoDAQ on our machine, we isolate it in a dedicated Python environment.
Let’s execute the following command to create an environment called *pymodaq* with a 3.11 version of Python.

``mamba create -n pymodaq_env python=3.11.*``

.. note::
   * We can call the environment as we wish, here *pymodaq_env* (the environment is not to be mixed up with the pymodaq
     software that will be installed below)
   * As a rule of thumb, choose the second last minor version of Python to be sure that PyMoDAQ is compatible. Here 3.11
     as python 3.13 is on the market!
   * here `python=3.11.*` means the last patched version of python 3.11.x will be installed

And let’s activate it.

``mamba activate pymodaq_env``

After this command, we should notice that the name in brackets in the terminal is now *pymodaq*.

Install PyMoDAQ
---------------

After this preparation, the installation of PyMoDAQ is done with a single command line. It takes a few minutes to
download and install all the dependencies in our new environment.

``pip install pymodaq pyqt5``

.. note::

 For more details about the installation, see :ref:`installation_tips`

Check the installation
----------------------

To check that the installation went well, we can execute a PyMoDAQ’s *control module* called
:ref:`DAQ_Move <DAQ_Move_module>`, using the
command

``daq_move``

This prompts the following user interface. In the *Actuator* drop-down list, choose *Mock* and click
*Initialization*. This will simulate numerically the behavior of a simple actuator, with the reading of its position.

.. figure:: /image/quick_start/mock_actuator.png
   :width: 300

   The DAQ_Move module.

The basic installation is now complete! :)

.. note::

 For more details about the loading PyMoDAQ modules, see :ref:`load_installed_tips`

Control a real instrument
-------------------------

In principle, PyMoDAQ can control any instrument.
However, each specific hardware needs a supplementary package to be compatible with it, which we call an
:term:`instrument plugin <plugin>`.

List of supported instruments
+++++++++++++++++++++++++++++

Numerous plugins are already available for common scientific equipment suppliers, they are referenced in the
`list of supported instruments <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>`_.

.. figure:: /image/quick_start/supported_instruments_list.png

   List of supported instruments.

We can access it from the *Supported instruments* link on the left menu of this website.

Install the software of the supplier
++++++++++++++++++++++++++++++++++++

To illustrate concretely the procedure, we suppose that we want to control a *Thorlabs Zelux* camera.

.. figure:: /image/quick_start/zelux_camera.png
   :width: 200

   A Thorlabs Zelux camera.

This camera is controlled with the
`ThorCam software <https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam>`_ that is provided by
Thorlabs. Let’s download and install it.

.. figure:: /image/quick_start/thorcam.png

   The webpage to download Thorcam.

Once it is installed, connect the camera and check that it is working.

.. warning::
   It is crucial to first check that your instrument can be controlled with the supplier’s software before trying with
   PyMoDAQ.

The Plugin Manager
++++++++++++++++++

Once we have checked that our camera is working, we know that the supplier’s drivers, if any, are installed, and that
the communication between our camera and our computer is working. It is now time to control it with PyMoDAQ.

We have seen that the *Thorlabs* plugin manages this type of camera.

.. figure:: /image/quick_start/supported_instruments_list_thorlabs.png

   The Zelux camera is supported by the Thorlabs plugin.

In this case, we just have to install the Thorlabs plugin in our environment. To do so, we will use the Plugin Manager
by executing the following command in our terminal

``plugin_manager``

A window is displayed to easily install the plugin.

.. figure:: /image/quick_start/plugin_manager.png
   :width: 400

   The Plugin Manager interface.

.. note::
   We can skip the use of the Plugin Manager interface by using directly in the terminal
   *pip install pymodaq_plugins_thorlabs*.

After the plugin installation, we launch a :ref:`DAQ_Viewer_module` with the following command

``daq_viewer``

.. warning::
   Let’s not forget to disconnect the camera from ThorCam or any other program before trying to communicate with it.

We then have to select the correct *DAQ type* (here 2D because the detector outputs a matrix of pixels) (1), the
corresponding plugin (2), the specific camera through its serial number (3), initialize the communication with the
camera (4), and get a snapshot (5).

.. figure:: /image/quick_start/quick_start_image_thorlabs.png
   :width: 800

   Snapshot from a Thorlabs camera equipped with an objective, in a DAQ Viewer.

What if our instrument is not already supported?
++++++++++++++++++++++++++++++++++++++++++++++++

If the instrument we want to interface is not in the list, we should firstly ask for advices from the PyMoDAQ
community. The most efficient way to do so is to :ref:`raise an issue on GitHub <create_github_account>`. Let’s
describe our project, the instrument we want to interface... We will probably get some help there!

Secondly, we can consider to develop a plugin by our own. It is not that difficult, and a lot of documentation is
available to help us step by step:

* :ref:`Developer’s documentation on instrument plugins <instrument_plugin_doc>`
* :ref:`Story of an instrument plugin development <plugin_development>`
* :ref:`Create & release a new plugin <new_plugin>`

We should also have a look at external Python driver libraries, the communication with our instrument may already be
implemented there:

* `PyMeasure <https://pymeasure.readthedocs.io/en/latest/index.html>`_
* `PyLabLib <https://pylablib.readthedocs.io/en/latest/index.html>`_
* `Instrumental <https://instrumental-lib.readthedocs.io/en/stable/index.html>`_

Synchronize our instruments
---------------------------

Once all the instruments of our experimental setup are controlled with a dedicated
:term:`control module <control modules>`, the most
difficult task is behind us.

We can now group them in a :ref:`Dashboard <dashboard_module>`,
and enjoy all the
features available through the Dashboard Extensions. The
:ref:`DAQ Scan <daq_scan_module>` extension is the first one to consider, as it meets the needs of any experiment that
consists in scanning automatically
one or several parameters and save the detector’s output.

Organization of the documentation
---------------------------------

The basic use of PyMoDAQ, that do not need any coding, is documentated in the :ref:`User’s Guide <user_guide>`.

The :ref:`Tutorials <tutorials>` address specific questions about PyMoDAQ, but also about the Python ecosystem and
useful tools for open-source development. As PyMoDAQ is not a library for developers but for experimental physicists
and teachers, we find relevant to introduce those tools from scratch. The tutorials are of various difficulties that
are indicated
at the beginning of the page.

We wish you a good experience :)
