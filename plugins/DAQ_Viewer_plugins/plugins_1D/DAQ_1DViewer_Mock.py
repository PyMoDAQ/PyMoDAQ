from PyQt5.QtCore import QThread
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_Viewer_base
import numpy as np
from easydict import EasyDict as edict
from collections import OrderedDict
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand
from PyMoDAQ.DAQ_Utils.DAQ_utils import gauss1D
from PyMoDAQ.DAQ_Viewer.utility_classes import comon_parameters

class DAQ_1DViewer_Mock(DAQ_Viewer_base):
    """
        ==================== ==================
        **Atrributes**        **Type**
        *params*              dictionnary list
        *hardware_averaging*  boolean
        *x_axis*              1D numpy array      
        *ind_data*            int
        ==================== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
    params= comon_parameters+[
             {'name': 'Mock1', 'type': 'group', 'children':[
                {'name': 'Npts', 'type': 'int', 'value': 200 , 'default':200, 'min':10},
                {'name': 'Amp', 'type': 'int', 'value': 20 , 'default':20, 'min':1},
                {'name': 'x0', 'type': 'float', 'value': 50 , 'default':50, 'min':0},
                {'name': 'dx', 'type': 'float', 'value': 20 , 'default':20, 'min':1},
                {'name': 'n', 'type': 'float', 'value': 1 , 'default':1, 'min':1},
                {'name': 'amp_noise', 'type': 'float', 'value': 0.1 , 'default':0.1, 'min':0}
                ]},
             {'name': 'Mock2', 'type': 'group', 'children':[
                    {'name': 'Npts', 'type': 'int', 'value': 200 , 'default':200, 'min':10},
                    {'name': 'Amp', 'type': 'int', 'value': 10 , 'default':10, 'min':1},
                    {'name': 'x0', 'type': 'float', 'value': 100 , 'default':100, 'min':0},
                    {'name': 'dx', 'type': 'float', 'value': 30 , 'default':30, 'min':1},
                    {'name': 'n', 'type': 'float', 'value': 2 , 'default':2, 'min':1},
                    {'name': 'amp_noise', 'type': 'float', 'value': 0.1 , 'default':0.1, 'min':0}
                ]}]
    hardware_averaging=False

    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_1DViewer_Mock,self).__init__(parent,params_state)


        self.x_axis=None
        self.ind_data=0


    def commit_settings(self,param):
        """
            Setting the mock data

            ============== ========= =================
            **Parameters**  **Type**  **Description**
            *param*         none      not used
            ============== ========= =================

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()    
               
                
    def set_Mock_data(self):
        """
            For each parameter of the settings tree :
                * compute linspace numpy distribution with local parameters values
                * shift right the current data of ind_data position
                * add computed results to the data_mock list 

            Returns
            -------
            list
                The computed data_mock list.
        """
        self.data_mock=[]
        for param in self.settings.children():#the first one is ROIselect only valid in the 2D case
            if param.name()!='ROIselect' and param.name()!='controller_status':
                self.x_axis=np.linspace(0,param.children()[0].value()-1,param.children()[0].value())
                data_tmp=param.children()[1].value()*gauss1D(self.x_axis,param.children()[2].value(),param.children()[3].value(),param.children()[4].value())+param.children()[5].value()*np.random.rand((param.children()[0].value()))
                data_tmp=np.roll(data_tmp,self.ind_data)
                self.data_mock.append(data_tmp)
        self.ind_data+=1
        return self.data_mock

    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector updating the status dictionnary.

            See Also
            --------
            set_Mock_data, DAQ_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:

            if self.settings.child(('controller_status')).value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller=controller
            else:
                self.controller="Mock controller"

            self.set_Mock_data()
            self.status.initialized=True
            self.status.controller=self.controller
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Close(self):
        """
            Not implemented.
        """
        pass




    def Grab(self,Naverage=1,**kwargs):
        """
            | Start new acquisition
            | 

            For each integer step of naverage range:
                * set mock data
                * wait 100 ms
                * update the data_tot array

            | 
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of spectrum to average.
                                      Specify the threshold of the mean calculation
            =============== ======== ===============================================

            See Also
            --------
            set_Mock_data
        """
        Naverage=1
        data_tot=self.set_Mock_data()
        for ind in range(Naverage-1):
            data_tmp=self.set_Mock_data()
            QThread.msleep(100)

            for ind,data in enumerate(data_tmp):
                data_tot[ind]+=data

        data_tot=[data/Naverage for data in data_tot]

        self.data_grabed_signal.emit([OrderedDict(name='Mock1',data=data_tot, type='Data1D'),OrderedDict(name='Mock2',data=[data_tot[1]], type='Data1D')])

    def Stop(self):
        """
            not implemented.
        """
        
        return ""
