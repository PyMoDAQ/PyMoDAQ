.. _new_plugin:

How to create and release a new plugin for PyMoDAQ?
===================================================

+------------------------------------+---------------------------------------+
| Author email                       | sebastien.weber@cemes.fr              |
+------------------------------------+---------------------------------------+
| Last update                        | July 2024                             |
+------------------------------------+---------------------------------------+
| Difficulty                         | Intermediate                          |
+------------------------------------+---------------------------------------+



In this tutorial, we will learn how to create a brand new :term:`plugin` either for adding instruments, models or
extensions. We will then release it on PyPI so that every PyMoDAQ user can use it and contribute to its development!

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
* Modify and configure the automatic publication of your package on the PyPI server (see :ref:`pypi_publish`)


.. _template_structure:

.. figure:: /image/tutorial_template/template_repo_structure.png

   The template package initial structure


.. _pypi_publish:

Releasing on PyPI
-----------------

What is PyPI?
+++++++++++++

In the Python ecosystem, we often install packages using the `pip` application. But what happens when we execute
`pip install mypackage`? Well `pip` is actually looking on a web server for the existence of such a package, then
download and install it. This server is the PyPI `Python Package Index <https://pypi.org/>`_.

Developers who wish to share their package with others can therefore upload their package there as it is so easy to
install it using `pip`. In our case, we will upload there our plugin as a Python package.

In the following, we will release our plugin on `TestPyPI`. The latter is exactly the same as PyPI, except that the
Python packages that are stored there are not accessible with pip. It has been created so that we can safely test the
release procedure without interacting with the actual PyPI. When we will be ready to actually release a plugin, we will
just have to follow the procedure bellow, replacing TestPyPI by PyPI.

Create an account on PyPI
+++++++++++++++++++++++++

Let's go to `test.pypi.org <https://test.pypi.org/>`_ to create an account.

.. _pypi_account:

.. figure:: /image/tutorial_template/pypi_register.png

   Creation of an account on PyPI.

After the registration, we will have to configure the two factor authentication (2FA). We first need to generate
recovery codes.

.. figure:: /image/tutorial_template/pypi_recovery_codes.png

   Generate recovery codes.

It will generate 8 of them. Save the .txt file on a safe drive.

.. figure:: /image/tutorial_template/pypi_save_recovery_codes.png

   Save the recovery codes.

To configure 2FA, we will need to scan a QR code with an authentication application.
We will install the Firefox extension `Authenticator`.

.. figure:: /image/tutorial_template/firefox_authenticator.png

   `Authenticator` Firefox extension.

Then, we will add 2FA with an authentication application.

.. figure:: /image/tutorial_template/pypi_authentication_application.png

   2FA with an authentication application.

Use `Authenticator` to scan the QR code. It will give us a 6-digit code that we will enter in the form.

.. figure:: /image/tutorial_template/pypi_qr_code.png

   Configure the 2FA application.

.. note::
    Be careful to autorize `Authenticator` in private windows if you use them. Otherwise it will not appear in the
    extensions menu.

We will finally create an API token. The latter will be useful in the following to authorize GitHub to connect to our
PyPI account.

Let's go to the proper menu.

.. figure:: /image/tutorial_template/pypi_add_api_token.png

   Create an API token.

We call this token `GitHub account` and make a copy.

.. note::
    Be careful to save the token properly as it will appear only once!

That's it for now with PyPI. Let's now configure GitHub properly!