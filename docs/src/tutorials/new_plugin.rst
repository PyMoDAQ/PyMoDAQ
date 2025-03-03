.. _new_plugin:

Write and release a new plugin
==============================

+------------------------------------+---------------------------------------+
| Author email                       | sebastien.weber@cemes.fr              |
+------------------------------------+---------------------------------------+
| Last update                        | August 2024                           |
+------------------------------------+---------------------------------------+
| Difficulty                         | Intermediate                          |
+------------------------------------+---------------------------------------+



In this tutorial, we will learn how to create a brand new :term:`plugin` for adding either instruments, models or
extensions. We will then release it on PyPI so that every PyMoDAQ user can use it and contribute to its development.

Prerequisites
-------------

We suppose that you have followed these tutorials:

* :ref:`Basics of Git and GitHub <git_tutorial>`
* :ref:`contribute_to_pymodaq_code`

In the latter, we presented how to interact with existing repositories but what if:

* you have an instrument from a manufacturer that doesn't have yet its package?
* you want to build a brand new extension to the :ref:`Dashboard_module`?

No worries, you don't have to start from scratch, but from a fairly complete template package!

The PyMoDAQ's plugin template repository
----------------------------------------

.. note::
    This is the tutorial for the last version, if you want to develop a plugin for the version 4.x, change the documentation version accordingly.

    	.. image:: /image/tutorial_template/pymodaq_change_doc_version.png
            :width: 200

Among all the PyMoDAQ related GitHub repositories, there is one that is a bit different. This is the
`pymodaq_plugins_template <https://github.com/PyMoDAQ/pymodaq_plugins_template/tree/5.0.x>`_ (see :numref:`template_repo`).
for the template corresponding to `PyMoDAQ v5.0.x` (You should switch branch according to the pymodaq version).


.. _template_repo:

.. figure:: /image/tutorial_template/template_repo.png

   The Template repository to create new plugin packages!

You see that on this repository home page, a new green button `Use this template` appeared (red box on figure).
By clicking on it, you'll be prompted to *create a new repository*. In the next page, you'll be prompted to enter
a owner and a name for the repository (see :numref:`create_repo`).


.. _create_repo:

.. figure:: /image/tutorial_template/create_new_repo.png

   The creation page of the new plugin repository

You can choose as a owner either yourself or an organisation that you are part of.

.. note::
   If you wish to be part of the PyMoDAQ organization, send an email to the mailing list *pymodaq@services.cnrs.fr*.
   You can host there your future package and be set as the manager.

The name of the plugin as to follow the naming convention `pymodaq_plugins_<my_repo_name>` where you have to replace
*<my_repo_name>*
by the name of the manufacturer if you're
planning to add instruments or a clear name for your application/extension...

Make the repository *Public* because we want to share
our work within the PyMoDAQ community!

That's it, our new GitHub repository compatible with PyMoDAQ is created. We now have to configure it properly.

Configuring a new plugin repository
-----------------------------------

For a correct configuration (for your plugin to be installable and recognised by PyMoDAQ), you'll have to modify a few
files and folders. :numref:`template_structure` highlights the package initial structure. You'll have to:

* rename with the new package name the two directories **highlighted in red**.
* fill in the appropriate information in pyproject.toml and README.rst files, **highlighted in green**.
* rename the python instrument file, **highlighted in purple** with the dedicated instrument name (see
  :ref:`plugin_development` for details on instrument, python file and class name convention).
* add appropriate default settings in the config_template.toml file (do not rename it) in the resources folder.
* remove the unused instrument example files of the template repository in the *daq_move_plugins* and
  *daq_viewer_plugins* subfolders.
* Modify and configure the automatic publication of your package on the PyPI server (see :ref:`pypi_publish`).


.. _template_structure:

.. figure:: /image/tutorial_template/template_repo_structure.png
   :width: 300

   The template package initial structure


.. _pypi_publish:

Releasing on PyPI
-----------------

What is PyPI? What is TestPyPI?
+++++++++++++++++++++++++++++++

