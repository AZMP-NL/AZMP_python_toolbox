'''

WORK IN PROGRESS...


To generate bottom climato:

import numpy as np
import azmp_utils as azu
dc = .1
lonLims = [-60, -43] # fish_hab region
latLims = [39, 56]
lonLims = [-60, -45] # FC AZMP report region
latLims = [42, 56]
lon_reg = np.arange(lonLims[0]+dc/2, lonLims[1]-dc/2, dc)
lat_reg = np.arange(latLims[0]+dc/2, latLims[1]-dc/2, dc)
azu.get_bottomT_climato('/home/cyrf0006/data/dev_database/*.nc', lon_reg, lat_reg, season='spring', h5_outputfile='Tbot_climato_spring_0.10.h5') 

'''

## mport netCDF4
import h5py
## import xarray as xr
from mpl_toolkits.basemap import Basemap
import numpy as  np
import matplotlib.pyplot as plt
## import openpyxl, pprint
import pandas as pd
from scipy.interpolate import griddata
from scipy.interpolate import interp1d  # to remove NaNs in profiles
from scipy.interpolate import RegularGridInterpolator as rgi
import azmp_utils as azu
from shapely.geometry.polygon import Polygon
from shapely.ops import cascaded_union


## ---- preamble ---- ##
years = np.arange(1980, 2018)
lon_0 = -50
lat_0 = 50
proj = 'merc'
plot = False # to plot or not to plot...
season = 'fall'

# load climato
if season == 'fall':
    climato_file = 'Tbot_climato_fall_0.10.h5'
elif season == 'spring':
    climato_file = 'Tbot_climato_spring_0.10.h5'
h5f = h5py.File(climato_file, 'r')
Tbot_climato = h5f['Tbot'][:]
lon_reg = h5f['lon_reg'][:]
lat_reg = h5f['lat_reg'][:]
Zitp = h5f['Zitp'][:]
h5f.close()

# Derive some map parameters
lon_0 = np.round(np.mean(lon_reg))
lat_0 = np.round(np.mean(lat_reg))
lonLims = [lon_reg[0], lon_reg[-1]]
latLims = [lat_reg[0], lat_reg[-1]]

# NAFO divisions
nafo_div = azu.get_nafo_divisions()
polygon3L = Polygon(zip(nafo_div['3L']['lon'], nafo_div['3L']['lat']))
polygon3N = Polygon(zip(nafo_div['3N']['lon'], nafo_div['3N']['lat']))
polygon3O = Polygon(zip(nafo_div['3O']['lon'], nafo_div['3O']['lat']))
shape = [polygon3L, polygon3N, polygon3O]
shape_3LNO = cascaded_union(shape)
shape_3Ps = Polygon(zip(nafo_div['3Ps']['lon'], nafo_div['3Ps']['lat']))
shape_2J = Polygon(zip(nafo_div['2J']['lon'], nafo_div['2J']['lat']))
shape_3K = Polygon(zip(nafo_div['3K']['lon'], nafo_div['3K']['lat']))


dict_stats_3LNO = {}
dict_stats_3Ps = {}
dict_stats_3K = {}
dict_stats_2J = {}


