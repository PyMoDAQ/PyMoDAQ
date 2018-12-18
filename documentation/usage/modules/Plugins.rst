.. _plugin_doc:

Plugins
=======

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Any new hardware has to be included in PyMoDAQ as a python plugin. This is a script containing a python object following a particular template and behaviour and inheriting from a base class.
Plugins are articulated given their type: Moves or Viewers and for the last their main dimensionality: **0D**, **1D** or **2D**.
It is recommended to start from the *template* plugins given with the base version of PyMoDAQ (daq_move_Template, daq_NDviewer_Template,...)
and available for each type of module
and then check from other examples (plugin `repository`__) the proper way of writing a plugin. You will find below some information on the **how to**
but comparison with existing ones will be beneficial.

__ https://github.com/CEMES-CNRS/Plugins


Naming convention:
------------------

For the plugin to be properly recognised by PyMoDAQ, its location and name must follow these rules:

* An actuator plugin (name: xxxx) will be a script whose name is daq_move_Xxxx (notice first X letter is capital)
* The plugin class within the script will be named DAQ_Move_Xxxx (notice the capital letters here as well)
* the script will be located within pymodaq's installed package tree in ``C:\WPy-3710\...\pymodaq\plugins\daq_move_plugins\``

* A detector plugin of dimensionality N (N=0, 1 or 2) (name: xxxx) will be a script whose name is daq_NDviewer_Xxxx (notice first X letter is capital, and replace N by 0, 1 or 2)
* The plugin class within the script will be named DAQ_NDViewer_Xxxx (notice the capital letters here as well)
* the script will be located within pymodaq's installed package tree in ``C:\WPy-3710\...\pymodaq\plugins\daq_viewer_plugins\plugins_ND`` (replace N by 0, 1 or 2)

.. _hardware_settings:

Hardware Settings
-----------------

An important feature similar for all modules is the layout as a tree structure of all the hardware parameters.
These settings will appear on the UI as a tree of parameters with a title and different types, see :numref:`figure_settings`.
On the module side, they will be instantiated as a list of dictionaries and later exist in the object ``self.settings``.
This object is based on the ``Parameter`` object defined in `pyqtgraph`__.

__ http://www.pyqtgraph.org/documentation/parametertree/index.html

   .. _figure_settings:

.. figure:: /image/settings_example.png
   :alt: Settings example


   Typical hardware settings represented as a tree structure (here from the ``daq_2Dviewer_AndorCCD`` plugin)

Here is an example of such a dictionary corresponding to :numref:`figure_settings`:

