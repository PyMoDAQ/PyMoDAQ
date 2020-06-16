Utility Modules
***************

.. currentmodule:: pymodaq.daq_utils.h5saver

.. autosummary::

.. _H5BackendClassDescr:

H5Backend
---------
The H5Backend is a wrapper around three hdf5 python packages: pytables, h5py and h5pyd. It allows seemless integration
of any of these with PyMoDAQ features

.. _H5SaverClassDescr:

H5Saver
-------

This module is a help to save data in a hierachical hdf5 binary file through the H5Backend object . Using the ``H5Saver``
object will make sure you can explore your datas with the H5Browser. The object can be used to: punctually save one set
of data such as with the DAQ_Viewer (see :ref:`daq_viewer_saving_single`), save multiple acquisition such as with the DAQ_Scan
(see :ref:`daq_scan_saving`) or save on the fly with enlargeable arrays such as the :ref:`continuous_saving` mode of the DAQ_Viewer.

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


.. autoclass:: H5Saver
   :members:
   :special-members:


