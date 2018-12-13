#%%
#%reset -f
#%%
import os
import python_lib as mylib
import matplotlib.pyplot as plt
import numpy as np
import inspect


from PyQt5 import QtWidgets
#%%

path="D:\\Data\\2016\\Vincent\\PL SiNCs_NWs"
fname = QtWidgets.QFileDialog.getOpenFileName(None, 'Choose image file',path,"image file (*.dat)")
fname=fname[0]
#%%
data_tmp=np.loadtxt(fname,delimiter='\t',skiprows=1);
xaxis=data_tmp[0,1:]
yaxis=data_tmp[1:,0]
data=data_tmp[1:,1:]
#%%



#%% plot image raw

fig=mylib.figure_docked('raw',clf=True)
ax1=plt.subplot(1,1,1)
plt.pcolormesh(xaxis,yaxis,(data), cmap='copper')
# for other choices of maps:http://matplotlib.org/examples/color/colormaps_reference.html

ax1.set_aspect('equal')
ax1.set_xlim([-2,3.5])
ax1.set_ylim([-1.3,1.2])
ax1.set_xlabel('x axis (µm)')
ax1.set_ylabel('y axis (µm)')
ax1.set_title('Lockin Magnitude cartography (µV or mV)')
plt.colorbar()

#%% saving

#mylib.add_figure_timestamp(fig,fname,FontSize=10)
(name,ext)=os.path.splitext(fname)
fig.savefig(name+'.png')