.. code-block:: python

   [{'title': 'Dll library:', 'name': 'andor_lib', 'type': 'browsepath', 'value': libpath},
    {'title': 'Camera Settings:', 'name': 'camera_settings', 'type': 'group', 'expanded': True, 'children': [
        {'title': 'Camera SN:', 'name': 'camera_serialnumber', 'type': 'int', 'value': 0, 'readonly': True},
        {'title': 'Camera Model:', 'name': 'camera_model', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Readout Modes:', 'name': 'readout', 'type': 'list', 'values': ['FullVertBinning','Imaging'], 'value': 'FullVertBinning'},
        {'title': 'Readout Settings:', 'name': 'readout_settings', 'type': 'group', 'children':[
            {'title': 'single Track Settings:', 'name': 'st_settings', 'type': 'group', 'visible': False, 'children':[
                {'title': 'Center pixel:', 'name': 'st_center', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                {'title': 'Height:', 'name': 'st_height', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                ]},]}]}]

The list of available types of parameters :module:`custom_parameter_tree` (defined in ``pymodaq.daq_utils.custom_parameter_tree.py``) is:

* ``group`` : "camera settings" on :numref:`figure_settings` is of type group
* ``int`` : settable integer (SpinBox_Custom object)
* ``float`` : settable float (SpinBox_Custom object)
* ``str`` : a QLineEdit object (see Qt5 documentation)
* ``list`` : "Readout Modes" :numref:`figure_settings` is a combo box
* ``bool`` : checkable boolean
* ``led`` : checkable boolean in the form of a green (True) of red (False) led
* ``date_time`` : a QDateTime object (see Qt5 documentation)
* ``date`` : a QDate object (see Qt5 documentation)
* ``time`` : a QTime object (see Qt5 documentation)
* ``slide`` : a combination of a slide and spinbox for floating point values
* ``itemselect`` : an object to easily select one or more items among a few
* ``browsepath``: a text area and a pushbutton to select a given path or file
* ``text`` : a text area (for comments for instance)

Once the module is initialized, any modification on the UI hardware settings will be send to the plugin through
the ``commit_settings`` method of the plugin class and illustrated below (still from the ``daq_2Dviewer_AndorCCD`` plugin).
The ``param`` method argument is of the type ``Parameter`` (from ``pyqtgraph``):

.. code-block:: python

    def commit_settings(self,param):
        """
            | Activate parameters changes on the hardware from parameter's name.
        """
        try:
            if param.name()=='set_point':
                self.controller.SetTemperature(param.value())

            elif param.name() == 'readout' or param.name() in custom_parameter_tree.iter_children(self.settings.child('camera_settings', 'readout_settings')):
                self.update_read_mode()

            elif param.name()=='exposure':
                self.controller.SetExposureTime(self.settings.child('camera_settings','exposure').value()/1000) #temp should be in s
                (err, timings) = self.controller.GetAcquisitionTimings()
                self.settings.child('camera_settings','exposure').setValue(timings['exposure']*1000)
            elif param.name() == 'grating':
                index_grating = self.grating_list.index(param.value())
                self.get_set_grating(index_grating)
                self.emit_status(ThreadCommand('show_splash', ["Setting wavelength"]))
                err = self.controller.SetWavelengthSR(0, self.settings.child('spectro_settings','spectro_wl').value())
                self.emit_status(ThreadCommand('close_splash'))






DAQ Move plugin template
------------------------

An actuator plugin is a python class inheriting from a base class. Let's say you want to create the *template* plugin.
You will first create a ``daq_move_Template.py`` file in the ``\pymodaq\plugins\daq_move_plugins`` folder.
The plugin class will be called ``DAQ_Move_Template``.

See :download:`daq_move_Template.py <daq_move_Template.py>` for a detailed template.


.. _viewer_plugins:

DAQ Viewer plugin template
--------------------------

A detector plugin is a python class inheriting from a base class. Let's say you want to create the *template* plugin.
You will first create a ``daq_NDviewer_Template.py`` file in the ``\pymodaq\plugins\daq_viewer_plugins\plugins_ND\``
folder (with N=0, 1 or 2 depending the data dimensionality of your detector).
The plugin class will be called ``DAQ_NDViewer_Template``.

See :download:`daq_NDviewer_Template.py <daq_NDviewer_Template.py>` for a detailed template.

Emission of data
****************
When data are ready (see :ref:`data_ready` to know about that), the plugin has to notify the viewer module in order
to display data and eventually save them. For this PyMoDAQ use two types of signals (see pyqtsignal documentation for details):

* ``data_grabed_signal_temp``
* ``data_grabed_signal``

They both *emit* the same type of signal but will trigger different behaviour from the viewer module. The first is to be
used to send temporary data to update the plotting but without triggering anything else (so that the DAQ_Scan still awaits
for data completion before moving on). It is also used in the initialisation of the plugin in order to preset the type and number of data viewers
displayed by the viewer module. The second signal is to be used once data are fully ready to be send back to the user interface
and further processed by DAQ_Scan or DAQ_Viewer instances. The code below is an example of emission of data:

.. code-block:: python

    self.data_grabed_signal.emit([OrderedDict(name='Camera',data=[data2D_0, data2D_1,...], type='Data2D',x_axis=vector_X,y_axis=vector_Y),
                                  OrderedDict(name='Spectrum',data=[data1D_0, data1D_1,...], type='Data1D',x_axis=vector_X),
                                  OrderedDict(name='Current',data=[data0D_0, data0D_1,...], type='Data0D'),
                                  OrderedDict(name='Datacube',data=[dataND_0, dataND_1,...], type='DataND', nav_axes=[0,2]),
                                            ])

Such an emitted signal would trigger the initialization of 4 data viewers in the viewer module. One for each ``OrderedDict``
in the emitted list. The type of data viewer will be determined by the *type* key value while its name will be set to the *name* key value.
The *data* key value is also a list of numpy arrays, their shape should be adequate with the *type* key of the dictionary.
Each array will generate one channel within the corresponding viewer. Here is the detailed list of the possible keys:

* ``name``: will display the corresponding value on the viewer dock
* ``type``: will set the viewer type (0D, 1D, 2D or multi-dimensional ND). The ND viewer will be able to deal with data dimensionality up to 4)
* ``data``: list of numpy array. Each array shape should correspond to the *type*
* ``x_axis``: numpy 1D array representing the x axis of the detector (wavelength for a spectrometer for instance). Default is pixel number
* ``y_axis``: numpy 1D array representing the y axis of the detector (only for 2D datas). Default is pixel number
* ``nav_axis``: in case of a ND data viewer, will be the index of the navigation axis, see :ref:`NDviewer`

.. _data_ready:

Data ready?
***********
One difficulty with these viewer plugins is to determine when data is ready to be read from the controller and then
to be send to the user interface for plotting and saving. There are a few solutions:

* **synchronous**: The simplest one. When the ``grab`` command has been send to the controller (let's say to its ``grab_sync`` method), the ``grab_sync`` method will hold and freeze the plugin until the data are ready. The Mock or Tektronix modules work like this.
* **asynchronous**: There are 2 ways of doing asynchronous *waiting*. The first is to poll the controller state to check if data are
  ready within a loop. This polling could be done with a while loop but if nothing more is done then the plugin will still be
  freezed, except if one process periodically the Qt queue event using ``QtWidgets.QApplication.processEvents()`` method. The
  polling can also be done with a timer event, firing periodically a check of the data state (ready or not). Finally, the
  nicest/hardest solution is to use callbacks (if the controller provides one) and link it to a ``emit_data`` method.

Synchronous example:
********************

The code below illustrates the poll method using a loop:

.. code-block:: python

    def poll_data(self):
        """
        Poll the current data state
        """
        sleep_ms=50
        ind=0
        data_ready = False
        while not self.controller.is_ready():
            QThread.msleep(sleep_ms)

            ind+=1

            if ind*sleep_ms>=self.settings.child(('timeout')).value():

                self.emit_status(ThreadCommand('raise_timeout'))
                break

            QtWidgets.QApplication.processEvents()
        self.emit_data()

Asynchronous example:
*********************

The code below is derived from *daq_Andor_SDK2* (in *andor* hardware folder) and shows how to create a thread waiting for data ready and triggering the emission of data

.. code-block:: python

    class DAQ_AndorSDK2(DAQ_Viewer_base):

        callback_signal = QtCore.pyqtSignal() #used to talk with the callback object
        ...

        def ini_camera(self):
            ...
            callback = AndorCallback(self.controller.WaitForAcquisition) # the callback is linked to the controller WaitForAcquisition method
            self.callback_thread = QtCore.QThread() #creation of a Qt5 thread
            callback.moveToThread(self.callback_thread) #callback object will live within this thread
            callback.data_sig.connect(self.emit_data)  # when the wait for acquisition returns (with data taken), emit_data will be fired

            self.callback_signal.connect(callback.wait_for_acquisition) #
            self.callback_thread.callback = callback
            self.callback_thread.start()

        def grab(self,Naverage=1,**kwargs):
            ...
            self.callback_signal.emit()  #trigger the wait_for_acquisition method

    def emit_data(self):
        """
            Function used to emit data obtained by callback.
        """
        ...
        self.data_grabed_signal.emit([OrderedDict(name='Camera',data=[np.squeeze(self.data.reshape((sizey, sizex)).astype(np.float))], type=self.data_shape)])


    class AndorCallback(QtCore.QObject):

        data_sig=QtCore.pyqtSignal()
        def __init__(self,wait_fn):
            super(AndorCallback, self).__init__()
            self.wait_fn = wait_fn

        def wait_for_acquisition(self):
            err = self.wait_fn()

            if err != 'DRV_NO_NEW_DATA': #will be returned if the main thread called CancelWait
                self.data_sig.emit()

Documentation from Andor SDK concerning the WaitForAcquisition method of the dll:

..

  | *unsigned int WINAPI WaitForAcquisition(void)*
  |
  | ``WaitForAcquisition`` can be called after an acquisition is started using StartAcquisition to put the calling thread to sleep until an Acquisition Event occurs.
  | It will use less processor resources than continuously polling with the GetStatus function. If you wish to restart the calling thread without waiting for an Acquisition event, call the function CancelWait.




Hardware needed files
---------------------

If you are using/referring to custom python wrappers/dlls... within your plugin and need a place where to copy them
in PyMoDAQ, then use the ``\pymodaq\plugins\hardware`` folder. For instance, the ``daq_2Dviewer_AndorCCD`` plugin need various files stored
in the ``andor`` folder (on github repository). I would therefore copy it as ``\pymodaq\plugins\hardware\andor``
and call whatever module I need within (meaning there is a __init__.py file in the *andor* folder) as:

.. code-block:: python

    #import controller wrapper
    from pymodaq.plugins.hardware.andor import daq_AndorSDK2 #this import the module DAQ_AndorSDK2 containing classes, methods...
    #and then use it as you see fit in your module


Specific TCP/IP plugin
----------------------

It is possible to use a TCP/IP plugin in order to communicate with a distant client. For instance, the module
``daq_2Dviewer_TCP_GRABBER`` is one such example. It inherits from the base ``DAQ_TCP_Server`` class:

.. code-block:: python

    from pymodaq.daq_viewer.utility_classes import DAQ_TCP_server

This plugin is still experimental and focused on one particular relation with a client. Please open an issue on github
if you have specific need and/or propositions.
