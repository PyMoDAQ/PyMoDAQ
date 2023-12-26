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
allow their users to easily share their source code. They are an essential actors for the open-source development. You
can find on GitHub such projects as the `Linux kernel`__, the software that runs `Wikipedia`__... and last but not
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

* Our **local repository** is the local folder that we created and configured to be followed by Git. Here it is our
  *MyAmazingProject!!!* folder, that is stored on our local machine.
* We call **remote repository** the one that we just created. Its name is *monkey_repository* and its Git address is
  *https://github.com/Fakegithubaccountt/monkey_repository.git*.
* When we talk about **pushing**, we mean that we upload the state of our local repository to the remote repository.
* When we talk about **cloning**, we mean that we downloaded the state of the remote repository to a local repository.

All this is summed up in the following schematic.

.. figure:: /image/tutorial_git/git_local_remote_repositories.png
    :width: 600

Push our local repository to GitHub
+++++++++++++++++++++++++++++++++++

We started this tutorial from a local folder. What we will do now is to push this repository to GitHub servers.

Note that it is not obvious that you will always work this way. Most of the time, you will start by cloning a remote
repository to your local machine.

We will follow what is recommanded at the end of the last web page (red frame). `This documentation`__ may also be
helpful to deal with GitHub remote repositories.

__ https://docs.github.com/en/get-started/getting-started-with-git/managing-remote-repositories?platform=windows

With the following command, we tell Git that our local repository (the folder where we are executing the command) is now
connected to the remote repository that we just created on GitHub. The latter is called *origin*.

.. figure:: /image/tutorial_git/git_add_remote.png
    :width: 600

With the next command we just check that everything is as expected. We call for information about the remote repository.

.. figure:: /image/tutorial_git/git_remote_v.png
    :width: 600

This is all good. The first line, ending with *fetch*, means that when we will ask to update our local repository (with
a *pull* command, we will see that latter), it will call the origin repository. The second line, ending with *push*,
means that when we will ask to update the remote repository with the work we have done locally, it will go to origin.

Let us try to push our repository.

.. figure:: /image/tutorial_git/git_push_fatal_authentication.png
    :width: 600

Here there is an error because we need to authenticate to GitHub, he will not let anyone push what he wants on this
repository! We have to proove him that we own the repository. The authentication is a bit more complicated than using a
password, but we will explain it step by step in the next section.

Authentication to GitHub with an SSH key
++++++++++++++++++++++++++++++++++++++++

This operation will have to be done each time you want to do operations on your remote repository with a different
machine. But if you keep the same computer, you do it once and then no more password will never be asked.

We will make a secure connection with an SSH key. To do so, we just have to follow those documentations:

`Generating a new SSH key (GitHub)`__

__ https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

`Adding a new SSH key to a GitHub account`__

__ https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account

Let start by generating a new SSH key. Put the email address that is linked with the GitHub account that you just
created.

.. figure:: /image/tutorial_git/ssh_keygen.png
    :width: 600

We now start the ssh agent

.. figure:: /image/tutorial_git/ssh_key_agent.png
    :width: 600

and add the SSH private key to the ssh-agent.

.. figure:: /image/tutorial_git/ssh-add.png
    :width: 600

This command will create a new SSH key that will be stored in the .ssh folder at your home.

.. figure:: /image/tutorial_git/ssh_keygen_in_ssh.png
    :width: 300

The following command is equivalent to copying the content of the key to your clipboard.

.. figure:: /image/tutorial_git/ssh-copy-key.png
    :width: 600

We now have to paste it in our GitHub profile. Go to the settings.

.. figure:: /image/tutorial_git/github_account_settings.png
    :width: 300

.. figure:: /image/tutorial_git/github_add_ssh_private_key.png
    :width: 600

And paste the key in the form

.. figure:: /image/tutorial_git/github_add_ssh_private_key_form.png
    :width: 600

Push our local repository to GitHub (Part II)
+++++++++++++++++++++++++++++++++++++++++++++

Let’s try to push again!

