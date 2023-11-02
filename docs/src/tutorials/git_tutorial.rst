.. _git_tutorial:

Basics of Git and GitHub
========================

+------------------------------------+---------------------------------------+
| Author email                       | david.bresteau@cea.fr                 |
+------------------------------------+---------------------------------------+
| First edition                      | november 2023                         |
+------------------------------------+---------------------------------------+
| Difficulty                         | Easy                                  |
+------------------------------------+---------------------------------------+

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
    :width: 400

For the default editor, do not let Vim if you don't know about it, for example you can choose Notepad++.

.. figure:: /image/tutorial_git/git_editor_selection.png
    :width: 400

Use the following option for the name of the default branch.

.. figure:: /image/tutorial_git/git_install_init_configuration.png
    :width: 400

If you develop from Windows, it is better that you let Git manage the line endings.

.. figure:: /image/tutorial_git/git_install_line_ending.png
    :width: 400

Use the second option here.

.. figure:: /image/tutorial_git/git_install_path.png
    :width: 400

Open the Git Bash terminal (Windows Applications > Git > Git Bash or Search for "Git Bash") that has been installed with
the Git installer.

.. figure:: /image/tutorial_git/git_bash.png
    :width: 400

We can now check that it is actually installed on our system.

.. figure:: /image/tutorial_git/git_version.png
    :width: 400

Configuration
+++++++++++++

Just after the installation, you should configure Git so that he knows your email and name. This configuration is
*global* in the sense that it does not depend on the project (the repository) you are working on. Use the following
commands replacing with your own email and a name of your choice:

``git config --global user.email "david.bresteau@cea.fr"``

``git config --global user.name "David Bresteau"``

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

Local use of Git
----------------

We will start by using Git just on our local machine.

Before we start...
++++++++++++++++++

**What kind of files I CAN track with Git?**

Opened file formats that use text language: any "normal" language like C++, Python, Latex, markdown...

**What kind of files I CANNOT track with Git?**

* Closed file format like Word, pdf, Labview...
* Images, drawings...

The *init* command: start a new project
+++++++++++++++++++++++++++++++++++++++

We start a project by creating a folder

``C:\Users\dbrestea>mkdir MyAmazingProject!!!``

And *cd* into this folder

``C:\Users\dbrestea>cd MyAmazingProject!!!``

Now, we tell Git to track this folder with the *init* command

``C:\Users\dbrestea\MyAmazingProject!!!>git init``

Any folder that is tracked by Git contains a *.git subfolder* and called a *repository*.

.. figure:: /image/tutorial_git/git_init_git_folder.png
    :width: 400

We now create a new file in this folder

.. figure:: /image/tutorial_git/git_first_file.png
    :width: 400

The *status* command
++++++++++++++++++++

You should never hesitate to run this command, it gives you the current status of the project.

.. figure:: /image/tutorial_git/git_status.png
    :width: 700

Here Git says that he noticed that we created a new file, but he placed it under the *Untracked files* and colored it in
red.

The red means that Git does not know what to do with this file, he is waiting for an order from us.

We have to tell him explicitly to track this file. To do so, we will just follow what he advised us, and use the *add* command.

The *add* command
+++++++++++++++++

To put a file under the supervision of Git (to *track* the file), we use the *add* command. This has to be done only the
first time you add a file into the folder.

.. figure:: /image/tutorial_git/git_add.png
    :width: 700

Then we do again the *status* command to see what have changed.

Now the filename turned green, which means that the file is tracked by Git and ready to be *commited*.

The *commit* command
++++++++++++++++++++

A *commit* is a fundamental notion of Git.

**A commit is a snapshot of the folder status at a point in time.**

It is you, the user, that decide when to do a commit.

**A commit should be done at every little change you do on your program, after you tested that the result is as you
expected.** For example, you should do a commit each time you add a new functionality that is working properly.

For now, we just have one sentence in the file: "Hello world!", but that's a start. Let us do our initial commit.

.. figure:: /image/tutorial_git/git_commit.png
    :width: 700

After the *-am* options (which means that you *add* the files that are not already tracked, and you type the *message*
of your commit just after the command), we put a message to describe what we have done between parenthesis.

If we now look at the status of our project

.. figure:: /image/tutorial_git/git_tree_clean.png
    :width: 600

Everything is clean, good! We just did our first commit! :)

The *log* command
+++++++++++++++++

The *log* command will give you the complete history of the commits since the beginning of the project.

.. figure:: /image/tutorial_git/git_log_complete.png
    :width: 700

You can see that for each commit you have:

* An *id* that has been attributed to the commit, which is the big number in orange
* The name and email address of the author.
* The date and time of the commit.
* The message that the author has written.

In the following we will use the *--oneline* option to get the useful information in a more compact way.

.. figure:: /image/tutorial_git/git_log.png
    :width: 700

The *diff* command
++++++++++++++++++

The *diff* command is here to tell you what have changed since your last commit.

Let us now put some interesting content in our file. We will found this in the `textart.me`__ website. Choose an
animal and copy paste it into our file. (Textart is the art of drawing something with some keyboard characters. It
would be equivalent to just add a sentence in the file!).

__ https://textart.me/#animals and birds

.. figure:: /image/tutorial_git/git_textart.png
    :width: 700

Let's go for the monkey, he is fun!

.. figure:: /image/tutorial_git/git_monkey.png
    :width: 700

What happen if we ask for a difference from Git?

.. figure:: /image/tutorial_git/git_diff_monkey.png
    :width: 700

In *green* appears what we have added, in *red* appears what we have removed.

The *diff* command allows us to check what we have modified. Since we are happy with our last modification, we will
commit our changes.

.. figure:: /image/tutorial_git/git_commit_the_monkey.png
    :width: 700

Let us check what the log says now.

.. figure:: /image/tutorial_git/git_log_the_monkey.png
    :width: 700

We now have two commits in our history.

The *revert* command
++++++++++++++++++++

The *revert* command is here if you want to come back to a previous state of your folder.

Let's say that we are not happy with the monkey anymore. We would like to come back to the original state of the file
just before we added the monkey. Since we did the things properly, by commiting at every important point, this is a
child play.

We use the *revert* command and the commit number that we want to cancel. The commit number is found by using the
*log --oneline* command. In our case it is 0b6ad27.

.. figure:: /image/tutorial_git/git_revert_monkey.png
    :width: 500

This command will open Notepad++ (because we configured this editor in the installation section), just close it or
modify the first text line if you want another commit message.

.. figure:: /image/tutorial_git/git_revert_open_notepad.png
    :width: 700

Let's now see the history

.. figure:: /image/tutorial_git/git_log_after_revert.png
    :width: 700

You can see that the revert operation has been written in the history, just as a usual commit.

Let see how it looks like inside our amazing file (it may be needed to close/reopen the file).

.. figure:: /image/tutorial_git/git_file_content_after_revert.png
    :width: 500

The monkey actually disappeared! :O