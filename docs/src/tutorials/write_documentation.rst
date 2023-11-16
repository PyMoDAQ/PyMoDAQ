.. _write_documentation:

How to contribute to PyMoDAQ’s documentation?
=============================================

In this tutorial we will learn how to contribute to PyMoDAQ’s documentation. This is quite an advanced topic so we consider that you know quite well Python and PyMoDAQ ecosystem.

The documentation of PyMoDAQ
----------------------------

There are several levels of documentation of the project that we introduce in the following sections.

Documentation of the source code: docstrings
++++++++++++++++++++++++++++++++++++++++++++

The documentation of the source code is done using comments in the source files that are called *docstrings*. This documentation is addressed to the developers and is very precise. Typically, it will explain the job of a particular method, give the type of its arguments, what it returns...

.. figure:: /image/write_documentation/move_abs_docstring.svg
    :width: 600

    Docstring of the *move_abs* method in the `daq_move_Template.py`__ file.

__ https://github.com/PyMoDAQ/pymodaq_plugins_template/blob/main/src/pymodaq_plugins_template/daq_move_plugins/daq_move_Template.py

This kind of documentation is standardized. PyMoDAQ follows the `Numpy docstrings style`__. Following those conventions permits to generate automatically the :ref:`Library Reference <library_reference>`.

__ https://numpydoc.readthedocs.io/en/latest/format.html

Tests
+++++

At each modification of the source code of PyMoDAQ, a series of tests is launched automatically. This is done to ensure that the modification proposed does not have an unexpected effect and does not break the rest of the code. This development practice is indispensable to ensure its stability. A big effort has been devoted to testing in the version 4 of PyMoDAQ.

The files defining the tests are located in the `/tests`__ directory at the root of the repository.

__ https://github.com/PyMoDAQ/PyMoDAQ/tree/main/tests

Most of those tests simulate a user interacting with PyMoDAQ UI, pressing buttons and so on, and verify that everything is working as expected.

Reading those tests (which is not straightforward ;) ) allows to get a global picture of what the application is doing.

Website
+++++++

Finally, there is the website that you are reading right now. This documentation is of higher level than the previous ones, easier to read for a human! It is then adapted mostly to an introduction of PyMoDAQ to users.

This tutorial intends to present the workflow to contribute to the improvement of this website.

Sphinx
------

You may have noticed that most of Python librairies, share a common presentation of their website, this is because they all use `Sphinx`__ as a documentation generator.

__ https://pypi.org/project/Sphinx/

Sphinx uses `reStructuredText`__, which is the standard lightweight language to write documentation within the Python community.

__ https://en.wikipedia.org/wiki/ReStructuredText

Using Sphinx saves a lot of time because you just have to care about the *content* of your documentation, Sphinx will then render it as a beautiful PDF file... or even a website, like the one you are reading right now!

The folder within which there is a conf.py file is the *source directory* of a Sphinx project. In our case this directory is `PyMoDAQ/docs/src`__.

__ https://github.com/PyMoDAQ/PyMoDAQ/tree/main/docs/src

Notice that this directory is included in PyMoDAQ repository. Therefore, contributing to the documentation, from the point of view of Git, is exactly the same thing as contributing to the source code: we will modify files in the repository.

.. note::
	The */docs* directory of PyMoDAQ is located at the root of the repository, aside with the */src* directory. When you install the *pymodaq* package, what will be copied in the *site-packages* of your Python environment in the *PyMoDAQ/src/pymodaq* folder. Therefore, all the folders that are upstream from this one (including */docs*) will not be copied in the *site-packages*. This is what we want, it would be useless to have all this documentation, intended for humans, in the *site-packages*.

Preparation
-----------

Let’s prepare properly our workspace. We consider that you have a GitHub account, that you know the basics about its usage, and that you have already a remote repository (you have forked PyMoDAQ in your GitHub account).

First we need to know on which branch of the `upstream repository`__ we will work. If we want to contribute to the core of PyMoDAQ, we should send a pull request to the *pymodaq-dev* branch.

__ https://github.com/PyMoDAQ/PyMoDAQ/

.. note::
	The important branches of the PyMoDAQ repository are as follow:
		* **main** is the last stable version. This branch is maintained by the owner of the repository, and we should not send a pull request directly to it.
		* **pymodaq-dev** is the development branch, which is ahead of the *main* branch (it contains more commits than the *main* branch. External contributions should be send on this branch. The owner of the repository will test all the changes that has been suggested in the *pymodaq-dev* branch before sending them into the *main* branch.
		* **pymodaq_v3** concerns the version 3.

Let’s :ref:`create and activate a new Python environment <section_installation>`, that we will call *pmd_dev* in this tutorial.

Let’s now clone this specific branch on our local machine. We will call our local repository *pmd4_write_documentation_tutorial*.

``git clone --branch pymodaq-dev https://github.com/PyMoDAQ/PyMoDAQ.git pmd4_write_doc_tutorial``

and cd into it

``cd pmd4_write_doc_tutorial``

We have to change the configuration of *origin* so that our local repository is linked to our remote repository, and not to the upstream repository.

``git remote set-url origin https://github.com/<your GitHub name>/PyMoDAQ.git``

.. note::
	*origin* is an alias in Git that should target your remote repository. It specifies where to push your commits.

We can check that it has been taken into account with

``git remote -v``

We will now create a new branch from *pymodaq-dev* so that we can isolate our changes. We call it *write-doc-tutorial*.

``git checkout -b write-doc-tutorial``

Finally, install our local repository in edition mode in our Python environment

``(pmd_dev) >pip install -e .``

We can now safely modify our local repository.

Build the website locally
-------------------------

Since the source of the website (in */docs/src*) is included in the PyMoDAQ repository, it means that we have everything needed to build it locally!

Some additional packages are necessary to install, in particular *sphinx*, *docutils*, *numpydoc*... Those guys are listed in the *requirements.txt* file in the */docs* directory. Let’s go into it and execute the command

``(pmd_dev) >pip install -r requirements.txt``

Still in the */docs* folder (where you should have a *make.bat* file) execute

``make html`` (``.\make html`` on windows powershell)

This will run *Sphinx* that will build the website and put it into the newly created *docs/_build* folder. Open the */docs/_build/html/index.html* file with your favorite navigator. You just build the website locally!

.. _local_website:

.. figure:: /image/write_documentation/local_website.svg
    :width: 600

    Local build of the PyMoDAQ website.

Add a new tutorial
------------------

Let’s take a practical case, and suppose we want to add a tutorial about "How to contribute to PyMoDAQ’s documentation?" ;)

