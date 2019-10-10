from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QSize

import sys
from pymodaq.daq_measurement.daq_measurement_GUI import Ui_Form
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.fourier_filterer import FourierFilterer
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
import pyqtgraph as pg
import numpy as np
from enum import Enum

class Measurement_type(Enum):
    Cursor_Integration = 0
    Max = 1
    Min = 2
    Gaussian_Fit = 3
    Lorentzian_Fit = 4
    Exponential_Decay_Fit = 5
    Sinus = 6

    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]

    @classmethod
    def update_measurement_subtype(cls, mtype):
        measurement_gaussian_subitems = ["amp", "dx", "x0", "offset"]
        measurement_laurentzian_subitems = ["alpha", "gamma", "x0", "offset"]
        measurement_decay_subitems = ["N0", "gamma", 'x0', "offset"]
        measurement_cursor_subitems = ["sum", "mean", "std"]
        measurement_sinus_subtitems = ['A', 'dx', 'phi', 'offset']
        variables = ", "
        formula = ""
        subitems = []
        if mtype == 'Cursor_Integration':  # "Cursor integration":
            subitems = measurement_cursor_subitems

        if mtype == 'Gaussian_Fit':  # "Gaussian Fit":
            subitems = measurement_gaussian_subitems
            formula = "amp*np.exp(-2*np.log(2)*(x-x0)**2/dx**2)+offset"
            variables = variables.join(measurement_gaussian_subitems)

        elif mtype == 'Lorentzian_Fit':  # "Lorentzian Fit":
            subitems = measurement_laurentzian_subitems
            variables = variables.join(measurement_laurentzian_subitems)
            formula = "alpha/np.pi*gamma/2/((x-x0)**2+(gamma/2)**2)+offset"

        elif mtype == 'Exponential_Decay_Fit':  # "Exponential Decay Fit":
            subitems = measurement_decay_subitems
            variables = variables.join(measurement_decay_subitems)
            formula = "N0*np.exp(-(x-x0)/gamma)+offset"

        elif mtype == 'Sinus':
            subitems = measurement_sinus_subtitems
            variables = variables.join(measurement_sinus_subtitems)
            formula = "A*np.sin(2*np.pi*x/dx-phi)+offset"

        return [variables, formula, subitems]
    def gaussian_func(self, x, amp, dx, x0, offset):
        return amp * np.exp(-2 * np.log(2) * (x - x0) ** 2 / dx ** 2) + offset

    def laurentzian_func(self, x, alpha, gamma, x0, offset):
        return alpha / np.pi * 1 / 2 * gamma / ((x - x0) ** 2 + (1 / 2 * gamma) ** 2) + offset

    def decaying_func(self, x, N0, gamma, x0, offset):
        return N0 * np.exp(-(x-x0) / gamma) + offset

    def sinus_func(self, x, A, dx, phi, offset):
        return A*np.sin(2*np.pi*x/dx-phi)+offset

