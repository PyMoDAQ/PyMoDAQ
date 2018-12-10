from PyQt5 import QtWidgets 
from PyQt5.QtCore import pyqtSignal, QThread
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand
import numpy as np
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_Viewer_base
from easydict import EasyDict as edict
from collections import OrderedDict
from PyMoDAQ.DAQ_Utils.DAQ_utils import gauss1D
from PyMoDAQ.DAQ_Viewer.utility_classes import comon_parameters
class DAQ_0DViewer_Mock(DAQ_Viewer_base):
    """
        =============== =================
        **Attributes**  **Type**
        *params*        dictionnary list
        *x_axis*        1D numpy array
        *ind_data*      int
        =============== =================
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

    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_0DViewer_Mock,self).__init__(parent,params_state)
        self.x_axis=None
        self.ind_data=0


    def commit_settings(self,param):
        """
            Setting the mock data.

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
            For each parameter of the settings tree compute linspace numpy distribution with local parameters values
            and add computed results to the data_mock list.
        """
        self.data_mock=[]
        for param in self.settings.children():#the first one is ROIselect only valid in the 2D case
            if param.name()!='ROIselect' and param.name()!='controller_status':
                x=np.linspace(0,param.children()[0].value()-1,param.children()[0].value())
                self.data_mock.append(param.children()[1].value()*gauss1D(x,param.children()[2].value(),param.children()[3].value(),param.children()[4].value())
                                      +param.children()[5].value()*np.random.rand((param.children()[0].value())))

    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector.

            Returns
            -------
            ???
                the initialized status.

            See Also
            --------
            set_Mock_data
        """


        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        if self.settings.child(('controller_status')).value()=="Slave":
            if controller is None: 
                raise Exception('no controller has been defined externally while this detector is a slave one')
            else:
                self.controller=controller
        else:
            self.controller="Mock controller"
        self.set_Mock_data()
        #initialize viewers with the future type of data
        self.data_grabed_signal_temp.emit([OrderedDict(name='Mock1',data=[0], type='Data0D')])

        self.status.initialized=True
        self.status.controller=self.controller
        return self.status

    def Close(self):
        """
            not implemented.
        """
        pass

    def Grab(self,Naverage=1,**kwargs):
        """
            | Start new acquisition.
            |

            For each data on data_mock :
                * shift right data of ind_data positions
                * if naverage parameter is defined append the mean of the current data to the data to be grabbed.
                
            |
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       specify the threshold of the mean calculation
            =============== ======== ===============================================

        """
        data_tot=[]
        data_tot_bis=[]
        for data in self.data_mock:
            data=np.roll(data,self.ind_data)
            if Naverage>1:
                data_tot.append(np.array([np.mean(data[0:Naverage-1])]))
                data_tot_bis.append(np.array([1-np.mean(data[0:Naverage-1])]))
            else:
                data_tot.append(np.array([data[0]]))
                data_tot_bis.append(np.array([1-data[0]]))

        #self.data_grabed_signal.emit([OrderedDict(name='Mock1',data=data_tot, type='Data0D'), OrderedDict(name='Mock2',data=data_tot_bis, type='Data0D')])
        self.data_grabed_signal.emit([OrderedDict(name='Mock1',data=data_tot, type='Data0D')])
        self.ind_data+=1

    def Stop(self):
        """
            not implemented.
        """

        return ""
