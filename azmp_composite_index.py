# -*- coding: utf-8 -*-
'''
To generate Colbourne's and STACFIS composite anomalies


Uses this pickled DataFrame:

/home/cyrf0006/AZMP/state_reports/SSTs/SSTs_merged_monthly.pkl
generated by from azmp_sst_scorecards.py


'''

import numpy as  np
import matplotlib.pyplot as plt
import pandas as pd
import os
import unicodedata
from matplotlib.colors import from_levels_and_colors
import cmocean as cmo

clim_year = [1981, 2010]
years = [1980, 2019]
width = 0.5
year0 = 1985
yearf = 2019
n=5

#### ---- LOAD THE DATA ---- ####
# 1. CIL [years: vol_itp, core_itp, core_depth_itp]
df_CIL_SI = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_CIL_SI_summer.pkl')
df_CIL_BB = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_CIL_BB_summer.pkl')
df_CIL_FC = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_CIL_FC_summer.pkl')

# 2. NAO & AO [years: Value]
nao_winter = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/NAO/NAO_winter.pkl')
nao_winter = nao_winter[nao_winter.index<=yearf]
ao = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/NAO/AO_annual.pkl')

# 3. Air Temperature
df_air = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/airTemp/airT_monthly.pkl')
df_air = df_air.resample('As').mean()
df_air.index = df_air.index.year

# 4. SSTs (problem: NS data missing prior 1997...)
df_sst = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/SSTs/SSTs_merged_monthly.pkl')
df_sst = df_sst.resample('As').mean()
df_sst.index = df_sst.index.year

df_sst_1997 = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/SSTs/SSTs_bometrics_annual.pkl')
df_sst_1997 = df_sst_1997.resample('As').mean()
df_sst_1997.index = df_sst_1997.index.year


# 5. Bottom temperature
# 3LNO - Spring
df_3LNO_spring = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_3LNO_spring.pkl')
df_3LNO_spring.index = pd.to_datetime(df_3LNO_spring.index) # update index to datetime
df_3LNO_spring.index = df_3LNO_spring.index.year
df_3LNO_spring = df_3LNO_spring.Tmean
# 3Ps - Spring
df_3Ps_spring = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_3Ps_spring.pkl')
df_3Ps_spring.index = pd.to_datetime(df_3Ps_spring.index) # update index to datetime
df_3Ps_spring.index = df_3Ps_spring.index.year
df_3Ps_spring = df_3Ps_spring.Tmean
# 2H - Fall
df_2H_fall = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_2H_fall.pkl')
df_2H_fall.index = pd.to_datetime(df_2H_fall.index) # update index to datetime
df_2H_fall.index = df_2H_fall.index.year
df_2H_fall = df_2H_fall.Tmean
# 2J - Fall
df_2J_fall = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_2J_fall.pkl')
df_2J_fall.index = pd.to_datetime(df_2J_fall.index) # update index to datetime
df_2J_fall.index = df_2J_fall.index.year
df_2J_fall = df_2J_fall.Tmean
# 3K - Fall
df_3K_fall = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_3K_fall.pkl')
df_3K_fall.index = pd.to_datetime(df_3K_fall.index) # update index to datetime
df_3K_fall.index = df_3K_fall.index.year
df_3K_fall = df_3K_fall.Tmean
# 3LNO - Fall
df_3LNO_fall = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_3LNO_fall.pkl')
df_3LNO_fall.index = pd.to_datetime(df_3LNO_fall.index) # update index to datetime
df_3LNO_fall.index = df_3LNO_fall.index.year
df_3LNO_fall = df_3LNO_fall.Tmean
# 3M - Summer
df_3M_summer = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_3M_summer.pkl')
df_3M_summer.index = pd.to_datetime(df_3M_summer.index) # update index to datetime
df_3M_summer.index = df_3M_summer.index.year
df_3M_summer = df_3M_summer.Tmean
# 4VWX - Summer ** shitty to generate,
# I need to use azrt.bottom_stats(years=np.arange(1980, 2020), season='summer', climato_file='Tbot_climato_SA4_summer_0.10.h5')
df_4VWX_summer = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/stats_4VWX_summer.pkl')
df_4VWX_summer.index = pd.to_datetime(df_4VWX_summer.index) # update index to datetime
df_4VWX_summer.index = df_4VWX_summer.index.year
df_4VWX_summer = df_4VWX_summer.Tmean

