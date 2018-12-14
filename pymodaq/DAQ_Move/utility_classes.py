from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QVariant, QSize
# from enum import IntEnum
from easydict import EasyDict as edict
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree
from pymodaq.daq_utils.daq_utils import ThreadCommand,find_file,find_in_path,get_names,make_enum

import os
import sys
import numpy as np

comon_parameters=[  {'name': 'epsilon', 'type': 'float', 'value': 0.01},
                  {'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 10000, 'default': 10000},

                    {'title': 'Bounds:', 'name': 'bounds', 'type': 'group', 'children':[
                        {'title': 'Set Bounds:', 'name': 'is_bounds', 'type': 'bool', 'value': False},
                        {'title': 'Min:', 'name': 'min_bound', 'type': 'float', 'value': 0, 'default': 0},
                        {'title': 'Max:', 'name': 'max_bound', 'type': 'float', 'value': 1, 'default': 1},]},
                    
                    {'title': 'Scaling:', 'name': 'scaling', 'type': 'group', 'children':[
                         {'title': 'Use scaling:', 'name': 'use_scaling', 'type': 'bool', 'value': False, 'default': False},
                         {'title': 'Scaling factor:', 'name': 'scaling', 'type': 'float', 'value': 1., 'default': 1.},
                         {'title': 'Offset factor:', 'name': 'offset', 'type': 'float', 'value': 0., 'default': 0.}]}]


class DAQ_Move_base(QObject):
    """
        ================== =================================================
        **Attributes**      **Type**

        *Move_Done_signal*  instance of pyqtSignal
        *params*            list

        *parent*            QObject
        *controller*        instance of the controller object
        *stage*             instance of the stage (axis or whatever) object
        *status*            dictionnary
        *current_position*  float
        *target_position*   float
        *settings*          instance of pyqtgraph Parametertree
        ================== =================================================

        See Also
        --------
        send_param_status
    """
    Move_Done_signal=pyqtSignal(float)
    is_multiaxes=False
    params= []

    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_base,self).__init__()

        self.parent=parent
        self.controller=None
        self.stage=None
        self.status=edict(info="",controller=None,stage=None,initialized=False)
        self.current_position=0
        self.target_position=0
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            self.settings.restoreState(params_state)

        self.settings.sigTreeStateChanged.connect(self.send_param_status)

    def check_bound(self,position):
        if self.settings.child('bounds','is_bounds').value():
            if position>self.settings.child('bounds','max_bound').value():
                position=self.settings.child('bounds','max_bound').value()
                self.emit_status(ThreadCommand('outofbounds',[]))
            elif position<self.settings.child('bounds','min_bound').value():
                position=self.settings.child('bounds','min_bound').value()
                self.emit_status(ThreadCommand('outofbounds',[]))
        return position

    def get_position_with_scaling(self,pos):
        """
            Get the current position from the hardware with scaling conversion.

            =============== ========= =====================
            **Parameters**  **Type**  **Description**
             *pos*           float    the current position
            =============== ========= =====================

            Returns
            =======
            float
                the computed position.
        """
        if self.settings.child('scaling','use_scaling').value():
            pos=(pos-self.settings.child('scaling','offset').value())*self.settings.child('scaling','scaling').value()
        return pos

    def set_position_with_scaling(self,pos):
        """
            Set the current position from the parameter and hardware with scaling conversion.

            =============== ========= ==========================
            **Parameters**  **Type**  **Description**
             *pos*           float    the position to be setted
            =============== ========= ==========================

            Returns
            =======
            float
                the computed position.
        """
        if self.settings.child('scaling','use_scaling').value():
            pos=pos/self.settings.child('scaling','scaling').value()+self.settings.child('scaling','offset').value()
        return pos

    def emit_status(self,status):
        """
            | Emit the statut signal from the given status parameter.
            |
            | The signal is sended to the gui to update the user interface.

            =============== ===================== ========================================================================================================================================
            **Parameters**   **Type**              **Description**
             *status*        ordered dictionnary    dictionnary containing keys:
                                                        * *info* : string displaying various info
                                                        * *controller*: instance of the controller object in order to control other axes without the need to init the same controller twice
                                                        * *stage*: instance of the stage (axis or whatever) object
                                                        * *initialized*: boolean indicating if initialization has been done corretly
            =============== ===================== ========================================================================================================================================
        """
        if self.parent is not None:
            self.parent.status_sig.emit(status)
        else:
            print(status)

    def poll_moving(self):
        """
            Poll the current moving. In case of timeout emit the raise timeout Thread command.
            
            See Also
            --------
            DAQ_utils.ThreadCommand, Move_Done
        """
        sleep_ms=50
        ind=0
        while np.abs(self.Check_position()-self.target_position)>self.settings.child(('epsilon')).value():
            QThread.msleep(sleep_ms)

            ind+=1

            if ind*sleep_ms>=self.settings.child(('timeout')).value():

                self.emit_status(ThreadCommand('raise_timeout'))
                break
            self.current_position=self.Check_position()
            QtWidgets.QApplication.processEvents()
        self.Move_Done()

    def Move_Done(self,position=None):#the position argument is just there to match some signature of child classes
        """
            | Emit a move done signal transmitting the float position to hardware.
            | The position argument is just there to match some signature of child classes.

            =============== ========== =============================================================================
             **Arguments**   **Type**  **Description**
             *position*      float     The position argument is just there to match some signature of child classes
            =============== ========== =============================================================================

        """
        position=self.Check_position()
        self.Move_Done_signal.emit(position)

    @pyqtSlot(edict)
    def update_settings(self,settings_parameter_dict):#settings_parameter_dict=edict(path=path,param=param)
        """
            Receive the settings_parameter signal from the param_tree_changed method and make hardware updates of mmodified values.

            ==========================  =========== ==========================================================================================================
            **Arguments**               **Type**     **Description**
            *settings_parameter_dict*   dictionnary Dictionnary with the path of the parameter in hardware structure as key and the parameter name as element
            ==========================  =========== ==========================================================================================================

            See Also
            --------
            send_param_status, commit_settings
        """
        path=settings_parameter_dict.path
        param=settings_parameter_dict.param
        try:
            self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
        except: pass
        self.settings.child(*path[1:]).setValue(param.value())

        self.settings.sigTreeStateChanged.connect(self.send_param_status)
        self.commit_common_settings(param)
        self.commit_settings(param)


    def commit_common_settings(self,param):
        pass

    def commit_settings(self,param):
      """
        to subclass to transfer parameters to hardware
      """
      pass

    def send_param_status(self,param,changes):
        """
            | Send changes value updates to the gui to update consequently the User Interface.
            | The message passing is made via the Thread Command "update_settings".

            =============== =================================== ==================================================
            **Parameters**  **Type**                             **Description**
            *param*         instance of pyqtgraph parameter      The parameter to be checked
            *changes*       (parameter,change,infos)tuple list   The (parameter,change,infos) list to be treated
            =============== =================================== ==================================================

            See Also
            ========
            DAQ_utils.ThreadCommand
        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                self.emit_status(ThreadCommand('update_settings',[path,data,change])) #send parameters values/limits back to the GUI

            elif change == 'value' or change == 'limits' or change=='options':
                self.emit_status(ThreadCommand('update_settings',[path,data,change])) #parent is the main detector object and status_sig will be send to the GUI thrad
            elif change == 'parent':
                pass

if __name__=='__main__':
    test=DAQ_Move_base()