class DAQ_Measurement(Ui_Form,QObject):
    """
        =================== ================================== =======================================
        **Attributes**       **Type**                          **Description**


        *ui*                 QObject                           The local instance of User Interface
        *wait_time*          int                               The default delay of showing
        *parent*             QObject                           The QObject initializing the UI
        *xdata*              1D numpy array                    The x axis data
        *ydata*              1D numpy array                    The y axis data
        *measurement_types*  instance of daq_utils.DAQ_enums   The type of the measurement, between:
                                                                    * 'Cursor_Integration'
                                                                    * 'Max'
                                                                    * 'Min'
                                                                    * 'Gaussian_Fit'
                                                                    * 'Lorentzian_Fit'
                                                                    * 'Exponential_Decay_Fit'
        =================== ================================== =======================================

        References
        ----------
        Ui_Form, QObject, PyQt5, pyqtgraph
    """
    measurement_signal=pyqtSignal(list)
    def __init__(self,parent):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Ui_Form, self).__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(parent)

        self.widg = QtWidgets.QWidget()
        self.fourierfilt = FourierFilterer(self.widg)
        self.ui.splitter_2.addWidget(self.widg)
        self.ui.graph1D = self.fourierfilt.viewer1D.plotwidget
        QtWidgets.QApplication.processEvents()

        self.ui.splitter.setSizes([200, 400])
        self.ui.statusbar=QtWidgets.QStatusBar(parent)
        self.ui.statusbar.setMaximumHeight(15)
        self.ui.StatusBarLayout.addWidget(self.ui.statusbar)
        self.wait_time=1000
        self.parent=parent
        self.xdata=None
        self.ydata=None

        self.measurement_types=Measurement_type.names()
        self.measurement_type=Measurement_type(0)
        self.ui.measurement_type_combo.clear()
        self.ui.measurement_type_combo.addItems(self.measurement_types)

        self.ui.fit_curve = self.fourierfilt.viewer1D.plotwidget.plot()
        self.ui.fit_curve.setPen("y")
        self.ui.fit_curve.setVisible(False)

        self.ui.selected_region = self.fourierfilt.viewer1D.ROI
        self.ui.selected_region.setZValue(-10)
        self.ui.selected_region.setBrush('b')
        self.ui.selected_region.setOpacity(0.2)
        self.ui.selected_region.setVisible(True)
        self.fourierfilt.viewer1D.plotwidget.addItem(self.ui.selected_region)


        ##Connecting buttons:
        self.ui.Quit_pb.clicked.connect(self.Quit_fun,type = Qt.QueuedConnection)
        self.ui.measurement_type_combo.currentTextChanged[str].connect(self.update_measurement_subtype)
        self.ui.measure_subtype_combo.currentTextChanged[str].connect(self.update_measurement)
        self.update_measurement_subtype(self.ui.measurement_type_combo.currentText(),update=False)
        self.ui.selected_region.sigRegionChanged.connect(self.update_measurement)
        self.ui.result_sb.valueChanged.connect(self.ui.result_lcd.display)

    @pyqtSlot(dict)
    def update_fft_filter(self,d):
        self.frequency = d['frequency']
        self.phase = d['phase']
        self.update_measurement()

    def Quit_fun(self):
        """
            close the current instance of daq_measurement.

        """
        # insert anything that needs to be closed before leaving
        self.parent.close()

    def update_status(self,txt,wait_time=0):
        """
            Update the statut bar showing the given text message with a delay of wait_time ms (0s by default).

            =============== ========= ===========================
            **Parameters**

            *txt*             string   the text message to show

            *wait_time*       int      the delay time of waiting
            =============== ========= ===========================

        """
        self.ui.statusbar.showMessage(txt,wait_time)

    @pyqtSlot(str)
    def update_measurement_subtype(self,mtype,update=True):
        """
            | Update the ui-measure_subtype_combo from subitems and formula attributes, if specified by update parameter.
            | Linked with the update_measurement method

            ================ ========== =====================================================================================
            **Parameters**    **Type**   **Description**

            mtype             string      the Measurement_type index of the Measurement_type array (imported from daq_utils)

            update            boolean     the update boolean link with the update_measurement method
            ================ ========== =====================================================================================

            See Also
            --------
            update_measurement_subtype, update_measurement, update_status

        """
        self.measurement_type=Measurement_type[mtype]
        [variables,self.formula,self.subitems]=Measurement_type.update_measurement_subtype(mtype)

        try:
            self.ui.measure_subtype_combo.clear()
            self.ui.measure_subtype_combo.addItems(self.subitems)
            self.ui.formula_edit.setPlainText(self.formula)

            if update:
                self.update_measurement()
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def update_measurement(self):
        """
            Update :
             * the measurement results from the update_measurements method
             * the statut bar on cascade (if needed)
             * the User Interface function curve state and data (if needed).

            Emit the measurement_signal corresponding.

            See Also
            --------
            update_measurement, update_status

        """
        try:
            xlimits=self.ui.selected_region.getRegion()
            mtype = self.ui.measurement_type_combo.currentText()
            msubtype=self.ui.measure_subtype_combo.currentText()
            if mtype == 'Sinus':

                # boundaries = utils.find_index(self.xdata, [xlimits[0], xlimits[1]])
                # sub_xaxis = self.xdata[boundaries[0][0]:boundaries[1][0]]
                # sub_data = self.ydata[boundaries[0][0]:boundaries[1][0]]
                #self.fourierfilt.parent.setVisible(True)
                self.fourierfilt.show_data(dict(data=self.ydata, xaxis=self.xdata))
            else:
                #self.fourierfilt.parent.setVisible(False)
                pass

            measurement_results=self.do_measurement(xlimits[0],xlimits[1],self.xdata,self.ydata,mtype,msubtype)
            if measurement_results['status'] is not None:
                self.update_status(measurement_results['status'],wait_time=self.wait_time)
                return
            self.ui.result_sb.setValue(measurement_results['value'])
            self.measurement_signal.emit([measurement_results['value']])
            if measurement_results['datafit'] is not None:
                self.ui.fit_curve.setVisible(True)
                self.ui.fit_curve.setData(measurement_results['xaxis'],measurement_results['datafit'])
            else:
                self.ui.fit_curve.setVisible(False)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def eval_func(self,x,*args):
        dic = dict(zip(self.subitems, args))
        dic.update(dict(np=np,x=x))
        return eval(self.formula, dic)


    def do_measurement(self, xmin, xmax, xaxis, data1D, mtype, msubtype):
        try:
            boundaries = utils.find_index(xaxis, [xmin, xmax])
            sub_xaxis = xaxis[boundaries[0][0]:boundaries[1][0]]
            sub_data = data1D[boundaries[0][0]:boundaries[1][0]]
            mtypes = Measurement_type.names()
            if msubtype in self.subitems:
                msub_ind = self.subitems.index(msubtype)

            measurement_results=dict(status=None, value = 0, xaxis= np.array([]), datafit =np.array([]))

            if mtype == 'Cursor_Integration':  # "Cursor Intensity Integration":
                if msubtype == "sum":
                    result_measurement = np.sum(sub_data)
                elif msubtype == "mean":
                    result_measurement = np.mean(sub_data)
                elif msubtype == "std":
                    result_measurement = np.std(sub_data)
                else:
                    result_measurement = 0

            elif mtype == 'Max':  # "Max":
                result_measurement = np.max(sub_data)

            elif mtype == 'Min':  # "Min":
                result_measurement = np.min(sub_data)

            elif mtype == 'Gaussian_Fit':  # "Gaussian Fit":
                measurement_results['xaxis'] = sub_xaxis
                offset = np.min(sub_data)
                amp = np.max(sub_data) - np.min(sub_data)
                m = utils.my_moment(sub_xaxis, sub_data)
                p0 = [amp, m[1], m[0], offset]
                popt, pcov = curve_fit(self.eval_func, sub_xaxis, sub_data, p0=p0)
                measurement_results['datafit']=self.eval_func(sub_xaxis, *popt)
                result_measurement = popt[msub_ind]

            elif mtype == 'Lorentzian_Fit':  # "Lorentzian Fit":
                measurement_results['xaxis'] = sub_xaxis
                offset = np.min(sub_data)
                amp = np.max(sub_data) - np.min(sub_data)
                m = utils.my_moment(sub_xaxis, sub_data)
                p0 = [amp, m[1], m[0], offset]
                popt, pcov = curve_fit(self.eval_func, sub_xaxis, sub_data, p0=p0)
                measurement_results['datafit'] = self.eval_func(sub_xaxis, *popt)
                if msub_ind == 4:  # amplitude
                    result_measurement = popt[0] * 2 / (np.pi * popt[1])  # 2*alpha/(pi*gamma)
                else:
                    result_measurement = popt[msub_ind]

            elif mtype == 'Exponential_Decay_Fit':  # "Exponential Decay Fit":
                ind_x0 = utils.find_index(sub_data, np.max(sub_data))[0][0]
                x0 = sub_xaxis[ind_x0]
                sub_xaxis = sub_xaxis[ind_x0:]
                sub_data = sub_data[ind_x0:]
                offset = min([sub_data[0], sub_data[-1]])
                measurement_results['xaxis'] = sub_xaxis
                N0 = np.max(sub_data) - offset
                t37 = sub_xaxis[utils.find_index(sub_data-offset,0.37*N0)[0][0]]-x0
                #polynome = np.polyfit(sub_xaxis, -np.log((sub_data - 0.99 * offset) / N0), 1)
                p0 = [N0, t37, x0, offset]
                popt, pcov = curve_fit(self.eval_func, sub_xaxis, sub_data, p0=p0)
                measurement_results['datafit'] = self.eval_func(sub_xaxis, *popt)
                result_measurement = popt[msub_ind]

            elif mtype == 'Sinus':  #
                offset = np.mean(sub_data)
                A = (np.max(sub_data)-np.min(sub_data))/2
                phi=self.fourierfilt.phase
                dx=1/self.fourierfilt.frequency
                measurement_results['xaxis'] = sub_xaxis
                p0 = [A, dx, phi, offset]
                popt, pcov = curve_fit(self.eval_func, sub_xaxis, sub_data, p0=p0)
                measurement_results['datafit'] = self.eval_func(sub_xaxis, *popt)
                result_measurement = popt[msub_ind]

            # elif mtype=="Custom Formula":
            #    #offset=np.min(sub_data)
            #    #amp=np.max(sub_data)-np.min(sub_data)
            #    #m=utils.my_moment(sub_xaxis,sub_data)
            #    #p0=[amp,m[1],m[0],offset]
            #    popt, pcov = curve_fit(self.custom_func, sub_xaxis, sub_data,p0=[140,750,50,15])
            #    self.curve_fitting_sig.emit([sub_xaxis,self.gaussian_func(sub_xaxis,*popt)])
            #    result_measurement=popt[msub_ind]
            else:
                result_measurement = 0


            measurement_results['value']=result_measurement


            return measurement_results
        except Exception as e:
            result_measurement = 0
            measurement_results['status'] = str(e)
            return measurement_results

    def update_data(self,xdata=None,ydata=None):
        """
            | Update xdata attribute with the numpy linspcae regular distribution (if param is none) and update the User Interface curve data.
            | Call the update_measurement method synchronously to keep same values.

            =============== ============   ======================
            **Parameters**   **Type**       **Description**

            *xdata*          float list    the x axis data
            *ydata*          float list    the y axis data
            =============== ============   ======================

            See Also
            --------
            update_measurement

        """
        if xdata is None:
            self.xdata=np.linspace(0,len(ydata)-1,len(ydata))
        else:
            self.xdata=xdata
        self.ydata=ydata
        self.fourierfilt.show_data(dict(data=self.ydata,xaxis=self.xdata))
        self.update_measurement()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    from pymodaq.daq_utils.daq_utils import gauss1D
    prog = DAQ_Measurement(Form)
    xdata=np.linspace(0,400,401)
    x0=50
    dx=20
    tau = 27
    tau2=100
    ydata_gauss=10*gauss1D(xdata,x0,dx)+np.random.rand(len(xdata))
    ydata_expodec = np.zeros((len(xdata)))
    ydata_expodec[:50] = 10*gauss1D(xdata[:50],x0,dx,2)
    ydata_expodec[50:] = 10*np.exp(-(xdata[50:]-x0)/tau)#+10*np.exp(-(xdata[50:]-x0)/tau2)
    ydata_expodec += 2*np.random.rand(len(xdata))
    ydata_sin =10+2*np.sin(2*np.pi*xdata/21-np.deg2rad(55))+2*np.random.rand(len(xdata))
    prog.update_data(xdata,ydata_sin)
    Form.show()

    sys.exit(app.exec_())
