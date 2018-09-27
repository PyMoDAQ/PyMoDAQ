from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QSize

import sys
from PyMoDAQ.DAQ_Measurement.GUI.DAQ_Measurement_GUI import Ui_Form
from PyMoDAQ.DAQ_Utils.python_lib.mathematics.mat_functions import gauss1D
import pyqtgraph as pg
import numpy as np
from PyMoDAQ.DAQ_Utils.DAQ_enums import Measurement_type


class DAQ_Measurement(Ui_Form,QObject):
    """
        =================== ================================== =======================================
        **Attributes**       **Type**                          **Description**


        *ui*                 QObject                           The local instance of User Interface
        *wait_time*          int                               The default delay of showing
        *parent*             QObject                           The QObject initializing the UI
        *xdata*              1D numpy array                    The x axis data
        *ydata*              1D numpy array                    The y axis data
        *measurement_types*  instance of DAQ_Utils.DAQ_enums   The type of the measurement, between:
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
        super(Ui_Form,self).__init__()

        self.ui=Ui_Form()
        self.ui.setupUi(parent)
        self.ui.splitter.setSizes([200, 400])
        self.ui.statusbar=QtWidgets.QStatusBar(parent)
        self.ui.statusbar.setMaximumHeight(15)
        self.ui.StatusBarLayout.addWidget(self.ui.statusbar)
        self.wait_time=1000
        self.parent=parent
        self.xdata=None
        self.ydata=None

        self.measurement_types=Measurement_type.names(Measurement_type)
        self.measurement_type=Measurement_type(0)
        self.ui.measurement_type_combo.clear()
        self.ui.measurement_type_combo.addItems(self.measurement_types)

        self.ui.data_curve=self.ui.graph1D.plot()
        self.ui.data_curve.setPen("w")
        self.ui.fit_curve=self.ui.graph1D.plot()
        self.ui.fit_curve.setPen("y")
        self.ui.fit_curve.setVisible(False)

        self.ui.selected_region=pg.LinearRegionItem([0 ,100])
        self.ui.selected_region.setZValue(-10)
        self.ui.selected_region.setBrush('b')
        self.ui.selected_region.setOpacity(0.2)
        self.ui.selected_region.setVisible(True)
        self.ui.graph1D.addItem(self.ui.selected_region)


        ##Connecting buttons:
        self.ui.Quit_pb.clicked.connect(self.Quit_fun,type = Qt.QueuedConnection)
        self.ui.measurement_type_combo.currentTextChanged[str].connect(self.update_measurement_subtype)
        self.ui.measure_subtype_combo.currentTextChanged[str].connect(self.update_measurement)
        self.update_measurement_subtype(self.ui.measurement_type_combo.currentText(),update=False)
        self.ui.selected_region.sigRegionChanged.connect(self.update_measurement)
        self.ui.result_sb.valueChanged.connect(self.ui.result_lcd.display)

    def Quit_fun(self):
        """
            Close the current instance of DAQ_Measurement.

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

            mtype             string      the Measurement_type index of the Measurement_type array (imported from DAQ_Utils)

            update            boolean     the update boolean link with the update_measurement method
            ================ ========== =====================================================================================

            See Also
            --------
            update_measurement_subtype, update_measurement, update_status

        """
        self.measurement_type=Measurement_type[mtype]
        [variables,self.formula,self.subitems]=Measurement_type.update_measurement_subtype(Measurement_type,mtype)

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
            msub_ind=self.ui.measure_subtype_combo.currentIndex()
            measurement_results=self.measurement_type.update_measurement(xlimits[0],xlimits[1],self.xdata,self.ydata,msub_ind)
            if measurement_results['Status'] is not None:
                self.update_status(measurement_results['Status'],wait_time=self.wait_time)
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
        self.ui.data_curve.setData(self.xdata,self.ydata)
        self.update_measurement()

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	Form = QtWidgets.QWidget()
	prog = DAQ_Measurement(Form);xdata=np.linspace(0,100,101);x0=50;dx=20;ydata=10*gauss1D(xdata,x0,dx)+np.random.rand(len(xdata));prog.update_data(xdata,ydata)
	Form.show()
	sys.exit(app.exec_())