.. figure:: /image/write_documentation/sphinx_source_directory.svg
    :width: 200

    Sphinx source directory. It contains *index.rst* which defines the welcome page of the website and the table of contents. It contains also the *conf.py* file which defines the configuration of Sphinx. In the subfolders are others .rst file defining other pages. The /image folder is where one can store the images that are included in the pages.

The *index.rst* file defines the welcome page of the website, add also the table of contents that you see on the left column.

.. figure:: /image/write_documentation/index_toctree.svg
    :width: 600

    In the *index.rst* file, the toctree tag defines the first level of the table of contents.

We clearly have to go in the *tutorial* folder. Here we found the *plugin_development.rst* file where is written the tutorial "Story of an instrument plugin development".

Let’s just create a new .rst file named *write_documentation.rst*. We will copy the introduction of the other file, just replacing the name of the label (first line) and the title.

.. code-block::

	.. _write_documentation:

	How to contribute to PyMoDAQ’s documentation?
	=============================================

In the *tutorials.rst* file, there is another *toctree* tag which defines the second level of the table of contents within the *Tutorials* section. We have to say that there is a new entry. Notice that it is here that the label at the first line of the file is important.

.. code-block::

	Tutorials
	=========

	.. toctree::
		:maxdepth: 5
		:caption: Contents:

	   tutorials/plugin_development
	   tutorials/write_documentation

Save this file and compile again with Sphinx in the */docs* directory

``make html`` (``.\make html`` on windows powershell)

and refresh the page in the navigator. Our new tutorial is already included in the website, and the table of contents has been updated!

.. figure:: /image/write_documentation/title_new_tutorial.svg
    :width: 600

    First compilation of our new tutorial.

We just have to fill the rest of the page with what we have to say! We will introduce a bit the RST language in the following section.

reStructuredText (RST) language
-------------------------------

Here we give a brief overview of the RST language. Here is the `full documentation about RST`__.

__ https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html

Page structure
++++++++++++++

.. code-block::

	Title
	=====

	Section
	-------

	Lorem ipsum lorem ipsum.

	Subsection
	++++++++++

	Lorem ipsum lorem ipsum. Lorem ipsum lorem ipsum.

List
++++

.. code-block::

	* First item

		* First item of nested list
		* Second item of nested list

	* Second item

External link (URL)
+++++++++++++++++++

.. code-block::

	`PyMoDAQ repository`__

	__ https://github.com/PyMoDAQ/PyMoDAQ

Integrate an image
++++++++++++++++++

.. code-block::

	.. _fig_label
	.. figure:: /image/write_documentation/my_image.svg
		:width: 600

	Caption of the figure.

The images are saved in the */src/image* folder and subfolders.

Notice that you can directly integrate SVG images.

.. note::
	Be careful that the extensions of your files **should be lowercase**. The Windows operating system does not differentiate file extensions .PNG and .png for example (it is not case sensitive). If you build the documentation locally on Windows, it could render it without problem, while when compiled with a Linux system (what will be done on the server) your paths can be broken and your images not found.

Cross-referencing
+++++++++++++++++

If we want to refer to the image from the previous section:

.. code-block::

	:numref:`fig_label`

.. note::
	Note that the underscore disappeared.

If we want to refer to another page of the documentation:

.. code-block::

	:ref:`text to display <label at the begining of the page>`

for example to refer to the installation page, we will use

.. code-block::

	:ref:`install PyMoDAQ <section_installation>`

Glossary terms
++++++++++++++

You may have notice the :ref:`Glossary Terms <glossary>` page in the page of contents. This is a kind of dictionary dedicated to PyMoDAQ documentation. There are defined terms that are used frequently in the documentation. Refering to those term is then very simple

.. code-block::

	:term:`the glossary term`

Browse the already written RST files to get some examples ;)

Submit our documentation to the upstream repository
---------------------------------------------------

We are now happy with the content of our page. It is time to submit it for reviewing.

First we have to commit our modifications with Git

``git commit -am "Tutorial: How to contribute to PyMoDAQ documentation. Initial commit."``

.. note::
	If we also included some new files in the repository, like images, we have to tell Git to take those files under its supervision, which is done with the ``git add -i`` command. A simple command line interface will guide you to `select the files to add`__.

__ https://stackoverflow.com/questions/7446640/adding-only-untracked-files

We then push our changes to our remote repository

``git push``

Finally, we will open a pull request to the upstream repository from the GitHub interface. Be careful to select the *pymodaq-dev* branch!

Those steps are explained with more details in the :ref:`plugin development tutorial <pull_request_to_upstream>`.

.. figure:: /image/write_documentation/pull_request_write_doc_tutorial.svg
    :width: 600

    Pull request to the upstream repository. Be careful to select the **pymodaq-dev** branch!

Let’s hope we will convince the owner that our tutorial is usefull! Thanks for contributing ;)