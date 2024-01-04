.. _connect_github_with_ssh:

+------------------------------------+---------------------------------------+
| Author email                       | david.bresteau@cea.fr                 |
+------------------------------------+---------------------------------------+
| Last update                        | december 2023                         |
+------------------------------------+---------------------------------------+
| Difficulty                         | Intermediate                          |
+------------------------------------+---------------------------------------+

.. figure:: /image/tutorial_create_github_account/github_logo.png
    :width: 200

Authenticate to GitHub with an SSH key
======================================

In general, when we need to authenticate to a website, we will provide a password. Since quite recently, it is not
possible to make our local Git connect to GitHub with a password. It is now mandatory to connect with the SSH protocol
for security reasons. We thus have to follow this quite obscure procedure (it is not so bad!). After overcoming this
little difficulty, the reward will be that we will not have to enter any password anymore to interact with GitHub!

Prerequisite
------------

To follow this tutorial, you should already have a GitHub account and Git installed on your local machine. If it is not
the case, please start with the following tutorials:

:ref:`Create an account & raise an issue on GitHub <create_github_account>`

:ref:`Basics of Git and GitHub <git_tutorial>`

What is SSH?
------------

*SSH*, for Secure SHell, is a protocol that permits to connect to distant servers safely. Underlying it uses *public-key
cryptography* to implement a secure connection between our local machine (the client) and GitHub (the server). Each of
the two parts will have a *public* and a *private key*. Those *keys* are basically big numbers stored in files.

If you want to know more about SSH, you can read this documentation: `About SSH (GitHub)`__

__ https://docs.github.com/en/authentication/connecting-to-github-with-ssh/about-ssh

How to make a secure connection with SSH?
-----------------------------------------

Let’s take a big breath, we do not need to know what is happening in details! We will just follow blindly the procedure
that is proposed by GitHub. Basically there are 3 steps:

* We have to generate our private and public SSH keys (our SSH *key pair*). Our *private key* will be kept on our local
  machine.
* We then have to add our private key to the *ssh-agent*. Whatever the ssh-agent is... let say it means that we tell
  SSH to take this new private key into account and manage it.
* Finally, we will have to add our *public key* to our GitHub account.

Let’s go!

Generate our SSH key pair
+++++++++++++++++++++++++

Let’s open a *Git Bash* terminal.

.. note::
    If you are working with Windows, *Git Bash* should be installed on your machine. If it is not the case, follow the
    procedure that is described in the tutorial :ref:`Basics of Git and GitHub <git_tutorial>`.
    If you are working with Ubuntu, just use a standard terminal.

Copy-paste the following command that will generate our key pair. We should replace the email address by the one that is
linked to our GitHub account.

``$ ssh-keygen -t ed25519 -C "your_email@example.com"``

Press *Enter* to every question that is prompted.

We now have several files that are stored in a *.ssh* folder that have been created at our home (C:\\Users\\dbrestea). If
you do not see the *.ssh* directory maybe you need a Ctrl + H to show the hidden folders.

.. figure:: /image/tutorial_connect_github_with_ssh/ssh_keygen_in_ssh.png
    :width: 300

The *id_ed25519.pub* file contains our public key. The *id_ed25519* file contains our private key. We
should never reveal the content of the latter, it must stay only on our local machine.

Add our private key to the ssh-agent
++++++++++++++++++++++++++++++++++++

Now that we have our key pair, we must tell SSH to manage this key, using the following command

``$ ssh-add ~/.ssh/id_ed25519``

Add our public key to our GitHub account
++++++++++++++++++++++++++++++++++++++++

We will now copy the content of our public key with the following command, which is equivalent to opening the file and
copying its content to the clipboard

``$ clip < ~/.ssh/id_ed25519.pub``

.. note::
    Notice that we use the public key here by taking the file with the *.pub* extension.

We now have to paste it in our GitHub settings.

.. figure:: /image/tutorial_connect_github_with_ssh/github_account_settings.png
    :width: 300

.. figure:: /image/tutorial_connect_github_with_ssh/github_add_ssh_public_key.png
    :width: 600

And paste the key in the form

.. figure:: /image/tutorial_connect_github_with_ssh/github_add_ssh_public_key_form.png
    :width: 600

Finally, press the *Add SSH key* button. We are done ;)

This section has been inspired by those documentations:

`Generating a new SSH key and adding it to the ssh-agent (GitHub)`__

`Adding a new SSH key to your GitHub account (GitHub)`__

__ https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent?platform=windows

__ https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account

Concluding remarks
------------------

We are now ready to easily and safely interact with our remote repositories on GitHub!

Note that this procedure must be done again each time you want to interact with your GitHub repositories with a
different machine.

If you have any remarks regarding this tutorial please do not hesitate to :ref:`raise an issue <create_github_account>`
or write an email to the author.