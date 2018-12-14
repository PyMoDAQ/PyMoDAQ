from PyQt5.QtCore import pyqtSignal
from easydict import EasyDict as edict
from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
from collections import OrderedDict
import numpy as np

from pymodaq.daq_viewer.utility_classes import comon_parameters




class DAQ_1DViewer_Tektronix(DAQ_Viewer_base):
    """
        ==================== ========================
        **Attributes**        **Type**
        *data_grabed_signal*  instance of pyqtSignal
        *VISA_rm*             ResourceManager
        *com_ports*           
        *params*              dictionnary list
        *keithley*
        *settings*
        ==================== ========================
    """
    data_grabed_signal=pyqtSignal(list)

    ##checking VISA ressources

    from visa import ResourceManager
    VISA_rm=ResourceManager()
    com_ports=list(VISA_rm.list_resources())


    params= comon_parameters+[
              {'title': 'VISA:','name': 'VISA_ressources', 'type': 'list', 'values': com_ports },
            {'title': 'Id:', 'name': 'id', 'type': 'text', 'value': ""},
            {'title': 'Channels:', 'name': 'channels', 'type': 'itemselect', 'value': dict(all_items=['CH1', 'CH2', 'CH3', 'CH4'], selected=['CH1'])},

            ]

    def __init__(self,parent=None,params_state=None):
        super(DAQ_1DViewer_Tektronix,self).__init__(parent,params_state)
        from visa import ResourceManager
        self.VISA_rm=ResourceManager()
        self.controller=None



    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector.

            Returns
            -------

                The initialized status.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:

            if self.settings.child(('controller_status')).value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller=controller
            else:
                self.controller=self.VISA_rm.open_resource(self.settings.child(('VISA_ressources')).value(), read_termination='\n')


            txt = self.controller.query('*IDN?')
            self.settings.child(('id')).setValue(txt)
            Nchannels = self.number_of_channel()
            if Nchannels == 2:
                self.settings.child(('channels')).setValue(dict(all_items=['CH1', 'CH2'], selected=['CH1']))
            else:
                self.settings.child(('channels')).setValue(dict(all_items=['CH1', 'CH2', 'CH3', 'CH4'], selected=['CH1']))


            self.status.initialized=True
            self.status.controller=self.controller
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def number_of_channel(self):
        """Return the number of available channel on the scope (4 or 2)"""
        if ':CH4:SCA' in self.get_setup_dict().keys():
            return 4
        else:
            return 2

    def load_setup(self):
        l = self.controller.query('SET?')
        dico = dict([e.split(' ') for e in l.split(';')[1:]])
        self.dico = dico

    def get_setup_dict(self, force_load=False):
        """Return the dictionnary of the setup

        By default, the method does not load the setup from the instrument
        unless it has not been loaded before or force_load is set to true.
        """
        if not hasattr(self, 'dico') or force_load:
            self.load_setup()
        return self.dico

    def commit_settings(self, param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================= ============================
            **Parameters**   **Type**                         **Description**
            *param*         instance of pyqtgraph.parameter   The parameter to be checked.
            =============== ================================= ============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            pass


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))

    def Close(self):
        """
            Close the current instance.
        """
        self.controller._inst.close() #the close method has not been written in tektronix object

    def Grab(self,Naverage=1,**kwargs):
        """
            | Start new acquisition.
            | Grab the current values with keithley profile procedure.
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================
        """
        data_tot=[]
        x_axis = None
        for ind, channel in enumerate(self.settings.child(('channels')).value()['selected']):
            if ind == 0:
                x_axis, data_tmp = self.read_channel_data(channel,x_axis_out= True)
            else:
                data_tmp = self.read_channel_data(channel,x_axis_out= False)
            data_tot.append(data_tmp)

        self.data_grabed_signal.emit([OrderedDict(name='Tektronix',data=data_tot, type='Data1D', x_axis= dict(data= x_axis ,label= 'Time', units= 's'))])


    def get_out_waveform_horizontal_sampling_interval(self):
        return float(self.controller.query('WFMO:XIN?'))

    def get_out_waveform_horizontal_zero(self):
        return float(self.controller.query('WFMO:XZERO?'))

    def get_out_waveform_vertical_scale_factor(self):
        return float(self.controller.query('WFMO:YMUlt?'))

    def get_out_waveform_vertical_position(self):
        return float(self.controller.query('WFMO:YOFf?'))

    def get_data_start(self):
        return int(self.controller.query('DATA:START?'))

    def get_horizontal_record_length(self):
        return int(self.controller.query("horizontal:recordlength?"))

    def get_data_stop(self):
        return int(self.controller.query('DATA:STOP?'))

    def set_data_source(self, name):
        self.controller.write('DAT:SOUR '+str(name))

    def read_channel_data(self,channel,x_axis_out= False):
        self.controller.write("DATA:ENCDG ASCII")
        self.controller.write("DATA:WIDTH 2")
        if channel is not None:
            self.set_data_source(channel)
        self.offset = self.get_out_waveform_vertical_position()
        self.scale = self.get_out_waveform_vertical_scale_factor()
        if x_axis_out:
            self.data_start = self.get_data_start()
            self.data_stop = self.get_data_stop()
            self.x_0 = self.get_out_waveform_horizontal_zero()
            self.delta_x = self.get_out_waveform_horizontal_sampling_interval()

            X_axis = self.x_0 + np.arange(0, self.get_horizontal_record_length()) * self.delta_x

        res = np.array(self.controller.query_ascii_values('CURVE?'))
        #res = np.frombuffer(buffer, dtype=np.dtype('int16').newbyteorder('<'),
        #                    offset=0)

        # The output of CURVE? is scaled to the display of the scope
        # The following converts the data to the right scale
        Y_axis = (res - self.offset)*self.scale

        if x_axis_out:
            return X_axis, Y_axis
        else:
            return Y_axis

    def Stop(self):
        """
            not implemented?
        """
        return ""
