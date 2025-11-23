.. _ubuntu:

Ubuntu
======

PyMoDAQ installation on Ubuntu is done in a few steps. We just need an internet connexion.

Python installation
-------------------

We first need to download the `Miniforge <https://github.com/conda-forge/miniforge/>`_ installer.
Let's open a terminal and run the following command (for example in the ~/Downloads directory):

.. note::

   On Linux, `~` is an alias to indicate the home directory, i.e. `/home/<username>`

``wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"``

Once the download is finished, we should run the installer:

``bash Miniforge3-$(uname)-$(uname -m).sh``

.. note::

   * On Linux, the `.sh` files are executed using the `bash` command.
   * The "$(uname)" and "$(uname -m)" variables are here to get the filename that corresponds to our machine
     configuration. Run `uname` and `uname -m   ` commands in a terminal to understand!

The installer will ask us several questions in the terminal, we will keep the default choices except for the last
question, for which we should answer "yes".

.. figure:: /image/quick_start/miniforge_end_question.png

   By answering "yes", we authorize Miniforge to modify the configuration of our terminal. It will then display in
   which Python environment we are into brackets at the beginning of each line.

We should then close the current terminal and reopen a new one. It should indicate that we are in the `base`
environment into brackets.

.. figure:: /image/quick_start/miniforge_base_env.png

   The default environment is called `base`, but we will never work into it. We will rather create a dedicated
   environment to properly isolate our work. That is what we will see in the following section.

.. note::

   Miniforge will install in particular:

   * an :term:`environment` manager: :term:`mamba`. Mamba is a :term:`CLI` to manage environments just like
     :term:`conda`. However conda has restrictions in terms of licencing, hence the use of mamba as of now.
   * a Python interpreter (a *python.exe* file) in a *base* environment
   * :term:`pip <pip & PyPI>`

   It will also create a folder ~/miniforge3 in our home directory, where all our Python environments will be stored.


.. _section_installation:

Set up a new Python environment
-------------------------------

In order to have a clean installation of PyMoDAQ on our machine, we isolate it in a dedicated Python environment.
Let’s execute the following command to create an environment called *pmd_env* with a 3.12 version of Python.

``mamba create -n pmd_env python=3.12.*``

.. note::
   * We can call the environment as we wish, here *pmd_env* (the environment is not to be mixed up with the pymodaq
     software that will be installed below)
   * As a rule of thumb, choose the second last minor version of Python to be sure that PyMoDAQ is compatible. Here 3.12
     as python 3.14 is on the market!
   * here `python=3.12.*` means that the last patched version of python 3.12.x will be installed

And let’s activate it.

``mamba activate pmd_env``

After this command, we should notice that the name in brackets in the terminal is now *pmd_env*.

Install PyMoDAQ
---------------

After this preparation, the installation of PyMoDAQ is done with a single command line. It takes a few minutes to
download and install all the dependencies in our new environment.

``pip install pymodaq pyqt6``

One also needs to make sure
that the Qt environment can be used. Running the following command should be sufficient to start with:

``sudo apt install libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 libxcb-xfixes0 x11-utils  libgl1 libegl1``

It is also necessary to give some reading and writing permission access to some specific folders. In particular,
PyMoDAQ creates two folders that are used to store configurations files, one assigned to the system in /etc/.pymodaq/
and one assigned to the user ~/.pymodaq/. We need to give reading/writing permission acess to the system folder.
One should then run before/after installing pymodaq:

* ``sudo mkdir /etc/.pymodaq/``
* ``sudo chmod uo+rw /etc/.pymodaq``

As a side note, these files are shared between different pymodaq's versions (going from 3 to 4 for example). It is
suggested to delete/remake the folder (or empty its content) when setting up a new environment with a different pymodaq
version.

Check the installation
----------------------

To check that the installation went well, we can execute a PyMoDAQ’s *control module* called
:ref:`DAQ_Move <DAQ_Move_module>`, using the
command

``daq_move``

This prompts the following user interface. In the *Actuator* drop-down list, choose *Mock* and click
*Initialization*. This will simulate numerically the behavior of a simple actuator, with the reading of its position.

.. figure:: /image/quick_start/daq_move_interface.png
   :width: 800

   The DAQ_Move module.

The basic installation is now complete! :)

.. note::

 For more details about loading PyMoDAQ modules, see :ref:`load_installed_tips`

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

.. warning::
   * Be careful that those plugins are mostly compatible with Windows, and not necessarily for Ubuntu.
   * As a general rule, if possible, we should be careful that our instrument supplier provides Linux drivers and
     a Python wrapper before purchasing the instrument.

Install the software of the supplier
++++++++++++++++++++++++++++++++++++

To illustrate concretely the procedure, we suppose that we want to control a *Basler* camera.

.. figure:: /image/quick_start/basler.png
   :width: 200

   A Basler camera.

Let's follow the lab story :ref:`Read a Basler camera <basler>` for detailed instructions.

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

We can now group them in a :ref:`Dashboard <dashboard_module>`, and enjoy all the features available through
the Dashboard Extensions. A group of control modules in a dashboard can be saved in a :ref:`preset <preset_manager>`.
A dashboard can be started with command line arguments, as explained on the
:ref:`dashboard page <dashboard_cli_arguments_note>`

The :ref:`DAQ Scan <daq_scan_module>` extension is the first one to consider, as it meets the needs of any experiment
that consists in scanning automatically one or several parameters and save the detector’s output.

Organization of the documentation
---------------------------------

The basic use of PyMoDAQ, that do not need any coding, is documentated in the :ref:`User’s Guide <user_guide>`.

The :ref:`Tutorials <tutorials>` address specific questions about PyMoDAQ, but also about the Python ecosystem and
useful tools for open-source development. As PyMoDAQ is not a library for developers but for experimental physicists
and teachers, we find relevant to introduce those tools from scratch. The tutorials are of various difficulties that
are indicated
at the beginning of the page.

The :ref:`Lab stories <lab_story>` section is dedicated to concrete examples of use in the lab or for educational
purposes.

We wish you a good experience :)