# 4VWX from Hebert (not used for now)
df_4v = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/4v_julyGroundfishBottomT.csv', index_col='year')
df_4vn = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/4vn_julyGroundfishBottomT.csv', index_col='year')
df_4vs = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/4vs_julyGroundfishBottomT.csv', index_col='year')
df_4w = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/4w_julyGroundfishBottomT.csv', index_col='year')
df_4x = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/4x_julyGroundfishBottomT.csv', index_col='year')
df_4vwx = pd.concat([df_4v['ann.mean'],df_4w['ann.mean'],df_4x['ann.mean']], axis=1).mean(axis=1)
df_4VWX_summer.plot()
df_4vwx.plot()
plt.legend(['from NAFC using IGOSS', 'from BIO'])
plt.title('Bottom temperature - NAFO 4VWX')
plt.ylabel(r'$\rm T(^{\circ}C)$')

# 6. Fixed stations
# S27
df_s27 = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/stn27/S27_temperature_monthly.pkl')
df_s27 = df_s27.resample('As').mean() 
df_s27.index = df_s27.index.year
df_s27_mean = df_s27.mean(axis=1)

# HFX-2 0-50m
#df_hfx2_surf = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/HFX2_Integrated_0-50m.csv', index_col='Year')
#df_hfx2_surf = df_hfx2_surf.iloc[:,0]
#df_hfx2_surf.index = np.array(df_hfx2_surf.index, dtype=int) 
#df_hfx2_surf = pd.to_numeric(df_hfx2_surf, errors='coerce').astype('Float64')
df_hfx2_surf = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/H2_0-50m_integrated.dat', sep=' ', index_col='Year')
df_hfx2_surf.drop('----', inplace=True)
df_hfx2_surf = df_hfx2_surf['T'].astype('float')
df_hfx2_surf.index = df_hfx2_surf.index.astype('int')       

# HFX-2 150m
#df_hfx2_150 = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/HFX2_150m_Temperature.csv', header=2, index_col='Year')
#df_hfx2_150 = df_hfx2_150.iloc[:,2]
df_hfx2_150 = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/HFX2_150m_temp.dat', sep=' ')
df_hfx2_150.columns=['year', 'temp']
df_hfx2_150.set_index('year', inplace=True)


# Prince-5 0-50m
#df_p5_surf = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/P5_Annual_Series_0-50m.csv', header=1, index_col='Year')
df_p5_surf = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/P5_0-50m_integrated.dat', sep=' ', index_col='Year')
df_p5_surf.drop('----', inplace=True)
df_p5_surf = df_p5_surf['T'].astype('float')

# Prince-5 0-90m
#df_p5_90 = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/P5_Integrated_0-90m.csv', header=0, index_col='Year')
#df_p5_90 = df_p5_90.iloc[:,1]
df_p5_90 = pd.read_csv('/home/cyrf0006/data/Hebert_timeseries/prince5integratedVariables.csv', index_col='year')
df_p5_90 = df_p5_90['integratedTemperature']

# 7. Section average Temeprature (should eventually add salinity in these dataFrame, see azmp_CIL_stats.py)
df_SI = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_SI_meanT_summer.pkl')
df_BB = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_BB_meanT_summer.pkl')
df_FC = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_FC_meanT_summer.pkl')
df_FC_shelf = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_FC_meanT_shelf_summer.pkl')
df_FC_cap = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/CIL/df_FC_meanT_cap_summer.pkl')

