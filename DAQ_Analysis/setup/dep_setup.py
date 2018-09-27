#!/usr/bin/env python

#win distribution : bdist_wininst
# @author  CABOS Matthieu
# @release 30/04/2018

from setuptools import setup
import os
import ez_setup
import os

def sip_setup():
	try:
		os.system('pip install wheel')
		os.system('pip3 install -e ../Libraries_packages/sip/sip-4.19.8-cp35-none-win_amd64.whl')
	except:
		print("pip3 needed to perform setup. Please download and install.")
		exit(0)

def tables_setup():
	try:
		os.system('pip install tables>=3.3.0')
	except:
		print("tables module needed to perform setup; Please download and install tables.")
		exit(0)

#Check and install setuptools if needed
ez_setup.use_setuptools()
sip_setup()
tables_setup()
setup(
	  #Metadata informations
	  name='PyMoDAQ_dependencies',
	  version='1.0',
	  description='CEMES DAQ Analysis Distribution',
	  author='Sebastien Weber',
	  author_email='sebastien.weber@cemes.fr',
	  url='https://github.com/CEMES-CNRS',

	  #internal requirement (from standard python dist)
	  requires=['sys','os','collections','xml','datetime','pickle','re','socket',
'select','enum','decimal','ctypes'],

	  #build local dependancies from source directory
	  package_dir={"PyMoDAQ":"../.."},
	  py_modules = [ 'PyMoDAQ.DAQ_Analysis',
	  				 'PyMoDAQ.DAQ_Analysis.DAQ_analysis_main',
	  				 'PyMoDAQ.DAQ_Measurement',
	  				 'PyMoDAQ.DAQ_Measurement.DAQ_Measurement_main',
	  				 'PyMoDAQ.DAQ_Measurement.GUI.DAQ_Measurement_GUI',
	  				 'PyMoDAQ.DAQ_Metheor',
	  				 'PyMoDAQ.DAQ_Metheor.DAQ_metheor_main_v3',
					 'PyMoDAQ.DAQ_Move',
					 'PyMoDAQ.DAQ_Move.hardware',
					 'PyMoDAQ.DAQ_Move.DAQ_Move_GUI',
					 'PyMoDAQ.DAQ_Move.DAQ_Move_main',
					 'PyMoDAQ.DAQ_Scan',
					 'PyMoDAQ.DAQ_Scan.DAQ_Scan_main',
	  				 'PyMoDAQ.DAQ_Scan.GUI.DAQ_Scan_GUI',
	                 'PyMoDAQ.DAQ_Utils', 
	  				 'PyMoDAQ.DAQ_Utils.custom_parameter_tree', 
	  				 'PyMoDAQ.DAQ_Utils.DAQ_utils', 
	  				 'PyMoDAQ.DAQ_Utils.GUI_utils', 
	  				 'PyMoDAQ.DAQ_Utils.hardware.digilent.digilent_main',
					 'PyMoDAQ.DAQ_Utils.hardware.picoscope.picoscope_5000A',
					 'PyMoDAQ.DAQ_Utils.hardware.piezoconcept.piezoconcept',
					 'PyMoDAQ.DAQ_Utils.plotting.viewer1D.viewer1D_main',
					 'PyMoDAQ.DAQ_Utils.plotting.viewer0D.viewer0D_main',
					 'PyMoDAQ.DAQ_Utils.plotting.viewer1D.viewer1D_main',
					 'PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor',
					 'PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor.image_view_multicolor',
	  				 'PyMoDAQ.DAQ_Utils.Tree_layout.Tree_layout_main',
	  				 'PyMoDAQ.DAQ_Utils.plotting.QLED.qled',
	  				 'PyMoDAQ.DAQ_Utils.DAQ_enums',
	  				 'PyMoDAQ.DAQ_Viewer',
					 'PyMoDAQ.DAQ_Viewer.DAQ_GUI_settings',
					 'PyMoDAQ.DAQ_Viewer.DAQ_viewer_main',
					 'PyMoDAQ.plugins.DAQ_Viewer_plugins._0D',
					 'PyMoDAQ.plugins.DAQ_Viewer_plugins._1D',
					 'PyMoDAQ.plugins.DAQ_Viewer_plugins._2D',
					 'PyMoDAQ.DAQ_Viewer.utility_classes',
					 'PyMoDAQ.QtDesigner_Ressources',
					 'PyMoDAQ.QtDesigner_Ressources.QtDesigner_ressources_rc'],
	  
	  #build dependancies from Pypi and given links
	  install_requires=['numpy>=1.11.3',
	  					'pyqtgraph>=0.10.0',
	  					'easydict>=1.7',
	  					'PyQt5>=5.5.1',
	  					'pandas>=0.19.2',
	  					'bitstring>=3.1.5',
	  					'pathlib>=1.0.1',
	  					'scipy>=0.18.1',
	  					'matplotlib>=2.0.0',
	  					'datetime',
	  					'pyvisa>=1.9.0',
	  					'clr',
						'pyserial>=3.2.1'],
						
	  dependency_links=['https://pypi.org/project/PyQt5',
	  					'https://github.com/pyqtgraph/pyqtgraph.git',
	  					'https://github.com/makinacorpus/easydict.git',
	  					'https://github.com/PyTables/PyTables.git',
	  					'https://github.com/scipy/scipy',
	  					'https://github.com/pyvisa/pyvisa.git',
	  					'https://github.com/pyserial/pyserial']
	  )
