Any new hardware has to be included in PyMoDAQ as a plugin. A PyMoDAQ's plugin is a script containing a python object
following a particular template and behaviour and inheriting from a base class.
Plugins are articulated given their type: Moves or Viewers and for the latter their main dimensionality: **0D**, **1D** or **2D**.
It is recommended to start from the *template* plugins (daq_move_Template, daq_NDviewer_Template, see below)
and then check from other examples (pymodaq_plugins `repository`__) the proper way of writing a plugin.
You will find below some information on the **how to** but comparison with existing ones will be beneficial.

__ https://github.com/PyMoDAQ/pymodaq_plugins

Installation
------------

The main and official list of plugins is located in the `pymodaq_plugins`__ repository on github. This constitutes a
list of (contributed) python package that can be installed using the :ref:`PluginManager`. Other unofficial  plugins may
also be installed if they follow PyMoDAQ's plugin specifications but you are invited to let know other users of the plugins
you develop in order to contribute to PyMoDAQ's development.

PyMoDAQ is looking at startup for all installed packages that it can consider as its plugins. This includes by default
the *pymodaq_plugins* package installed on the *site_packages* location in python distribution.

__ https://github.com/PyMoDAQ/pymodaq_plugin_manager

Contributions:
--------------

Users are welcomed to contribute to PyMoDAQ by writing their own plugins. Two approaches are possible:

* Fork one of the official plugin package repositories and add within your own plugin scripts
* Copy the `plugin template package`__ on you disk and work on the templates within then ask to create an official
  plugin package

__ https://github.com/PyMoDAQ/pymodaq_plugins_template

Naming convention:
------------------

For the plugin to be properly recognised by PyMoDAQ, its location and name must follow some rules and syntax. The
`plugin template package`__ could be copied locally as a starting point:

* An actuator plugin (name: xxxx) will be a script whose name is daq_move_Xxxx (notice first X letter is capital)
* The plugin class within the script will be named DAQ_Move_Xxxx (notice the capital letters here as well)

* A detector plugin of dimensionality N (N=0, 1, 2 or N) (name: xxxx) will be a script whose name is daq_NDviewer_Xxxx (notice first X letter is capital, and replace N by 0, 1 or 2)
* The plugin class within the script will be named DAQ_NDViewer_Xxxx (notice the capital letters here as well)

__ https://github.com/PyMoDAQ/pymodaq_plugins_template

.. _hardware_settings:

Hardware Settings
-----------------

An important feature similar for all modules is the layout as a tree structure of all the hardware parameters.
These settings will appear on the UI as a tree of parameters with a title and different types, see :numref:`figure_settings`.
On the module side, they will be instantiated as a list of dictionaries and later exist in the object ``self.settings``.
This object inherits from the ``Parameter`` object defined in `pyqtgraph`__.


__ http://www.pyqtgraph.org/documentation/parametertree/index.html

   .. _figure_settings:

.. figure:: /image/settings_example.PNG
   :alt: Settings example

   Typical hardware settings represented as a tree structure (here from the ``daq_2Dviewer_AndorCCD`` plugin)

Here is an example of such a list of dictionaries corresponding to :numref:`figure_settings`:

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


.. _parameter_tree:

The list of available types of parameters :module:`pymodaq_ptypes`
(defined in ``pymodaq.daq_utils.parameter.pymodaq_ptypes.py``) is:

* ``group`` : "camera settings" on :numref:`figure_settings` is of type group
* ``int`` : settable integer (SpinBox_Custom object)
* ``float`` : settable float (SpinBox_Custom object)
* ``str`` : a QLineEdit object (see Qt5 documentation)
* ``list`` : "Readout Modes" :numref:`figure_settings` is a combo box
* ``bool`` : checkable boolean
* ``bool_push`` : a checkable boolean in the form of a QPushButton
* ``led`` : non checkable boolean in the form of a green (True) of red (False) led
* ``led_push`` : checkable boolean in the form of a green (True) of red (False) led
* ``date_time`` : a QDateTime object (see Qt5 documentation)
* ``date`` : a QDate object (see Qt5 documentation)
* ``time`` : a QTime object (see Qt5 documentation)
* ``slide`` : a combination of a slide and spinbox for floating point values (linear of log scale)
* ``itemselect`` : an object to easily select one or more items among a few
* ``browsepath``: a text area and a pushbutton to select a given path or file
* ``text`` : a text area (for comments for instance)

