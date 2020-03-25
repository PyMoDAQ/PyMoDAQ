from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize

import sys
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from easydict import EasyDict as edict
import socket, select
import numpy as np
from pymodaq.daq_utils.daq_utils import gauss1D, gauss2D, check_received_length, check_sended, message_to_bytes,\
    get_int, get_list, send_string, send_list, get_array, get_string
from collections import OrderedDict
from pymodaq.daq_utils.daq_utils import ThreadCommand, ScanParameters, getLineInfo
from pymodaq.daq_utils.tcp_server_client import TCPServer, tcp_parameters

comon_parameters=[{'title': 'Controller Status:', 'name': 'controller_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},]


class DAQ_Viewer_base(QObject):
    """
        ===================== ===================================
        **Attributes**          **Type**
        *hardware_averaging*    boolean
        *data_grabed_signal*    instance of pyqtSignal
        *params*                list
        *settings*              instance of pyqtgraph Parameter
        *parent*                ???
        *status*                dictionnary
        ===================== ===================================

        See Also
        --------
        send_param_status
    """
    hardware_averaging=False
    data_grabed_signal=pyqtSignal(list)
    data_grabed_signal_temp=pyqtSignal(list)

    params = []
    def __init__(self,parent=None,params_state=None):
        QObject.__init__(self)
        self.parent_parameters_path = [] #this is to be added in the send_param_status to take into account when the current class instance parameter list is a child of some other class
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())

        if '0D' in str(self.__class__):
            self.plugin_type = '0D'
        elif '1D' in str(self.__class__):
            self.plugin_type = '1D'
        else:
            self.plugin_type = '2D'

        self.settings.sigTreeStateChanged.connect(self.send_param_status)

        self.parent = parent
        self.status = edict(info="",controller=None,initialized=False)
        self.scan_parameters = None

    def get_axis(self):
        if self.plugin_type == '1D' or  self.plugin_type == '2D':
            self.emit_x_axis()

        if  self.plugin_type == '2D' :
            self.emit_y_axis()

    def emit_status(self,status):
        """
            Emit the status signal from the given status.

            =============== ============ =====================================
            **Parameters**    **Type**     **Description**
            *status*                       the status information to transmit
            =============== ============ =====================================
        """
        if self.parent is not None:
            self.parent.status_sig.emit(status)
            QtWidgets.QApplication.processEvents()
        else:
            print(*status)

    @pyqtSlot(ScanParameters)
    def update_scanner(self, scan_parameters):
        self.scan_parameters = scan_parameters

    def update_com(self):
        """
        If some communications settings have to be reinit
        Returns
        -------

        """
        pass

    @pyqtSlot(edict)
    def update_settings(self, settings_parameter_dict):
        """
            Update the settings tree from settings_parameter_dict.
            Finally do a commit to activate changes.
            
            ========================== ============= =====================================================
            **Parameters**              **Type**      **Description**
            *settings_parameter_dict*   dictionnnary  a dictionnary listing path and associated parameter
            ========================== ============= =====================================================

            See Also
            --------
            send_param_status, commit_settings
        """
            # settings_parameter_dict=edict(path=path,param=param)
        try:
            path = settings_parameter_dict['path']
            param = settings_parameter_dict['param']
            change = settings_parameter_dict['change']
            try:
                self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
            except: pass
            if change == 'value':
                self.settings.child(*path[1:]).setValue(param.value()) #blocks signal back to main UI
            elif change == 'childAdded':
                child = Parameter.create(name = 'tmp')
                child.restoreState(param)
                self.settings.child(*path[1:]).addChild(child) #blocks signal back to main UI
                param = child

            elif change == 'parent':
                children = custom_tree.get_param_from_name(self.settings, param.name())

                if children is not None:
                    path = custom_tree.get_param_path(children)
                    self.settings.child(*path[1:-1]).removeChild(children)

            self.settings.sigTreeStateChanged.connect(self.send_param_status)

            self.commit_settings(param)
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

    def commit_settings(self,param):
        """
            Not implemented.
        """
        pass

    def stop(self):
        pass


    def send_param_status(self,param,changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, send the 'update_settings' ThreadCommand with concerned path,data and change as attributes.

            =============== ============================================ ============================
            **Parameters**    **Type**                                    **Description**
            *param*           instance of pyqtgraph parameter             The parameter to check
            *changes*         (parameter,change,information) tuple list   The changes list to course
            =============== ============================================ ============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                #first create a "copy" of the actual parameter and send this "copy", to be restored in the main UI
                self.emit_status(ThreadCommand('update_settings',[self.parent_parameters_path+path, [data[0].saveState(), data[1]], change])) #send parameters values/limits back to the GUI. Send kind of a copy back the GUI otherwise the child reference will be the same in both th eUI and the plugin so one of them will be removed

            elif change == 'value' or change == 'limits' or change == 'options':
                self.emit_status(ThreadCommand('update_settings', [self.parent_parameters_path+path, data, change])) #send parameters values/limits back to the GUI
            elif change == 'parent':
                pass

            pass

    def emit_x_axis(self):
        """
            Convenience function
            Emit the thread command "x_axis" with x_axis as an attribute.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand("x_axis",[self.x_axis]))

    def emit_y_axis(self):
        """
            Emit the thread command "y_axis" with y_axis as an attribute.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand("y_axis",[self.y_axis]))
 

class DAQ_Viewer_TCP_server(DAQ_Viewer_base, TCPServer):
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
    params_GRABBER =[] #parameters of a client grabber
    command_server=pyqtSignal(list)

    message_list=["Quit","Send Data 0D","Send Data 1D","Send Data 2D","Status","Done","Server Closed","Info","Infos",
                  "Info_xml", 'x_axis', 'y_axis']
    socket_types=["GRABBER"]
    params= comon_parameters+tcp_parameters

    def __init__(self,parent=None,params_state=None, grabber_type='2D'):
        """

        Parameters
        ----------
        parent
        params_state
        grabber_type: (str) either '0D', '1D' or '2D'
        """
        self.client_type = "GRABBER"
        DAQ_Viewer_base.__init__(self, parent,params_state) #initialize base class with commom attributes and methods
        TCPServer.__init__(self, self.client_type)

        self.x_axis = None
        self.y_axis = None
        self.data = None
        self.grabber_type = grabber_type
        self.ind_data=0
        self.data_mock=None

    def command_to_from_client(self,command):
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command

            if command == 'x_axis':
                x_axis = dict(data=get_array(sock))
                x_axis['label'] = get_string(sock)
                x_axis['units'] = get_string(sock)
                self.x_axis = x_axis.copy()
                self.emit_x_axis()
            elif command == 'y_axis':
                y_axis = dict(data=get_array(sock))
                y_axis['label'] = get_string(sock)
                y_axis['units'] = get_string(sock)
                self.y_axis = y_axis.copy()
                self.emit_y_axis()

            else:
                self.send_command(sock, command)



        else:  # else simulate mock data
            if command == "Send Data 0D":
                self.set_1D_Mock_data()
                self.data_mock = np.array([self.data_mock[0]])
            elif command == "Send Data 1D":
                self.set_1D_Mock_data()
                data = self.data_mock
            elif command == "Send Data 2D":
                self.set_2D_Mock_data()
                data = self.data_mock
            self.process_cmds('Done')

    def send_data(self, sock, data):
        """
            To match digital and labview, send again a command.

            =============== ============================== ====================
            **Parameters**   **Type**                       **Description**
            *sock*                                          the socket receipt
            *data*           double precision float array   the data to be sent
            =============== ============================== ====================

            See Also
            --------
            send_command, check_send_data
        """
        self.send_command(sock, 'Done')

        if len(data.shape) == 0:
            Nrow = 1
            Ncol = 0
        elif len(data.shape) == 1:
            Nrow = data.shape[0]
            Ncol = 0
        elif len(data.shape) == 2:
            Nrow = data.shape[0]
            Ncol = data.shape[1]
        data_bytes = data.tobytes()
        check_sended(sock, np.array([len(data_bytes)],
                                    dtype='>i4').tobytes())  # first send length of data after reshaping as 1D bytes array
        check_sended(sock, np.array([Nrow], dtype='>i4').tobytes())  # then send dimension of lines
        check_sended(sock, np.array([Ncol], dtype='>i4').tobytes())  # then send dimensions of columns

        check_sended(sock, data_bytes)  # then send data

    def read_data(self,sock):
        """
            Read the unsigned 32bits int data contained in the given socket in five steps :
                * get back the message
                * get the list length
                * get the data length
                * get the number of row
                * get the number of column
                * get data

            =============== ===================== =========================
            **Parameters**    **Type**             **Description**
            *sock*              ???                the socket to be readed
            *dtype*           numpy unint 32bits   ???
            =============== ===================== =========================

            See Also
            --------
            check_received_length
        """

        data_list = get_list(sock, 'array')

        return data_list



    def data_ready(self,data):
        """
            Send the grabed data signal. to be written in the detailed plugin using this base class

        for instance:
        self.data_grabed_signal.emit([OrderedDict(name=self.client_type,data=[data], type='Data2D')])  #to be overloaded
        """
        pass

    def command_done(self, command_sock):
        try:
            sock = self.find_socket_within_connected_clients(self.client_type)
            if sock is not None:  # if client self.client_type is connected then send it the command
                data = self.read_data(sock)
            else:
                data = self.data_mock

            if command_sock is None:
                # self.data_grabed_signal.emit([OrderedDict(data=[data],name='TCP GRABBER', type='Data2D')]) #to be directly send to a viewer
                self.data_ready(data)
                # print(data)
            else:
                self.send_data(command_sock, data)  # to be send to a client

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

    def commit_settings(self,param):

        if param.name() in custom_tree.iter_children(self.settings.child(('infos')), []):
            grabber_socket = [client['socket'] for client in self.connected_clients if client['type'] == self.client_type][0]
            send_string(grabber_socket, 'set_info')

            path = custom_tree.get_param_path(param)[2:]#get the path of this param as a list starting at parent 'infos'
            send_list(grabber_socket, path)

            #send value
            data = custom_tree.parameter_to_xml_string(param)
            send_string(grabber_socket, data)

    def ini_detector(self, controller=None):
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
            self.settings.child(('infos')).addChildren(self.params_GRABBER)

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
            self.status.info=getLineInfo()+ str(e)
            self.status.initialized=False
            return self.status

    def close(self):
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

    def grab_data(self, Naverage=1, **kwargs):
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
            self.process_cmds("Send Data {:s}".format(self.grabber_type))
            #self.command_server.emit(["process_cmds","Send Data 2D"])


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[getLineInfo()+ str(e),"log"]))

    def stop(self):
        """
            not implemented.
        """
        pass
        return ""


    def set_1D_Mock_data(self):
        self.data_mock
        x=np.linspace(0,99,100)
        data_tmp=10*gauss1D(x,50,10,1)+1*np.random.rand((100))
        self.ind_data+=1
        self.data_mock=np.roll(data_tmp,self.ind_data)


    def set_2D_Mock_data(self):
        self.x_axis=np.linspace(0,50,50,endpoint=False)
        self.y_axis=np.linspace(0,30,30,endpoint=False)
        self.data_mock=10*gauss2D(self.x_axis,20,10,
                                  self.y_axis,15,7,1)+2*np.random.rand(len(self.y_axis),len(self.x_axis))


if __name__ == '__main__':
    prog = DAQ_TCP_server()