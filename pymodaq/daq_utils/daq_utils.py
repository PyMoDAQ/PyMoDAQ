from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, QObject
import sys
import tables
from collections import OrderedDict

import numpy as np
import datetime
from pathlib import Path
from ctypes import CFUNCTYPE
if 'win32' in sys.platform:
    from ctypes import WINFUNCTYPE

from pyqtgraph import dockarea
import enum
import os
import re
import importlib
import inspect

plot_colors = ['r', 'g','b',  'c', 'm', 'y', 'k',' w']
Cb = 1.602176e-19  # coulomb
h = 6.626068e-34  # J.s
c = 2.997924586e8  # m.s-1

def Enm2cmrel(E_nm, ref_wavelength=515):
    return 1/(ref_wavelength*1e-7)-1/(E_nm*1e-7)

def Ecmrel2Enm(Ecmrel, ref_wavelength=515):
    Ecm = 1/(ref_wavelength*1e-7)-Ecmrel
    return 1/(Ecm*1e-7)


def eV2nm(E_eV):
    E_J = E_eV * Cb
    E_freq = E_J / h
    E_nm = c / E_freq * 1e9
    return E_nm


def nm2eV(E_nm):
    E_freq = c / E_nm * 1e9;
    E_J = E_freq * h;
    E_eV = E_J / Cb;
    return E_eV


def E_J2eV(E_J):
    E_eV = E_J / Cb;
    return E_eV


def eV2cm(E_eV):
    E_nm = eV2nm(E_eV)
    E_cm = 1 / (E_nm * 1e-7);
    return E_cm

def nm2cm(E_nm):
    return 1/(E_nm*1e7)

def cm2nm(E_cm):
    return 1 / (E_cm * 1e-7)


def eV2E_J(E_eV):
    E_J = E_eV * Cb;
    return E_J


def eV2radfs(E_eV):
    E_J = E_eV * Cb
    E_freq = E_J / h
    E_radfs = E_freq * 2 * np.pi / 1e15
    return E_radfs


def l2w(x, speedlight=300):
    # y=l2w(x,c)
    # speedlight is the speed of light =300 nm/fs
    y = 2 * np.pi * speedlight / x
    return y


def capitalize(string):
    """
    Returns same string but with first letter capitalized
    Parameters
    ----------
    string: (str)

    Returns
    -------
    str
    """
    return string.capitalize()[0]+string[1:]

def uncapitalize(string):
    return string.lower()[0] + string[1:]