.. figure:: /image/tutorial_git/git_push_success.png
    :width: 600

.. note::
    Here I cheated a bit. GitHub was not autorizing that I add a SSH key with a fake account, so I switched to my real
    account (github.com/quantumm) and I created there the monkey_repository, but if you did not provide a fake email
    address it should work fine! :)

Our file is online!

.. figure:: /image/tutorial_git/repository-online.png
    :width: 600

But it is not like we just store a file on a server, we also have access to all the history of the commits.

.. figure:: /image/tutorial_git/quantum_monkey_repository.png
    :width: 600

Here they are.

.. figure:: /image/tutorial_git/quantum_monkey_repository_commits.png
    :width: 600

Let’s click on the second commit *The monkey has been added in our file*.

.. figure:: /image/tutorial_git/quantum_monkey_commit.png
    :width: 600

Here he is!

We see that the GitHub website provides an equivalent to what we see in the terminal.

Finally, the development workflow is as follow:

* Do modifications in the file on your local repository.

* Test that the result is as expected.

* Do a commit.

* You can repeat the previous steps several times.

* At the end of the day, push all your commits to your remote repository.

**Now, your remote repository should always be your reference, and not your local version anymore!**

The lastest version of your code must be stored on the server, not locally. Once your push is done, you can safely
delete your local folder. You will be able to get your code back at the latest version at any time from any computer,
thanks to the *clone* command.

The *clone* command
+++++++++++++++++++

Let start by deleting our folder locally. This command is equivalent to right-click on the folder and Delete.

.. figure:: /image/tutorial_git/rm-rf-directory.png
    :width: 300

Since our work is now stored in the GitHub server, it is not a problem even if our computer goes up in smoke. We can
get it back with the following command.

First, copy the adress of the repository

.. figure:: /image/tutorial_git/git-clone.png
    :width: 600

Then, clone the repository

.. figure:: /image/tutorial_git/git-clone-command.png
    :width: 600

We created a *pmd_pretraining_git* folder and cd into it just to start from a fresh folder. The command created a
subfolder monkey_repository with our file into it.

.. figure:: /image/tutorial_git/git-clone-result.png
    :width: 400

We found our work back!

Notice that when you clone a repository, you do not need anymore the *init* command.
You do not need either to configure the address of the remote repository, Git already
knows where you took it from.

.. figure:: /image/tutorial_git/result_of_cloning.png
    :width: 600

You can do this for any public repository on GitHub, which allows you to download
basically all the open-source codes in the world!

Git in practice: integration within PyCharm
-------------------------------------------

We started this tutorial by presenting the use of Git with the command line for educational purposes. There are several
graphical user interfaces that can ease the use of Git in the daily life, such as `GitHub Desktop`__ if you are working
with Windows.

__ https://docs.github.com/en/desktop/installing-and-authenticating-to-github-desktop/installing-github-desktop

However, we will rather recommand to use the direct integration within your favorite Python IDE, because it does not
require to download another software, and because it is cross platform. We will present the practical use of Git with
`PyCharm`__.

__ https://www.jetbrains.com/pycharm/

Register your GitHub account
++++++++++++++++++++++++++++

As a first step, we should autorize PyCharm to connect to our GitHub account. We recommand to use a token. This way we
will not have to enter a password each time PyCharm needs to connect to GitHub. The procedure is described in the
following documentations:

`PyCharm & GitHub (jetbrains.com)`__

__ https://www.jetbrains.com/help/pycharm/github.html#9c1dc6ec

`PyCharm Integration with GitHub (medium.com)`__

__ https://medium.com/@akshay.sinha/pycharm-integration-with-github-876510c6ca1f

Clone a project
+++++++++++++++

We first clone the *monkey_repository* from our GitHub account. Go to Git > Clone..., select the remote repository and
a local folder where the files will be saved (it does not matter where we decide to save locally the repository).

.. figure:: /image/tutorial_git/pycharm_clone.png
    :width: 600

Configure our Python environment
++++++++++++++++++++++++++++++++

