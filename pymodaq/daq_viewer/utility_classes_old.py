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
from pymodaq.daq_utils.daq_utils import gauss1D, gauss2D, check_received_length, check_sended, message_to_bytes
from collections import OrderedDict
from pymodaq.daq_utils.daq_utils import ThreadCommand, ScanParameters, getLineInfo
from pymodaq.daq_utils.tcp_server_client import TCPServer

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
        super(DAQ_Viewer_base, self).__init__()
        self.parent_parameters_path = [] #this is to be added in the send_param_status to take into account when the current class instance parameter list is a child of some other class
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())


        self.settings.sigTreeStateChanged.connect(self.send_param_status)

        self.parent = parent
        self.status = edict(info="",controller=None,initialized=False)
        self.scan_parameters = None

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
 
class DAQ_TCP_server(DAQ_Viewer_base):
    """
        ==================== ===============================
        **Attributes**         **Type**
        *message_list*         string list
        *socket_types*         string list
        *params*               dictionnary list
        *ind_data*             int
        *data_mock*            double precision float array
        *connected_clients*    list
        *listening*            boolean
        *processing*           ???
        ==================== ===============================
    """
    message_list=["Quit","Send Data 0D","Send Data 1D","Send Data 2D","Status","Done","Server Closed","Info","Infos", "Info_xml"]
    socket_types=["DAQ0D","DAQ1D","DAQ2D","GRABBER"]
    params= comon_parameters+[{'title': 'Port:', 'name': 'port_id', 'type': 'int', 'value': 6341 , 'default':6341},
             {'title': 'IP:', 'name': 'socket_ip', 'type': 'str', 'value': 'localhost' , 'default':'10.47.1.33'},
             {'title': 'Timeout (s):', 'name': 'listen_timeout', 'type': 'int','value': 0, 'default': 0},
             {'title': 'Infos:', 'name': 'infos', 'type': 'group', 'children':[
                 #{'title': 'Exposure (s):', 'name': 'exposure', 'type': 'float','value': 0, 'default': 0, 'readonly': True},
                 #{'title': 'Nx:', 'name': 'Nx', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
                 #{'title': 'Ny:', 'name': 'Ny', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
                 #{'title': 'binx:', 'name': 'binx', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
                 #{'title': 'biny:', 'name': 'biny', 'type': 'int','value': 0, 'default': 0, 'readonly': True},
             ]},
             {'title': 'Connected clients:', 'name': 'conn_clients', 'type': 'table', 'value': dict() , 'header':['Type','adress']},
             ]

    def __init__(self,parent=None,params_state=None):
        """
            Parameters
            ----------
            Ip: str
                either None (then one use socket.gethostname()) or 'localhost' or '127.0.0.1' or '' for all available ressource
            port: int
                the port on which we want to communicate
        """

        super(DAQ_TCP_server,self).__init__(parent,params_state)
        self.ind_data=0
        self.data_mock=None
        self.connected_clients=[]
        self.listening=True
        self.processing=False
        #self.init_server()

                                                 
    def close_server(self):
        """
            close the current opened server.
            Update the settings tree consequently.

            See Also
            --------
            set_connected_clients_table, daq_utils.ThreadCommand
        """
        for sock_dict in self.connected_clients:
            try:
                sock_dict['socket'].close()
            except: pass
        self.connected_clients=[]
        self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())

    def init_server(self):
        self.emit_status(ThreadCommand("Update_Status",["Started new server for {:s}:{:d}".format(self.settings.child(('socket_ip')).value(),self.settings.child(('port_id')).value()),'log']))
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind the socket to a public host, and a well-known port
        try:
            #self.serversocket.bind((self.settings.child(('socket_ip')).value(),self.settings.child(('port_id')).value()))
            self.serversocket.bind((socket.gethostname(),self.settings.child(('port_id')).value()))
        except socket.error as msg:
            self.emit_status(ThreadCommand("Update_Status",['Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror,'log']))
            raise Exception('Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror)
        
        self.serversocket.listen(1)
        self.connected_clients.append(dict(socket=self.serversocket,type='server'))
        self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())

        self.timer=self.startTimer(100) #Timer event fired every 100ms
        #self.listen_client()

        

    def timerEvent(self, event):
        """
            Called by set timers. 
            If the process is free, start the listen_client function.

            =============== ==================== ==============================================
            **Parameters**   **Type**              **Description**

            *event*          QTimerEvent object    Containing id from timer issuing this event
            =============== ==================== ==============================================

            See Also
            --------
            listen_client
        """
        if not self.processing:
            self.listen_client()

    def set_connected_clients_table(self):
        """

        """
        con_clients=OrderedDict()
        for socket_dict in self.connected_clients:
            try:
                address=str(socket_dict['socket'].getsockname())
            except:
                address=""
            con_clients[socket_dict['type']]=address
        return con_clients

    @pyqtSlot(list)
    def print_status(self,status):
        """
            Print the given status.

            =============== ============= ================================================
            **Parameters**    **Type**       **Description**
            *status*          string list    a string list representing the status socket
            =============== ============= ================================================
        """
        print(status)


    def listen_client(self):
        """
            Server function.
            Used to listen incoming message from a client.
            Start a connection and :
            * if current socket corresponding to the serversocket attribute :

                * Read received command
                * Send the 'Update_Status' thread command if needed (log is not valid)

            * Else, in case of :

                * data received from client : process it reading commands from sock. Process the command or quit if asked.
                * client disconnected : remove from socket list
                

            See Also
            --------
            find_socket_type_within_connected_clients, set_connected_clients_table, daq_utils.ThreadCommand, read_commands, process_cmds, utility_classes.DAQ_Viewer_base.emit_status
        """
        try:
            self.processing=True
            #QtWidgets.QApplication.processEvents() #to let external commands in
            read_sockets,write_sockets,error_sockets = select.select([client['socket'] for client in self.connected_clients],[],[client['socket'] for client in self.connected_clients],self.settings.child(('listen_timeout')).value())
            for sock in error_sockets:
                sock_type=self.find_socket_type_within_connected_clients(sock)
                if sock_type is not None:
                    self.connected_clients.remove(dict(socket=sock,type=sock_type))
                    self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                    try:
                        sock.close()
                    except: pass
                    self.emit_status(ThreadCommand("Update_Status",['Client '+sock_type+' disconnected','log']))

            for sock in read_sockets:
                QThread.msleep(100)
                #New connection
                if sock == self.serversocket:
                    (client_socket, address) = self.serversocket.accept()
                    #client_socket.setblocking(False)
                    DAQ_type=self.read_commands(client_socket)
                    if DAQ_type not in self.socket_types:
                        self.emit_status(ThreadCommand("Update_Status",[DAQ_type+' is not a valid type','log']))
                        break

                    self.connected_clients.append(dict(socket=client_socket,type=DAQ_type))
                    self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                    self.emit_status(ThreadCommand("Update_Status",[DAQ_type+' connected with ' + address[0] + ':' + str(address[1]),'log']))
                    QtWidgets.QApplication.processEvents()
                #Some incoming message from a client
                else:
                    # Data received from client, process it
                    try:
                        message=self.read_commands(sock)
                        if message == 'Done' or message == 'Info' or message == 'Infos' or message == 'Info_xml':
                            self.process_cmds(message)
                        elif message == 'Quit':
                            raise Exception("socket disconnect by user")
                        else:
                            self.process_cmds(message,command_sock=sock)
                        
                    # client disconnected, so remove from socket list
                    except Exception as e:
                        sock_type=self.find_socket_type_within_connected_clients(sock)
                        if sock_type is not None:
                            self.connected_clients.remove(dict(socket=sock,type=sock_type))
                            self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                            #sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                            self.emit_status(ThreadCommand("Update_Status",['Client '+sock_type+' disconnected','log']))

            self.processing=False

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

    def read_commands(self,sock):
        """
            Read the commands from the given socket.
            
            =============== ============
            **Parameters**    **Type**
            *sock*  
            =============== ============
            
            Returns
            -------
            message_bytes
                The readed and decoded message

            See Also
            --------
            check_received_length
        """

        length_bytes = check_received_length(sock,4)
        length=np.frombuffer(length_bytes,dtype=np.int32)[0].byteswap()
        message_bytes=check_received_length(sock,length)
        message=message_bytes.decode() #checkout the presence of 4 (or not) comes from labview shitty stuff
        return message

    def send_command(self,sock,command="Send Data 0D"):
        """ 
            Send one of the message contained in self.message_list toward a socket with identity socket_type.
            First send the length of the command with 4bytes.

            =============== =========== ==========================
            **Parameters**    **Type**    **Description**
            *sock*             ???        The current socket
            *command*         string      The command as a string
            =============== =========== ==========================

            See Also
            --------
            utility_classes.DAQ_Viewer_base.emit_status, daq_utils.ThreadCommand, message_to_bytes
        """
        if command not in self.message_list:
            self.emit_status(ThreadCommand("Update_Status",['Command: '+str(command) +' not in the specified list','log']))
            return

        message,message_length=message_to_bytes(command)
        if sock is not None:
            check_sended(sock, message_length)
            check_sended(sock, message)

    def find_socket_within_connected_clients(self,client_type):
        """
            Find a socket from a conneceted client with socket type corresponding.

            =============== =========== ================================
            **Parameters**    **Type**    **Description**
            *client_type*      string     The corresponding client type
            =============== =========== ================================

            Returns
            -------
            dictionnary
                the socket dictionnary
        """
        res=None
        for socket_dict in self.connected_clients:
            if socket_dict['type']==client_type:
                res=socket_dict['socket']
        return res

    def find_socket_type_within_connected_clients(self,sock):
        """
            Find a socket type from a connected client with socket content corresponding.

            =============== =========== ===================================
            **Parameters**    **Type**   **Description**
            *sock*             ???       The socket content corresponding.
            =============== =========== ===================================

            Returns
            -------
            dictionnary
                the socket dictionnary
        """
        res=None
        for socket_dict in self.connected_clients:
            if socket_dict['socket']==sock:
                res=socket_dict['type']
        return res

    def data_ready(self, data):
        pass

    def process_cmds(self,command,command_sock=None):
        """
            Process the given command.

            Depending on the command name :
            * Done : 

                * Find a socket from the 'GRABBER' connected client.
                * Send data to a viewer or a client (depending on command_sock).

            * Info : Find a socket from the 'GRABBER' connected client and read infos. 

            * Send Data 0D : 

                * Find a socket from the 'GRABBER' connected client.
                * set a 1D Mock data.

            * Send Data 1D : 

                * Find a socket from the 'GRABBER' connected client.
                * set a 1D Mock data.

            * Send Data 2D : 
            
                * Find a socket from the 'GRABBER' connected client.
                * set a 2D Mock data.

            =============== =========== ==========================
            **Parameters**    **Type**    **Description**
            *command*         string      the command as a string
            *command_sock*    ???
            =============== =========== ==========================   

            See Also
            --------
            find_socket_within_connected_clients, read_data, send_data, utility_classes.DAQ_Viewer_base.emit_status, daq_utils.ThreadCommand, send_command, set_1D_Mock_data, set_2D_Mock_data, process_cmds           
        """
        if command not in self.message_list:
            return

        if command=='Done': #means the given socket finished grabbing data and is ready to send them
            try:
                sock=self.find_socket_within_connected_clients('GRABBER')
                if sock is not None: #if client 'GRABBER' is connected then send it the command
                    data=self.read_data(sock)
                else:
                    data=self.data_mock

                if command_sock is None:
                    #self.data_grabed_signal.emit([OrderedDict(data=[data],name='TCP GRABBER', type='Data2D')]) #to be directly send to a viewer
                    self.data_ready(data)
                    #print(data)
                else:
                    self.send_data(command_sock,data) #to be send to a client

            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

        elif command=="Infos":
            try:
                sock=self.find_socket_within_connected_clients('GRABBER')
                if sock is not None: #if client 'GRABBER' is connected then send it the command
                    self.read_infos(sock)


            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

        elif command=="Info":
            try:
                sock=self.find_socket_within_connected_clients('GRABBER')
                if sock is not None: #if client 'GRABBER' is connected then send it the command
                    self.read_info(sock)
            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

        elif command == 'Info_xml':
            sock = self.find_socket_within_connected_clients('GRABBER')
            if sock is not None:
                list_len = int.from_bytes(check_received_length(sock, 4), 'big')
                path = []
                for ind in range(list_len):
                    data_len = int.from_bytes(check_received_length(sock, 4), 'big')
                    path.append(check_received_length(sock, data_len).decode())
                data_len = int.from_bytes(check_received_length(sock, 4), 'big')
                param_xml = check_received_length(sock, data_len).decode()
                param_dict = custom_tree.XML_string_to_parameter(param_xml)[0]

                param_here = self.settings.child('infos',*path[1:])
                param_here.restoreState(param_dict)

        elif command=="Send Data 0D" or command=="Send Data 1D" or command=="Send Data 2D":
            sock=self.find_socket_within_connected_clients('GRABBER')
            if sock is not None: #if client 'GRABBER' is connected then send it the command
                self.send_command(sock,command)

            else:#else simulate mock data
                if command=="Send Data 0D":
                    self.set_1D_Mock_data()
                    self.data_mock=np.array([self.data_mock[0]])
                elif command=="Send Data 1D":
                    self.set_1D_Mock_data()
                    data=self.data_mock
                elif command=="Send Data 2D":
                    self.set_2D_Mock_data()
                    data=self.data_mock
                self.process_cmds('Done')


        else:
            pass

    def read_infos(self,sock):
        length_bytes = check_received_length(sock, 4)
        length = np.frombuffer(length_bytes, dtype='>i4')[0]  # big endian 4 bytes==uint32 swaped
        infos = check_received_length(sock, length).decode()
        params = custom_tree.XML_string_to_parameter(infos)
        param_state = {'title': 'Infos:', 'name': 'infos', 'type': 'group', 'children':params}
        self.settings.child(('infos')).restoreState(param_state)

    def read_info(self,sock,dtype=np.float64):
        """
        """
        try:

            ##first get the info type
            length_bytes=check_received_length(sock,4)
            length=np.frombuffer(length_bytes,dtype='>i4')[0] #big endian 4 bytes==uint32 swaped
            message=check_received_length(sock,length).decode()

            #get data length
            length_bytes = check_received_length(sock,4)
            length=np.frombuffer(length_bytes,dtype='>i4')[0]



            ##then get data
            data_bytes=check_received_length(sock,length)

            data=np.frombuffer(data_bytes,dtype=dtype)
            data=data.newbyteorder()[0] #convert it to big endian
            try:
                self.settings.child('infos', message).setValue(data)
            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
  
        except Exception as e:
            data=0

        return data


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


        length_bytes = check_received_length(sock, 4)
        list_length = np.frombuffer(length_bytes,dtype='>i4')[0]

        data_list = []

        for ind in range(list_length):

            length_bytes=check_received_length(sock,4)
            length=np.frombuffer(length_bytes,dtype='>i4')[0] #big endian 4 bytes==uint32 swaped
            data_type = check_received_length(sock,length).decode()

            #get data length
            length_bytes = check_received_length(sock,4)
            length=np.frombuffer(length_bytes,dtype='>i4')[0]

            ##then get Nrow
            Nrow = check_received_length(sock,4)
            Nrow=np.frombuffer(Nrow,dtype='>i4')[0]

            ##then get Ncol
            Ncol = check_received_length(sock,4)
            Ncol=np.frombuffer(Ncol,dtype='>i4')[0]

            ##then get data
            data_bytes=check_received_length(sock,length)

            data=np.frombuffer(data_bytes,dtype=data_type)
            #data=data.newbyteorder() #convert it to big endian
            #data=np.array([[1,2,3],[1,2,3]])

            if Ncol!=0:
                data=data.reshape((Nrow,Ncol))
                #data=np.fliplr(data)  #because it gets inverted compared to digital...
            data = np.squeeze(data)  # in case one dimension is 1
            data_list.append(data)

        return data_list




    def send_data(self,sock,data):
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
        self.send_command(sock,'Done')

        if len(data.shape)==0:
            Nrow=1
            Ncol=0
        elif len(data.shape)==1:
            Nrow=data.shape[0]
            Ncol=0
        elif len(data.shape)==2:
            Nrow=data.shape[0]
            Ncol=data.shape[1]
        data_bytes=data.tobytes()
        check_sended(sock, np.array([len(data_bytes)],dtype='>i4').tobytes())#first send length of data after reshaping as 1D bytes array
        check_sended(sock, np.array([Nrow],dtype='>i4').tobytes()) #then send dimension of lines
        check_sended(sock, np.array([Ncol],dtype='>i4').tobytes()) #then send dimensions of columns
        
        check_sended(sock, data_bytes) #then send data


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

        
class DAQ_Viewer_TCP_server(DAQ_TCP_server):
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

    def __init__(self,parent=None,params_state=None, grabber_type='2D'):
        """

        Parameters
        ----------
        parent
        params_state
        grabber_type: (str) either '0D', '1D' or '2D'
        """

        super().__init__(parent,params_state) #initialize base class with commom attributes and methods
        self.x_axis = None
        self.y_axis = None
        self.data = None
        self.grabber_type = grabber_type

    def data_ready(self,data):
        """
            Send the grabed data signal. to be written in the detailed plugin using this base class

        for instance:
        self.data_grabed_signal.emit([OrderedDict(name='grabber',data=[data], type='Data2D')])  #to be overloaded
        """
        pass

    def commit_settings(self,param):

        if param.name() in custom_tree.iter_children(self.settings.child(('infos')), []):
            grabber_socket = [client['socket'] for client in self.connected_clients if client['type'] == 'GRABBER'][0]
            message, message_length = message_to_bytes('set_info')
            check_sended(grabber_socket, message_length)
            check_sended(grabber_socket, message)

            offset_ROIselect = 6
            param_here_index = custom_tree.iter_children(self.settings.child(('infos')), []).index(param.name(),offset_ROIselect)
            param_here = custom_tree.iter_children_params(self.settings.child(('infos')), [])[param_here_index]

            path = self.settings.childPath(param_here) #get the path of this param as a list
            check_sended(grabber_socket, len(path).to_bytes(4,'big')) # send list length
            for ind in range(len(path)):
                message, message_length = message_to_bytes(path[ind])
                check_sended(grabber_socket, message_length)
                check_sended(grabber_socket, message)
            #send value
            data = custom_tree.parameter_to_xml_string(param)
            message, message_length = message_to_bytes(data)
            check_sended(grabber_socket, message_length)
            check_sended(grabber_socket, message)


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




if __name__ == '__main__':
    prog = DAQ_TCP_server()