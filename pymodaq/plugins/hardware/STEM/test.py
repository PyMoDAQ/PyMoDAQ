"""
test proxy"
"""
import OrsayHardwareProxy
import time

t = OrsayHardwareProxy.OrsayHardwareProxy()
print ("pixel time(us): ", t.pixel_time_us)
t.pixel_time_us = 1
print ("pixel time(us): ", t.pixel_time_us)
t.pixel_time_us = 2
print ("pixel time(us): ", t.pixel_time_us)
print("Image size: ", t.scan_size)
t.start()
time.sleep(30)
t.stop(1)
print("Done")