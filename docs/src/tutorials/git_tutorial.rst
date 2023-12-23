.. _git_tutorial:

+------------------------------------+---------------------------------------+
| Author email                       | david.bresteau@cea.fr                 |
+------------------------------------+---------------------------------------+
| First edition                      | november 2023                         |
+------------------------------------+---------------------------------------+
| Difficulty                         | Easy                                  |
+------------------------------------+---------------------------------------+

.. figure:: /image/tutorial_git/git_logo.png
    :width: 200

Basics of Git and GitHub
========================

We introduce Git and GitHub in Pymodaq documentation because we believe that every experimental physicist should know
about those wonderful tools that have been made by developers. They will help you code and share your code efficiently,
not only within the framework of Pymodaq or even Python. Moreover, since Pymodaq is an open source project, its
development is based on those tools. They have to be mastered if you want to contribute to the project or develop your
own extension. Even as a simple user, you will learn where to ask for help when you are in difficulty, because Pymodaq’s
community is organized around those tools.

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

    Download the installer from the official website.

Download the installer from `the official website`__. Run the installer. From all the windows that will appear, let
the default option, except for the following ones.

__ https://git-scm.com/

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

We have to tell him explicitly to track this file. To do so, we will just follow what he advised us, and use the *add*
command.

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

Work with branches
++++++++++++++++++

Within a given project, we can define several *branches*. Each branch will define different evolutions of the project.
Git allows you to easily switch between those different branches, and to work in parallel on different *versions* of the
same project. It is a central concept of a version control system.

Up to now, we worked on the default branch, which is by convention named *main*. This branch should be the most
reliable, the most *stable*. A good practice is to **never work directly on the main branch**. We actually
did not follow this rule up to now for simplicity. In order to keep the main branch stable, **each time we want to
modify our project, we should create a new branch** to isolate our future changes, that may lead to break the
consistency of the code.

Here is a representation of what is the current status of our project.

.. figure:: /image/tutorial_git/git_branch_initial.svg
    :width: 500

    We are on the *main* branch and we did 3 commits. The most recent commit of the branch is also called *HEAD*.

We will create a new branch, that we will call *develop*, with the following command

``git checkout -b develop``

Within this branch, we will be very safe to try any modification of the code we like, because it will be completely
isolated from the *main* one. If we look at the status

``git status``

the first line of the answer should be "On branch develop".

Let say that we now modify our file by adding some new animals (a bird and a mosquito), and commiting at each time. Here
is a representation of the new status of our project.

.. figure:: /image/tutorial_git/git_branch_merge.svg
    :width: 500

If we are happy with those two last commits, and we want to include them in the main branch, we will *merge* the
*develop* branch into the *main* one, using the following procedure.

We first have to go back to the *main* branch. For that, we use

``git checkout main``

Then, we tell Git to *merge* the *develop* branch into the current one, which is *main*

``git merge develop``

And we can now delete the *develop* branch which is now useless.

``git branch -d develop``

We end up with a *main* branch that inherited from the last commits of the former *develop* one (RIP)

.. figure:: /image/tutorial_git/git_branch_final.svg
    :width: 500

This procedure looks overkill at first sight on such a simple example, but we strongly recommend that you try to stick
with it at the very beginning of your practice with Git. It will make you more familiar with the concept of branch and
force you to code with a precise purpose in mind before doing any modification. Finally, the concept of branch will
become much more powerful when dealing with the remote use of Git.

Local development workflow
++++++++++++++++++++++++++

To conclude, the local development workflow is as follow:

* Start from a clean repository.
* Create a new branch *develop* to isolate the development of my new feature from the stable version of the code in
  *main*. **Never work directly on the main branch!**
* Do modifications in the files.
* Test that the result is as expected.
* Do a commit.
* Repeat the 3 previous steps as much as necessary. **Try to decompose as much as possible any modification into very
  small ones**.
* Once the new feature is fully operational and tested, merge the *develop* branch into the *main* one.

Doing a commit is like saving your progression in a video game. It is a checkpoint where you will always be able to come
back to, whatever you do after.

Once you will be more familiar with Git, you will feel very safe to test any crazy modification of your code!

.. figure:: /image/tutorial_git/github_logo.png
    :width: 200

Remote use of Git: GitHub
-------------------------

`GitHub`__ is a free cloud service that **allows anyone to have Git repositories on distant servers**. Such services
allow their users to easily share their source code. They are an essential actor for the open-source development. You
can find on GitHub such projects as the `Linux kernel`__ , the software that runs `Wikipedia`__... and last but not
least: `PyMoDAQ`__!

__ https://github.com/

__ https://github.com/torvalds/linux

__ https://github.com/wikimedia/mediawiki

__ https://github.com/pymodaq/pymodaq

Other solutions exist such as `GitLab`__, but may be a bit more complicated since you will need someone to maintain
the servers that host your Git repositories.

__ https://about.gitlab.com/fr-fr/

Create an account
+++++++++++++++++

Click on *Sign up* and follow the guide. Creating an account is free.

.. figure:: /image/tutorial_git/github_sign_up.png
    :width: 600

Create a remote repository
++++++++++++++++++++++++++

Once your profile is created, go to the top right of the screen and click on the icon representing your profile.

.. figure:: /image/tutorial_git/github_account_2.png
    :width: 600

Let’s create a remote repository.

.. figure:: /image/tutorial_git/github_create_remote_repository_2.png
    :width: 600

.. figure:: /image/tutorial_git/create_remote_repository.png
    :width: 600

The next page will give us some help to *push* our *local repository* to the newly created *remote repository*.

.. figure:: /image/tutorial_git/github_push_local_repository_2.png
    :width: 600

Let’s stop here for a bit of vocabulary:

* Our **local repository** is the local folder that we created and configured to be followed by Git. Here it is our *MyAmazingProject!!!* folder, that is stored on our local machine.
* We call **remote repository** the one that we just created. Its name is *monkey_repository* and its Git address is *https://github.com/Fakegithubaccountt/monkey_repository.git*.
* When we talk about **pushing**, we mean that we upload the state of our local repository to the remote repository.
* When we talk about **cloning**, we mean that we downloaded the state of the remote repository to a local repository.

All this is summed up in the following schematic.

.. figure:: /image/tutorial_git/git_local_remote_repositories.png
    :width: 600