Once the remote repository has been cloned, we have to configure our environment. Go to File > Settings... and select
our Conda environment (here *pmd4*).

.. figure:: /image/tutorial_git/pycharm_configure_environment.png
    :width: 600

Create a new branch
+++++++++++++++++++

Here are the main important places on the PyCharm interface to manage Git.

.. figure:: /image/tutorial_git/pycharm_git_interface.png
    :width: 600

We will follow our best practices and create a new local branch before modifying the files in the repository. To do so
we click on the Git branch button and create a new branch that we call *develop*.

Diff & commit
+++++++++++++

Let’s now add a bird in the file. Go to Git > Commit... It will open a window that allows us to easily see the files
that have been modified. If we right click on *my_new_file.md* and select *Show diff*, we will see the difference
between the two versions of the file, just as with the command line, but with a more evolved interface.

.. figure:: /image/tutorial_git/pycharm_git_commit.png
    :width: 600

If we are happy with that, we can close this window and commit our changes.

Log
+++

If we open the Git bottom panel we can have information about the local and remote branches, and the history of the
commits.

.. figure:: /image/tutorial_git/pycharm_git_log.png
    :width: 800

Add a file
++++++++++

Adding a file is also very easy since you just have to paste it in the right folder within the *Project* panel of
PyCharm. It will automatically ask us if we want Git to track the new file.

Push
++++

To send our changes to the remote repository we just have to go to Git > Push... in the main menu.

The PyMoDAQ repositories
------------------------

From the previous sections we know how to connect our local repository to our remote repository. But up to now we just
worked on our own. In the next section will learn how to contribute to an existing project like PyMoDAQ!

Let’s now go to the `PyMoDAQ GitHub account`__.

__ https://github.com/PyMoDAQ

.. figure:: /image/tutorial_git/pmd_github_account.png
    :width: 600

There are a lot of repositories, most of them correspond to *Python packages*. Briefly, there is:

* The `PyMoDAQ repository`__: this is the core of the code, you cannot run PyMoDAQ without it.

* The plugins’ repositories: those repositories follow the naming convention *pymodaq_plugins_<name>*. Most of the time,
  *<name>* corresponds to the name of an instrument supplier, like *Thorlabs*. Those are optional pieces of code. They
  will be useful depending on the instruments the final user wants to control.

__ https://github.com/PyMoDAQ/PyMoDAQ

Troubleshoot PyMoDAQ: raise an issue on GitHub
++++++++++++++++++++++++++++++++++++++++++++++

The main feature of GitHub is the repository hosting, but it also propose some very usefull functionalities around the
repositories. One of the most important is the possibility for any user to raise an *issue*.

.. figure:: /image/tutorial_git/pmd_repository_issue_V3.png
    :width: 600

.. figure:: /image/tutorial_git/pmd_repository_open_issue.png
    :width: 600

Anytime you face a problem or a bug in the program you can raise an issue. Describe as precisely your problem. A
discussion will be opened with the developers who will try to help you. This is the most efficient way to troubleshoot
PyMoDAQ because the history of the issues is conserved, which could be helpful to solve future problems. This
contributes to the documentation of the code. **You don’t need to know the code to raise an issue, and it is really
helpful to improve the stability of the program, so don’t hesitate to do so ;)**

With such functionalities, the GitHub repository is the meeting point of the community around PyMoDAQ.

PyMoDAQ branches
++++++++++++++++

.. figure:: /image/tutorial_git/pmd_branches.png
    :width: 600

There are several branches of the PyMoDAQ repository. The most important ones are:

* **main** This is the most stable branch. It is the present state of the code. When you install PyMoDAQ with pip, it
  is this version of the code that is downloaded.

* **pymodaq-dev** This is the development branch. It is *ahead* of the main branch, in the sense that it contains more
  recent commits than the main branch. It is thus the future state of the code. This is where the last developments
  of the code of PyMoDAQ are pushed. When the developers are happy with the state of this branch, typically when they
  finished to develop a new functionality and they tested it, they will merge the develop branch into the main branch,
  which will lead to a new *release* of PyMoDAQ.

How to propose a modification of the code of PyMoDAQ?
+++++++++++++++++++++++++++++++++++++++++++++++++++++

Compared to our previous situation where we had to deal with our local repository and our remote repository, we now have
to deal with an external repository on which we have no right. This external repository, which in our example is the
PyMoDAQ one, is called the **upstream repository**. The workflow is represented below and we will detail each step in
the following.

.. figure:: /image/tutorial_git/git_full_repositories.png
    :width: 600

**(1) Fork the upstream repository**

While you are connected to your GitHub account, go to the PyMoDAQ repository and select the *pymodaq-dev branch*. Then
click on the *Fork* button.

.. figure:: /image/tutorial_git/fork_pmd.png
    :width: 600

This will create a copy of the PyMoDAQ repository on our personal account, it then become our remote repository and **we
have every right on it**.

.. figure:: /image/tutorial_git/fork_pmd_on_quantumm.png
    :width: 600

**Every modification of the code of PyMoDAQ should first go on the pymodaq-dev branch, and not on the main branch**.
The proper way to propose our contribution is that we create a branch from the pymodaq-dev branch, so that it will ease
the integration of our modifications and isolate or work from other contributions.

We create a branch *monkey-branch* from the *pymodaq-dev* branch.

.. figure:: /image/tutorial_git/create-branch.png
    :width: 600

**(2) Clone our new remote repository locally**

We will now clone our repository locally. We can clone a particular branch of the repository with the following command

.. figure:: /image/tutorial_git/clone_monkey_branch.png
    :width: 600

Rather than the comand line, you can also clone directly from PyCharm, like we did in the previous section.

**(3) Do modifications and push**

We now have the PyMoDAQ code on our local machine. We will put the monkey into the README.rst file at the root of the
PyMoDAQ package. This file is the one that is displayed at the home page of a repository.

.. figure:: /image/tutorial_git/monkey_in_readme.png
    :width: 600

Let’s commit and push.

.. figure:: /image/tutorial_git/push_the_monkey.png
    :width: 600

Here is the result on our remote repository.

.. figure:: /image/tutorial_git/see_monkey_in_repository.png
    :width: 600

The monkey looks more like a crocodile now... it is not very satisfactory. But anyway we will propose this modification
of the code!

**(4) Pull request (PR) to the upstream repository**

We can be very proud of our modification, but of course, this will not be implemented directly, we will need the
agreement of the owner of the PyMoDAQ repository.

**Opening a pull request is proposing a modification of the code to the owner of the upstream repository**. This is
again very easy through the GitHub interface.

.. figure:: /image/tutorial_git/pull_request_the_monkey.png
    :width: 600

Be careful to properly select the branch of your repository and the branch of the upstream repository, and then send.
That’s it! You now have to wait for the answer of the owner of the repository. Let’s hope he will appreciate our work!
You can see the status of your PR on the PyMoDAQ repository home page.

.. figure:: /image/tutorial_git/pmd_pr_tab.png
    :width: 600

Conclusion
----------

You now master the basics of the worldwide standard for code development!

Following those guidelines, you will code more efficiently. Git is appropriate for any (descent) language (not Word or
Labview!).

It is an indispensable tool if you want to share your code with colleagues and not reinvent the wheel.

Git is one of the reasons why you will make better acquisition programs with PyMoDAQ than with Labview ;)

Here are a few external ressources:

`The YouTube channel of Grafikart (in French)`__

__ https://www.youtube.com/watch?v=rP3T0Ee6pLU&list=PLjwdMgw5TTLXuY5i7RW0QqGdW0NZntqiP&index=2

`The course of OpenClassroom (in English)`__

__ https://openclassrooms.com/en/courses/7476131-manage-your-code-project-with-git-and-github

`The Pro Git book (in English)`__. Exhaustive and painful. You will probably not need it!

__ https://git-scm.com/book/en/v2