In the Python ecosystem, we often install packages using the `pip` application. But what happens when we execute
`pip install mypackage`? Well `pip` is actually looking on a web server for the existence of such a package, then
download and install it. This server is the PyPI `Python Package Index <https://pypi.org/>`_.

Developers who wish to share their package with others can therefore upload their package there as it is so easy to
install it using `pip`. In our case, we will upload there our plugin as a Python package.

In the following, we will release our plugin on `TestPyPI`. It is exactly the same as PyPI, except that the
Python packages that are stored there are not accessible with *pip*. It has been created so that we can safely test the
release procedure without interacting with the actual PyPI. When we will be ready to actually release a plugin, we will
just have to follow the procedure bellow, replacing TestPyPI by PyPI.

Create an account on TestPyPI
+++++++++++++++++++++++++++++

Let's go to `test.pypi.org <https://test.pypi.org/>`_ to create an account.

.. _pypi_account:

.. figure:: /image/tutorial_template/pypi_register.png

   Creation of an account on TestPyPI.

After the registration, we have to configure the two factor authentication (2FA). We first need to generate
recovery codes.

.. figure:: /image/tutorial_template/pypi_recovery_codes.png

   Generate recovery codes.

It will generate 8 of them. Save the .txt file on a safe drive.

.. figure:: /image/tutorial_template/pypi_save_recovery_codes.png

   Save the recovery codes.

To configure 2FA, we will need to scan a QR code with an authentication application.
If you don’t have one, you can use the Firefox extension called Authenticator. We will install this one in this
tutorial, but if you already have another one (1Password for example) you can use it instead.

.. figure:: /image/tutorial_template/firefox_authenticator.png

   `Authenticator` Firefox extension.

Then, we will add 2FA with an authentication application.

.. figure:: /image/tutorial_template/pypi_authentication_application.png

   2FA with an authentication application.

Use `Authenticator` to scan the QR code. It will give us a 6-digit code that we will enter in the form.

.. figure:: /image/tutorial_template/pypi_qr_code.png

   Configure the 2FA application.

.. note::
   If you want to be able to use Authenticator in private browsing mode, think about authorizing the extension for
   this specific mode, otherwise it will not appear in the extensions bar.

We will finally create an API token. It will be useful in the following to authorize GitHub to connect to our
TestPyPI account.

Let's go to the proper menu.

.. figure:: /image/tutorial_template/pypi_add_api_token.png

   Create an API token.

We call this token `GitHub account` in this example (but you can call it as you want) and make a copy of it.

.. figure:: /image/tutorial_template/pypi_copy_token.png

   Copy the token.

.. note::
    Be careful to save the token properly as it will appear only once. If you lose it, you will have to generate
    a new one.

That's it for now with TestPyPI. Let's now configure our GitHub account properly!

Release our plugin on TestPyPI with GitHub Actions
++++++++++++++++++++++++++++++++++++++++++++++++++

We will start by creating a GitHub organization. This is useful if you have several developers working in a team.
In the context of experimental physics, it is worth creating an organization for our lab group.

Let's go in the tab `Your organization`, choose the free plan, and give it a name.

.. figure:: /image/tutorial_template/create_organization.png

   Create an organization.

We will now save the TestPyPI token that we created just before in the settings of the organization, so that it will be
authorized to access the TestPyPI account.

Once it is created, go to the `Settings` tab.

.. figure:: /image/tutorial_template/fk_organization_settings.png

   Settings of the organization.

Scroll down the left menu in `Security > Secrets and variables > Actions`

There we create two organization secrets.

The name of the first one is `PYPI_USERNAME` and its value is `__token__`.

The second one is `PYPI_PASSWORD`, within which we will paste the token from TestPyPI that we created in the previous
section.

.. figure:: /image/tutorial_template/fk_organization_new_secret.png

   Create new secrets to allow the connection to the TestPyPI account.

Now the organization has the credentials to connect to our TestPyPI account.

Let's now create a new repository in the organization by using the plugin template, as we did at the beginning of the
tutorial.

.. figure:: /image/tutorial_template/plugins_template_create_repository.png

   Create a new repository in the organization from the template.

Then clone it on our local machine.

.. note::
    Let's not forget to change the names of the folders and the files as described in the beginning of the tutorial!