# 8. Greenland Fylla and Cape Desolation
df_FB4 = pd.read_csv('/home/cyrf0006/data/IROC_timeseries/Greenland_Fylla_0-50_Annual.csv', header=15, index_col='Year', encoding = "ISO-8859-1")
df_CD3_2000 = pd.read_csv('/home/cyrf0006/data/IROC_timeseries/Greenland_Desolation_2000_Annual.csv', header=14, index_col='Year', encoding = "ISO-8859-1")
df_CD3_200 = pd.read_csv('/home/cyrf0006/data/IROC_timeseries/Greenland_Desolation_75-200_Annual.csv', header=15, index_col='Year', encoding = "ISO-8859-1")
# Keep only temeprature
df_FB4 = df_FB4.iloc[:,0]
df_CD3_2000 = df_CD3_2000.iloc[:,0]
df_CD3_200 = df_CD3_200.iloc[:,0]

# 9. Scotian shelf and GoM timeseries (from IROC)
df_emeral = pd.read_csv('/home/cyrf0006/data/IROC_timeseries/Scotian_Emerald_Annual.csv', header=15, index_col='Year', encoding = "ISO-8859-1")
df_misaine = pd.read_csv('/home/cyrf0006/data/IROC_timeseries/Scotian_Misaine_Annual.csv', header=15, index_col='Year', encoding = "ISO-8859-1")
df_egom =  pd.read_csv('/home/cyrf0006/data/IROC_timeseries/USA_EGOM_Annual.csv', header=19, index_col='Year', encoding = "ISO-8859-1")
df_nec = pd.read_csv('/home/cyrf0006/data/IROC_timeseries/USA_NEC_Annual.csv', header=19, index_col='Year', encoding = "ISO-8859-1")
# Keep only temperature
df_emeral = df_emeral.iloc[:,0]
df_misaine = df_misaine.iloc[:,0]
df_egom = df_egom.iloc[:,0]
df_nec = df_nec.iloc[:,0]


#### ---- STACFIS - 3LNO ---- ####
df_comp_3LNO = pd.concat([df_s27_mean,
                          df_3LNO_spring, df_3LNO_fall,
                          df_SI, df_BB, df_FC_shelf,
                          df_CIL_SI.vol_itp, df_CIL_BB.vol_itp, df_CIL_FC.vol_itp,
                          df_sst.Avalon_Channel, df_sst.Hybernia, df_sst.Flemish_Pass 
                          ], axis=1)

df_3LNO_clim = df_comp_3LNO[(df_comp_3LNO.index>=clim_year[0]) & (df_comp_3LNO.index<=clim_year[1])]
std_anom_3LNO = (df_comp_3LNO-df_3LNO_clim.mean(axis=0))/df_3LNO_clim.std(axis=0)
# revert CIL volume
std_anom_3LNO['vol_itp'] = std_anom_3LNO['vol_itp']*-1
# mean anomaly
composite_3LNO = std_anom_3LNO.mean(axis=1)
composite_3LNO.to_csv('composite_3LNO.csv', float_format='%.2f')

# Plot
composite_3LNO = composite_3LNO[composite_3LNO.index>=year0]
fig, ax = plt.subplots(nrows=1, ncols=1)
sign=composite_3LNO>0
composite_3LNO.plot(kind='bar', color=sign.map({True: 'indianred', False: 'steelblue'}), width = width)
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.fill_between([ticks[0], ticks[-1]], [-.5, -.5], [.5, .5], facecolor='gray', alpha=.2)
plt.ylabel('Standardized Anomaly', weight='bold', fontsize=14)
plt.title('Composite anomaly 3LNO', weight='bold', fontsize=14)
plt.grid()
plt.ylim([-2,2])
fig.set_size_inches(w=15,h=7)
fig_name = 'composite_3LNO.png'
fig.savefig(fig_name, dpi=200)
os.system('convert -trim composite_3LNO.png composite_3LNO.png')


#### ---- STACFIS - 3M ---- ####
df_comp_3M = pd.concat([df_FC_cap, 
                        df_sst.Flemish_Cap,
                        df_3M_summer
                        ], axis=1)

df_3M_clim = df_comp_3M[(df_comp_3M.index>=clim_year[0]) & (df_comp_3M.index<=clim_year[1])]
std_anom_3M = (df_comp_3M-df_3M_clim.mean(axis=0))/df_3M_clim.std(axis=0)
composite_3M = std_anom_3M.mean(axis=1)
composite_3M.to_csv('composite_3M.csv', float_format='%.2f')

# Plot
composite_3M = composite_3M[composite_3M.index>=year0]
fig, ax = plt.subplots(nrows=1, ncols=1)
sign=composite_3M>0
composite_3M.plot(kind='bar', color=sign.map({True: 'indianred', False: 'steelblue'}), width = width)
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.fill_between([ticks[0], ticks[-1]], [-.5, -.5], [.5, .5], facecolor='gray', alpha=.2)
plt.ylabel('Standardized Anomaly', weight='bold', fontsize=14)
plt.title('Composite anomaly 3M', weight='bold', fontsize=14)
plt.grid()
plt.ylim([-1.5,1.5])
fig.set_size_inches(w=15,h=7)
fig_name = 'composite_3M.png'
fig.savefig(fig_name, dpi=200)
os.system('convert -trim composite_3M.png composite_3M.png')

#### ---- STACFIS - SA01 ---- #### (0B1CDEF)
df_comp_SA01 = pd.concat([df_sst.Central_Labrador_Sea,
                         df_sst.North_Central_Labrador_Sea,
                         df_sst.Greenland_Shelf,
                         df_sst.Hudson_Strait,
                         df_FB4, df_CD3_200, df_CD3_2000,
                         df_air.Nuuk, df_air.Iqaluit
                          ], axis=1)

df_SA01_clim = df_comp_SA01[(df_comp_SA01.index>=clim_year[0]) & (df_comp_SA01.index<=clim_year[1])]
std_anom_SA01 = (df_comp_SA01-df_SA01_clim.mean(axis=0))/df_SA01_clim.std(axis=0)
composite_SA01 = std_anom_SA01.mean(axis=1)
composite_SA01.to_csv('composite_SA01.csv', float_format='%.2f')

# Plot
composite_SA01 = composite_SA01[composite_SA01.index>=year0]
fig, ax = plt.subplots(nrows=1, ncols=1)
sign=composite_SA01>0
composite_SA01.plot(kind='bar', color=sign.map({True: 'indianred', False: 'steelblue'}), width = width, zorder=10)
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.fill_between([ticks[0], ticks[-1]], [-.5, -.5], [.5, .5], facecolor='gray', alpha=.2)
plt.ylabel('Normalized Anomaly', weight='bold', fontsize=14)
plt.title('Composite anomaly SA01', weight='bold', fontsize=14)
plt.grid()
plt.ylim([-2,2])
fig.set_size_inches(w=15,h=7)
fig_name = 'composite_SA01.png'
fig.savefig(fig_name, dpi=200)
os.system('convert -trim composite_SA01.png composite_SA01.png')


#### ---- STACFIS - SA234 ---- ####
# ** HEre I ignored SSTs, because not available for NS region prior to 1997
#                          df_sst.Hudson_Strait, df_sst.Hamilton_Bank, df_sst['St.Anthony_Basin'], df_sst.Orphan_Knoll 
#                          df_sst.Avalon_Channel, df_sst.Hybernia, df_sst.Flemish_Pass, df_sst.Flemish_Cap, ...
df_sst_SA3 = pd.concat([df_sst['St.Anthony_Basin'], df_sst['Northeast_Nfld_Shelf'],
                        df_sst['Orphan_Knoll'],df_sst['Avalon_Channel'],
                        df_sst['Hybernia'],df_sst['Flemish_Cap'],
                        df_sst['Flemish_Pass'],df_sst['Green-St._Pierre_Bank']
                        ], axis=1)
                        
