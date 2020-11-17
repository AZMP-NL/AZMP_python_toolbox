'''
Pickled climatologies are generated by azmp_section_clim.py

see also an automatic function in:

azmp_section_tools.seasonal_section_plot(VAR, SECTION, SEASON, YEAR):


'''
import os
import netCDF4
import xarray as xr
#from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import pandas as pd
import numpy as  np
from scipy.interpolate import interp1d  # to remove NaNs in profiles
from scipy.interpolate import griddata
import azmp_sections_tools as azst
import cmocean


## ---- Region parameters ---- ## <-------------------------------Would be nice to pass this in a config file '2017.report'
VAR = 'temperature'
SECTION = 'SI'
SEASON = 'summer'
YEAR = 1990
STATION_BASED=False
ZMAX = 500

# derived parameters
if VAR == 'temperature':
    v = np.arange(-2,11,1)
    v_anom = np.linspace(-3.5, 3.5, 15)
    v_anom = np.delete(v_anom, np.where(v_anom==0)) 
    CMAP = cmocean.cm.thermal
elif VAR == 'salinity':
    v = np.arange(29,36,.5)
    v_anom = np.linspace(-1.5, 1.5, 16)
    CMAP = cmocean.cm.haline
elif VAR == 'sigma-t':
    v = np.arange(24,28,.2)
    v_anom = np.linspace(-1.5, 1.5, 16)
    CMAP = cmocean.cm.haline
else:
    v = 10
    v_anom = 10
    CMAP = cmocean.cm.thermal
SECTION_BATHY = SECTION

    
    
# CIL surface (Note that there is a bias because )
def area(vs):
    a = 0
    x0,y0 = vs[0]
    for [x1,y1] in vs[1:]:
        dx = x1-x0
        dy = y1-y0
        a += 0.5*(y0*dx - x0*dy)
        x0 = x1
        y0 = y1
    return a


## ---- Get this year's section ---- ## 
df_section_stn, df_section_itp = azst.get_section(SECTION, YEAR, SEASON, VAR, dz=5, zmin=2)
if STATION_BASED:
    df_section = df_section_stn
else:
    df_section = df_section_itp

# In case df_section only contains NaNs..
df_section.dropna(axis=0,how='all')  
if df_section.size == 0:
    print(' !!! Empty section [return None] !!!')
