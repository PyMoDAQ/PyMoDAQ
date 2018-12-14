from PyQt5 import QtWidgets
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
import numpy as np
from collections import OrderedDict
from pymodaq.daq_utils.daq_utils import ThreadCommand
import sys
import clr
from easydict import EasyDict as edict
from pymodaq.daq_viewer.utility_classes import comon_parameters

class DAQ_1DViewer_OceanOptics(DAQ_Viewer_base):
    """
        ==================== ==================
        **Atrributes**        **Type**
        *params*              dictionnary list
        *hardware_averaging*  boolean
        *x_axis*              1D numpy array      
        ==================== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
    omnidriver_path='C:\\Program Files\\Ocean Optics\\OmniDriver\\OOI_HOME'
    try:
        sys.path.append(omnidriver_path)
        clr.AddReference("NETOmniDriver-NET40")
        import OmniDriver as omnidriver

    except:
        omnidriver =None

    params=comon_parameters+ [{'title': 'Omnidriver path:', 'name': 'omnidriver_path', 'type': 'browsepath', 'value': omnidriver_path},
            {'title': 'N spectrometers:','name': 'Nspectrometers', 'type': 'int', 'value': 0 , 'default':0, 'min':0},
             {'title': 'Spectrometers:','name': 'spectrometers', 'type': 'group', 'children': []},
            ]
    hardware_averaging=True


    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_1DViewer_OceanOptics,self).__init__(parent,params_state)


        self.wrapper=None
        self.spectro_names=[]

    def commit_settings(self,param):
        """

        """
        if param.name()=='exposure_time':
            ind_spectro=self.spectro_names.index(param.parent().title())
            self.wrapper.setIntegrationTime(ind_spectro,param.value()*1000)
            param.setValue(self.wrapper.getIntegrationTime(ind_spectro))


        elif param.name()=='omnidriver_path':
            try:
                sys.path.append(param.value())
                clr.AddReference("NETOmniDriver-NET40")
                import OmniDriver
                self.omnidriver=OmniDriver
            except:
                pass
                


    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector updating the status dictionnary.

            See Also
            --------
            set_Mock_data, daq_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:
            #open spectro, check and set spectro connected, check and set min max exposure

            if self.settings.child(('controller_status')).value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.wrapper=controller
            else:
                self.wrapper=self.omnidriver.NETWrapper()

            N=self.wrapper.openAllSpectrometers()
            self.settings.child('Nspectrometers').setValue(N)
            self.spectro_names=[]
            data_init=[]
            for ind_spectro in range(N):
                name=self.wrapper.getName(ind_spectro)
                self.spectro_names.append(name)
                exp_max=self.wrapper.getMaximumIntegrationTime(ind_spectro)
                exp_min=self.wrapper.getMinimumIntegrationTime(ind_spectro)
                wavelengths = self.get_xaxis(ind_spectro)
                data_init.append(OrderedDict(name=name,data=[np.zeros_like(wavelengths)], type='Data1D',x_axis=dict(data= wavelengths ,label= 'Wavelength', units= 'nm')))
                for ind in range(2): #this is to take into account that adding it once doen't work (see pyqtgraph Parameter...)
                    try:
                        self.settings.child(('spectrometers')).addChild({'title': name,'name': 'spectro{:d}'.format(ind_spectro), 'type': 'group', 'children':[
                            {'title': 'Grab spectrum:','name': 'grab', 'type': 'bool', 'value': True},
                            {'title': 'Exposure time (ms):','name': 'exposure_time', 'type': 'int', 'value': 100, 'min': int(exp_min/1000), 'max': int(exp_max/1000)},
                            ]
                            })
                    except:
                        pass


                QtWidgets.QApplication.processEvents()
            #init viewers
            if N == 0:
                raise Exception('No detected hardware')
            self.data_grabed_signal_temp.emit(data_init)

            self.status.initialized=True
            self.status.controller=self.wrapper
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def get_xaxis(self,ind_spectro):
        wavelengths_chelou = self.wrapper.getWavelengths(ind_spectro)
        wavelengths = np.array([wavelengths_chelou[ind] for ind in range(len(wavelengths_chelou))])

        return wavelengths

    def Close(self):
        """
            Not implemented.
        """
        self.wrapper.closeAllSpectrometers()


    def Grab(self,Naverage=1,**kwargs):
        """

        """
        try:
            datas=[]
            for ind_spectro in range(len(self.spectro_names)):
                if self.settings.child('spectrometers','spectro{:d}'.format(ind_spectro),'grab').value():
                    self.wrapper.setScansToAverage(ind_spectro,Naverage)
                    data_chelou=self.wrapper.getSpectrum(ind_spectro)
                    data=np.array([data_chelou[ind] for ind in range(len(data_chelou))])
                    datas.append(OrderedDict(name=self.spectro_names[ind_spectro],data=[data], type='Data1D'))
                    QtWidgets.QApplication.processEvents()

            self.data_grabed_signal.emit(datas)

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def Stop(self):
        """

        """
        for ind_spec, name in enumerate(self.spectro_names):
            self.wrapper.stopAveraging(ind_spec)
