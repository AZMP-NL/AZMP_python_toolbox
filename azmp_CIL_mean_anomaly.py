# -*- coding: utf-8 -*-
'''

df_CIL_*_summer.pkl are generated by azmp_CIL_stats.py



'''

import numpy as  np
import matplotlib.pyplot as plt
import pandas as pd
import os


clim_year = [1981, 2010]
years = [1950, 2020]

#### ---- Load the data and compute anomalies ---- ####
df_SI = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_CIL_SI_summer.pkl')
df_BB = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_CIL_BB_summer.pkl')
df_FC = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_CIL_FC_summer.pkl')

#df_SI = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/df_CIL_SI_summer.pkl')
#df_BB = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/df_CIL_BB_summer.pkl')
#df_FC = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/df_CIL_FC_summer.pkl')

df_years = df_SI[(df_SI.index>=years[0]) & (df_SI.index<=years[1])]
df_clim = df_SI[(df_SI.index>=clim_year[0]) & (df_SI.index<=clim_year[1])]
std_anom_SI = (df_years - df_clim.mean()) / df_clim.std()

df_years = df_BB[(df_BB.index>=years[0]) & (df_BB.index<=years[1])]
df_clim = df_BB[(df_BB.index>=clim_year[0]) & (df_BB.index<=clim_year[1])]
std_anom_BB = (df_years - df_clim.mean()) / df_clim.std()

df_years = df_FC[(df_FC.index>=years[0]) & (df_FC.index<=years[1])]
df_clim = df_FC[(df_FC.index>=clim_year[0]) & (df_FC.index<=clim_year[1])]
std_anom_FC = (df_years - df_clim.mean()) / df_clim.std()

# average quatities
std_core = pd.concat([std_anom_SI.core_itp, std_anom_BB.core_itp, std_anom_FC.core_itp], axis=1).mean(axis=1)
std_vol = pd.concat([std_anom_SI.vol_itp, std_anom_BB.vol_itp, std_anom_FC.vol_itp], axis=1).mean(axis=1)
#std_core.index = pd.to_datetime(std_core.index, format='%Y')
#std_vol.index = pd.to_datetime(std_vol.index, format='%Y')


# Save for climate index
cil_section_index = pd.concat([std_core, std_vol], axis=1, keys=['core','volume'])
cil_section_index.to_pickle('section_cil_index.pkl')


## ---- plot index ---- ##
width=.7
fig = plt.figure(4)
fig.clf()
ax = plt.subplot2grid((2, 1), (0, 0))
sign=std_core>0
std_core.plot(kind='bar', color=sign.map({False: 'steelblue', True: 'indianred'}), width = width, zorder=10)
n = 5 # xtick every n years
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.fill_between([ticks[0], ticks[-1]], [-.5, -.5], [.5, .5], facecolor='gray', alpha=.2)
plt.ylabel('Standardized Anomaly', weight='bold', fontsize=14)
plt.xlabel(' ')
plt.grid()
plt.ylim([-2.5,2.5])
plt.title('CIL core - Sections SI, BB & FC', weight='bold', fontsize=14)
ax.tick_params(labelbottom=False)

ax2 = plt.subplot2grid((2, 1), (1, 0))
sign=std_vol>0
std_vol.plot(kind='bar', color=sign.map({True: 'steelblue', False: 'indianred'}), width = width, zorder=10)
n = 5 # xtick every n years
ticks = ax2.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax2.xaxis.get_ticklabels()]
ax2.xaxis.set_ticks(ticks[::n])
ax2.xaxis.set_ticklabels(ticklabels[::n])
plt.fill_between([ticks[0], ticks[-1]], [-.5, -.5], [.5, .5], facecolor='gray', alpha=.2)
plt.ylabel('Standardized Anomaly', weight='bold', fontsize=14)
plt.xlabel(' ')
plt.grid()
plt.ylim([-2.5,2.5])
plt.title('CIL area - Sections SI, BB & FC', weight='bold', fontsize=14)
ax2.tick_params(axis='x', rotation=0)

fig_name = 'section_CIL_anomaly.png'
fig.set_size_inches(w=15,h=7)
fig.savefig(fig_name, dpi=200)
os.system('convert -trim ' + fig_name + ' ' + fig_name)


## ---- Figure in French ---- ##
fig = plt.figure(4)
fig.clf()
ax = plt.subplot2grid((2, 1), (0, 0))
sign=std_core>0
std_core.plot(kind='bar', color=sign.map({False: 'steelblue', True: 'indianred'}), width = width, zorder=10)
n = 5 # xtick every n years
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.ylabel('Anomalie normalisée', weight='bold', fontsize=14)
plt.xlabel(' ')
plt.grid()
plt.ylim([-2.5,2.5])
plt.title('Coeur de la CIF - Sections SI, BB & FC', weight='bold', fontsize=14)
ax.tick_params(labelbottom=False)

ax2 = plt.subplot2grid((2, 1), (1, 0))
sign=std_vol>0
std_vol.plot(kind='bar', color=sign.map({True: 'steelblue', False: 'indianred'}), width = width, zorder=10)
n = 5 # xtick every n years
ticks = ax2.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax2.xaxis.get_ticklabels()]
ax2.xaxis.set_ticks(ticks[::n])
ax2.xaxis.set_ticklabels(ticklabels[::n])
plt.ylabel('Anomalie normalisée', weight='bold', fontsize=14)
plt.xlabel(' ')
plt.grid()
plt.ylim([-2.5,2.5])
plt.title('Aire de la CIF - Sections SI, BB & FC', weight='bold', fontsize=14)
ax2.tick_params(axis='x', rotation=0)

fig_name = 'section_CIL_anomaly_FR.png'
fig.set_size_inches(w=15,h=7)
fig.savefig(fig_name, dpi=200)
os.system('convert -trim ' + fig_name + ' ' + fig_name)

