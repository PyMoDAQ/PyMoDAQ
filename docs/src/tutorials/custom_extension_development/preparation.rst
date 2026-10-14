Preparing the stage
===================

This section is devoted to a recap on how to set up the module's folder structure and Python's virtual environment.

Used tools
----------

A couple of tools will be used in this tutorial. To avoid cluttering-up the text, no special introduction will be given to these tools here.

* Git and github
* Conda / venv
* No special editor or IDE is needed. PyCharm is a good choice since PyMoDAQ developers use it a lot.
* pde (the built-in Python Debugger) or the debugger built into PyCharm
* git-shell / a UN*X bash shell is used for handling operations on the level of the computer's file system.


Setting up the Python module skeleton
-------------------------------------

To get a starting point for our code we are cloning the plugin template repository on github. Note that the route taken here does not build a fork of an existing repository. We're going to develop something new, right?::

  $ cd /path/to/extension-plugin-code

Then clone the template repository::

  $ git clone -b 5.0.x https://github.com/PyMoDAQ/pymodaq_plugins_template.git
  Cloning into 'pymodaq_plugins_template'...

Note that we are using here a version one step behind the current one at the time of publishing this tutorial (October 26). 5.0.x is the version of the plugins the tutorial has been developed and been based on. The changes since then ease plugin development without a tutorial since contrary to earlier versions the code is already running without the completions. The intended functionality can then simple be added. However, rebasing the matter on the improved plugins would ask for yet another delay in publishing the present tutorial because a series of sub chapters would have to be checked again to be still in sync with the literal code provided by the templates.

The way to work through this tutorial should therefore be to start with the slightly oder template version. The developed code should be working also under newer PyMoDAQ versions in the 5 main branch. You may therefore use PyMoDAQ version 5.3.x (or newer) for this tutorial. In case something doesn't work and it is not a matter of typos or similar, please raise an issue on PyMoDAQ's github repository. The maintainers will then have to decide whether some compatibility code should be introduced or rather updating an obsolete part of the documentation is due.

We'll call the project :code:`tutorial_extension` and give the repository the corresponding name::

  $ mv pymodaq_plugins_template pymodaq_plugins_tutorial_extension
  $ cd pymodaq_plugins_tutorial_extension
  $ mv src/pymodaq_plugins_template src/pymodaq_plugins_tutorial_extension

We're not going to need the templates for 0D and 2D viewer plugins, neither for custom models. Let's delete the corresponding template files because they would show up in the dashboard's plugin list. However, don't delete the folders and the :file:`__init__.py` files in there because at some later point you may want to add real plugins there. The now deleted template code can easily be retrieved from github in case.

Being a git clone of the :code:`pymodaq_plugins_template` repository, it still is linked to the history of that template module which is probably not what you want. It is better to take a fresh start by deleting git's repository folder and re-initialising git::

  $ rm -rf .git
  $ git init
  $ git add -A
  $ git commit -m "initial repository commit"

If you plan to develop multiple plugins, you may also tar or zip the project folder right after having deleted the :file:`.git` folder or download the sources from github as a zip file and keep the material aside for re-use later on.

My preferred code editor (being a keyboard player) makes backup copies of changed files by appending a tilde to the file name. I therefore add the line

.. code-block::

  *~

at the bottom of :file:`.gitignore`. You may add similar matter to prevent git considering temporal files which are not supposed to enter into the repository.

Let's inspect the root folder::

  $ ls
  hatch_build.py	icon.ico  LICENSE  pyproject.toml  README.rst  src  tests

A couple of files in there should be modified.

* :file:`LICENSE`: You may want to add your name to the Copyright (c) statement.
* :file:`pyproject.toml`: Here goes main information for the installation procedure. The code is pretty self-explaining. Just fill in the blanks. The package-url depends on whether you want to host your package on your own repository or you plan to get it hosted on the PyMoDAQ repository. Don't worry too much about it at this time. It is a good idea to delete the comments telling what to do once you did it. We'll leave the features as they are for the moment, announcing only instruments, because that is what we are going to do as a first step. The extension comes later. Fill in sensible information in the project section until the comment :code:`nottodo`. Make sure that the PyMoDAQ version is set to at least 5.2 because this tutorial covers features which were not present in earlier versions.
* :file:`README.rst`: This file is intended to give the user of your plugin the necessary information to install and to run it. Have a look into other plugin repositories to get an idea of what is typically provided here and how.

That's it for the root folder and the book-keeping matter in there.


Preparing the environment
.........................