**Important**: the *name* key in the dictionnaries must **not** contain any space, please use underscore if necessary!

.. note::

  For a live example of these Parameters and their widget, type in ``parameter_example`` in your shell or check the
  example folder


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



.. _data_emission:

Emission of data
****************
When data are ready (see :ref:`data_ready` to know about that), the plugin has to notify the viewer module in order
to display data and eventually save them. For this PyMoDAQ use two types of signals (see pyqtsignal documentation for details):

* ``data_grabed_signal_temp``
* ``data_grabed_signal``

They both *emit* the same type of signal but will trigger different behaviour from the viewer module. The first is to be
used to send temporary data to update the plotting but without triggering anything else (so that the DAQ_Scan still awaits
for data completion before moving on). It is also used in the initialisation of the plugin in order to preset the type
and number of data viewers displayed by the viewer module. The second signal is to be used once data are fully ready to
be send back to the user interface
and further processed by DAQ_Scan or DAQ_Viewer instances. The code below is an example of emission of data:

.. code-block:: python

    from pymodaq.daq_utils.daq_utils import Axis
    from pymodaq.daq_utils.daq_utils import DataFromPlugins
    x_axis = Axis(label='Wavelength', units= "nm", data = vector_X)
    y_axis = Axis(data=vector_Y)
    self.data_grabed_signal.emit([DataFromPlugins(name='Camera',data=[data2D_0, data2D_1,...],
                                        dim='Data2D', x_axis=x_axis,y_axis=y_axis),
                                  DataFromPlugins(name='Spectrum',data=[data1D_0, data1D_1,...],
                                        dim='Data1D', x_axis=x_axis, labels=['label0', 'label1', ...]),
                                  DataFromPlugins(name='Current',data=[data0D_0, data0D_1,...],
                                        dim='Data0D'),
                                  DataFromPlugins(name='Datacube',data=[dataND_0, dataND_1,...],
                                        dim='DataND', nav_axes=[0,2]),
                                        nav_x_axis=NavAxis(data=.., label='Xaxis', units= "µm", nav_index=0])

Such an emitted signal would trigger the initialization of 4 data viewers in the viewer module. One for each ``DataFromPlugins``
in the emitted list. The type of data viewer will be determined by the *dim* key value while its name will be set to the *name* key value.
The *data* key value is also a list of numpy arrays, their shape should be adequate with the *dim* key of the dictionary. (in fact the
*dim* key could be omitted as the ``DataFromPlugins`` class check its values or assess it from the data numpy array shape.
Each array will generate one channel within the corresponding viewer. Here is the detailed list of the possible keys:

* ``name``: will display the corresponding value on the viewer dock
* ``dim``: (either 'Data0D', 'Data1D', 'Data2D' or 'DataND') will set the viewer type (0D, 1D, 2D or multi-dimensional ND). The ND viewer will be able to deal with data dimensionality up to 4)
* ``data``: list of numpy array. Each array shape should correspond to the *type*
* ``labels``: list of string, one for each numpy array within the ``data`` field. Will be displayed on 0DViewer and 1DViewer
* ``x_axis``: **Axis** instance containing various fields to set the axis *label*, *units* and *data* on the viewer
  (see code above and the Axis object in the daq_utils module)
* ``y_axis``: **Axis** instance containing various fields to set the axis *label*, *units* and *data* on the viewer
  (see code above and the Axis object in the daq_utils module)
* ``nav_axes``: in case of a ND data viewer, will be the index of the navigation axis, see :ref:`NDviewer`
* ``nav_x_axis``: **NavAxis** instance containing various fields to set the axis *label*, *units* and *data* on the NDViewer, concerning the navigation viewer
  (see code above, the NavAxis object in the daq_utils module and the paragraph below)
* ``nav_y_axis``: **NavAxis** instance containing various fields to set the axis *label*, *units* and *data* on the NDViewer, concerning the navigation viewer
  (see code above, the NavAxis object in the daq_utils module and the paragraph below)

To export properly ND datas, the DataFromPlugins object must have 2 other arguments set (compared to 0D, 1D or 2D datas):

* nav_axes: it is a tuple of integers telling which dimensions of the data numpy array is to be considered as navigation
  axis. The first integer of the tuple will be used as the *xaxis* in the viewers (1D or 2D) while the second will be
  used as the *yaxis* in the viewers.
* the navigation axis objects (optional): these are arguments starting by *nav* (the *_x_axis* or *_y_axis* or whatever
  part is just there to clarify the meaning for the reader of the code) and are instances of **NavAxis**. A
  **NavAxis** is similar to the **Axis** object but **have an important supplementary argument** that is *nav_index*.
  This one will be used to sort all navigation axes. An index of 0 means this particular NavAxis will be used to display
  properties of the *xaxis* on the viewers

:numref:`figure_viewerND` highlights how these arguments will change the behaviour of the NDviewer.


   .. _figure_viewerND:

.. figure:: /image/DAQ_Viewer/viewerND_axes.png
   :alt: NavAxis stuff

   An example of 3D datas with 2 navigation axes and how these will be displayed by the NDviewer.



.. _data_ready:

Data ready?
***********
One difficulty with these viewer plugins is to determine when data is ready to be read from the controller and then
to be send to the user interface for plotting and saving. There are a few solutions:

* **synchronous**: The simplest one. When the ``grab`` command has been send to the controller (let's say to its
  ``grab_sync`` method), the ``grab_sync`` method will hold and freeze the plugin until the data are ready.
   The Mock plugin work like this.

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

        callback_signal = QtCore.Signal() #used to talk with the callback object
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

        data_sig=QtCore.Signal()
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


.. _hardware_averaging:

Hardware averaging
******************

By default, if averaging of data is needed the Viewer module will take care of it software wise. However, if the hardware
controller provides an efficient method to do it (that will save time) then you should set the class field
``hardware_averaging`` to ``True``.

.. code-block:: python

    class DAQ_NDViewer_Template(DAQ_Viewer_base):
    """
     Template to be used in order to write your own viewer modules
    """
        hardware_averaging = True #will use the accumulate acquisition mode if averaging
        #is True else averaging is done software wise



Hardware needed files
---------------------

If you are using/referring to custom python wrappers/dlls... within your plugin and need a place where to copy them
in PyMoDAQ, then use the ``\hardware`` folder of your plugin package. For instance, the ``daq_2Dviewer_AndorCCD`` plugin need various files stored
in the ``andor`` folder (on github repository). I would therefore copy it as ``\pymodaq_plugins_andor\hardware\andor``
and call whatever module I need within (meaning there is a __init__.py file in the *andor* folder) as:

.. code-block:: python

    #import controller wrapper
    from pymodaq_plugins.hardware.andor import daq_AndorSDK2 #this import the module DAQ_AndorSDK2 containing classes, methods...
    #and then use it as you see fit in your module


How to contribute?
------------------

If you wish to develop a plugin specific to a new hardware not present on the github repo (and I strongly encourage you
to do so!!), you will have to follow the rules as stated above. However, the best practice would be to *fork*
pymodaq_plugins repository. On windows, you can use
`Github Desktop`__. Then you can manually install the forked package in developer using ``pip install -e .`` from
the command line where you *cd* within the forked package. This command will install the package but
any change you apply on the local folder will be applied on the package. Once you're ready with a working plugin, you can then
*push* your branch that will be merged with the main branch after validation.

__ https://desktop.github.com/