.. _new_plugin:

How to create a new plugin/package for PyMoDAQ?
===============================================

+------------------------------------+---------------------------------------+
| Author email                       | sebastien.weber@cemes.fr              |
+------------------------------------+---------------------------------------+
| Last update                        | january 2024                          |
+------------------------------------+---------------------------------------+
| Difficulty                         | Intermediate                          |
+------------------------------------+---------------------------------------+



In this tutorial, we will learn how to create a brand new :term:`plugin` either for adding instruments, models or
extensions!

Prerequisite
------------

We will suppose that you have followed these tutorials:

* :ref:`Basics of Git and GitHub <git_tutorial>`
* :ref:`contribute_to_pymodaq_code`

In the latter, we presented how to interact with existing repositories but what if:

* you have an instrument from a manufacturer that doesn't have yet its package!
* you want to build a brand new extension to the :ref:`Dashboard_module`!

No worries, you don't have to start from scratch, but from a fairly complete template package!

The PyMoDAQ's plugin template repository
----------------------------------------

Among all the PyMoDAQ related github repository, there is one that is not a real one. This is the
`pymodaq_plugins_template <https://github.com/PyMoDAQ/pymodaq_plugins_template>`_ (see :numref:`template_repo`)


.. _template_repo:

.. figure:: /image/tutorial_template/template_repo.png

   The Template repository to create new plugin packages!

You see that on this repository home page, a new green button `Use this template` appeared (red box on figure).
By clicking on it, you'll be prompted to *create a new repository*. In the next page, you'll be prompted to enter
a owner and a name for the repo, see :numref:`create_repo`:


.. _create_repo:

.. figure:: /image/tutorial_template/create_new_repo.png

   The creation page of the new plugin repository

In there, you can choose as a owner either yourself or the PyMoDAQ organisation if you're already part of it. If not
but you are willing, just send an email to the mailing list asking for it and you'll be added and set as the
manager of your future new plugin package. The name of the plugin as to follow the rule:
`pymodaq_plugins_<my_repo_name>` where you have to replace *<my_repo_name>* by the name of the manufacturer if you're
planning to add instruments or a clear name for your application/extension... Make it *Public* because we want to share
our work within the PyMoDAQ community!

That's it, your new github repo compatible with PyMoDAQ is created. You now have to properly configure it!

Configuring a new plugin repository
-----------------------------------

For a correct configuration (for your plugin be installable and recognised by PyMoDAQ), you'll have to modify a few
files and folders. :numref:`template_structure` highlight the package initial structure. You'll have to:

* rename with the new package name the two directories in highlighted red
* fill in the appropriate information in plugin_info.toml and README.rst files, highlighted in green
* rename the python instrument file, highlighted in purple with the dedicated instrument name (see
  :ref:`plugin_development` for details on instrument, python file and class name convention).
* add appropriate default settings in the config_template.toml file (do not rename it) in the resources folder,
* remove the unused instrument example files of the template repository in the *daq_move_plugins* and
  *daq_viewer_plugins* subfolders.
* Modify and configure the automatic publication of your package on the Pypi server (see :ref:`pypi_publish`)


.. _template_structure:

.. figure:: /image/tutorial_template/create_new_repo.png

   The template package initial structure


.. _pypi_publish:

Publishing on Pypi
------------------

In the Python ecosystem, we often install packages using the `pip` application. But what happens when we execute
`pip install mypackage`? Well `pip` is actually looking on a web server for the existence of such a package, then
download it and install it. This server is the Pypi `Python Package Index<https://pypi.org/>`_

Developers who wish to share their package with others can therefore upload their package there as it is so easy to
install it using pip. To do that you will need to create an account on Pypi:

.. _pypi_account:

.. figure:: /image/tutorial_template/pypi_account.png

   Creation of an account on Pypi

.. note::

  Until recently (late 2023) only a user name and password were needed to create the account and upload packages. Now
  the account creation requires double identification (can use an authentication app on your mobile or a token). The
  configuration of the Github action for automatic publication requires also modifications... See below.

The token will allow you to create new package on your account, see `API Token <https://pypi.org/help/#apitoken>`_ for
more in depth explanation.

.. _publish_action:

.. figure:: /image/tutorial_template/python_publish_action.png

   The modification on the github action for automatic publication on Pypi


#. Publish your repo on pypi (just by doing a release on github will trigger the creation
   of a pypi repository, you'll just have to create an account on pypi and enter your credentials
in the SECRETS on github)