class ListPicker(QObject):

    def __init__(self,list_str):
        super(ListPicker,self).__init__()
        self.list = list_str

    def pick_dialog(self):
        self.dialog = QtWidgets.QDialog()
        self.dialog.setMinimumWidth(500)
        vlayout = QtWidgets.QVBoxLayout()


        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(self.list)

        vlayout.addWidget(self.list_widget, 10)
        self.dialog.setLayout(vlayout)

        buttonBox = QtWidgets.QDialogButtonBox();
        buttonBox.addButton('Apply', buttonBox.AcceptRole)
        buttonBox.accepted.connect(self.dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        vlayout.addWidget(buttonBox)
        self.dialog.setWindowTitle('Select an entry in the list')

        res = self.dialog.show()

        pass
        if res == self.dialog.Accepted:
            # save preset parameters in a xml file
            return  [self.list_widget.currentIndex(), self.list_widget.currentItem().text()]
        else:
            return [-1, ""]

def get_data_dimension(arr, scan_type='scan1D', remove_scan_dimension=False):
    dimension = len(arr.shape)
    if dimension == 1:
        if arr.size == 1:
            dimension = 0
    if remove_scan_dimension:
        if scan_type.lower() == 'scan1d':
            dimension -= 1
        elif scan_type.lower() == 'scan2d':
            dimension -= 2

    return arr.shape, '{:d}D'.format(dimension), arr.size

def scroll_log(scroll_val, min_val , max_val):
    """
    Convert a scroll value [0-100] to a log scale between min_val and max_val
    Parameters
    ----------
    scroll
    min_val
    max_val
    Returns
    -------

    """
    scr = scroll_val
    value = scr * (np.log10(max_val)-np.log10(min_val))/100+ np.log10(min_val)
    return 10**value

def scroll_linear(scroll_val, min_val , max_val):
    """
    Convert a scroll value [0-100] to a linear scale between min_val and max_val
    Parameters
    ----------
    scroll
    min_val
    max_val
    Returns
    -------

    """
    scr = scroll_val
    value = scr * (max_val-min_val)/100+ min_val
    return value

def extract_TTTR_histo_every_pixels(nanotimes, markers, marker = 65, Nx = 1, Ny = 1, Ntime = 512, ind_line_offset = 0,
                                    channel = 0):
    """
    Extract histograms from photon tags and attributes them in the given pixel of the FLIM
    The marker is used to check where a new line within the image starts
    Parameters
    ----------
    nanotimes: (ndarray of uint16) photon arrival times (in timeharp units)
    markers: (ndarray of uint8) markers: 0 means the corresponding nanotime is a photon on detector 0,
                                         1 means the corresponding nanotime is a photon on detector 1,
                                         65 => Marker 1 event
                                         66 => Marker 2 event
                                         ...
                                         79 => Marker 15 event
                                         127 =>overflow
    marker: (int) the marker value corresponding to a new Y line within the image (for instance 65)
    Nx: (int) the number of pixels along the xaxis
    Ny: (int) the number of pixels along the yaxis
    Ntime: (int) the number of pixels alond the time axis
    ind_line_offset: (int) the offset of previously read lines
    channel: (int) marker of the specific channel (0 or 1) for channel 1 or 2

    Returns
    -------
    ndarray: FLIM hypertemporal image in the order (X, Y, time)
    """
    bins = np.linspace(0, Ntime, Ntime + 1, dtype=np.uint32)
    nanotimes = nanotimes[np.logical_or(markers == marker, markers == channel)]
    markers = markers[np.logical_or(markers == marker, markers == channel)]
    indexes_new_line = np.squeeze(np.argwhere(markers == marker)).astype(np.uint64)
    datas = np.zeros((Nx, Ny, Ntime), dtype=np.int64)

    if indexes_new_line.size == 0:
        indexes_new_line = np.array([0, nanotimes.size], dtype=np.uint64)
    # print(indexes_new_line)
    for ind_line in range(indexes_new_line.size - 1):
        # print(ind_line)
        data_line_tmp = nanotimes[int(indexes_new_line[ind_line] + 1):indexes_new_line[ind_line + 1]]
        ix = np.int((ind_line + ind_line_offset) % Nx)
        iy = np.int(((ind_line + ind_line_offset) // Nx) % Ny)
        datas[ix, iy, :] += np.histogram(data_line_tmp, bins, range=None)[0]

    return datas


def getLineInfo():
    return "in {:s}, method: {:s}, line: {:d}: ".format(os.path.split(inspect.stack()[1][1])[1], inspect.stack()[1][3], inspect.stack()[1][2])

class ScanParameters(object):
    def __init__(self, Nsteps=0,axis_1_indexes=[],axis_2_indexes=[],axis_1_unique=[],axis_2_unique=[],
                 positions=[]):
        super(ScanParameters, self).__init__()
        self.positions = positions
        self.axis_2D_1 = axis_1_unique
        self.axis_2D_2 = axis_2_unique
        self.axis_2D_1_indexes = axis_1_indexes
        self.axis_2D_2_indexes = axis_2_indexes
        self.Nsteps = Nsteps

    def __repr__(self):
        return 'Scanner with {:d} positions and shape:({:d}, {:d})'.format(self.Nsteps, len(self.axis_2D_1), len(self.axis_2D_2))

class DockArea(dockarea.DockArea, QObject):
    dock_signal = pyqtSignal()

    def __init__(self, temporary=False, home=None):
        super(DockArea, self).__init__(temporary, home)

    def moveDock(self, dock, position, neighbor):
        """
        Move an existing Dock to a new location.
        """
        ## Moving to the edge of a tabbed dock causes a drop outside the tab box
        if position in ['left', 'right', 'top', 'bottom'] and neighbor is not None and neighbor.container() is not None and neighbor.container().type() == 'tab':
            neighbor = neighbor.container()
        self.addDock(dock, position, neighbor)
        self.dock_signal.emit()

class ThreadCommand(object):
    """ | Micro class managing the thread commands.
        |
        | A thread command is composed of a string name defining the command to execute and an attribute list splitable making arguments of the called function.

        =============== =============
        **Attributes**  **Type**
        *command*       string
        *attributes*    generic list
        =============== =============

    """
    def __init__(self,command="",attributes=[]):
        self.command=command
        self.attributes=attributes

def elt_as_first_element(elt_list,match_word='Mock'):
    if elt_list!=[]:
        ind_elt=0
        for ind,elt in enumerate(elt_list):
            if 'Mock' in elt:
                ind_elt=ind
                break
        plugin_mock=elt_list[ind_elt]
        elt_list.remove(plugin_mock)
        plugins=[plugin_mock]
        plugins.extend(elt_list)
    else: plugins=[]
    return plugins

def send_string(socket, string):
    cmd_bytes, cmd_length_bytes = message_to_bytes(string)
    check_sended(socket, cmd_length_bytes)
    check_sended(socket, cmd_bytes)

def send_scalar(socket, data):
    """
    Convert it to numpy array then send the data type, the data_byte length and finally the data_bytes
    Parameters
    ----------
    data

    Returns
    -------

    """
    data = np.array([data])
    data_type = data.dtype.descr[0][1]
    data_bytes = data.tobytes()
    send_string(socket, data_type)
    check_sended(socket, len(data_bytes).to_bytes(4, 'big'))
    check_sended(socket, data_bytes)

def get_string(socket):
    string_len = get_int(socket)
    string = check_received_length(socket, string_len).decode()
    return string

def get_int(socket):
    data = int.from_bytes(check_received_length(socket, 4), 'big')
    return data

def get_scalar(socket):

    data_type = get_string(socket)
    data_len = get_int(socket)
    data_bytes = check_received_length(socket, data_len)

    data = np.frombuffer(data_bytes, dtype=data_type)[0]
    return data

def send_list(socket, data_list):

    check_sended(socket, len(data_list).to_bytes(4, 'big'))
    for data in data_list:

        if isinstance(data, np.ndarray):
            send_array(socket, data)

        elif isinstance(data, str):
            send_string(socket, data)

        elif isinstance(data, int) or isinstance(data, float):
            send_scalar(socket, data)

def get_list(socket, data_type):
    """
    Receive data from socket as a list
    Parameters
    ----------
    socket: the communication socket
    data_type: either 'string', 'scalar', 'array' depending which function has been used to send the list

    Returns
    -------

    """
    data = []
    list_len = get_int(socket)

    for ind in range(list_len):
        if data_type == 'scalar':
            data.append(get_scalar(socket))
        elif data_type == 'string':
            data.append(get_string(socket))
        elif data_type == 'array':
            data.append(get_array(socket))
    return data

def get_array(socket):
    data_type = get_string(socket)
    data_len = get_int(socket)
    Nrow = get_int(socket)
    Ncol = get_int(socket)
    data_bytes = check_received_length(socket, data_len)

    data = np.frombuffer(data_bytes, dtype=data_type)
    if Ncol != 0:
        data = data.reshape((Nrow, Ncol))
        # data=np.fliplr(data)  #because it gets inverted compared to digital...
    data = np.squeeze(data)  # in case one dimension is 1

    return data



def send_array(socket, data_array):
    """
    get data type as a string
    reshape array as 1D array and get number of rows and cols
    convert Data array as bytes
    send data type
    send data length
    send N rows
    send Ncols
    send data as bytes
    """
    data_type = data_array.dtype.descr[0][1]
    data_shape = data_array.shape
    Nrow = data_shape[0]
    if len(data_shape) > 1:
        Ncol = data_shape[1]
    else:
        Ncol = 1

    data = data_array.reshape(np.prod(data_shape))
    data_bytes = data.tobytes()

    send_string(socket, data_type)

    check_sended(socket, len(data_bytes).to_bytes(4, 'big'))
    check_sended(socket, Nrow.to_bytes(4, 'big'))
    check_sended(socket, Ncol.to_bytes(4, 'big'))
    check_sended(socket, data_bytes)

def message_to_bytes(message):
    """
    Convert a string to a byte array
    Parameters
    ----------
    message (str): message

    Returns
    -------
    Tuple consisting of the message converted as a byte array, and the length of the byte array, itself as a byte array of length 4
    """

    if not isinstance(message, bytes):
        message=message.encode()
    return message,len(message).to_bytes(4, 'big')

def check_sended(socket, data_bytes):
    """
    Make sure all bytes are sent through the socket
    Parameters
    ----------
    socket
    data_bytes

    Returns
    -------

    """
    sended = 0
    while sended < len(data_bytes):
        sended += socket.send(data_bytes[sended:])
    #print(data_bytes)


def check_received_length(sock,length):
    """
    Make sure all bytes (length) that should be received are received through the socket
    Parameters
    ----------
    sock
    length

    Returns
    -------

    """
    l=0
    data_bytes=b''
    while l<length:
        if l<length-4096:
            data_bytes_tmp=sock.recv(4096)
        else:
            data_bytes_tmp=sock.recv(length-l)
        l+=len(data_bytes_tmp)
        data_bytes+=data_bytes_tmp
    #print(data_bytes)
    return data_bytes


def find_in_path(path, mode):
    """
        Find the .py files in the given path directory

        =============== =========== ====================================
        **Parameters**    **Type**   **Description**
        *path*            string     The path to the directory to check
        =============== =========== ====================================

        Returns
        -------
        String list
            The list containing all the .py files in the directory.
    """
    plugins = []
    paths = os.listdir(path)
    for entry in paths:
        if mode in entry:
            if (mode == 'daq_move'):
                plugins.append(entry[9:-3])
            else:
                plugins.append(entry[13:-3])

    return plugins

def get_names_simple(mode):
    import pymodaq_plugins
    base_path = os.path.split(pymodaq_plugins.__file__)[0]

    if (mode == 'daq_move'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_move_plugins'), mode)
        plugins_import = elt_as_first_element(plugin_list, match_word='Mock')

    elif (mode == 'daq_0Dviewer'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_viewer_plugins', 'plugins_0D'), mode)
        plugins_import = elt_as_first_element(plugin_list, match_word='Mock')

    elif (mode == 'daq_1Dviewer'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_viewer_plugins', 'plugins_1D'), mode)
        plugins_import = elt_as_first_element(plugin_list, match_word='Mock')

    elif (mode == 'daq_2Dviewer'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_viewer_plugins', 'plugins_2D'), mode)
        plugins_import = elt_as_first_element(plugin_list, match_word='Mock')

    return plugins_import



def get_names(mode):
    """
        Get plugins names list from os dir command on plugins folder.
        The mode arguments specify the directory to list between DAQ_Move
        and DAQ_Viewer_XD

        =============== =========== ====================================================================
        **Parameters**    **Type**   **Description**
        *mode*            *string    The plugins directory to check between :
                                        * *DAQ_Move* : Check for DAQ_Move controllers plugins
                                        * *DAQ_Viewer_0D* : Chack for DAQ_Viewer\0D controllers plugins
                                        * *DAQ_Viewer_1D* : Chack for DAQ_Viewer\1D controllers plugins
                                        * *DAQ_Viewer_2D* : Chack for DAQ_Viewer\2D controllers plugins
        =============== =========== ====================================================================

        Returns
        -------
        String list
            The list containing all the present plugins names.

        See Also
        --------
        find_in_path
    """
    # liste=[]
    import pymodaq_plugins
    base_path = os.path.split(pymodaq_plugins.__file__)[0]
    # base_path=os.path.join(os.path.split(os.path.split(__file__)[0])[0],'plugins')
    if (mode == 'daq_move'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_move_plugins'), mode)
        plugins = elt_as_first_element(plugin_list, match_word='Mock')
        # check if modules are importable
        plugins_import = []
        for mod in plugins:
            try:
                importlib.import_module('.daq_move_' + mod, 'pymodaq_plugins.daq_move_plugins')
                plugins_import.append(mod)
            except:
                pass

        return plugins_import
    elif (mode == 'daq_0Dviewer'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_viewer_plugins', 'plugins_0D'), mode)
        plugins = elt_as_first_element(plugin_list, match_word='Mock')
        # check if modules are importable
        plugins_import = []
        for mod in plugins:
            try:
                importlib.import_module('.daq_0Dviewer_' + mod, 'pymodaq_plugins.daq_viewer_plugins.plugins_0D')
                plugins_import.append(mod)
            except:
                pass

        return plugins_import
    elif (mode == 'daq_1Dviewer'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_viewer_plugins', 'plugins_1D'), mode)
        plugins = elt_as_first_element(plugin_list, match_word='Mock')
        # check if modules are importable
        plugins_import = []
        for mod in plugins:
            try:
                importlib.import_module('.daq_1Dviewer_' + mod, 'pymodaq_plugins.daq_viewer_plugins.plugins_1D')
                plugins_import.append(mod)
            except:
                pass

        return plugins_import
    elif (mode == 'daq_2Dviewer'):
        plugin_list = find_in_path(os.path.join(base_path, 'daq_viewer_plugins', 'plugins_2D'), mode)
        plugins = elt_as_first_element(plugin_list, match_word='Mock')
        # check if modules are importable
        plugins_import = []
        for mod in plugins:
            try:
                importlib.import_module('.daq_2Dviewer_' + mod, 'pymodaq_plugins.daq_viewer_plugins.plugins_2D')
                plugins_import.append(mod)
            except:
                pass

        return plugins_import


# class EnumMeta (EnumMeta):

def make_enum(mode):
    """
        Custom class generator.
        Create a dynamic enum containing the plugins folder file names.

        Returns
        -------
        Instance of Enum
            The enum object representing loaded plugins
    """
    names=get_names(mode)
    values={}
    for i in range(0,len(names)):
        values.update({names[i]:i+1})
    meta=type(enum.Enum)
    bases=(enum.Enum,)
    dict=meta.__prepare__(names,bases)
    dict.update({'names': get_names})
    for key,value in values.items():
        dict[key]=value
    if(mode=='daq_move'):
        return meta(mode+'_Stage_type',bases,dict)
    else :
        return meta(mode+'_Type',bases,dict)





def check_modules(detectors, detectors_type, actuators):
    for ind_det, det in enumerate(detectors):
        if detectors_type[ind_det] == 'DAQ0D':
            if det not in get_names_simple('daq_0Dviewer'):
                raise Exception('Invalid actuator plugin')
        elif detectors_type[ind_det] == 'DAQ1D':
            if det not in get_names_simple('daq_1Dviewer'):
                raise Exception('Invalid actuator plugin')
        elif detectors_type[ind_det] == 'DAQ2D':
            if det not in get_names_simple('daq_2Dviewer'):
                raise Exception('Invalid actuator plugin')

    for act in actuators:
        if act not in get_names_simple('daq_move'):
            raise Exception('Invalid actuator plugin')

class PIDModelGeneric():
    params = []

    status_sig = pyqtSignal(ThreadCommand)
    actuators = []
    actuators_name = []
    detectors_type = [] # with entries either 'DAQ0D', 'DAQ1D' or 'DAQ2D'
    detectors = []
    detectors_name = []





    def __init__(self, pid_controller):
        self.pid_controller = pid_controller #instance of the pid_controller using this model
        self.settings = self.pid_controller.settings.child('models', 'model_params') #set of parameters
        self.data_names = None
        self.curr_output = None
        self.curr_input = None

    def update_detector_names(self):
        names = self.pid_controller.settings.child('main_settings', 'detector_modules').value()['selected']
        self.data_names = []
        for name in names:
            name = name.split('//')
            self.data_names.append(name)


    def update_settings(self, param):
        """
        Get a parameter instance whose value has been modified by a user on the UI
        To be overwritten in child class
        """
        if param.name() == '':
            pass

    def ini_model(self):
        pass

    def convert_input(self, measurements):
        """
        Convert the measurements in the units to be fed to the PID (same dimensionality as the setpoint)
        Parameters
        ----------
        measurements: (Ordereddict) Ordereded dict of object from which the model extract a value of the same units as the setpoint

        Returns
        -------
        float: the converted input

        """
        return 0

    def convert_output(self, output, dt):
        """
        Convert the output of the PID in units to be fed into the actuator
        Parameters
        ----------
        output: (float) output value from the PID from which the model extract a value of the same units as the actuator
        dt: (float) ellapsed time in seconds since last call
        Returns
        -------
        list: the converted output as a list (in case there are a few actuators)

        """
        #print('output converted')

        return [output]

def get_set_log_path():
    local_path = get_set_local_dir()
    log_path = os.path.join(local_path, 'logging')
    if not os.path.isdir(log_path):
        os.makedirs(log_path)
    return log_path

def get_set_pid_path():
    local_path = get_set_local_dir()
    pid_path = os.path.join(local_path, 'config_pid')
    if not os.path.isdir(pid_path):
        os.makedirs(pid_path)
    return pid_path


def zeros_aligned(n, align, dtype=np.uint32):
    """
    Get aligned memory array wih alignment align.
    Parameters
    ----------
    n: (int) length in dtype bytes of memory
    align: (int) memory alignment
    dtype: (numpy.dtype) type of the stored memory elements

    Returns
    -------

    """
    """
    
    """

    a = np.zeros(n + (align - 1), dtype=dtype)
    data_align = a.ctypes.data % align
    offset = 0 if data_align == 0 else (align - data_align)
    return a[offset: offset + n]

def cfunc(name, dll, result, *args):
    """build and apply a ctypes prototype complete with parameter flags

    Parameters
    ----------
    name: (str) function name in the dll
    dll: (ctypes.windll) dll object
    result : result is the type of the result (c_int,..., python function handle,...)
    args: list of tuples with 3 or 4 elements each like (argname, argtype, in/out, default) where argname is the
    name of the argument, argtype is the type, in/out is 1 for input and 2 for output, and default is an optional
    default value.

    Returns
    -------
    python function
    """
    atypes = []
    aflags = []
    for arg in args:
        atypes.append(arg[1])
        aflags.append((arg[2], arg[0]) + arg[3:])
    return CFUNCTYPE(result, *atypes)((name, dll), tuple(aflags))


def winfunc(name, dll, result, *args):
    """build and apply a ctypes prototype complete with parameter flags
    Parameters
    ----------
    name:(str) function name in the dll
    dll: (ctypes.windll) dll object
    result: result is the type of the result (c_int,..., python function handle,...)
    args: list of tuples with 3 or 4 elements each like (argname, argtype, in/out, default) where argname is the
    name of the argument, argtype is the type, in/out is 1 for input and 2 for output, and default is an optional
    default value.

    Returns
    -------
    python function
    """
    atypes = []
    aflags = []
    for arg in args:
        atypes.append(arg[1])
        aflags.append((arg[2], arg[0]) + arg[3:])
    return WINFUNCTYPE(result, *atypes)((name, dll), tuple(aflags))


def get_set_local_dir():
    if 'win32' in sys.platform:
        local_path = os.path.join(os.environ['HOMEDRIVE'] + os.environ['HOMEPATH'], 'pymodaq_local')
    else:
        local_path = os.path.join(os.environ['PATH'], 'pymodaq_local')

    if not os.path.isdir(local_path):
        os.makedirs(local_path)


    return local_path



def set_enable_recursive(children,enable=False):
    """
        | Set enable childs of chidren root argument with enable parameter value (False as default) calling recursively the method on children.
        |
        | Recursivity decreasing on children argument.

        =============== ===================== ==================================================
        **Parameters**    **Type**             **Description**
        *children*        settings tree node   The starting node of the (sub)tree to be treated
        *enable*          boolean              the default value to map
        =============== ===================== ==================================================

    """
    for child in children:
        if children==[]:
            return
        elif type(child) is QtWidgets.QSpinBox or type(child) is QtWidgets.QComboBox or type(child) is QtWidgets.QPushButton or type(child) is QtWidgets.QListWidget:
            child.setEnabled(enable)
        else:
            set_enable_recursive(child.children(),enable)


def find_file(string,extension):
    """
        Find .extension file list from the given list and the regular expression

        ============== ========== =======================================================
        **Parameters**   **Type**   **Description**
        *string*         string     raw splitted command result containing the file name
        *extension*      string     file extension (without .)
        ============== ========== =======================================================

        Returns
        -------
        string list
            The file list of the splitted os command result

        Examples
        --------
        >>> print(test_file)
        04/05/2018  11:55    <DIR>          .
        04/05/2018  11:55    <DIR>          ..
        04/05/2018  11:55    <DIR>          DAQ_Analysis
        04/05/2018  11:53             8ÿ758 find_and_replace.py
        03/05/2018  13:04             1ÿ327 find_py.py
        03/05/2018  13:25             3ÿ119 find_py_and_replace.py
        03/05/2018  15:47               619 find_words_in_line.py
        03/05/2018  16:02               524 replace_QtDesRess.py
        03/05/2018  13:20               142 test.py
        04/05/2018  11:53    <DIR>          __pycache__
                       6 fichier(s)           14ÿ489 octets
        >>> found_file=find_file(test_file,'py')
        >>> for i in range(0,len(found_file)):
        ...     print(found_file[i])
        ...
        find_and_replace.py
        find_py.py
        find_py_and_replace.py
        find_words_in_line.py
        replace_QtDesRess.py
        test.py
    """
    string_reg="([a-zA-Z0-9-_]*"+"\."+extension+")"
    regex=re.compile(string_reg,re.MULTILINE)
    ret=[]
    ret=re.findall(regex,string)
    re.purge()
    string_reg="[a-zA-Z0-9-_]*"
    regex=re.compile(string_reg,re.MULTILINE)
    for i in range(0,len(ret)):
        ret[i]=re.search(regex,ret[i]).group(0)
    return ret[:-1]


def recursive_find_files_extension(ini_path, ext, paths=[]):
    with os.scandir(ini_path) as it:
        for entry in it:
            if os.path.splitext(entry.name)[1][1:] == ext and entry.is_file():
                paths.append(entry.path)
            elif entry.is_dir():
                recursive_find_files_extension(entry.path, ext, paths)
    return paths






def nparray2Qpixmap(arr):
    result = QtGui.QImage(arr.data, arr.shape[1], arr.shape[0], QtGui.QImage.Format_RGB32)
    a=QtGui.QPixmap()
    a.convertFromImage(result)
    return a


def h5tree_to_QTree(h5file,base_node,base_tree_elt=None,pixmap_items=[]):
    """
        | Convert a loaded h5 file to a QTreeWidgetItem element structure containing two columns.
        | The first is the name of the h5 current node, the second is the path of the node in the h5 structure.
        |
        | Recursive function discreasing on base_node.

        ==================   ======================================== ===============================
        **Parameters**        **Type**                                 **Description**

          *h5file*            instance class File from tables module   loaded h5 file

          *base_node*         pytables h5 node                         parent node

          *base_tree_elt*     QTreeWidgetItem                          parent QTreeWidgetItem element
        ==================   ======================================== ===============================

        Returns
        -------
        QTreeWidgetItem
            h5 structure copy converted into QtreeWidgetItem structure.

        See Also
        --------
        h5tree_to_QTree

    """
    
    if base_tree_elt is None:
        base_tree_elt=QtWidgets.QTreeWidgetItem([base_node._v_name,"",base_node._v_pathname])
    for node in h5file.list_nodes(base_node):
        child=QtWidgets.QTreeWidgetItem([node._v_name,"",node._v_pathname])
        if 'pixmap' in node._v_attrs:
            pixmap_items.append(dict(node=node,item=child))
        if isinstance(node, tables.Group):
            h5tree_to_QTree(h5file,node,child,pixmap_items)

        base_tree_elt.addChild(child)

    return base_tree_elt,pixmap_items

def get_h5file_scans(h5file,path='/'):
    scan_list=[]
    for node in h5file.walk_nodes(path):
        if 'pixmap2D' in node._v_attrs:
            scan_list.append(dict(scan_name='{:s}_{:s}'.format(node._v_parent._v_name,node._v_name),path=node._v_pathname, data=node._v_attrs['pixmap2D']))

    return scan_list


def pixmap2ndarray(pixmap,scale=None):
    channels_count = 4
    image = pixmap.toImage()
    if scale==None:
        scale=[100,100]
    image=image.scaled(scale[0],scale[1],QtCore.Qt.KeepAspectRatio)

    #s = image.bits().asstring(image.width() * image.height() * channels_count)
    #arr = np.fromstring(s, dtype=np.uint8).reshape((image.height(), image.width(), channels_count)) 


    b = image.bits()
    # sip.voidptr must know size to support python buffer interface
    b.setsize(image.width() * image.height() * channels_count)
    arr = np.frombuffer(b, np.uint8).reshape((image.height(), image.width(), channels_count))
    return arr

def my_moment(x,y):
    dx=np.mean(np.diff(x))
    norm=np.sum(y)*dx
    m=[np.sum(x*y)*dx/norm]
    m.extend([np.sqrt(np.sum((x-m[0])**2*y)*dx/norm)])
    return m

def odd_even(x):
    """
		odd_even tells if a number is odd (return True) or even (return False)
		
		Parameters
		----------
		x: the integer number to test
		  
		Returns
		-------
		bool : boolean
    """
    if int(x)%2==0:
        bool=False
    else:
        bool=True
    return bool 

def set_scan_spiral(start_axis1,start_axis2,rmax,rstep):
    """Set a spiral scan of a 0D Data aquisition.

        =============== ========== ==========================================
        **Parameters**   **Type**   **Description**
        *start_axis1*    int        The starting value of the first sequence
        *start_axis2*    int        The starting value of the second sequence  
        *rmax*           int        The end point
        *rstep*          int        The value of one step
        =============== ========== ==========================================

        Returns
        -------
        (int,int list,int list,float list,float list,float list,list of 2 float lists) tuple
            The tuple containing :
             * the number of steps
             * the first axis indexes
             * the second axis indexes
             * the first axis with unique values
             * the second axis with unique values
             * the first axis
             * the second axis
             * the positions float values

        Examples
        --------

            >>> import daq_utils as Du
            >>> start_axis1,start_axis2=1,1
            >>> rmax=2
            >>> rstep=1
            >>> spiral_scan=Du.set_scan_spiral(start_axis1,start_axis2,rmax,rstep)
            >>> print(spiral_scan[0])       #The number of step
            25                                  
            >>> print(spiral_scan[1])       #The first distributed axis
            [-1  0  1  2  3]
            >>> print(spiral_scan[2])       #The second distributed axis
            [-1  0  1  2  3]
            >>> print(spiral_scan[3])       #The positions scalar list computed
            [[1, 1], [2, 1], [2, 2], [1, 2], [0, 2],
            [0, 1], [0, 0], [1, 0], [2, 0], [3, 0],
            [3, 1], [3, 2], [3, 3], [2, 3], [1, 3],
            [0, 3], [-1, 3], [-1, 2], [-1, 1], [-1, 0],
            [-1, -1], [0, -1], [1, -1], [2, -1], [3, -1]]
    """
    ind=0
    flag=True
    
    Nlin=np.trunc(rmax/rstep)    
    axis_1_indexes=[0]
    axis_2_indexes=[0]


    while flag:
        if odd_even(ind):
            step=1
        else:
            step=-1
        if flag:
            for ind_step in range(ind):
                axis_1_indexes.append(axis_1_indexes[-1]+step)
                axis_2_indexes.append(axis_2_indexes[-1])
                if len(axis_1_indexes)>=(2*Nlin+1)**2:
                    flag=False
                    break
        if flag:            
            for ind_step in range(ind):

                axis_1_indexes.append(axis_1_indexes[-1])
                axis_2_indexes.append(axis_2_indexes[-1]+step)
                if len(axis_1_indexes)>=(2*Nlin+1)**2:
                    flag=False
                    break
        ind+=1
    axis_1_indexes=np.array(axis_1_indexes,dtype=int)
    axis_2_indexes=np.array(axis_2_indexes,dtype=int)
    
    axis_1_unique=np.unique(axis_1_indexes)
    axis_1_unique=axis_1_unique.astype(float)
    axis_2_unique=np.unique(axis_2_indexes)
    axis_2_unique=axis_2_unique.astype(float)
    axis_1=np.zeros_like(axis_1_indexes,dtype=float)
    axis_2=np.zeros_like(axis_2_indexes,dtype=float)
    
    positions=[]
    for ind in range(len(axis_1)):
        axis_1[ind]=axis_1_indexes[ind]*rstep+start_axis1
        axis_2[ind]=axis_2_indexes[ind]*rstep+start_axis2
        positions.append([axis_1[ind],axis_2[ind]])

    for ind in range(len(axis_1_unique)):
        axis_1_unique[ind]=axis_1_unique[ind]*rstep+start_axis1
        axis_2_unique[ind]=axis_2_unique[ind]*rstep+start_axis2

 
    axis_1_indexes=axis_1_indexes-np.min(axis_1_indexes)
    axis_2_indexes=axis_2_indexes-np.min(axis_2_indexes)


    Nsteps=len(positions)
    return ScanParameters(Nsteps,axis_1_indexes,axis_2_indexes,axis_1_unique,axis_2_unique,positions)

def linspace_step(start,stop,step):
    """
        Compute a regular linspace_step distribution from start to stop values.

        =============== =========== ======================================
        **Parameters**    **Type**    **Description**
        *start*            scalar      the starting value of distribution
        *stop*             scalar      the stopping value of distribution
        *step*             scalar      the length of a distribution step
        =============== =========== ======================================

        Returns
        -------

        scalar array
            The computed distribution axis as an array.

        Examples
        --------
        >>> import DAQ_utils as Du
        >>> import numpy as np
        >>>    #arguments initializing
        >>> start=0
        >>> stop=5
        >>> step=0.25
        >>> linspace_distribution=Du.linspace_step(start,stop,step)
        >>> print(linspace_distribution)
        >>>    #computed distribution
        [ 0.    0.25  0.5   0.75  1.    1.25  1.5   1.75  2.    2.25  2.5   2.75
          3.    3.25  3.5   3.75  4.    4.25  4.5   4.75  5.  ]        
    """
    tmp=start
    out=np.array([tmp])    
    if step>=0:
        while (tmp<=stop):
            tmp=tmp+step
            out=np.append(out,tmp)
    else:
        while (tmp>=stop):
            tmp=tmp+step
            out=np.append(out,tmp)
    return out[0:-1]



def set_scan_linear(start_axis1,start_axis2,stop_axis1,stop_axis2,step_axis1,step_axis2,back_and_force=False):
    """
        Set a linear scan of a 0D Data aquisition.
        The positions scalar list is computed by a Cartesian product of the first distributed axis and the second one.
        
        The result size is composed by :
        * a single integer representing the number of step
        * a n items integer array representing the first distributed axis
        * a k items integer array representing the second distributed axis
        * a n*k items containing the combinaisons of the first and the second axis distribution.

        ================ ========== =============================================
        **Parameters**    **Type**   **Description**
        *start_axis1*     scalar     The starting value of the first sequence
        *start_axis2*     scalar     The starting value of the second sequence
        *stop_axis1*      scalar     The end point of the first sequence
        *stop_axis2*      scalar     The end point of the second sequence
        *step_axis1*      float      The value of one step of the first sequence
        *step_axis2*     float      The value of one step of the second sequence
        *back_and_force*  boolean    ???
        ================ ========== =============================================


        Returns
        -------
        (int,float list,float list,scalar list) tuple
            The tuple containing:
             * The number of step
             * The first distributed axis
             * The second distributed axis
             * The positions scalar list computed

        Examples
        --------
        ..doctest::

            >>> import DAQ_utils as Du
            >>> start_axis1,start_axis2=1,1
            >>> stop_axis1,stop_axis2=3,3
            >>> step_axis1,step_axis2=1,1
            >>> linear_scan=Du.set_scan_linear(start_axis1,start_axis2,stop_axis1,stop_axis2,step_axis1,step_axis2)
            >>> print(linear_scan[0])       #The number of step
            9
            >>> print(linear_scan[1])       #The first distributed axis
            [1 2 3]
            >>> print(linear_scan[2])       #The second distributed axis
            [1 2 3]
            >>> print(linear_scan[3])       #The positions scalar list computed
            [[1, 1], [1, 2], [1, 3], [2, 1], [2, 2], [2, 3], [3, 1], [3, 2], [3, 3]]
    """
    axis_1_unique=linspace_step(start_axis1,stop_axis1,step_axis1)
    axis_2_unique=linspace_step(start_axis2,stop_axis2,step_axis2)
    positions=[]
    axis_1_indexes=[]
    axis_2_indexes=[]
    axis_1=[]
    axis_2=[]   
    for ind_x,pos1 in enumerate(axis_1_unique):
        if back_and_force:
            for ind_y,pos2 in enumerate(axis_2_unique):
                if not odd_even(ind_x):
                    positions.append([pos1,pos2])
                    axis_1.append(pos1)
                    axis_2.append(pos2)
                    axis_1_indexes.append(ind_x)
                    axis_2_indexes.append(ind_y)
                else:
                    positions.append([pos1,axis_2_unique[len(axis_2_unique)-ind_y-1]])
                    axis_1.append(pos1)
                    axis_2.append(axis_2_unique[len(axis_2_unique)-ind_y-1])
                    axis_1_indexes.append(ind_x)
                    axis_2_indexes.append(len(axis_2_unique)-ind_y-1)   
        else:
            for ind_y,pos2 in enumerate(axis_2_unique):
                axis_1.append(pos1)
                axis_2.append(pos2)
                positions.append([pos1,pos2])
                axis_1_indexes.append(ind_x)
                axis_2_indexes.append(ind_y)


    Nsteps=len(positions)
    return ScanParameters(Nsteps,axis_1_indexes,axis_2_indexes,axis_1_unique,axis_2_unique,positions)


def set_scan_random(start_axis1,start_axis2,stop_axis1,stop_axis2,step_axis1,step_axis2):
    scan_parameters = set_scan_linear(start_axis1, start_axis2, stop_axis1, stop_axis2, step_axis1, step_axis2, back_and_force=False)

    positions_shuffled=scan_parameters.positions[:]
    np.random.shuffle(positions_shuffled)
    axis_1_indexes=[]
    axis_2_indexes=[]

    for pos in positions_shuffled:
        axis_1_indexes.append(np.where(scan_parameters.axis_2D_1==pos[0])[0][0])
        axis_2_indexes.append(np.where(scan_parameters.axis_2D_2==pos[1])[0][0])


    Nsteps = len(scan_parameters.positions)
    return ScanParameters(Nsteps,axis_1_indexes,axis_2_indexes,scan_parameters.axis_2D_1,scan_parameters.axis_2D_2,
                          positions_shuffled)

def set_param_from_param(param_old,param_new):
    """
        Walk through parameters children and set values using new parameter values.
    """
    for child_old in param_old.children():
        try:
            path=param_old.childPath(child_old)
            child_new=param_new.child(*path)
            param_type=child_old.type()

            if 'group' not in param_type: #covers 'group', custom 'groupmove'...
                try:
                    if 'list' in param_type:#check if the value is in the limits of the old params (limits are usually set at initialization)
                        if child_new.value() not in child_old.opts['limits']:
                            child_old.opts['limits'].append(child_new.value())

                        child_old.setValue(child_new.value())
                    elif 'str' in param_type or 'browsepath' in param_type or 'text' in param_type:
                        if child_new.value()!="":#to make sure one doesnt overwrite something
                            child_old.setValue(child_new.value())
                    else:
                        child_old.setValue(child_new.value())
                except Exception as e:
                    print(str(e))
            else:
                set_param_from_param(child_old,child_new)
        except Exception as e:
            print(str(e))

def find_part_in_path_and_subpath(base_dir,part='',create=False):
    """
        Find path from part time.

        =============== ============ =============================================
        **Parameters**  **Type**      **Description**
        *base_dir*      Path object   The directory to browse
        *part*          string        The date of the directory to find/create
        *create*        boolean       Indicate the creation flag of the directory
        =============== ============ =============================================

        Returns
        -------
        Path object
            found path from part

        Examples
        --------
        ..doctest::

            >>> import DAQ_utils as Du
            >>> import pathlib as pl
            >>> base_dir=pl.Path("") #Getting the current path
            >>> print(base_dir)
            .
            >>> path=Du.find_part_in_path_and_subpath(base_dir,"2018",True)
            >>> print(path)       #Path of created directory "2018"
            2018
            >>> path=Du.find_part_in_path_and_subpath(base_dir,"2017",False)
            >>> print(path)       #Path is none since "2017" dir doesn't exist
            None
            >>> path=Du.find_part_in_path_and_subpath(base_dir,"2018",False)
            >>> print(path)       #Path of directory "2018"
            2018
    """
    found_path=None
    if part in base_dir.parts: #check if current year is in the given base path
        if base_dir.name==part:
            found_path=base_dir
        else:
            for ind in range(len(base_dir.parts)):
                tmp_path=base_dir.parents[ind]
                if tmp_path.name==part:
                    found_path=base_dir.parents[ind]
                    break
    else:#if not check if year is in the subfolders
        subfolders_year_name=[x.name for x in base_dir.iterdir() if x.is_dir()]
        subfolders_found_path=[x for x in base_dir.iterdir() if x.is_dir()]
        if part not in subfolders_year_name:
            if create:
                found_path=base_dir.joinpath(part)
                found_path.mkdir()
            else:
                found_path = base_dir
        else:
            ind_path=subfolders_year_name.index(part)
            found_path=subfolders_found_path[ind_path]
    return found_path

def set_current_scan_path(base_dir,base_name='Scan',update_h5=False,next_scan_index=0,create_scan_folder = False, create_dataset_folder=True):
    """
        Set the path of the current scan and create associated directory tree.
        As default :

        Year/Date/Dataset_Date_ScanID/ScanID


        =============== ============ =====================================
        **Parameters**  **Type**      **Description**
        base_dir        Path object   The base directory
        base_name       string        Name of the current scan
        update_h5       boolean       1/0 to update the associated h5 file
        =============== ============ =====================================

        Returns
        -------
        scan_path 
            indexed base_name, new folder indexed from base name at the day

        See Also
        --------
        DAQ_utils.find_part_in_path_and_subpath

        Examples
        --------
        ..doctest::

            >>> import DAQ_utils as Du
            >>> import pathlib as pl
            >>> base_dir=pl.Path("") #Getting the current path
            >>>
            >>> current_scan_path=Du.set_current_scan_path(base_dir)
            >>>  #Function call with default name
            >>> print(current_scan_path[0])       #The full scan path
            2018\20180424\Dataset_20180424_000\Scan000
            >>> print(current_scan_path[1])       #The indexed base name
            Scan000
            >>> print(current_scan_path[2])       #The dataset_path
            2018\20180424\Dataset_20180424_000
            >>>
            >>> current_scan_path=Du.set_current_scan_path(base_dir,'Specific name')
            >>> #Function call with a specific name
            >>> print(current_scan_path[0])       #The full scan path
            2018\20180424\Dataset_20180424_000\Specific name000
            >>> print(current_scan_path[1])       #The indexed base name
            Specific name000
            >>> print(current_scan_path[2])       #The dataset_path
            2018\20180424\Dataset_20180424_000
    """
    base_dir=Path(base_dir)
    date=datetime.date.today()

    year_path=find_part_in_path_and_subpath(base_dir,part=str(date.year),create=True)# create directory of the year if it doen't exist and return it
    day_path=find_part_in_path_and_subpath(year_path,part=date.strftime('%Y%m%d'),create=True)# create directory of the day if it doen't exist and return it

    date=datetime.date.today()
    dataset_base_name=date.strftime('Dataset_%Y%m%d')
    dataset_paths=sorted([path for path in day_path.glob(dataset_base_name+"*") if path.is_dir()])
    if dataset_paths==[]:
        ind_dataset=0
    else:
        if update_h5:
            ind_dataset=int(dataset_paths[-1].name.partition(dataset_base_name+"_")[2])+1
        else:
            ind_dataset=int(dataset_paths[-1].name.partition(dataset_base_name+"_")[2])
    dataset_path=find_part_in_path_and_subpath(day_path,part=dataset_base_name+"_{:03d}".format(ind_dataset),create=create_dataset_folder)

    scan_paths=sorted([path for path in dataset_path.glob(base_name+'*') if path.is_dir()])
    # if scan_paths==[]:
    #     ind_scan=0
    # else:
    #     if list(scan_paths[-1].iterdir())==[]:
    #         ind_scan=int(scan_paths[-1].name.partition(base_name)[2])
    #     else:
    #         ind_scan=int(scan_paths[-1].name.partition(base_name)[2])+1
    ind_scan = next_scan_index

    scan_path=find_part_in_path_and_subpath(dataset_path,part=base_name+'{:03d}'.format(ind_scan),create=create_scan_folder)
    return scan_path,base_name+'{:03d}'.format(ind_scan),dataset_path


def select_file(start_path=None,save=True, ext=None):
    """
        Save or open a file with Qt5 file dialog, to be used within an Qt5 loop.

        =============== ======================================= ===========================================================================
        **Parameters**     **Type**                              **Description**

        *start_path*       Path object or str or None, optional  the path Qt5 will open in te dialog
        *save*             bool, optional                        * if True, a savefile dialog will open in order to set a savefilename
                                                                 * if False, a openfile dialog will open in order to open an existing file
        *ext*              str, optional                         the extension of the file to be saved or opened
        =============== ======================================= ===========================================================================

        Returns
        -------
        Path object
            the Path object pointing to the file

        Examples
        --------
        >>>from PyQt5 import QtWidgets
        >>>from PyMoDAQ.DAQ_Utils.DAQ_utils import select_file
        >>>import sys
        >>>app = QtWidgets.QApplication(sys.argv)
        >>>    #Open a save windows
        >>>select_file(start_path="C:/test",save=False,ext='h5')
        >>>sys.exit(app.exec_())

    """
    if ext is None:
        ext = '*'
    if not save:
        if not isinstance(ext, list):
            ext = [ext]
        
        filter = "Data files ("
        for ext_tmp in ext:
            filter += '*.'+ext_tmp+" "
        filter += ")"
    if start_path is not None:
        if not isinstance(start_path, str):
            start_path = str(start_path)
    if save:
        fname = QtWidgets.QFileDialog.getSaveFileName(None, 'Enter a .'+ext+' file name', start_path, ext+" file (*."+ext+")")
    else:
        fname = QtWidgets.QFileDialog.getOpenFileName(None, 'Select a file name', start_path, filter)

    fname=fname[0]
    if fname != '': #execute if the user didn't cancel the file selection
        fname=Path(fname)
        if save:
            parent=fname.parent
            filename=fname.stem
            fname=parent.joinpath(filename+"."+ext) #forcing the right extension on the filename
    return fname #fname is a Path object

def find_index(x,threshold):
    """
    find_index finds the index ix such that x(ix) is the closest from threshold
    
    Parameters
    ----------
    x : vector
    threshold : list of scalar

    Returns
    -------
    out : list of 2-tuple containing ix,x[ix]
            out=[(ix0,xval0),(ix1,xval1),...]
    
    Examples
    --------
    >>> import array_manipulation as am
    >>> import numpy as np
    >>>    #vector creation
    >>> x_vector=np.array([1,2,3])
    >>> index=am.find_index(x_vector,4)
    >>>    #the nearest index from threshold
    >>> print(index)
    >>>    #ix=2, x[2]=3  , threshold=4
    [(2, 3)]
    >>>
    >>> x_vector=np.array([1,2,3,4,5,6,7,8,9,10])
    >>> index=am.find_index(x_vector,[3.8,7.5,12.])
    >>>    #the nearest indexs from threshold list [3.8,7.5,12.]
    >>> print(index)
    >>>    #ix0=3, x[3]=4  , threshold=3.8
    >>>    #ix1=6, x[6]=7  , threshold=7.5
    >>>    #ix2=9, x[9]=10 , threshold=12.0
    [(3, 4), (6, 7), (9, 10)]
    """
        
    if np.isscalar(threshold):
        threshold=[threshold]
    out=[]
    for value in threshold:
        ix=int(np.argmin(np.abs(x-value))) 
        out.append((ix,x[ix]))
    return out

def gauss1D(x,x0,dx,n=1):
    """
    compute the gaussian function along a vector x, centered in x0 and with a
    FWHM i intensity of dx. n=1 is for the standart gaussian while n>1 defines
    a hypergaussian

    =============== =========== ============================================================
    **Parameters**    **Type**    **Description**
    *x*               vector      vector
    *x0*              float       the central position of the gaussian
    *dx*              float       the FWHM of the gaussian
    *n*               float       define hypergaussian, n=1 by default for regular gaussian
    =============== =========== ============================================================     

    Returns
    -------
    out : vector
      the value taken by the gaussian along x axis

    Examples
    --------
    >>> import DAQ_utils as Du
    >>> import numpy as np                
    >>> x=np.array([0,1,2,3,4])            #argument initializing
    >>> x0=2
    >>> dx=0.5
    >>> gaussian_distribution=Du.gauss1D(x,x0,dx)
    >>> print(gaussian_distribution)       #The computed gaussian distribution
    [  2.32830644e-10   3.90625000e-03   1.00000000e+00   3.90625000e-03
       2.32830644e-10]    
    """
    out=np.exp(-2*np.log(2)**(1/n)*(((x-x0)/dx))**(2*n))
    return out

def gauss2D(x,x0,dx,y,y0,dy,n=1,angle=0):
    """
    compute the 2D gaussian function along a vector x, centered in x0 and with a
    FWHM in intensity of dx and smae along y axis. n=1 is for the standart gaussian while n>1 defines
    a hypergaussian. optionally rotate it by an angle in degree

    Parameters
    ----------
    x : vector
    x0 : a float: the central position of the gaussian
    dx : a float :the FWHM of the gaussian
    n=1 : a float to define hypergaussian, n=1 by default for regular gaussian        
    angle=0 : a float to rotate main axes
    
    Returns
    -------
    out : vector
      the value taken by the gaussian along x axis
    """
    if angle==0:
        data=np.transpose(np.outer(gauss1D(x,x0,dx,n),gauss1D(y,y0,dy,n)))

    else:

        theta = np.radians(angle)
        c, s = np.cos(theta), np.sin(theta)
        R = np.array(((c,-s), (s, c)))
        (x0r,y0r)=tuple(R.dot(np.array([x0,y0])))
        
        data=np.zeros((len(y),len(x)))
        
        for indx,xtmp in enumerate(x):
            for indy,ytmp in enumerate(y):
                rotatedvect=R.dot(np.array([xtmp,ytmp]))
                data[indy,indx]=np.exp(-2*np.log(2)**(1/n)*((rotatedvect[0]-x0r)/dx)**(2*n))*np.exp(-2*np.log(2)**(1/n)*((rotatedvect[1]-y0r)/dy)**(2*n))
                  
    return data
    
def ftAxis_time(Npts,time_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    =============== =========== ===========================================================================
    **Parameters**    **Type**    **Description**
    *Npts*            int          A number of points defining the length of both grids
    *time_max*       float         The maximum circular frequency in the spectral domain. its unit defines
                                   the temporal units. ex: omega_max in rad/fs implies time_grid in fs
    =============== =========== ===========================================================================

    Returns
    -------
    omega_grid : vector
      The spectral axis of the FFT

    time_grid : vector
      The temporal axis of the FFT

    Example
    -------
    >>> (omega_grid, time_grid)=ftAxis(Npts,omega_max)
    ...
    """
    dT=time_max/Npts
    omega_max=(Npts-1)/2*2*np.pi/time_max
    omega_grid = np.linspace(-omega_max,omega_max,Npts)
    time_grid = dT*np.linspace(-(Npts-1)/2,(Npts-1)/2,Npts)
    return omega_grid, time_grid
    
    
def ft(x,dim=0):
    out=np.fft.fftshift(np.fft.fft(np.fft.fftshift(x,axes=dim),axis=dim),axes=dim)
    return out
    
def ift(x,dim=0):
    out=np.fft.fftshift(np.fft.ifft(np.fft.fftshift(x,axes=dim),axis=dim),axes=dim)
    return out


def ftAxis(Npts, omega_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    Parameters
    ----------
    Npts : number
      A number of points defining the length of both grids
    omega_max : number
      The maximum circular frequency in the spectral domain. its unit defines
      the temporal units. ex: omega_max in rad/fs implies time_grid in fs

    Returns
    -------
    omega_grid : vector
      The spectral axis of the FFT

    time_grid : vector
      The temporal axis of the FFT

    Example
    -------
    >>> (omega_grid, time_grid)=ftAxis(Npts,omega_max)
    ...
    """
    dT = 2 * np.pi / (2 * omega_max)
    omega_grid = np.linspace(-omega_max, omega_max, Npts)
    time_grid = dT * np.linspace(-(Npts - 1) / 2, (Npts - 1) / 2, Npts)
    return omega_grid, time_grid


def ftAxis_time(Npts, time_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    Parameters
    ----------
    Npts : number
      A number of points defining the length of both grids
    omega_max : number
      The maximum circular frequency in the spectral domain. its unit defines
      the temporal units. ex: omega_max in rad/fs implies time_grid in fs

    Returns
    -------
    omega_grid : vector
      The spectral axis of the FFT

    time_grid : vector
      The temporal axis of the FFT

    Example
    -------
    >>> (omega_grid, time_grid)=ftAxis(Npts,omega_max)
    ...
    """
    dT = time_max / Npts
    omega_max = (Npts - 1) / 2 * 2 * np.pi / time_max
    omega_grid = np.linspace(-omega_max, omega_max, Npts)
    time_grid = dT * np.linspace(-(Npts - 1) / 2, (Npts - 1) / 2, Npts)
    return omega_grid, time_grid


def ft(x, dim=0):
    out = np.fft.fftshift(np.fft.fft(np.fft.fftshift(x, axes=dim), axis=dim), axes=dim)
    return out


def ft2(x, dim=None):
    out = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(x, axes=dim)), axes=dim)
    return out


def ift2(x, dim=0):
    out = np.fft.fftshift(np.fft.ifft2(np.fft.fftshift(x, axes=dim)), axes=dim)
    return out







if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget();
    file_path=".//test.h5"
    h5file=tables.open_file(file_path)
    prog = H5Browser(form,h5file)
    form.show()
    sys.exit(app.exec_())
