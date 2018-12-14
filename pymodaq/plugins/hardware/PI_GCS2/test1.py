# -*- coding: utf-8 -*-
"""
Created on Wed Jul 12 17:35:04 2017

@author: Seb
"""

from pipython import GCSDevice
import os

try:
    GCS_path=os.environ['PI_GCS2']
except KeyError:
    GCS_path="C:\\Users\\Public\\PI\\PI_Programming_Files_PI_GCS2_DLL"

gcs1=GCSDevice(gcsdll=os.path.join(GCS_path,"PI_GCS2_DLL_x64.dll"))
from pipython.gcscommands import GCSCommands
#%%
gcs2=GCSDevice(gcsdll=os.path.join(GCS_path,"PI_GCS2_DLL_x64.dll"))
#%%
devices=gcs1.EnumerateUSB()

#%%
dev_id=gcs1.ConnectUSB(devices[0])
#%%
gcs1.InterfaceSetupDlg()
#%%
dev_id=gcs1.OpenUSBDaisyChain(devices[0])

#%%
daisy_ID=gcs1.dcid
gcs1.ConnectDaisyChainDevice(1,daisy_ID)
gcs2.ConnectDaisyChainDevice(2,daisy_ID)


#%%
print(gcs1.qIDN())
print(gcs2.qIDN())
#%%
ax1=gcs1.axes[0]
ax2=gcs2.axes[0]
if not gcs1.qSVO()[ax1]:
    gcs1.SVO(ax1,True)
if not gcs2.qSVO()[ax2]:
    gcs2.SVO(ax2,True)
#%%


#%%
gcs1.JON(1,False)
gcs2.JON(1,False)

#%%
if not gcs1.qFRF('1'):
    gcs1.RON('1',True)
    gcs1.FRF('1')
    
#%%
if not gcs2.qFRF('1'):
    gcs2.RON('1',True)
    gcs2.FRF('1')
#%%
gcs1.GOH()

gcs1.MOV('1',12.5)
gcs2.MOV('1',10)
#%%
gcs1.MOV('1',10)


#%%
gcs1.qPOS()
#%%
gcs1.CloseConnection()
#%%
gcs1.CloseDaisyChain()

