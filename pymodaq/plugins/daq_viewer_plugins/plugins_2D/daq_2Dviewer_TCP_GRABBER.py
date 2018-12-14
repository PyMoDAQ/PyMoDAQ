from PyQt5.QtCore import pyqtSignal
from easydict import EasyDict as edict
from collections import OrderedDict
from pymodaq.daq_viewer.utility_classes import DAQ_TCP_server
from pymodaq.daq_utils.daq_utils import ThreadCommand

class DAQ_2DViewer_TCP_GRABBER(DAQ_TCP_server):
    """
        ================= ==============================
        **Attributes**      **Type**
        *command_server*    instance of pyqtSignal
        *x_axis*            1D numpy array
        *y_axis*            1D numpy array
        *data*              double precision float array
        ================= ==============================

        See Also
        --------
        utility_classes.DAQ_TCP_server
    """
    command_server=pyqtSignal(list)
    #params=DAQ_TCP_server.params
    def __init__(self,parent=None,params_state=None):

        super(DAQ_2DViewer_TCP_GRABBER,self).__init__(parent,params_state) #initialize base class with commom attributes and methods
        #server=DAQ_TCP_server(parent,params_state)
        #server.data_grabed_signal.connect(self.data_ready)
        #self.server_thread=QThread()
        ##server.moveToThread(self.server_thread)
        #self.command_server[list].connect(server.queue_command)

        #self.server_thread.server=server
        #self.server_thread.start()

        self.x_axis=None
        self.y_axis=None
        self.data=None

    def data_ready(self,data):
        """
            Send the grabed data signal.
        """
        self.data_grabed_signal.emit([OrderedDict(name='Gatan',data=[data], type='Data2D')])


    def commit_settings(self,param):
        pass


    def Ini_Detector(self,controller=None):
        """
            | Initialisation procedure of the detector updating the status dictionnary.
            |
            | Init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)

            See Also
            --------
            utility_classes.DAQ_TCP_server.init_server, get_xaxis, get_yaxis
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:
            self.init_server()

        #%%%%%%% init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)
            self.x_axis=self.get_xaxis()
            self.y_axis=self.get_yaxis()
            self.status.x_axis=self.x_axis
            self.status.y_axis=self.y_axis
            self.status.initialized=True
            self.status.controller=self.serversocket
            return self.status

        except Exception as e:
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Close(self):
        """
            Should be used to uninitialize hardware.

            See Also
            --------
            utility_classes.DAQ_TCP_server.close_server
        """
        self.listening=False
        self.close_server()

    def get_xaxis(self):
        """
            Obtain the horizontal axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the horizontal camera pixels.
        """
        pass
        return self.x_axis

    def get_yaxis(self):
        """
            Obtain the vertical axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the vertical camera pixels.
        """
        pass
        return self.y_axis

    def Grab(self,Naverage=1,**kwargs):
        """
            Start new acquisition.
            Grabbed indice is used to keep track of the current image in the average.

            ============== ========== ==============================
            **Parameters**   **Type**  **Description**

            *Naverage*        int       Number of images to average
            ============== ========== ==============================

            See Also
            --------
            utility_classes.DAQ_TCP_server.process_cmds
        """
        try:
            self.ind_grabbed=0 #to keep track of the current image in the average
            self.Naverage=Naverage
            self.process_cmds("Send Data 2D")
            #self.command_server.emit(["process_cmds","Send Data 2D"])


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def Stop(self):
        """
            not implemented.
        """
        pass
        return ""
