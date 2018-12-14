# PyMoDAQ

PyMoDAQ, Modular Data Acquisition with Python, is a set of **python** modules used to perform automated measurements. 

It is made for the scientist who need to perform various acquisitions without having to write a user/interface for each new experiment. PyMoDAQ interface is fixed, and any new hardware can be added as a small plugin. Preset modes of a given set of actuators and detectors can be written for easy experiment inititialization.

It is divided in three main modules:
* **DAQ_Move** : used to control/drive an actuator (stand alone and/or automated). Any number of these modules can be instantiated.
* **DAQ_Viewer** : used to control/drive a detector (stand alone and/or automated). Any number of these modules can be instantiated.
* **DAQ_Scan** : This is the module that will initialize all preset actuators and detectors. Then will automate the data acquisition.


GitHub repo: https://github.com/CEMES-CNRS

Documentation: http://pymodaq.cnrs.fr/