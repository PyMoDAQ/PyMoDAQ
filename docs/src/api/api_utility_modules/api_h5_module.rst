Hdf5 module and classes
=======================

.. currentmodule:: pymodaq.utils.h5modules

Summary of the classes in the h5module

.. autosummary::
    backends.H5Backend
    saving.H5Saver
    browsing.H5Browser


.. _H5BackendClassDescr:

Interacting with hdf5 files
---------------------------
The H5Backend is a wrapper around three hdf5 python packages: pytables, h5py and h5pyd. It allows seamless integration
of any of these with PyMoDAQ features.

.. autoclass:: H5Backend
   :members:



.. _H5SaverClassDescr:

Saving Data
-----------

`H5SaverBase` and `H5Saver` classes are a help to save data in a hierachical hdf5 binary file through the H5Backend
object and allowing integration in the PyMoDAQ Framework. Using the ``H5Saver``
object will make sure you can explore your datas with the H5Browser. The object can be used to: punctually save one set
of data such as with the DAQ_Viewer (see :ref:`daq_viewer_saving_single`), save multiple acquisition such as with the DAQ_Scan
(see :ref:`daq_scan_saving`) or save on the fly with enlargeable arrays such as the :ref:`continuous_saving` mode of the DAQ_Viewer.

The saving functionalities are divided in two objects: `H5SaverBase` and `H5Saver`. `H5SaverBase` contains everything
needed for saving, while `H5Saver`, inheriting `H5SaverBase`, add Qt functionality such as emitted signals.

Punctual use (adapted from the DAQ_Viewer)::

    # Datas to be saved are contained within a dictionary on the form
    """
    datas = OrderedDict(data1D=[OrderedDict(data=ndarray, xaxis=dict(data=..., units=..., labels=...),
                                OrderedDict(...),...])
    """

    path = '/test.h5'
    h5saver = H5Saver(save_type='detector')
    h5saver.init_file(update_h5=True, custom_naming=False, addhoc_file_path=path)

    settings_str = 'various information as a string. Best used to convert Parameter object as xml string, so the ' + \
                   'H5Browser can render the settings as a Tree'

    #creates an incremental detector group under the base raw_group adding detector metadata
    det_group = h5saver.add_det_group(h5saver.raw_group, "Data", settings_str) #creates a Det00i group

    try:
        self.channel_arrays = OrderedDict([])

        data_types = ['data1D'] #we don't record 0D data in this mode (only in continuous)
        if h5saver.settings.child(('save_2D')).value():
            data_types.append('data2D')

        for data_type in data_types:
            if datas[data_type] is not None:
                if data_type in datas.keys() and len(datas[data_type]) != 0:
                    if not h5saver.is_node_in_group(det_group, data_type):

                        data_group = h5saver.add_data_group(det_group, data_type) #for a given detector, creates one
                        #group by dimensionality of data

                        for ind_channel, channel in enumerate(datas[data_type]):  # list of OrderedDict

                            #creates a channel 00i group to store each set of data together with its axis (if relevant)
                            channel_group = h5saver.add_CH_group(data_group, title=channel)

                            #store data in the created channel group
                            h5saver.add_data(channel_group, datas[data_type][channel], scan_type='', enlargeable=False)


.. autoclass:: H5SaverBase
   :members:


.. autoclass:: H5Saver
   :members:

Browsing Data
-------------

using the `H5Backend` it is possible to write scripts to easily access a hdf5 file content. However, PyMoDAQ includes
a dedicated hdf5 viewer understanding dedicated metadata and therefore displaying nicely the content of the file,
see :ref:`H5Browser_module`. Two objects can be used to browse data: `H5BrowserUtil` and `H5Browser`. `H5BrowserUtil`
gives you methods to quickly (in a script) get info and data from your file while the `H5Browser` adds a UI to interact with the hdf5
file.

.. autoclass:: H5BrowserUtil
   :members:

.. autoclass:: H5Browser
   :members: