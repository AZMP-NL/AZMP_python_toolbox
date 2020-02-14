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

clim_year = [1981, 2010]
width = 0.7


#### ---- LOAD THE DATA (and prepare) ---- ####
# 1. NAO
nao = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/NAO/NAO_winter.pkl')
nao = nao*-1
nao = nao.rename(columns={'Value':'NAO'})

# 2. Air temp
air = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/airTemp/airT_std_anom.pkl')
air.index.name='Year'
air = air.mean(axis=1)
#air.rename(columns={'Air temp.'})

# 3. Sea Ice (And icebergs)
ice = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/ice/ice_index.pkl')
ice = ice*-1

# 4. Icebergs
bergs = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bergs/bergs_std_anom.pkl')
bergs.index.name='Year'
bergs = bergs*-1

# 5. SSTs
sst = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/SSTs/SST_anom.pkl')

# 6. Stn27 (0-176m, 0-50m, 150-176m)
s27_temp = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/stn27/s27_temp_stn_anom.pkl')
s27_temp.index = s27_temp.index.year
s27_sal = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/stn27/s27_sal_stn_anom.pkl')
s27_sal.index = s27_sal.index.year
# average 3 series above (assume fresh = cold)
s27_temp = s27_temp.mean(axis=1)
s27_sal = s27_sal.mean(axis=1)

# s27_cil not std_anom yet
s27_cil = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/stn27/S27_CIL_summer_stats.pkl')
s27_cil.index = s27_cil.index.year
s27_cil_clim = s27_cil[(s27_cil.index>=clim_year[0]) & (s27_cil.index<=clim_year[1])]
s27_cil = (s27_cil-s27_cil_clim.mean(axis=0))/s27_cil_clim.std(axis=0)
s27_cil = s27_cil[['CIL temp', 'CIL core T']].mean(axis=1)

# 7. Section CIL (only area)
section_cil = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/sections_plots/section_cil_index.pkl')
section_cil = section_cil.volume*-1

# 8. bottomT
bottomT_spring = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/bottomT_index_spring.pkl')
bottomT_fall = pd.read_pickle('/home/cyrf0006/AZMP/state_reports/bottomT/bottomT_index_fall.pkl')
bottomT = pd.concat([bottomT_spring, bottomT_fall], axis=1).mean(axis=1)


#### ----- Merge the data ---- ####
climate_index = pd.concat([nao, air, ice, bergs, sst, s27_temp,  s27_sal, s27_cil, section_cil, bottomT], axis=1)
climate_index = climate_index.rename(columns={0:'Air Temp'})
climate_index = climate_index.rename(columns={1:'Sea Ice'})
climate_index = climate_index.rename(columns={2:'Icebergs'})
climate_index = climate_index.rename(columns={3:'SST'})
climate_index = climate_index.rename(columns={4:'S27 Temp'})
climate_index = climate_index.rename(columns={5:'S27 Sal'})
climate_index = climate_index.rename(columns={6:'S27 CIL'})
climate_index = climate_index.rename(columns={'volume':'CIL volume'})
climate_index = climate_index.rename(columns={7:'Bottom Temp'})

climate_index = climate_index[climate_index.index>=1950]

#### ----- Plot climate index ---- ####
n = 5 # xtick every n years
#ax = climate_index.plot(kind='bar', stacked=True, cmap='gist_rainbow')
ax = climate_index.plot(kind='bar', stacked=True, cmap='nipy_spectral', zorder=10)
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.grid('on')
ax.set_ylabel(r'Cummulative standardized anomaly')
ax.set_title('NL Climate Index')
fig = ax.get_figure()
fig.set_size_inches(w=12,h=8)
fig_name = 'NL_climate_index.png'
fig.savefig(fig_name, dpi=200)
os.system('convert -trim ' + fig_name + ' ' + fig_name)


## Save index
climate_index.to_csv('NL_climate_index_preliminary_all_fields.csv', float_format='%.2f')



#### ----- Plot climate index (French) ---- ####
climate_index.rename(columns={
    'NAO':'ONA',
    'Air Temp':'Temp Air',
    'Sea Ice':'Glace',
    'SST':'TSM',
    'S27 CIL':'S27 CIF',
    'CIL volume':'Volume CIF',
    'Bottom Temp': 'Temp Fond'
    }, inplace=True)

ax = climate_index.plot(kind='bar', stacked=True, cmap='nipy_spectral', zorder=10)
ticks = ax.xaxis.get_ticklocs()
ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
ax.xaxis.set_ticks(ticks[::n])
ax.xaxis.set_ticklabels(ticklabels[::n])
plt.grid('on')
ax.set_ylabel(r'Anomalie normalisée cummulée')
ax.set_title('Indice climatique pour TNL')
fig = ax.get_figure()
fig.set_size_inches(w=12,h=8)
fig_name = 'NL_climate_index_FR.png'
fig.savefig(fig_name, dpi=200)
os.system('convert -trim ' + fig_name + ' ' + fig_name)



#### ----- Comparison with Eugene's CEI ---- ####
climate_index.mean(axis=1).to_csv('NL_climate_index_preliminary.csv', float_format='%.2f')
    
df_cei = pd.read_excel('/home/cyrf0006/data/AZMP/ColbourneStuff/composite_climate_index_english.xlsx')
df_cei = df_cei.T
df_cei = df_cei.dropna(how='all')
df_cei.columns = df_cei.iloc[0]
df_cei.drop(df_cei.index[0], inplace=True)
df_cei.drop(df_cei.index[-1], inplace=True)

#df_cei = df_cei.COMPOSITE
plt.close('all')
plt.plot(df_cei.mean(axis=1))
plt.plot(climate_index.mean(axis=1))
plt.legend(['CEI','new climate index'])
plt.show()

# correlation
df_merged = pd.concat([df_cei.mean(axis=1), climate_index.mean(axis=1)], axis=1)
df_merged.corr('pearson')