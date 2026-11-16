.. _custom_extension:

Writing a PyMoDAQ custom extension
==================================

This tutorial guides through writing a PyMoDAQ extension starting from the templates provided by PyMoDAQ. From the point of view of the application, a (simulated) spectro-photometer is turned into an absorption spectrometer. Writing the corresponding plugins is covered for the sake of completeness. Advanced chapters--for the time being partially still work in progress--treat incorporating configurator, sequencer and data mixer.

The code shown in this tutorial has been developed and tested under Linux. The code itself should be portable since everything is done in Python without relying on external libraries. Nonetheless, the surrounding tools may vary on different operating systems. Setting up the module structure and similar is done on the Linux command line (or git-shell). Experienced Windows users and PyCharm experts are warmly welcome to add corresponding instructions to this tutorial to cover their beloved coding environments.

At the time of this writing (October 26) the tutorial is based on the templates in version 5.0.x, but should be compatible with future version of the 5 main branch. There is a paragraph explaining how to handle the situation with newer versions at top 

The author gratefully acknowledges the help by Sébastien Weber to set up the code demonstrated in this tutorial, as well as by Johannes Wega and Joseph Kölbel (Physical Chemistry Departement of the University of Geneva) for extensive testing.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   intro.rst
   preparation.rst
   hardware.rst
   spectro-photometer.rst
   shutter.rst
   dashboard.rst
   extension.rst
   absorption.rst
   state-manager.rst
   future.rst