As a last step before diving into coding we have to set up a virtual environment which we are going to use during the development of our plugin. Due to the fast evolution of Python packages, keeping track of compatible versions is quite an important issue. Virtual environments are used as containers which isolate parallel installations using different and potentially incompatible versions of packages. In the past, conda was used by the PyMoDAQ community. Licence issues have changed that. On Linux systems Python typically is already there out of the box and the Python-onboard package venv can be used::

  $ python3 -m venv /path/to/your/environments/tut
  $ source /path/to/your/environments/tut/bin/activate
  $ pip install pymodaq pyqt6

As path you should choose a sensible name for your project. Where you create this environment folder depends on your personal preferences or on the preferences of the people you are cooperating with. Some prefer to have the environment folder in the folder of the corresponding module. However, a module may be used (and installed in editable mode) in various different environments on your computer. Two "best practices" could probably be named: i) have all environments under a comon root folder (that'sthe approach shown above), ii) place the folder of the environment which you use for developing your module inside the module's folder and keep other environments using that module (and potentially others) elsewhere.

The sub folders created in the environment folder contain links to the Python interpreter to be used and will receive all packages installed by pip once the environment is activated. Some prefer to have a separate environment for each package / plugin to be developed. Different environments are needed at least when working with different versions of some packages in parallel. But don't worry, new environments can always be set up later in case that incompatibilities come up. 

The activation will add the environment's bin directory to the head of the current search path so that the binaries therein will be found before any others with the same name. If you wish to use a specific Python version, say 3.12, call::

  $ python3.12 -m venv /path/to/your/environments/tut

That version must of course have been previously installed on your computer. After the activation, don't worry when Python complains about missing packages which you know are being already present on your system. Placing the Python interpreter into an environment actually makes it looking like a pristine installation of the bare interpreter without any additional packages.

To try whether things work as supposed, let's start the dashboard::

  $ dashboard

The dashboard should start up. However, in the experiment manager, no new plugins are visible. That is all right because we haven't installed the plugin module yet. This has to happen in the so-called editable mode. To this end, change to the root directory of your plugin, where e.g. the file :file:`pyproject.toml` is to be found and type::

  $ pip install -e .

This tells the Python installer to incorporate the module under development into the local site-packages. Watch out for the space-and-dot after the -e. Depending on the version of pip coming with your operating system, it might be necessary to first update pip::

  $ python -m pip install pip --upgrade

Note that the template plugins will still not appear in the dashboard's device list because without modification the code therein will throw exceptions, preventing the (anyway still useless) plugins to be loaded. The corresponding error messages show up in PyMoDAQ's log file. If that's not what you want then you may delete the unused template files (0D and 2D viewer and models). But keep the directories and the :file:`__init__.py` files therein because later on you may want to add further plugins. The deleted code can easily be recovered from the repository on github.

A few words on the virtual environments may be worth mentioning here.

* A common problem in Linux environments is that Python comes already with the system installation and is used for various tasks. However, no environments are set up by default. This may screw up things when Python packages are installed as superuser but not using the system's package manager (like apt for Debian). The latter and the work of the distribution maintainers take care of version issues. However, when using :code:`sudo pip install ...` you are on your own. Even worse, you may already have done so in the past without being aware of possible problems. They will probably hit you now.

  Therefore, use :code:`pip` only in virtual environments. Outside, always use the system's package manager instead!

* PyCharm seems to have sometimes difficulties in coping with already existing environments. After setting everything according to the instructions on the JetBrains website, the prompt in the terminal may show that instead of the chosen environment, PyCharm has actually activated the base environment. Supposedly missing packages are a good indication that this happened. Creating new environments from inside PyCharm seems to work more reliably.

At this point it is a good idea to commit what we have changed so far::

  $ git status

  On branch main
  Changes not staged for commit:
    (use "git add <file>..." to update what will be committed)
    (use "git restore <file>..." to discard changes in working directory)
          modified:   .gitignore
          modified:   README.rst
          modified:   pyproject.toml

  no changes added to commit (use "git add" and/or "git commit -a")

  $

tells you what will be committed when issuing::

  $ git add -u
  $ git commit -m "preparation"

If you want to compare your code with the code provided in the github repository which accompanies this tutorial, make a clone of that repository and check out the branch corresponding to your current stage::

  $ cd /path/to/comparison/code
  $ git clone https://github.com/bernhardlang/pymodaq_extension_tutorial.git tutorial_github
  $ cd tutorial_github
  $ git checkout preparation

A hint :code:`-> branch preparation` on the branch to check out will be placed at every mile stone in this tutorial.
