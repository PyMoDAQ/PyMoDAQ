.. _git_tutorial:

october 2023

david.bresteau@cea.fr

Basics of Git and GitHub
========================

.. figure:: /image/tutorial_git/git_logo.png
    :width: 200

Why Git?
--------

Git answers mainly two important questions:

How do I organize my code development efficiently? (local use)
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

* It allows you to come back to every version of your code.
* It forces you to document every step of the development of your code.
* You can try any modification of your code safely.
* It is an indispensable tool if you work on a bigger project than a few scripts.

How do I work with my colleagues on the same code? (remote use)
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

* Git tackles the general problem of several people working on the same project: it can be scientists working on a paper
  , some members of a parliament working on a law, some developers working on a program...
* It is a powerful tool that allows multiple developers to work on the same project without conflicting each other.
* It allows everyone that download an open-source project to have the complete history of its development.
* Coupled with a cloud-based version control service like GitHub, it allows to easily share your project with everyone,
  and have contributors, like PyMoDAQ!

How does it do that?
++++++++++++++++++++

A program is nothing more than a set of files placed in the right subfolders.

Git is a *version control software*: it follows the development of a program (i.e. its different *versions*) by keeping
track of every modifications of files in a folder.

Installation & configuration for Windows
----------------------------------------

Installation
++++++++++++

.. figure:: /image/tutorial_git/git_scm.svg
    :width: 600

    Download the installer from `the official website`__.

__ https://git-scm.com/

Run the installer. From all the windows that will appear, let the default option, except for the following ones.

Uncheck "Windows Explorer integration".

.. figure:: /image/tutorial_git/git_install_window.png
    :width: 600

For the default editor, do not let Vim if you don't know about it, for example you can choose Notepad++.

.. figure:: /image/tutorial_git/git_editor_selection.png
    :width: 600

Use the following option for the name of the default branch.

.. figure:: /image/tutorial_git/git_install_init_configuration.png
    :width: 600

If you develop from Windows, it is better that you let Git manage the line endings.

.. figure:: /image/tutorial_git/git_install_line_ending.png
    :width: 600

Use the second option here.

.. figure:: /image/tutorial_git/git_install_path.png
    :width: 600

Open the Git Bash terminal (Windows Applications > Git > Git Bash or Search for "Git Bash") that has been installed with
the Git installer.

.. figure:: /image/tutorial_git/git_bash.png
    :width: 600

We can now check that it is actually installed on our system.

.. figure:: /image/tutorial_git/git_version.png
    :width: 400

Configuration
+++++++++++++

Just after the installation, you should configure Git so that he knows your email and name. This configuration is
*global* in the sense that it does not depend on the project (the repository) you are working on. Use the following
commands replacing with your own email and a name of your choice:

.. figure:: /image/tutorial_git/git_configuration.png
    :width: 600

Good, we are now ready to use Git!

Installation & configuration for Ubuntu
---------------------------------------

Installation
++++++++++++

In a terminal

``sudo apt install git``

Configuration
+++++++++++++

Just after the installation, you should configure Git so that he knows your email and name. This configuration is
*global* in the sense that it does not depend on the project (the repository) you are working on. Use the following
commands replacing with your own email and a name of your choice:

``git config --global user.email "david.bresteau@cea.fr"``

``git config --global user.name "David Bresteau"``

Good, we are now ready to use Git!