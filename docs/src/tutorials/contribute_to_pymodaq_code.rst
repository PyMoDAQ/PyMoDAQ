.. _contribute_to_pymodaq_code:

How to modify existing PyMoDAQ’s code?
======================================

+------------------------------------+---------------------------------------------+
| Author email                       | david.bresteau@cea.fr romain.geneaux@cea.fr |
+------------------------------------+---------------------------------------------+
| Last update                        | january 2024                                |
+------------------------------------+---------------------------------------------+
| Difficulty                         | Intermediate                                |
+------------------------------------+---------------------------------------------+

.. figure:: /image/tutorial_create_github_account/github_logo.png
    :width: 200


In this tutorial, we will learn how to propose a modification of the code of PyMoDAQ. By doing so, you will learn how to
contribute to any open-source project!

Prerequisite
------------

We will suppose that you have followed the tutorial

:ref:`Basics of Git and GitHub <git_tutorial>`

In the latter, we presented how to deal with the interaction of a *local repository* with a *remote repository*.
Up to now we just worked on our own. In the following we will learn how to contribute to an external project like
PyMoDAQ!

The PyMoDAQ repositories
------------------------

Let’s now go to the `PyMoDAQ GitHub account`__.

__ https://github.com/PyMoDAQ

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pmd_github_account.png
    :width: 600

There are a lot of repositories, most of them correspond to *Python packages*. Briefly, there is:

* The `PyMoDAQ repository`__: this is the core of the code, you cannot run PyMoDAQ without it.

* The plugins’ repositories: those repositories follow the naming convention *pymodaq_plugins_<name>*. Most of the time,
  *<name>* corresponds to the name of an instrument supplier, like *Thorlabs*. Those are optional pieces of code. They
  will be useful depending on the instruments the final user wants to control.

__ https://github.com/PyMoDAQ/PyMoDAQ

PyMoDAQ branches
----------------

Let’s go to the `PyMoDAQ repository`__.

__ https://github.com/PyMoDAQ/PyMoDAQ

.. note::
    Be careful not to confuse the PyMoDAQ *GitHub account* and the *repository*.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pmd_branches.png

There are several branches of the PyMoDAQ repository. Branches are used to prepare future releases, to develop new
features or to patch bugs, without risking modifying the stable version of the code. The full branch structure is described
at length :ref:`in the Developer's guide <branches_release_cycle_doc>`. For our purposes here, let us just mention the two
most important branches:

* **the stable branch**. It is the present state of the code. When you install PyMoDAQ with pip, it
  is this version of the code that is downloaded.

* **The development branch**. It is *ahead* of the main branch, in the sense that it contains more
  recent commits than the main branch. It is thus the future state of the code. This is where the last developments
  of the code of PyMoDAQ are pushed. When the developers are happy with the state of this branch, typically when they
  finished to develop a new functionality and they tested it, they will merge the develop branch into the main branch,
  which will lead to a new *release* of PyMoDAQ.

How to propose a modification of the code of PyMoDAQ?
-----------------------------------------------------

Compared to the situation in the :ref:`Basics of Git and GitHub <git_tutorial>` tutorial, where we had to deal with
our *local repository* and our *remote repository*, we now have
to deal with an external repository on which we have no right. This external repository, which in our example is the
PyMoDAQ one, is called the **upstream repository**. The workflow is represented the schematic below and we will
detail each step in the following.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/git_full_repositories.png
    :width: 600

(1) Fork the upstream repository
++++++++++++++++++++++++++++++++

.. note::
    In the screenshots below, the stable and development branches are called *main* and *pymodaq-dev*. This naming scheme
    is now deprecated. Branch names now correspond to the current PyMoDAQ versions. For instance, if the current stable
    version is 5.6.2, the stable branch will be called *5.6.x* and the development branch will be called *5.7.x_dev*.

While we are connected to our GitHub account, let’s go to the PyMoDAQ repository and select the *pymodaq-dev* branch.
Then we click on the *Fork* button.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/fork_pmd.png
    :width: 600

This will create a copy of the PyMoDAQ repository on our personal account, it then become our remote repository and **we
have every right on it**.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/fork_pmd_on_quantumm.png
    :width: 600

**Every modification of the code of PyMoDAQ should first go to the pymodaq-dev branch, and not on the main branch**.
The proper way to propose our contribution is that we create a branch from the *pymodaq-dev* branch, so that it will
ease
the integration of our commits and isolate our work from other contributions.

We create a branch *monkey-branch* from the *pymodaq-dev* branch.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/create_branch.png
    :width: 600

(2) Clone our new remote repository locally
+++++++++++++++++++++++++++++++++++++++++++

We will now clone our remote repository locally.

Open PyCharm. Go to *Git > Clone...* and select the *PyMoDAQ* repository, which correspond to our recent fork.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pycharm_clone.png
    :width: 600

.. note::
    Here we put the local repository inside a *PyCharmProject* folder and called it *PyMoDAQ*, but you can change those
    names if you wish.

We configure PyCharm so that we have the good Python interpreter and we choose the *monkey_branch* of our remote
repository.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pycharm_configuration.png
    :width: 800

(3) Do modifications and push
+++++++++++++++++++++++++++++

We now have the PyMoDAQ code on our local machine. We will put the monkey into the README.rst file at the root of the
PyMoDAQ package. This file is the one that is displayed at the home page of a GitHub repository.

We can now go to *Git > Commit...*, right click on the file and *Show Diff*.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pycharm_add_monkey_in_readme.png
    :width: 600

If we are happy with our modifications,
let’s add a commit message and click *Commit and Push*.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pycharm_push.png
    :width: 600

This is the result on our remote repository.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/monkey_in_remote_repository.png
    :width: 600

We will now propose this modification, so that the monkey would appear at the front page of the PyMoDAQ repository!

(4) Pull request (PR) to the upstream repository
++++++++++++++++++++++++++++++++++++++++++++++++

We can be very proud of our modification, but of course, this will not be implemented directly, we will need the
agreement of the owner of the PyMoDAQ repository.

**Opening a pull request is proposing a modification of the code to the owner of the upstream repository**.

This can
be done through the GitHub website, at the location of our repository. Either click to *Compare & pull request* or to
the *Pull requests* tab and *New pull request*.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pull_request_the_monkey.png
    :width: 600

Be careful to properly select the branch of our repository and the branch of the upstream repository, and then *Send*.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/github_pull_request.png
    :width: 600

That’s it! We now have to wait for the answer of the owner of the upstream repository. Let’s hope he will appreciate
our work!
We can see the status of our PR on the PyMoDAQ repository home page, by clicking on the *Pull requests* tab.
There a discussion will be opened with the owner of the repository.

.. figure:: /image/tutorial_contribute_to_pymodaq_code/pmd_pr_tab.png
    :width: 600

Note that opening a PR does not prevent us from working on our remote repository anymore, while waiting for the answer
of the owner of the upstream repository.
If we continue to commit some changes to the branch that we used for our PR (the *monkey_branch* here), the PR will
be automatically updated, and the new commits will be considered as part of the PR.
If we want to pursue the work but not put the following commits in the PR, we can start a new branch from the
*monkey_branch*.