# Loop on years
for year in years:
    print ' ---- ' + np.str(year) + ' ---- '
    year_file = '/home/cyrf0006/data/dev_database/' + np.str(year) + '.nc'
    Tdict = azu.get_bottomT(year_file, season, climato_file)    
    Tbot = Tdict['Tbot']
    lons = Tdict['lons']
    lats = Tdict['lats']
    anom = Tbot-Tbot_climato

    
    # NAFO division stats    
    dict_stats_3LNO[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3LNO)
    dict_stats_3Ps[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3Ps)
    dict_stats_2J[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_2J)
    dict_stats_3K[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3K)

    if plot:
        # 1.1 - Plot Anomaly
        fig, ax = plt.subplots(nrows=1, ncols=1)
        m = Basemap(ax=ax, projection='merc',lon_0=lon_0,lat_0=lat_0, llcrnrlon=lonLims[0],llcrnrlat=latLims[0],urcrnrlon=lonLims[1],urcrnrlat=latLims[1], resolution= 'i')
        levels = np.linspace(-3.5, 3.5, 8)
        xi, yi = m(*np.meshgrid(lon_reg, lat_reg))
        c = m.contourf(xi, yi, anom, levels, cmap=plt.cm.RdBu_r, extend='both')
        cc = m.contour(xi, yi, -Zitp, [100, 500, 1000, 4000], colors='grey');
        plt.clabel(cc, inline=1, fontsize=10, fmt='%d')
        if season=='fall':
            plt.title('Fall Bottom Temperature Anomaly')
        elif season=='spring':
            plt.title('Spring Bottom Temperature Anomaly')
        else:
            plt.title('Bottom Temperature Anomaly')
        m.fillcontinents(color='tan');
        m.drawparallels([40, 45, 50, 55, 60], labels=[1,0,0,0], fontsize=12, fontweight='normal');
        m.drawmeridians([-60, -55, -50, -45], labels=[0,0,0,1], fontsize=12, fontweight='normal');
        cax = plt.axes([0.85,0.15,0.04,0.7], facecolor='grey')
        cb = plt.colorbar(c, cax=cax)
        cb.set_label(r'$\rm T(^{\circ}C)$', fontsize=12, fontweight='normal')
        div_toplot = ['2J', '3K', '3L', '3N', '3O', '3Ps']
        for div in div_toplot:
            div_lon, div_lat = m(nafo_div[div]['lon'], nafo_div[div]['lat'])
            m.plot(div_lon, div_lat, 'k', linewidth=2)
            ax.text(np.mean(div_lon), np.mean(div_lat), div, fontsize=12, color='black', fontweight='bold')    
        # Save Figure
        fig.set_size_inches(w=7, h=8)
        fig.set_dpi(200)
        outfile = 'bottom_temp_anomaly_' + season + '_' + np.str(year) + '.png'
        fig.savefig(outfile)

        # 1.2 - Plot Temperature
        fig, ax = plt.subplots(nrows=1, ncols=1)
        m = Basemap(ax=ax, projection='merc',lon_0=lon_0,lat_0=lat_0, llcrnrlon=lonLims[0],llcrnrlat=latLims[0],urcrnrlon=lonLims[1],urcrnrlat=latLims[1], resolution= 'i')
        levels = np.linspace(-2, 6, 9)
        xi, yi = m(*np.meshgrid(lon_reg, lat_reg))
        c = m.contourf(xi, yi, Tbot, levels, cmap=plt.cm.RdBu_r, extend='both')
        cc = m.contour(xi, yi, -Zitp, [100, 500, 1000, 4000], colors='grey');
        plt.clabel(cc, inline=1, fontsize=10, fmt='%d')
        if season=='fall':
            plt.title('Fall Bottom Temperature')
        elif season=='spring':
            plt.title('Spring Bottom Temperature')
        else:
            plt.title('Bottom Temperature')
        m.fillcontinents(color='tan');
        m.drawparallels([40, 45, 50, 55, 60], labels=[1,0,0,0], fontsize=12, fontweight='normal');
        m.drawmeridians([-60, -55, -50, -45], labels=[0,0,0,1], fontsize=12, fontweight='normal');
        x, y = m(lons, lats)
        m.scatter(x,y, s=50, marker='.',color='k')
        cax = plt.axes([0.85,0.15,0.04,0.7], facecolor='grey')
        cb = plt.colorbar(c, cax=cax)
        cb.set_label(r'$\rm T(^{\circ}C)$', fontsize=12, fontweight='normal')
        div_toplot = ['2J', '3K', '3L', '3N', '3O', '3Ps']
        for div in div_toplot:
            div_lon, div_lat = m(nafo_div[div]['lon'], nafo_div[div]['lat'])
            m.plot(div_lon, div_lat, 'k', linewidth=2)
            ax.text(np.mean(div_lon), np.mean(div_lat), div, fontsize=12, color='black', fontweight='bold')
        # Save Figure
        fig.set_size_inches(w=7, h=8)
        fig.set_dpi(200)
        outfile = 'bottom_temp_' + season + '_' + np.str(year) + '.png'
        fig.savefig(outfile)


    
df_3Ps = pd.DataFrame.from_dict(dict_stats_3Ps, orient='index')
df_3LNO = pd.DataFrame.from_dict(dict_stats_3LNO, orient='index')
df_3K = pd.DataFrame.from_dict(dict_stats_3K, orient='index')
df_2J = pd.DataFrame.from_dict(dict_stats_2J, orient='index')


outname = 'stats_3Ps_' + season + '.pkl'
df_3Ps.to_pickle(outname)
outname = 'stats_3LNO_' + season + '.pkl'
df_3LNO.to_pickle(outname)
outname = 'stats_3K_' + season + '.pkl'
df_3K.to_pickle(outname)
outname = 'stats_2J_' + season + '.pkl'
df_2J.to_pickle(outname)