We will now have a look at the `.github/workflows` folder that is at the root of our repository. There are several
files that correspond to `GitHub Actions <https://docs.github.com/en/actions>`_.
Those are automated tasks that can be triggered by an action of the user on
GitHub. For example, it can trigger some automated tests when someone is pushing some code in his repository. Here we
will be particularly interested in the `python-publish.yml` file.

.. figure:: /image/tutorial_template/plugin_template_configure_github_action.png

   The `python-publish.yml` file.

This file is part of the template, and we do not need to enter into the details of its writing. It basically defines
that when we will trigger a release from our GitHub repository, it will upload the current version of the repository
to TestPyPI.

We can notice that it makes use of the secrets `PYPI_USERNAME` and `PYPI_PASSWORD` that we configured earlier to
authenticate to TestPyPI at the moment of the release.

Since here we want to discover the release process by releasing to TestPyPI rather than PyPI, we need to change the
last line of the file and replace it by

``twine upload -r testpypi dist/*``
or
``hatch publish -r test``
if you're using hatch

.. note::
    In the case of a release to the actual PyPI, we should skip this last step!

Finally, we should modify the `resources/VERSION` file of our repository, so that it corresponds to the release tag
that we will use for our first release. We can use `1.0.0`.

Commit and push those changes towards the remote repository. We are now ready to try our first release!

On the page of our repository, let's create a new release.

.. figure:: /image/tutorial_template/github_new_release.png

   Create a new release.

We are prompted to a form to describe the release. In particular, we have to define a tag for the release,
which should correspond to the `resources/VERSION` file of the package, we use `1.0.0` as the first tag.

.. figure:: /image/tutorial_template/github_configure_release.png

   The release form.

By clicking the `Publish release` button, we automatically trigger the execution of the GitHub Action that is defined
in the `python-publish.yml` file. It will automatically take care of the upload of the package.

To follow what is going on, we have to go to the `Actions` tab of our GitHub repository.

.. figure:: /image/tutorial_template/github_action_tab_release_failed.png

   The GitHub `Actions` tab is where we found if the release went according to plan. The red cross indicates that it
   went wrong.

If we click on the workflow that corresponds to the release, we see that something went wrong during the `deploy` step.

.. figure:: /image/tutorial_template/github_see_action_log.png

   The `deploy` step of the release action went wrong.

Let’s click on it, it will open the log of the release workflow.

.. figure:: /image/tutorial_template/github_action_log_error.png

   Access the log of the workflow to get information about what went wrong. Here it indicates that we used a name for
   the package that was already taken.

.. note::
    This last step has been done (quite ;) ) on purpose to show how to debug a workflow.

After correcting the name of the package from `pymodaq_plugins_fk` to `pymodaq_plugins_fkk` the release process went
well!

.. figure:: /image/tutorial_template/github_release_green.png

   The workflow went well, we are green!

Let’s make a research of our package on TestPyPI, the upload should be quite instantaneous... Here it is! :)

.. figure:: /image/tutorial_template/pypi_package_published.png

   Our package has been uploaded to TestPyPI!! :)

What are the consequences of a release on PyPI?
+++++++++++++++++++++++++++++++++++++++++++++++

There are several consequences if we release a plugin on the actual PyPI (and not TestPyPI).

First, our newly released plugin will automatically be proposed by the :ref:`Plugin Manager <section_installation>`.
How is that miracle possible?! Because we respected the naming convention of our plugin, the Plugin Manager just has to
search for the Python packages stored on PyPI that start with *pymodaq_plugins_...*. It is as simple as that!

Secondly, the `list of supported instruments <https://github.com/PyMoDAQ/pymodaq_plugin_manager/blob/main/README.md>`_
will also be updated.

Resources
---------

If you want to understand better the tools that are used in this tutorials, here are a few external links.

In this GitHub documentation
`Building and testing Python <https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python#publishing-to-package-registries>`_
is explained in details how to write your own GitHub Actions to test and release a Python package.

Here is the
`PyPI documentation <https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/>`_
about using GitHub Actions.

Here is the `Twine documentation <https://twine.readthedocs.io/en/stable/>`_.
