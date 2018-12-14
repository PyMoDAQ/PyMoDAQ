from andor import Andor

import time
import numpy as np
import matplotlib.pyplot as plt



andorTest = Andor(targetT=-20, Npixels=1024, Wpixels=26, devNr=0, dllpath="")
for i in range(2):
    print "     Ready: ",andorTest.ready
    andorTest.loadAndor()
    print "     Ready: ",andorTest.ready
    
    print andorTest.grating
    print andorTest.getGratingInfo()
    print andorTest.wavelength
    print andorTest.getStatus()
    print '-----'
    print andorTest.getTemperature()
    print andorTest.tempMsg
    print '-----'
    
    andorTest.setExposureTime(0.1)
    print "Total expected time per measurement (s):", andorTest.wait_time
    plt.ion()
    for i in range(20):
        andorTest.startAquisition()
        DATA = andorTest.getAquisition()
        print " T:", andorTest.getTemperature(), ' ({})'.format(andorTest.tempMsg)
        
        plt.clf()
        plt.title("MEASUREMENT #{}".format(i+1))
        plt.plot(andorTest.calib, DATA)
        plt.draw()
        plt.pause(.01)
    plt.ioff()
    plt.show()
    
    print "     Ready: ",andorTest.ready
    print 30*"-" + "\nUNLOAD ANDOR...\n\n\n\n" + 30*"-"
    andorTest.unloadAndor()
print "     Ready: ",andorTest.ready