else:

    ## ---- Get climatology ---- ## 
    clim_name = '/home/cyrf0006/AZMP/state_reports/sections_plots/df_' + VAR + '_' + SECTION + '_' + SEASON + '_clim.pkl' 
    df_clim = pd.read_pickle(clim_name)
    # Update index to add distance (in addition to existing station name)    
    df_clim.index = df_section_itp.loc[df_clim.index].index
    
    ## ---- Retrieve bathymetry using function ---- ##
    bathymetry = azst.section_bathymetry(SECTION_BATHY)

    ## ---  ---- ## 
    #df_anom = df_section.reset_index(level=1, drop=True) - df_clim
    df_anom =  df_section - df_clim
    #df_anom_stations = df_anom.reset_index(level=0, drop=True)
    df_anom = df_anom.reset_index(level=0, drop=True)
    #df_section = df_section.reset_index(level=0, drop=True)
    # drop empty columns
    df_anom.dropna(how='all', inplace=True)
    distance = df_section.index.droplevel(0)                                   

    
    ## ---- plot Figure ---- ##
    XLIM = df_section_itp.index[-1][1]
    fig = plt.figure()
    # ax1
    ax = plt.subplot2grid((3, 1), (0, 0))
    c = plt.contourf(df_section.index.droplevel(0), df_section.columns, df_section.T, v, cmap=CMAP, extend='max')
    if VAR == 'temperature':
        c_cil_itp = plt.contour(df_section.index.droplevel(0), df_section.columns, df_section.T, [0,], colors='k', linewidths=2)
    ax.set_ylim([0, ZMAX])
    ax.set_xlim([0,  XLIM])
    ax.set_ylabel('Depth (m)', fontWeight = 'bold')
    ax.invert_yaxis()
    Bgon = plt.Polygon(bathymetry,color=np.multiply([1,.9333,.6667],.4), alpha=1, zorder=10)
    ax.add_patch(Bgon)
    for i in range(0,len(distance)):
        plt.plot(np.array([distance[i], distance[i]]), np.array([0, ZMAX]), '--k', linewidth=0.5, zorder=5)   
    plt.colorbar(c)
    ax.xaxis.label.set_visible(False)
    ax.tick_params(labelbottom='off')
    ax.set_title(VAR + ' for section ' + SECTION + ' - ' + SEASON + ' ' + str(YEAR))

    # ax2
    ax2 = plt.subplot2grid((3, 1), (1, 0))
    c = plt.contourf(df_clim.index.droplevel(0), df_clim.columns, df_clim.T, v, cmap=CMAP, extend='max')
    if VAR == 'temperature':
        c_cil_itp = plt.contour(df_clim.index.droplevel(0), df_clim.columns, df_clim.T, [0,], colors='k', linewidths=2)
    ax2.set_ylim([0, ZMAX])
    ax2.set_xlim([0,  XLIM])
    ax2.set_ylabel('Depth (m)', fontWeight = 'bold')
    ax2.invert_yaxis()
    Bgon = plt.Polygon(bathymetry,color=np.multiply([1,.9333,.6667],.4), alpha=1)
    ax2.add_patch(Bgon)
    plt.colorbar(c)
    ax2.xaxis.label.set_visible(False)
    ax2.tick_params(labelbottom='off')
    ax2.set_title('1981-2010 climatology')



    # ax3
    ax3 = plt.subplot2grid((3, 1), (2, 0))
    c = plt.contourf(df_anom.index, df_anom.columns, df_anom.T, v_anom, cmap=cmocean.cm.balance, extend='both')
    ax3.set_ylim([0, ZMAX])
    ax3.set_xlim([0,  XLIM])
    ax3.set_ylabel('Depth (m)', fontWeight = 'bold')
    ax3.set_xlabel('Distance (km)', fontWeight = 'bold')
    ax3.invert_yaxis()
    Bgon = plt.Polygon(bathymetry,color=np.multiply([1,.9333,.6667],.4), alpha=1)
    ax3.add_patch(Bgon)
    plt.colorbar(c)
    ax3.set_title(r'Anomaly')

    fig.set_size_inches(w=8,h=12)
    fig_name = VAR + '_' + SECTION + '_' + SEASON + '_' + str(YEAR) + '.png' 
    fig.savefig(fig_name, dpi=200)
    os.system('convert -trim ' + fig_name + ' ' + fig_name)

    # Save in French
    if (VAR == 'temperature') & (SEASON == 'summer'):
            ax.set_title('Température à la section ' + SECTION + ' - été ' + str(YEAR))
    elif (VAR == 'salinity') & (SEASON == 'summer'):
            ax.set_title('Salinité à la section ' + SECTION + ' - été ' + str(YEAR))    

    ax.set_ylabel('Profondeur (m)', fontWeight = 'bold')    
    ax2.set_ylabel('Profondeur (m)', fontWeight = 'bold')
    ax3.set_ylabel('Profondeur (m)', fontWeight = 'bold')
    
    ax2.set_title(r'Climatologie 1981-2010')
    ax3.set_title(r'Anomalie')
    fig_name = VAR + '_' + SECTION + '_' + SEASON + '_' + str(YEAR) + '_FR.png' 
    fig.savefig(fig_name, dpi=200)
    os.system('convert -trim ' + fig_name + ' ' + fig_name)    
    

    ## montage temperature_BB_summer_2018.png salinity_BB_summer_2018.png  -tile 2x1 -geometry +10+10  -background white BB_summer_2018.png 
    ## montage temperature_SI_summer_2018.png salinity_SI_summer_2018.png  -tile 2x1 -geometry +10+10  -background white SI_summer_2018.png 
    ## montage temperature_FC_summer_2018.png salinity_FC_summer_2018.png  -tile 2x1 -geometry +10+10  -background white FC_summer_2018.png 

    ## montage temperature_BB_summer_2018_FR.png salinity_BB_summer_2018_FR.png  -tile 2x1 -geometry +10+10  -background white BB_summer_2018_FR.png 
    ## montage temperature_SI_summer_2018_FR.png salinity_SI_summer_2018_FR.png  -tile 2x1 -geometry +10+10  -background white SI_summer_2018_FR.png 
    ## montage temperature_FC_summer_2018_FR.png salinity_FC_summer_2018_FR.png  -tile 2x1 -geometry +10+10  -background white FC_summer_2018_FR.png 
    
    # Save section in csv
    # ---> see azmp_sections_tools.py
    # Export data in csv.    
    ## stn_file = VAR + '_' + SECTION + '_' + SEASON + '_' + str(YEAR) + '_stn.csv' 
    ## itp_file = VAR + '_' + SECTION + '_' + SEASON + '_' + str(YEAR) + '_itp.csv' 
    ## df_section_stn.T.to_csv(stn_file, float_format='%.3f') 
    ## df_section_itp.T.to_csv(itp_file, float_format='%.3f') 

    # Pickle data 
    stn_pickle = VAR + '_' + SECTION + '_' + SEASON + '_' + str(YEAR) + '_stn.pkl' 
    itp_pickle = VAR + '_' + SECTION + '_' + SEASON + '_' + str(YEAR) + '_itp.pkl' 
    df_section_stn.to_pickle(stn_pickle, protocol=2) 
    df_section_itp.to_pickle(itp_pickle, protocol=2)
