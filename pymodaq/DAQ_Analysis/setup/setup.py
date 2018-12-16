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
	  name='DAQ_Analysis',
	  version='1.0',
	  description='CEMES DAQ Analysis Distribution',
	  author='Sebastien Weber',
	  author_email='sebastien.weber@cemes.fr',
	  url='https://github.com/CEMES-CNRS',

	  #internal requirement (from standard python dist)
	  requires=['sys','os','collections','xml'],

	  #build local dependancies from source directory
	  package_dir={"PyMoDAQ":"../.."},
	  py_modules = [ 'PyMoDAQ.DAQ_Utils', 
	  				 'PyMoDAQ.DAQ_Utils.plotting.viewer1D.viewer1D_main', 
	  				 'PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor.image_view_multicolor', 
	  				 'PyMoDAQ.DAQ_Utils.DAQ_utils', 
	  				 'PyMoDAQ.DAQ_Utils.custom_parameter_tree', 
	  				 'PyMoDAQ.DAQ_Utils.Tree_layout.Tree_layout_main',
	  				 'PyMoDAQ.DAQ_Utils.plotting.QLED.qled',
	  				 'PyMoDAQ.DAQ_Analysis',
	  				 'PyMoDAQ.DAQ_Analysis.DAQ_analysis_main',
	  				 'PyMoDAQ.QtDesigner_Ressources',
					 'PyMoDAQ.QtDesigner_Ressources.QtDesigner_ressources_rc'],
	  
	  #build dependancies from Pypi and given links
	  install_requires=['numpy>=1.11.3',
	  					'pyqtgraph>=0.10.0',
	  					'easydict>=1.7',
	  					'PyQt5>=5.5.1',
	  					'bitstring>=3.1.5',
	  					'pathlib>=1.0.1',
	  					'scipy'],
	  dependency_links=['https://sourceforge.net/projects/pyqt/files/sip/',
	  					'https://github.com/pyqtgraph/pyqtgraph.git',
	  					'https://github.com/makinacorpus/easydict.git',
	  					'https://github.com/PyTables/PyTables.git',
	  					'https://github.com/scipy/scipy']
	  )