from PyQt5.QtCore import QThread
from PyQt5 import QtWidgets
import numpy as np
import PyMoDAQ.DAQ_Utils.DAQ_utils as mylib
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_Viewer_base
from easydict import EasyDict as edict
from collections import OrderedDict
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand
from PyMoDAQ.DAQ_Viewer.utility_classes import comon_parameters
class DAQ_2DViewer_Mock(DAQ_Viewer_base):
    """
        =============== ==================
        **Attributes**   **Type**
        *params*         dictionnary list
        *x_axis*         1D numpy array
        *y_axis*         1D numpy array
        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """

    params = comon_parameters+[{'title': 'Nimages colors:', 'name': 'Nimagescolor', 'type': 'int', 'value': 1 , 'default':1, 'min':0, 'max': 3},
            {'title': 'Nimages pannels:', 'name': 'Nimagespannel', 'type': 'int', 'value': 1 , 'default':0, 'min':0}, 
            {'name': 'Nx', 'type': 'int', 'value': 20 , 'default':20, 'min':1},
            {'name': 'Ny', 'type': 'int', 'value': 30 , 'default':30, 'min':1},
            {'name': 'Amp', 'type': 'int', 'value': 20 , 'default':20, 'min':1},
            {'name': 'x0', 'type': 'slide', 'value': 10 , 'default':50, 'min':0},
            {'name': 'y0', 'type': 'float', 'value': 10 , 'default':50, 'min':0},
            {'name': 'dx', 'type': 'float', 'value': 5 , 'default':20, 'min':1},
            {'name': 'dy', 'type': 'float', 'value': 10 , 'default':20, 'min':1},
            {'name': 'n', 'type': 'float', 'value': 1 , 'default':1, 'min':1},
            {'name': 'amp_noise', 'type': 'float', 'value': 4 , 'default':0.1, 'min':0}
                ]
    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_2DViewer_Mock,self).__init__(parent,params_state)
        self.x_axis=None
        self.y_axis=None
        self.live=False


    def commit_settings(self,param):
        """
            Activate parameters changes on the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                          **Description**
            *param*          instance of pyqtgraph Parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()

    def set_Mock_data(self):
        """
            | Set the x_axis and y_axis with a linspace distribution from settings parameters.
            |

            Once done, set the data mock with parameters :
                * **Amp** : The amplitude
                * **x0** : the origin of x
                * **dx** : the derivative x pos
                * **y0** : the origin of y
                * **dy** : the derivative y pos
                * **n** : ???
                * **amp_noise** : the noise amplitude

            Returns
            -------
                The computed data mock.
        """

        if self.settings.child('ROIselect','use_ROI').value():
            x_axis=np.linspace(self.settings.child('ROIselect','x0').value(),self.settings.child('ROIselect','x0').value()+self.settings.child('ROIselect','width').value(),
                               self.settings.child('ROIselect','width').value(),endpoint=False)
            y_axis=np.linspace(self.settings.child('ROIselect','y0').value(),self.settings.child('ROIselect','y0').value()+self.settings.child('ROIselect','height').value(),
                               self.settings.child('ROIselect','height').value(),endpoint=False)
            data_mock=self.settings.child(('Amp')).value()*(mylib.gauss2D(x_axis,self.settings.child(('x0')).value(),self.settings.child(('dx')).value(),
                               y_axis,self.settings.child(('y0')).value(),self.settings.child(('dy')).value(),self.settings.child(('n')).value()))+self.settings.child(('amp_noise')).value()*np.random.rand(len(y_axis),len(x_axis))
            try:
                self.image[self.settings.child('ROIselect','y0').value():self.settings.child('ROIselect','y0').value()+self.settings.child('ROIselect','height').value(),
                           self.settings.child('ROIselect','x0').value():self.settings.child('ROIselect','x0').value()+self.settings.child('ROIselect','width').value()]=data_mock
            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
        else:
            x_axis=np.linspace(0,self.settings.child(('Nx')).value(),self.settings.child(('Nx')).value(),endpoint=False)
            y_axis=np.linspace(0,self.settings.child(('Ny')).value(),self.settings.child(('Ny')).value(),endpoint=False)

            self.image=self.settings.child(('Amp')).value()*(mylib.gauss2D(x_axis,self.settings.child(('x0')).value(),self.settings.child(('dx')).value(),
                               y_axis,self.settings.child(('y0')).value(),self.settings.child(('dy')).value(),self.settings.child(('n')).value()))+self.settings.child(('amp_noise')).value()*np.random.rand(len(y_axis),len(x_axis))
        
        return self.image




    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector initializing the status dictionnary.

            See Also
            --------
            DAQ_utils.ThreadCommand, get_xaxis, get_yaxis
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

            self.x_axis=self.get_xaxis()
            self.y_axis=self.get_yaxis()

            # initialize viewers with the future type of data
            self.data_grabed_signal_temp.emit([OrderedDict(name='Mock1', data=[np.zeros((128,30))], type='Data2D'),])
                                               #OrderedDict(name='Mock3', data=[np.zeros((128,))], type='Data1D')])

            self.status.x_axis=self.x_axis
            self.status.y_axis=self.y_axis
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
            not implemented.
        """
        pass

    def get_xaxis(self):
        """
            Get the current x_axis from the Mock data setting.

            Returns
            -------
            1D numpy array
                the current x_axis.

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()
        return self.x_axis

    def get_yaxis(self):
        """
            Get the current y_axis from the Mock data setting.

            Returns
            -------
            1D numpy array
                the current y_axis.

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()
        return self.y_axis

    def Grab(self,Naverage=1,**kwargs):
        """
            | For each integer step of naverage range set mock data.
            | Construct the data matrix and send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       The number of images to average.
                                      specify the threshold of the mean calculation
            =============== ======== ===============================================

            See Also
            --------
            set_Mock_data
        """
     
        
        if 'live' in kwargs:
            if kwargs['live']:
                self.live=True

        if self.live:
            while self.live:
                data=self.average_data(Naverage)
                QThread.msleep(100)
                self.data_grabed_signal_temp.emit(data)
                QtWidgets.QApplication.processEvents()
        else:
            data=self.average_data(Naverage)
            QThread.msleep(100)
            self.data_grabed_signal.emit(data)


    def average_data(self,Naverage):
        data=[] #list of image (at most 3 for red, green and blue channels)
        data_tmp=np.zeros_like(self.image)
        for ind in range(Naverage):
            data_tmp+=self.set_Mock_data()
        data_tmp=data_tmp/Naverage
        for ind in range(self.settings.child(('Nimagespannel')).value()):
            datatmptmp=[]
            for indbis in range(self.settings.child(('Nimagescolor')).value()):
                datatmptmp.append(data_tmp)
            data.append(OrderedDict(name='Mock2D_{:d}'.format(ind),data=datatmptmp, type='Data2D'))
        #data.append(OrderedDict(name='Mock2D_1D',data=[np.mean(data_tmp,axis=0)], type='Data1D'))
        return data

    def Stop(self):
        """
            not implemented.
        """
        self.live=False
        return ""