df_comp_SA234 = pd.concat([df_s27_mean, df_p5_90, df_hfx2_surf, df_hfx2_150,
                          df_2H_fall, df_2J_fall,
                          df_3LNO_spring, df_3LNO_fall, df_3M_summer, df_4VWX_summer,
                          df_SI, df_BB, df_FC_shelf,
                          df_CIL_SI.vol_itp, df_CIL_BB.vol_itp, df_CIL_FC.vol_itp,
                          df_egom, df_nec
                          ], axis=1)
df_comp_SA2 = pd.concat([df_2H_fall, df_2J_fall,
                         df_air.Cartwright,
                         df_sst.Hamilton_Bank,
                         df_SI,
                         df_CIL_SI.vol_itp
                         ], axis=1)
df_comp_SA3 = pd.concat([df_s27_mean,
                         df_air.Bonavista, df_air.StJohns,
                         df_sst_SA3.mean(axis=1),
                         df_3LNO_spring, df_3LNO_fall, df_3M_summer,
                         df_BB, df_FC_shelf,
                         df_CIL_BB.vol_itp, df_CIL_FC.vol_itp
                         ], axis=1)
df_comp_SA4 = pd.concat([df_p5_90, df_hfx2_surf, df_hfx2_150,
                          df_4VWX_summer,                          
                          df_egom, df_nec
                          ], axis=1)


df_SA234_clim = df_comp_SA234[(df_comp_SA234.index>=clim_year[0]) & (df_comp_SA234.index<=clim_year[1])]
std_anom_SA234 = (df_comp_SA234-df_SA234_clim.mean(axis=0))/df_SA234_clim.std(axis=0)
composite_SA234 = std_anom_SA234.mean(axis=1)
composite_SA234.to_csv('composite_SA234.csv', float_format='%.2f')

# Plot
composite_SA234 = composite_SA234[composite_SA234.index>=year0]
fig, ax = plt.subplots(nrows=1, ncols=1)
sign=composite_SA234>0
composite_SA234.plot(kind='bar', color=sign.map({True: 'indianred', False: 'steelblue'}), width = width)
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.fill_between([ticks[0], ticks[-1]], [-.5, -.5], [.5, .5], facecolor='gray', alpha=.2)
plt.ylabel('Standardized Anomaly', weight='bold', fontsize=14)
plt.title('Composite anomaly SA234', weight='bold', fontsize=14)
plt.grid()
plt.ylim([-1.5,1.5])
fig.set_size_inches(w=15,h=7)
fig_name = 'composite_SA234.png'
fig.savefig(fig_name, dpi=200)
os.system('convert -trim composite_SA234.png composite_SA234.png')


# Plot SA 2-3-4 stacked HERE!!!!!!!
df_comp_SA234_stack = pd.concat([df_comp_SA2.mean(axis=1),
                                 df_comp_SA3.mean(axis=1),
                                 df_comp_SA4.mean(axis=1),
                                 ], axis=1)
df_comp_SA234_stack = df_comp_SA234_stack[df_comp_SA234_stack.index>=1950]
df_SA234_stack_clim = df_comp_SA234_stack[(df_comp_SA234_stack.index>=clim_year[0]) & (df_comp_SA234_stack.index<=clim_year[1])]
std_anom_SA234_stack = (df_comp_SA234_stack-df_SA234_stack_clim.mean(axis=0))/df_SA234_stack_clim.std(axis=0)

## ---- plot annual ---- ##
#fig, ax = plt.subplots(nrows=1, ncols=1)
n = 5 # xtick every n years
ax = std_anom_SA234_stack.plot(kind='bar', stacked=True, cmap=cmo.cm.haline, alpha=.8)
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.grid('on')
ax.set_ylabel(r'Standardized anomaly')
ax.set_title('NAFO sub-areas 2, 3 & 4')
plt.legend(['SA-2', 'SA-3', 'SA-4'])
fig = ax.get_figure()
fig.set_size_inches(w=12,h=8)
fig_name = 'composite_SA234_stacked.png'
fig.savefig(fig_name, dpi=300)
os.system('convert -trim ' + fig_name + ' ' + fig_name)

