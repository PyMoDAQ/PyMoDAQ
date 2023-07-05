.. _write_documentation:

How to contribute to PyMoDAQ’s documentation?
=============================================

In this tutorial we will learn how to contribute to PyMoDAQ’s documentation. This is quite an advanced topic so we consider that you know quite well Python and PyMoDAQ ecosystem.

There are several levels of documentation of the project:

* the documentation in the source code: docstrings
* tests
* the documentation on the website (high level)

We will be interested here in the latter point.

Sphinx
------

You may have noticed that most of Python librairies, share a common presentation of their website, this is because they all use `Sphinx`__ as a documentation generator.

__ https://pypi.org/project/Sphinx/

Sphinx uses `reStructuredText`__, which is the standard lightweight language to write documentation in the Python community.

__ https://en.wikipedia.org/wiki/ReStructuredText

Using Sphinx saves a lot of time because you just have to care about the *content* of your documentation, Sphinx will then render it as a beautiful PDF file... or even a website, like the one you are reading right now!

The folder within which there is a conf.py file is the *source directory* of a Sphinx project. In our case this directory is `PyMoDAQ/docs/src`__.

__ https://github.com/PyMoDAQ/PyMoDAQ/tree/main/docs/src

Notice that this directory is included in PyMoDAQ repository.

.. note::
	The */docs* directory of PyMoDAQ is located at the root of the repository, aside with the */src* directory. When you install the *pymodaq* package, what will be copied in the *site-packages* of your Python environment in the *PyMoDAQ/src/pymodaq* folder. Therefore, all the folders that are upstream from this one (including */docs*) will not be copied in the *site-packages*. This is what we want, it would be useless to have all this documentation, intended for humans, in the *site-packages*.

Build the website locally
-------------------------

Since the source of the website (in */docs/src*) is included in the PyMoDAQ repository, it means that we have everything needed to build it locally!

Activate a Python environment with PyMoDAQ installed in it. Some additional packages are necessary to install, in particular *sphinx*, *docutils*, *numpydoc*... Those guys are listed in the *requirements.txt* file in the */docs* directory. Let’s go into it and execute the command

``pip install -r requirements.txt``

Still in the */docs* folder (where you should have a *make.bat* file) execute

``make html``

This will run *Sphinx* that will build the website and put it into the newly created *docs/_build* folder. Open the */docs/_build/html/index.html* file with your favorite navigator. You just build the website locally!

.. _local_website:

.. figure:: /image/write_documentation/local_website.svg
    :width: 600

    Local build of the PyMoDAQ website.

Restructured text
-----------------

Page structure
++++++++++++++

.. code-block::

	Title
	=====

	Section
	-------

	Subsection
	++++++++++

How to add a new page?

Page of contents
++++++++++++++++

index.rst toctree

Integrate an image
++++++++++++++++++

* Where to save my images
* Do not use .PNG uppercase: build on Windows.

Cross-referencing
+++++++++++++++++

External URL link
+++++++++++++++++
