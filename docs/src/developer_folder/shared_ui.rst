  .. _shared_ui:

Shared UI
=========

Introduction
------------
All user interfaces within PyMoDAQ are sharing some features that would be complex
to maintain if declared everywhere. This is why most of the UI derive from the
:ref:`custom_app` base class. However the latter provides only the framework to quickly build interfaces
that may be very different. It doesn't provide a unified way to add direct `actions` and
access to comonly used features such as the PyMoDAQ preferences, the log file or even a
direct link to the documentation. This is the role of the SharedUi object that will
wraps CustomApps with common features (mostly actions and menus) we will describe below.


Instantiating a SharedUI
------------------------

The code below shows how to create and instantiate a SharedUI. One should first
create a MainWindow either directly or using the `make_window` method. The SharedUI
object take this window as an argument and will build on it the menus and actions,
see :numref:`naked_shared_ui`

.. code-block::
    from pymodaq_gui.utils.widgets.window import make_window
    from pymodaq_gui.utils.shared_ui import SharedUI
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('CommonWindow')

    win, area = make_window(area=False, title='SharedUI')
    window = SharedUI(win)

    window.show()

    sys.exit(app.exec())



.. _naked_shared_ui:
.. figure:: /image/shared_ui/shared_ui_naked.png
   :alt: Shared UI

   SharedUI interface.


Menu Bar Description
--------------------

Figure :numref:`naked_shared_ui` displays the menu of the *SharedUI* window with access to all the tools useful
within PyMoDAQ and described below:


The **File** menu will allow you to *Restart* or *Quit* the DashBoard

The **View** menu is allowing to display or not the various toolbars

The **Tools** menu will allow you to:

* Look at the current log file in the default editor. The older logs can be found in the *.pymodaq* folder,
  see :ref:`section_configuration`.
* Open and modify the Preferences related to all pymodaq modules and plugins (see Fig. :numref:`edit_config`)
* Run the leco Coordinator (see :ref:`leco_communication`) if the pymodaq SharedUI is used:
  ``pymodaq.utils.shared_ui import SharedUI`` is used (adding some more functionalities compared to
  the pymodaq_gui one).


  .. _edit_config:

.. figure:: /image/configuration/edit_config.png
   :alt: config_file

   Preferences popup window.

Finally, the **Help** menu will allow you to:

* Browse the documentation
* Check for PyMoDAQ updates
* Print the current versions of PyMoDAQ.



Wrapping a SharedUI around a CustomApp
--------------------------------------

As displayed on :numref:`naked_shared_ui` several menus are already created in the SharedUI. Therefore when it will
wrap a CustomApp, the application menu will be merged (if named identically) together to offer some more advanced
options while providing the basic one without having to recode them. The code to allow this is shown below for the
DashBoard case:

.. code-block::

    from pymodaq_gui.utils.widgets.window import make_window
    from pymodaq_gui.utils.shared_ui import SharedUI
    from pymodaq_gui.qt_utils import mkQApp

    from pymodaq.dashboard import DashBoard


    app = mkQApp('CommonWindow')

    win, area = make_window(title='PyMoDAQ Dashboard')

    shared_ui = SharedUI(win)
    dashboard = DashBoard(area)
    shared_ui.affect_application(dashboard)

    sys.exit(app.exec())


where all the *magic* is done using the line: :code:`shared_ui.affect_application(dashboard)`
to add the menus and actions described above on top of those of the DashBoard.

