.. _python_environment:

Set up a Python environment
============================

Before installing PyMoDAQ, we recommend isolating it in a dedicated Python environment. We just need an
internet connexion. Pick your operating system below.

.. tab-set::

   .. tab-item:: Windows

      .. rubric:: Install Miniforge

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

      .. rubric:: Create and activate an environment

      From the Windows *Start* menu, execute the *Miniforge Prompt*.

      .. figure:: /image/quick_start/miniforge_prompt.png

         The Miniforge Prompt. The name in brackets at the beginning of the line indicates the *Python environment* that is
         currently activated. (base) indicates that we are in the default environment of *mamba*.

      In order to have a clean installation of PyMoDAQ on our machine, we isolate it in a dedicated Python environment.
      Let’s execute the following command to create an environment called *pymodaq* with a 3.12 version of Python.

      ``mamba create -n pymodaq_env python=3.12.*``

      .. note::
         * We can call the environment as we wish, here *pymodaq_env* (the environment is not to be mixed up with the pymodaq
           software that will be installed below)
         * As a rule of thumb, choose the second last minor version of Python to be sure that PyMoDAQ is compatible. Here 3.12
           as python 3.14 is on the market!
         * here `python=3.12.*` means the last patched version of python 3.12.x will be installed

      And let’s activate it.

      ``mamba activate pymodaq_env``

      After this command, we should notice that the name in brackets in the terminal is now *pymodaq*.

   .. tab-item:: Ubuntu

      .. rubric:: Install Miniforge

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
           configuration. Run ``uname`` and ``uname -m`` commands in a terminal to understand!

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

      .. _section_installation_ubuntu:

      .. rubric:: Create and activate an environment

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

Once the environment is created and activated, head to the :ref:`Quick Start <quick_start>` to install PyMoDAQ
itself into it.
