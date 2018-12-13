Main Modules
============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   DAQ_Move
   DAQ_Scan
   DAQ_Viewer

Introduction
------------

Any instance of the programm use two main thread by module:
	 * the gui interface of the standalone instance of the current class
	 * the hardware linked codes to synchronise the users action.

| The two main threads are linked by signals.
| The message passing procedure is also made by signals.
| A message passing signal generally contain data list, events or commands.
| The thread commands signals contain the name of the command as a string and an attribute list.
| The attribute list is splittable to transmit variable length arguments to function if needed.
| The events signals are used to transmit an event to the parent / to the gui interface (in case of sending parameters status for example).
| Data signals are used to transmit values array / list between the gui interface and the main program (in case of viewer data for example).

| Each module work independantly of the others, eventually linked by the user.
| 
| 
	
The program works with PyQt5 library including :
	 * QtWidgets
	 * QtGui
	 * QObject
	 * pyqtSlot
	 * QThread
	 * pyqtSignal
	 * Qlocale

`Ref doc link`_.

.. _Ref doc link: http://doc.qt.io/qt-5/qt5-intro.html