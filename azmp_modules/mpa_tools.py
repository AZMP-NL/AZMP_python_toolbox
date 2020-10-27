"""
Codes used of the RVSurvey CSAS 

Inspired from the work done for CSAS ResDocs.

"""

__author__ = 'Frederic.Cyr@dfo-mpo.gc.ca'
__version__ = '0.1'

import numpy as np
import matplotlib.pyplot as plt
import os
import sys
#from sys import version_info
# read/write tools
import netCDF4
import h5py
import xarray as xr
import pandas as pd
# maps
os.environ['PROJ_LIB'] = '/home/cyrf0006/anaconda3/share/proj'
from mpl_toolkits.basemap import Basemap
# interpolation tools
from scipy.interpolate import griddata
from scipy.interpolate import interp1d
# Shaping tools
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapely.ops import cascaded_union
## AZMP custom imports
import azmp_utils as azu
## for scorecards
import unicodedata
from matplotlib.colors import from_levels_and_colors
## For shape files
import shapefile 


def is_number(s):
    '''
    Used for differentiate numbers from letters in scorecards.
    https://www.pythoncentral.io/how-to-check-if-a-string-is-a-number-in-python-including-unicode/
    
    '''
    try:
        float(s)
        return True
    except ValueError:
        pass 
    try:
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass 
    return False

def add_path(PATH):
    """ Since this module uses (e.g.) bathymetry data, the path to the file must be specified if not already permanent.

    Usage ex: (for bathymetry data)
    import azmp_report_tools as az_r
    az_r.add_path('/home/cyrf0006/data/GEBCO/')
    az_r.add_path('/home/cyrf0006/data/dev_database/')

    ** Turns out to be a useless function...
    """

    sys.path.append(PATH)  # or .insert(0, YOUR_PATH) may give higher priority

def get_closures(name='mpas'):
    """ Will generate a dict with closures

    for idx, key in enumerate(mpas.keys()):
       coords = mpas[key]  
       poly_x = coords[:,0]
       poly_y = coords[:,1]
       poly = list(zip(poly_x, poly_y))
       pgon = Polygon(poly)
       ax.add_geometries([pgon], crs=ccrs.PlateCarree(), facecolor='red', alpha=0.5)
       ax.text(poly_x.mean(), poly_y.mean(), str(records[idx][0]), transform=ccrs.PlateCarree())

    ** see mpa_RVsurvey.py for map

    Frederic.Cyr@dfo-mpo.gc.ca - July 2020

    """
    # Read shapefiles
    if name == 'mpas':
        sf = shapefile.Reader('/home/cyrf0006/research/MPAs/Warren_shapefiles/RV_CSAS_closures_GCS')
    elif name == 'nafo_3O':
        sf = shapefile.Reader('/home/cyrf0006/research/MPAs/NAFO_closures/2015_Closures_3O')
    elif name == 'nafo_seamounts':
        sf = shapefile.Reader('/home/cyrf0006/research/MPAs/NAFO_closures/2018_Closures_seamounts')
    elif name == 'nafo_coral':
        sf = shapefile.Reader('/home/cyrf0006/research/MPAs/NAFO_closures/2019_Closures_sponge_coral')
        
    records = sf.records()
    shapes = sf.shapes()
    # Fill dictionary with closures (named MPAs for simplicity)
    mpas = {}
    for idx, rec in enumerate(records):
        if rec[0] == '':
            continue
        else:
            #print(rec)
            mpas[rec[0]] = np.array(shapes[idx].points)            
    return mpas
        
def bottom_temperature(season, year, zmin=0, zmax=1000, dz=5, proj='merc', netcdf_path='/home/cyrf0006/data/dev_database/netCDF/', climato_file='', closure_scenario = '4'):

    '''
    Closed area groupings:

    A.        Hopedale Saddle, NE Nfld Slope, 3O Coral Closure (corals and sponges including large & small gorgonians, sea pens, sponges)

    B.        Laurentian Channel (sea pens only)

    C.        Hawke Channel, Funk Island Deep (benthic habitat for cod)


    Scenarios:

    1.        Exclude group A only

    2.        Exclude group B only

    3.        Exclude groups A and B

    4.        Exclude groups A, B, C


    closure_scenario = ['1', '2', '3' or '4']

    for usage example see:
    >> mpa_genReport.py

    Frederic.Cyr@dfo-mpo.gc.ca - July 2020
    
    '''
    if len(climato_file) == 0: # climato file not provided
        if season=='spring':
            climato_file = '/home/cyrf0006/AZMP/state_reports/bottomT/Tbot_climato_spring_0.10.h5'
        elif season=='fall':
            climato_file = '/home/cyrf0006/AZMP/state_reports/bottomT/Tbot_climato_fall_0.10.h5'
        elif season=='summer':
            climato_file = '/home/cyrf0006/AZMP/state_reports/bottomT/Tbot_climato_summer_0.10.h5'
    
    year_file = netcdf_path + str(year) + '.nc'


    ## ---- Load Climato data ---- ##    
    print('Load ' + climato_file)
    h5f = h5py.File(climato_file, 'r')
    Tbot_climato = h5f['Tbot'][:]
    lon_reg = h5f['lon_reg'][:]
    lat_reg = h5f['lat_reg'][:]
    Zitp = h5f['Zitp'][:]
    h5f.close()

    ## ---- Derive some parameters ---- ##    
    lon_0 = np.round(np.mean(lon_reg))
    lat_0 = np.round(np.mean(lat_reg))
    lonLims = [lon_reg[0], lon_reg[-1]]
    latLims = [lat_reg[0], lat_reg[-1]]
    lon_grid, lat_grid = np.meshgrid(lon_reg,lat_reg)
    dc = np.diff(lon_reg[0:2])

    ## ---- get NAFO divisions ---- ##
    nafo_div = azu.get_nafo_divisions()

    ## ---- get closures ---- ##
    mpas = get_closures()
    nafo_3O = get_closures(name='nafo_3O') # group A
    nafo_seamounts = get_closures(name='nafo_seamounts') # group A
    nafo_coral = get_closures(name='nafo_coral') # group A

    ## ---- Get CTD data --- ##
    print('Get ' + year_file)
    ds = xr.open_dataset(year_file)
    # Remome problematic datasets
    print('!!Remove MEDBA data!!')
    print('  ---> I Should be improme because I remove good data!!!!')
    ds = ds.where(ds.instrument_ID!='MEDBA', drop=True)
    ds = ds.where(ds.instrument_ID!='MEDTE', drop=True)

    # Selection of a subset region
    ds = ds.where((ds.longitude>lonLims[0]) & (ds.longitude<lonLims[1]), drop=True)
    ds = ds.where((ds.latitude>latLims[0]) & (ds.latitude<latLims[1]), drop=True)
    # Select time (save several options here)
    if season == 'summer':
        ds = ds.sel(time=((ds['time.month']>=6)) & ((ds['time.month']<=9)))
    elif season == 'spring':
        ds = ds.sel(time=((ds['time.month']>=4)) & ((ds['time.month']<=6)))
    elif season == 'fall':
        ds = ds.sel(time=((ds['time.month']>=9)) & ((ds['time.month']<=12)))
    else:
        print('!! no season specified, used them all! !!')

    # Vertical binning (on dataArray; more appropriate here)
    da_temp = ds['temperature']
    lons = np.array(ds.longitude)
    lats = np.array(ds.latitude)
    #bins = np.arange(dz/2.0, ds.level.max(), dz)
    bins = np.arange(dz/2.0, 1000, dz)
    da_temp = da_temp.groupby_bins('level', bins).mean(dim='level')
    #To Pandas Dataframe
    df_temp = da_temp.to_pandas()
    df_temp.columns = bins[0:-1] #rename columns with 'bins'
    # Get comments
    da_comments = ds['comments']
    df_comments = da_comments.to_pandas()
    df_comments = df_comments.str.lower() # only lower case!
    # Remove empty columns
    idx_empty_rows = df_temp.isnull().all(1).nonzero()[0]
    df_temp = df_temp.dropna(axis=0,how='all')
    df_comments = df_comments.drop(df_comments.index[idx_empty_rows])
    lons = np.delete(lons,idx_empty_rows)
    lats = np.delete(lats,idx_empty_rows)
    print(' -> Done!')

    ## ---- Real difference to traditional bottom_temp. ----#
    print('Apply masks for closures scenario: ' + closure_scenario)
    # DFO closures
    polygon5 = Polygon(zip(mpas[5][:,0], mpas[5][:,1]))
    polygon6 = Polygon(zip(mpas[6][:,0], mpas[6][:,1]))
    polygon7 = Polygon(zip(mpas[7][:,0], mpas[7][:,1]))
    polygon35 = Polygon(zip(mpas[35][:,0], mpas[35][:,1]))
    polygon15 = Polygon(zip(mpas[15][:,0], mpas[15][:,1]))
    polygon9 = Polygon(zip(mpas[9][:,0], mpas[9][:,1]))
    polygon14 = Polygon(zip(mpas[14][:,0], mpas[14][:,1]))
    # NAFO 3O
    polygon_n3O = Polygon(zip(nafo_3O[0][:,0], nafo_3O[0][:,1]))
    # NAFO seamounts
    polygon_ns1 = Polygon(zip(nafo_seamounts[1][:,0], nafo_seamounts[1][:,1]))
    polygon_ns2 = Polygon(zip(nafo_seamounts[2][:,0], nafo_seamounts[2][:,1]))
    polygon_ns3 = Polygon(zip(nafo_seamounts[3][:,0], nafo_seamounts[3][:,1]))
    polygon_ns4 = Polygon(zip(nafo_seamounts[4][:,0], nafo_seamounts[4][:,1]))
    polygon_ns5 = Polygon(zip(nafo_seamounts[5][:,0], nafo_seamounts[5][:,1]))
    polygon_ns6 = Polygon(zip(nafo_seamounts[6][:,0], nafo_seamounts[6][:,1]))
    # NAFO Coral and Sponges
    polygon_nc1 = Polygon(zip(nafo_coral[1][:,0], nafo_coral[1][:,1]))
    polygon_nc2 = Polygon(zip(nafo_coral[2][:,0], nafo_coral[2][:,1]))
    polygon_nc3 = Polygon(zip(nafo_coral[3][:,0], nafo_coral[3][:,1]))
    polygon_nc4 = Polygon(zip(nafo_coral[4][:,0], nafo_coral[4][:,1]))
    polygon_nc5 = Polygon(zip(nafo_coral[5][:,0], nafo_coral[5][:,1]))
    polygon_nc6 = Polygon(zip(nafo_coral[6][:,0], nafo_coral[6][:,1]))
    polygon_nc7 = Polygon(zip(nafo_coral[7][:,0], nafo_coral[7][:,1]))
    polygon_nc8 = Polygon(zip(nafo_coral[8][:,0], nafo_coral[8][:,1]))
    polygon_nc9 = Polygon(zip(nafo_coral[9][:,0], nafo_coral[9][:,1]))
    polygon_nc10 = Polygon(zip(nafo_coral[10][:,0], nafo_coral[10][:,1]))
    polygon_nc11 = Polygon(zip(nafo_coral[11][:,0], nafo_coral[11][:,1]))
    polygon_nc12 = Polygon(zip(nafo_coral[12][:,0], nafo_coral[12][:,1]))
    polygon_nc13 = Polygon(zip(nafo_coral[13][:,0], nafo_coral[13][:,1]))

    idx_toremove = []
    for i, lat in enumerate(lats):
        if (df_comments[i] == '') | (('set' in df_comments[i]) | ('unsucces' in df_comments[i])): # check if string "set" or "unsucces" is there or comments is empty
        
            point = Point(lons[i], lats[i])
            if closure_scenario == '1': # Remove A only
                if polygon5.contains(point) | polygon6.contains(point) | polygon7.contains(point) | polygon35.contains(point) | polygon_n3O.contains(point) | polygon_ns1.contains(point) | polygon_ns2.contains(point) |  polygon_ns3.contains(point) | polygon_ns4.contains(point) | polygon_ns5.contains(point) | polygon_ns6.contains(point) | polygon_nc1.contains(point) | polygon_nc2.contains(point) | polygon_nc3.contains(point) | polygon_nc4.contains(point) | polygon_nc5.contains(point) | polygon_nc6.contains(point) | polygon_nc7.contains(point) | polygon_nc8.contains(point) | polygon_nc9.contains(point) | polygon_nc10.contains(point) | polygon_nc11.contains(point) | polygon_nc12.contains(point) | polygon_nc13.contains(point):

                    idx_toremove.append(i)

            elif closure_scenario == '2': # Remove B only
                if polygon15.contains(point):

                    idx_toremove.append(i)

            elif closure_scenario == '3': # Remove A & B
                if polygon5.contains(point) | polygon6.contains(point) | polygon7.contains(point) | polygon35.contains(point) | polygon_n3O.contains(point) | polygon_ns1.contains(point) | polygon_ns2.contains(point) |  polygon_ns3.contains(point) | polygon_ns4.contains(point) | polygon_ns5.contains(point) | polygon_ns6.contains(point) | polygon_nc1.contains(point) | polygon_nc2.contains(point) | polygon_nc3.contains(point) | polygon_nc4.contains(point) | polygon_nc5.contains(point) | polygon_nc6.contains(point) | polygon_nc7.contains(point) | polygon_nc8.contains(point) | polygon_nc9.contains(point) | polygon_nc10.contains(point) | polygon_nc11.contains(point) | polygon_nc12.contains(point) | polygon_nc13.contains(point) | polygon15.contains(point):

                    idx_toremove.append(i)

            elif closure_scenario == '4': # Remove A, B & C
                if polygon5.contains(point) | polygon6.contains(point) | polygon7.contains(point) | polygon35.contains(point) | polygon_n3O.contains(point) | polygon_ns1.contains(point) | polygon_ns2.contains(point) |  polygon_ns3.contains(point) | polygon_ns4.contains(point) | polygon_ns5.contains(point) | polygon_ns6.contains(point) | polygon_nc1.contains(point) | polygon_nc2.contains(point) | polygon_nc3.contains(point) | polygon_nc4.contains(point) | polygon_nc5.contains(point) | polygon_nc6.contains(point) | polygon_nc7.contains(point) | polygon_nc8.contains(point) | polygon_nc9.contains(point) | polygon_nc10.contains(point) | polygon_nc11.contains(point) | polygon_nc12.contains(point) | polygon_nc13.contains(point) | polygon15.contains(point) | polygon9.contains(point) | polygon14.contains(point) :

                    idx_toremove.append(i)
                
    # Drop now
    df_temp.drop(df_temp.index[idx_toremove], inplace=True) 
    lons = np.delete(lons,idx_toremove)
    lats = np.delete(lats,idx_toremove)
                
    ## --- fill 3D cube --- ##  
    print('Fill regular cube')
    z = df_temp.columns.values
    V = np.full((lat_reg.size, lon_reg.size, z.size), np.nan)

    # Aggregate on regular grid
    for i, xx in enumerate(lon_reg):
        for j, yy in enumerate(lat_reg):    
            idx = np.where((lons>=xx-dc/2) & (lons<xx+dc/2) & (lats>=yy-dc/2) & (lats<yy+dc/2))
            tmp = np.array(df_temp.iloc[idx].mean(axis=0))
            idx_good = np.argwhere((~np.isnan(tmp)) & (tmp<30))
            if np.size(idx_good)==1:
                V[j,i,:] = np.array(df_temp.iloc[idx].mean(axis=0))
            elif np.size(idx_good)>1: # vertical interpolation between pts
                interp = interp1d(np.squeeze(z[idx_good]), np.squeeze(tmp[idx_good]))
                idx_interp = np.arange(np.int(idx_good[0]),np.int(idx_good[-1]+1))
                V[j,i,idx_interp] = interp(z[idx_interp]) # interpolate only where possible (1st to last good idx)

    # horizontal interpolation at each depth
    lon_grid, lat_grid = np.meshgrid(lon_reg,lat_reg)
    lon_vec = np.reshape(lon_grid, lon_grid.size)
    lat_vec = np.reshape(lat_grid, lat_grid.size)
    for k, zz in enumerate(z):
        # Meshgrid 1D data (after removing NaNs)
        tmp_grid = V[:,:,k]
        tmp_vec = np.reshape(tmp_grid, tmp_grid.size)
        # griddata (after removing nans)
        idx_good = np.argwhere(~np.isnan(tmp_vec))
        if idx_good.size > 5: # will ignore depth where no data exist
            LN = np.squeeze(lon_vec[idx_good])
            LT = np.squeeze(lat_vec[idx_good])
            TT = np.squeeze(tmp_vec[idx_good])
            zi = griddata((LN, LT), TT, (lon_grid, lat_grid), method='linear')
            V[:,:,k] = zi
        else:
            continue
    print(' -> Done!')    

    # mask using bathymetry (I don't think it is necessary, but make nice figures)
    for i, xx in enumerate(lon_reg):
        for j,yy in enumerate(lat_reg):
            if Zitp[j,i] > -10: # remove shallower than 10m
                V[j,i,:] = np.nan

    # getting bottom temperature
    print('Getting bottom Temp.')    
    Tbot = np.full([lat_reg.size,lon_reg.size], np.nan) 
    for i, xx in enumerate(lon_reg):
        for j,yy in enumerate(lat_reg):
            bottom_depth = -Zitp[j,i] # minus to turn positive
            temp_vec = V[j,i,:]
            idx_good = np.squeeze(np.where(~np.isnan(temp_vec)))
            if idx_good.size:
                idx_closest = np.argmin(np.abs(bottom_depth-z[idx_good]))
            else:
                continue

            if np.abs([idx_closest] - bottom_depth) <= 20:
                Tbot[j,i] = temp_vec[idx_good[idx_closest]]
            elif np.abs(z[idx_closest] - bottom_depth) <= 50:
                #print('used data located [30,50]m from bottom')
                Tbot[j,i] = temp_vec[idx_good[idx_closest]]

    print(' -> Done!')    

    # Mask data outside Nafo div.
    print('Mask according to NAFO division for ' + season)
    # Polygons
    polygon4R = Polygon(zip(nafo_div['4R']['lon'], nafo_div['4R']['lat']))
    polygon3K = Polygon(zip(nafo_div['3Kx']['lon'], nafo_div['3Kx']['lat']))
    polygon3L = Polygon(zip(nafo_div['3L']['lon'], nafo_div['3L']['lat']))
    polygon3N = Polygon(zip(nafo_div['3N']['lon'], nafo_div['3N']['lat']))
    polygon3O = Polygon(zip(nafo_div['3O']['lon'], nafo_div['3O']['lat']))
    polygon3Ps = Polygon(zip(nafo_div['3Ps']['lon'], nafo_div['3Ps']['lat']))
    polygon2J = Polygon(zip(nafo_div['2J']['lon'], nafo_div['2J']['lat']))
    polygon2H = Polygon(zip(nafo_div['2H']['lon'], nafo_div['2H']['lat']))

    # Contour of data to mask
    contour_mask = np.load('/home/cyrf0006/AZMP/state_reports/bottomT/100m_contour_labrador.npy')
    polygon_mask = Polygon(contour_mask)

    if season == 'spring':
        for i, xx in enumerate(lon_reg):
            for j,yy in enumerate(lat_reg):
                point = Point(lon_reg[i], lat_reg[j])
                #if (~polygon3L.contains(point)) & (~polygon3N.contains(point)) & (~polygon3O.contains(point)) & (~polygon3Ps.contains(point)):
                if polygon3L.contains(point) | polygon3N.contains(point) | polygon3O.contains(point) | polygon3Ps.contains(point) | polygon4R.contains(point):
                    pass #nothing to do but cannot implement negative statement "if not" above
                else:
                    Tbot[j,i] = np.nan

    elif season == 'fall':
        for i, xx in enumerate(lon_reg):
            for j,yy in enumerate(lat_reg):
                point = Point(lon_reg[i], lat_reg[j])
                if polygon2H.contains(point) | polygon2J.contains(point) | polygon3K.contains(point) | polygon3L.contains(point) | polygon3N.contains(point) | polygon3O.contains(point):
                    pass #nothing to do but cannot implement negative statement "if not" above
                else:
                    Tbot[j,i] = np.nan ### <--------------------- Do mask the fall / OR / 

                if polygon_mask.contains(point): # mask data near Labrador in fall
                    Tbot[j,i] = np.nan 

    elif season == 'summer':
        for i, xx in enumerate(lon_reg):
            for j,yy in enumerate(lat_reg):
                point = Point(lon_reg[i], lat_reg[j])
                # Just mask labrador
                if polygon_mask.contains(point): # mask data near Labrador in fall
                    Tbot[j,i] = np.nan 

    else:
        print('no division mask, all data taken')

    print(' -> Done!')    

    # Temperature anomaly:
    anom = Tbot-Tbot_climato
    div_toplot = ['2H', '2J', '3K', '3L', '3N', '3O', '3Ps', '4R']

    ## ---- Plot Anomaly ---- ##
    fig, ax = plt.subplots(nrows=1, ncols=1)
    m = Basemap(ax=ax, projection='merc',lon_0=lon_0,lat_0=lat_0, llcrnrlon=lonLims[0],llcrnrlat=latLims[0],urcrnrlon=lonLims[1],urcrnrlat=latLims[1], resolution= 'i')
    levels = np.linspace(-3.5, 3.5, 8)
    #levels = np.linspace(-3.5, 3.5, 16)
    xi, yi = m(*np.meshgrid(lon_reg, lat_reg))
    c = m.contourf(xi, yi, anom, levels, cmap=plt.cm.RdBu_r, extend='both')
    cc = m.contour(xi, yi, -Zitp, [100, 500, 1000, 4000], colors='grey');
    plt.clabel(cc, inline=1, fontsize=10, fmt='%d')
    if season=='fall':
        plt.title('Fall Bottom Temperature ' + year + ' Anomaly')
    elif season=='spring':
        plt.title('Spring Bottom Temperature ' + year + ' Anomaly')
    else:
        plt.title('Bottom Temperature ' + year + '  Anomaly')
    m.fillcontinents(color='tan');
    m.drawparallels([40, 45, 50, 55, 60], labels=[0,0,0,0], fontsize=12, fontweight='normal');
    m.drawmeridians([-60, -55, -50, -45], labels=[0,0,0,1], fontsize=12, fontweight='normal');
    cax = fig.add_axes([0.16, 0.05, 0.7, 0.025])
    cb = plt.colorbar(c, cax=cax, orientation='horizontal')
    cb.set_label(r'$\rm T(^{\circ}C)$', fontsize=12, fontweight='normal')
    for div in div_toplot:
        div_lon, div_lat = m(nafo_div[div]['lon'], nafo_div[div]['lat'])
        m.plot(div_lon, div_lat, 'k', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), div, fontsize=12, color='black', fontweight='bold')
    for idx, key in enumerate(mpas.keys()):
        coords = mpas[key]  
        poly_x = coords[:,0]
        poly_y = coords[:,1]
        div_lon, div_lat = m(poly_x, poly_y)
        m.plot(div_lon, div_lat, 'olivedrab', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), str(key), fontsize=12, color='black', fontweight='bold')    
    # Save Figure
    fig.set_size_inches(w=6, h=9)
    fig.set_dpi(300)
    outfile = 'bottom_temp_anomaly_tmp.png'
    fig.savefig(outfile)
    os.system('convert -trim ' + outfile + ' ' + outfile)
    # Save French Figure
    plt.sca(ax)
    if season=='fall':
        plt.title(u'Anomalie de température au fond - Automne ' + year )
    elif season=='spring':
        plt.title(u'Anomalie de température au fond - Printemp ' + year )
    else:
        plt.title(u'Anomalie de température au fond ' + year )
    fig.set_size_inches(w=6, h=9)
    fig.set_dpi(300)
    outfile = 'bottom_temp_anomaly_tmp_FR.png'
    fig.savefig(outfile)
    os.system('convert -trim ' + outfile + ' ' + outfile)
    plt.close('all')
    
    ## ---- Plot Temperature ---- ##
    fig, ax = plt.subplots(nrows=1, ncols=1)
    m = Basemap(ax=ax, projection='merc',lon_0=lon_0,lat_0=lat_0, llcrnrlon=lonLims[0],llcrnrlat=latLims[0],urcrnrlon=lonLims[1],urcrnrlat=latLims[1], resolution= 'i')
    #levels = np.linspace(-2, 6, 9)
    levels = np.linspace(-2, 6, 17)
    xi, yi = m(*np.meshgrid(lon_reg, lat_reg))
    c = m.contourf(xi, yi, Tbot, levels, cmap=plt.cm.RdBu_r, extend='both')
    cc = m.contour(xi, yi, -Zitp, [100, 500, 1000, 4000], colors='grey');
    plt.clabel(cc, inline=1, fontsize=10, fmt='%d')
    if season=='fall':
        plt.title('Fall Bottom Temperature ' + year)
    elif season=='spring':
        plt.title('Spring Bottom Temperature ' + year)
    else:
        plt.title('Bottom Temperature ' + year)
    m.fillcontinents(color='tan');
    m.drawparallels([40, 45, 50, 55, 60], labels=[0,0,0,0], fontsize=12, fontweight='normal');
    m.drawmeridians([-60, -55, -50, -45], labels=[0,0,0,1], fontsize=12, fontweight='normal');
    x, y = m(lons, lats)
    m.scatter(x,y, s=50, marker='.',color='k')
    cax = fig.add_axes([0.16, 0.05, 0.7, 0.025])
    #cax = plt.axes([0.85,0.15,0.04,0.7], facecolor='grey')
    cb = plt.colorbar(c, cax=cax, orientation='horizontal')
    cb.set_label(r'$\rm T(^{\circ}C)$', fontsize=12, fontweight='normal')
    for div in div_toplot:
        div_lon, div_lat = m(nafo_div[div]['lon'], nafo_div[div]['lat'])
        m.plot(div_lon, div_lat, 'k', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), div, fontsize=12, color='black', fontweight='bold')
    for idx, key in enumerate(mpas.keys()):
        coords = mpas[key]  
        poly_x = coords[:,0]
        poly_y = coords[:,1]
        div_lon, div_lat = m(poly_x, poly_y)
        m.plot(div_lon, div_lat, 'olivedrab', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), str(key), fontsize=12, color='black', fontweight='bold')
    for idx, key in enumerate(nafo_3O.keys()):
        coords = nafo_3O[key]  
        poly_x = coords[:,0]
        poly_y = coords[:,1]
        div_lon, div_lat = m(poly_x, poly_y)
        m.plot(div_lon, div_lat, 'olivedrab', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), str(key), fontsize=12, color='black', fontweight='bold')
    for idx, key in enumerate(nafo_seamounts.keys()):
        coords = nafo_seamounts[key]
        poly_x = coords[:,0]
        poly_y = coords[:,1]
        div_lon, div_lat = m(poly_x, poly_y)
        m.plot(div_lon, div_lat, 'olivedrab', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), str(key), fontsize=12, color='black', fontweight='bold')    
    for idx, key in enumerate(nafo_coral.keys()):
        coords = nafo_coral[key]  
        poly_x = coords[:,0]
        poly_y = coords[:,1]
        div_lon, div_lat = m(poly_x, poly_y)
        m.plot(div_lon, div_lat, 'olivedrab', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), str(key), fontsize=12, color='black', fontweight='bold')
                  
    # Save Figure
    fig.set_size_inches(w=6, h=9)
    fig.set_dpi(200)
    outfile = 'bottom_temp_tmp.png'
    fig.savefig(outfile)
    os.system('convert -trim ' + outfile + ' ' + outfile)
    # Save French Figure
    plt.sca(ax)
    if season=='fall':
        plt.title(u'Température au fond - Automne ' + year )
    elif season=='spring':
        plt.title(u'Température au fond - Printemp ' + year )
    else:
        plt.title(u'Température au fond ' + year )
    fig.set_size_inches(w=6, h=9)
    fig.set_dpi(300)
    outfile = 'bottom_temp_tmp_FR.png'
    fig.savefig(outfile)
    os.system('convert -trim ' + outfile + ' ' + outfile)
    plt.close('all')


    ## ---- Plot Climato ---- ##
    fig, ax = plt.subplots(nrows=1, ncols=1)
    m = Basemap(ax=ax, projection='merc',lon_0=lon_0,lat_0=lat_0, llcrnrlon=lonLims[0],llcrnrlat=latLims[0],urcrnrlon=lonLims[1],urcrnrlat=latLims[1], resolution= 'i')
    #levels = np.linspace(-2, 6, 9)
    levels = np.linspace(-2, 6, 17)
    xi, yi = m(*np.meshgrid(lon_reg, lat_reg))
    c = m.contourf(xi, yi, Tbot_climato, levels, cmap=plt.cm.RdBu_r, extend='both')
    cc = m.contour(xi, yi, -Zitp, [100, 500, 1000, 4000], colors='grey');
    plt.clabel(cc, inline=1, fontsize=10, fmt='%d')
    if season=='fall':
        plt.title('Fall Bottom Temperature Climatology')
    elif season=='spring':
        plt.title('Spring Bottom Temperature Climatology')
    else:
        plt.title('Bottom Temperature Climatology')
    m.fillcontinents(color='tan');
    m.drawparallels([40, 45, 50, 55, 60], labels=[1,0,0,0], fontsize=12, fontweight='normal');
    m.drawmeridians([-60, -55, -50, -45], labels=[0,0,0,1], fontsize=12, fontweight='normal');
    cax = fig.add_axes([0.16, 0.05, 0.7, 0.025])
    cb = plt.colorbar(c, cax=cax, orientation='horizontal')
    cb.set_label(r'$\rm T(^{\circ}C)$', fontsize=12, fontweight='normal')
    for div in div_toplot:
        div_lon, div_lat = m(nafo_div[div]['lon'], nafo_div[div]['lat'])
        m.plot(div_lon, div_lat, 'k', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), div, fontsize=12, color='black', fontweight='bold')
    for idx, key in enumerate(mpas.keys()):
        coords = mpas[key]  
        poly_x = coords[:,0]
        poly_y = coords[:,1]
        div_lon, div_lat = m(poly_x, poly_y)
        m.plot(div_lon, div_lat, 'olivedrab', linewidth=2)
        ax.text(np.mean(div_lon), np.mean(div_lat), str(key), fontsize=12, color='black', fontweight='bold')
        
    # Save Figure
    fig.set_size_inches(w=6, h=9)
    fig.set_dpi(300)
    outfile = 'bottom_temp_climato_tmp.png'
    fig.savefig(outfile)
    os.system('convert -trim ' + outfile + ' ' + outfile)
    # Save French Figure
    plt.sca(ax)
    if season=='fall':
        plt.title(u'Climatologie de température au fond - Automne ' + year )
    elif season=='spring':
        plt.title(u'Climatologie de température au fond - Printemp ' + year )
    else:
        plt.title(u'Climatologie de température au fond ' + year )
    fig.set_size_inches(w=6, h=9)
    fig.set_dpi(300)
    outfile = 'bottom_temp_climato_tmp_FR.png'
    fig.savefig(outfile)
    os.system('convert -trim ' + outfile + ' ' + outfile)
    plt.close('all')


    # Convert to a subplot
    os.system('montage bottom_temp_climato_tmp.png bottom_temp_tmp.png bottom_temp_anomaly_tmp.png  -tile 3x1 -geometry +10+10  -background white  bottomT_' + closure_scenario + '_' + season + year + '.png') 
    # in French
    os.system('montage bottom_temp_climato_tmp_FR.png bottom_temp_tmp_FR.png bottom_temp_anomaly_tmp_FR.png  -tile 3x1 -geometry +10+10  -background white  bottomT_' + closure_scenario + '_' + season + year + '_FR.png') 
    # Remove temporary files
    os.system('rm bottom_temp_climato_tmp.png bottom_temp_tmp.png bottom_temp_anomaly_tmp.png')
    os.system('rm bottom_temp_climato_tmp_FR.png bottom_temp_tmp_FR.png bottom_temp_anomaly_tmp_FR.png')


#### get_bottomT (originally from azmp_utils)
def get_bottomT(year_file, season, climato_file, nafo_mask=True, lab_mask=True, closure_scenario = 'reference'):
    """ Generate and returns bottom temperature data corresponding to a certain climatology map
    (previously generated with get_bottomT_climato)
    Function returns:
    - Tbot:  gridded bottom temperature
    - lons, lats: coordinates of good casts used to generate the grid
    *Note: they are not regular coordinates of the grid that can be obtained with get_bottomT_climato
       
    Usage ex (suppose climato file already exist):
    import azmp_utils as azu
    climato_file = 'Tbot_climato_spring_0.25.h5'
    year_file = '/home/cyrf0006/data/dev_database/2017.nc'
    h5f = h5py.File(climato_file, 'r')
    Tbot_climato = h5f['Tbot'][:]
    lon_reg = h5f['lon_reg'][:]
    lat_reg = h5f['lat_reg'][:]
    Zitp = h5f['Zitp'][:]
    h5f.close()
    Tbot_dict = azu.get_bottomT(year_file, 'fall', climato_file)

      Dec. 2018: Added a flag for masking or not.

    """
    ## ---- Load Climato data ---- ##    
    print('Load ' + climato_file)
    h5f = h5py.File(climato_file, 'r')
    Tbot_climato = h5f['Tbot'][:]
    lon_reg = h5f['lon_reg'][:]
    lat_reg = h5f['lat_reg'][:]
    Zitp = h5f['Zitp'][:]
    z = h5f['z'][:]
    h5f.close()
    zmax = z.max()
    dz = z[1]-z[0]
    
    ## ---- Derive some parameters ---- ##    
    lon_0 = np.round(np.mean(lon_reg))
    lat_0 = np.round(np.mean(lat_reg))
    lonLims = [lon_reg[0], lon_reg[-1]]
    latLims = [lat_reg[0], lat_reg[-1]]
    lon_grid, lat_grid = np.meshgrid(lon_reg,lat_reg)
    dc = np.diff(lon_reg[0:2])
    
    ## ---- NAFO divisions ---- ##
    nafo_div = azu.get_nafo_divisions()

    ## ---- get closures ---- ##
    mpas = get_closures()
    nafo_3O = get_closures(name='nafo_3O') # group A
    nafo_seamounts = get_closures(name='nafo_seamounts') # group A
    nafo_coral = get_closures(name='nafo_coral') # group A
    
    ## ---- Get CTD data --- ##
    print('Get ' + year_file)
    ds = xr.open_dataset(year_file)
    # Selection of a subset region
    ds = ds.where((ds.longitude>lonLims[0]) & (ds.longitude<lonLims[1]), drop=True)
    ds = ds.where((ds.latitude>latLims[0]) & (ds.latitude<latLims[1]), drop=True)
    # Remome problematic datasets
    print('!!Remove MEDBA data!!')
    print('  ---> I Should be improme because I remove good data!!!!')
    ds = ds.where(ds.instrument_ID!='MEDBA', drop=True)        
    ds = ds.where(ds.instrument_ID!='MEDTE', drop=True)
    # Select time (save several options here)
    if season == 'summer':
        ds = ds.sel(time=((ds['time.month']>=7)) & ((ds['time.month']<=9)))
    elif season == 'spring':
        ds = ds.sel(time=((ds['time.month']>=4)) & ((ds['time.month']<=6)))
    elif season == 'fall':
        ds = ds.sel(time=((ds['time.month']>=9)) & ((ds['time.month']<=12)))
    else:
        print('!! no season specified, used them all! !!')

    # Restrict max depth to zmax defined earlier
    ds = ds.sel(level=ds['level']<zmax)
    # Remove duplicates
    X,index = np.unique(ds['time'], return_index=True)
    ds = ds.isel(time=index)
    # Vertical binning (on dataArray; more appropriate here
    da_temp = ds['temperature']
    lons = np.array(ds.longitude)
    lats = np.array(ds.latitude)
    bins = np.arange(dz/2.0, ds.level.max(), dz)
    da_temp = da_temp.groupby_bins('level', bins).mean(dim='level')
    # Get comments
    da_comments = ds['comments']
    df_comments = da_comments.to_pandas()
    df_comments = df_comments.str.lower() # only lower case!
    #To Pandas Dataframe
    df_temp = da_temp.to_pandas()
    df_temp.columns = bins[0:-1] #rename columns with 'bins'
    # Remove empty columns
    idx_empty_rows = df_temp.isnull().all(1).nonzero()[0]
    df_temp = df_temp.dropna(axis=0,how='all')
    lons = np.delete(lons,idx_empty_rows)
    lats = np.delete(lats,idx_empty_rows)
    #df_temp.to_pickle('T_2000-2017.pkl')
    del ds, da_temp
    print(' -> Done!')

    ## ---- Real difference to traditional bottom_temp. ----#
    print('Apply masks for closures scenario: ' + closure_scenario)
    # DFO closures
    polygon5 = Polygon(zip(mpas[5][:,0], mpas[5][:,1]))
    polygon6 = Polygon(zip(mpas[6][:,0], mpas[6][:,1]))
    polygon7 = Polygon(zip(mpas[7][:,0], mpas[7][:,1]))
    polygon35 = Polygon(zip(mpas[35][:,0], mpas[35][:,1]))
    polygon15 = Polygon(zip(mpas[15][:,0], mpas[15][:,1]))
    polygon9 = Polygon(zip(mpas[9][:,0], mpas[9][:,1]))
    polygon14 = Polygon(zip(mpas[14][:,0], mpas[14][:,1]))
    # NAFO 3O
    polygon_n3O = Polygon(zip(nafo_3O[0][:,0], nafo_3O[0][:,1]))
    # NAFO seamounts
    polygon_ns1 = Polygon(zip(nafo_seamounts[1][:,0], nafo_seamounts[1][:,1]))
    polygon_ns2 = Polygon(zip(nafo_seamounts[2][:,0], nafo_seamounts[2][:,1]))
    polygon_ns3 = Polygon(zip(nafo_seamounts[3][:,0], nafo_seamounts[3][:,1]))
    polygon_ns4 = Polygon(zip(nafo_seamounts[4][:,0], nafo_seamounts[4][:,1]))
    polygon_ns5 = Polygon(zip(nafo_seamounts[5][:,0], nafo_seamounts[5][:,1]))
    polygon_ns6 = Polygon(zip(nafo_seamounts[6][:,0], nafo_seamounts[6][:,1]))
    # NAFO Coral and Sponges
    polygon_nc1 = Polygon(zip(nafo_coral[1][:,0], nafo_coral[1][:,1]))
    polygon_nc2 = Polygon(zip(nafo_coral[2][:,0], nafo_coral[2][:,1]))
    polygon_nc3 = Polygon(zip(nafo_coral[3][:,0], nafo_coral[3][:,1]))
    polygon_nc4 = Polygon(zip(nafo_coral[4][:,0], nafo_coral[4][:,1]))
    polygon_nc5 = Polygon(zip(nafo_coral[5][:,0], nafo_coral[5][:,1]))
    polygon_nc6 = Polygon(zip(nafo_coral[6][:,0], nafo_coral[6][:,1]))
    polygon_nc7 = Polygon(zip(nafo_coral[7][:,0], nafo_coral[1][:,1]))
    polygon_nc8 = Polygon(zip(nafo_coral[8][:,0], nafo_coral[1][:,1]))
    polygon_nc9 = Polygon(zip(nafo_coral[9][:,0], nafo_coral[1][:,1]))
    polygon_nc10 = Polygon(zip(nafo_coral[10][:,0], nafo_coral[1][:,1]))
    polygon_nc11 = Polygon(zip(nafo_coral[11][:,0], nafo_coral[1][:,1]))
    polygon_nc12 = Polygon(zip(nafo_coral[12][:,0], nafo_coral[1][:,1]))
    polygon_nc13 = Polygon(zip(nafo_coral[13][:,0], nafo_coral[1][:,1]))

    # Now remove the sets in closures, except if reference scenario
    if closure_scenario == 'reference':
        print(' -> Reference scenario, nothing to remove.')
        
    else:
        idx_toremove = []
        for i, lat in enumerate(lats):
            if (df_comments[i] == '') | (('set' in df_comments[i]) | ('unsucces' in df_comments[i])):
                # check if string "set" or "unsucces" is there or comments is empty

                point = Point(lons[i], lats[i])
                if closure_scenario == '1': # Remove A only
                    if polygon5.contains(point) | polygon6.contains(point) | polygon7.contains(point) | polygon35.contains(point) | polygon_ns1.contains(point) | polygon_ns2.contains(point) |  polygon_ns3.contains(point) | polygon_ns4.contains(point) | polygon_ns5.contains(point) | polygon_ns6.contains(point) | polygon_nc1.contains(point) | polygon_nc2.contains(point) | polygon_nc3.contains(point) | polygon_nc4.contains(point) | polygon_nc5.contains(point) | polygon_nc6.contains(point) | polygon_nc7.contains(point) | polygon_nc8.contains(point) | polygon_nc9.contains(point) | polygon_nc10.contains(point) | polygon_nc11.contains(point) | polygon_nc12.contains(point) | polygon_nc13.contains(point):

                        idx_toremove.append(i)

                elif closure_scenario == '2': # Remove B only
                    if polygon15.contains(point):

                        idx_toremove.append(i)

                elif closure_scenario == '3': # Remove A & B
                    if polygon5.contains(point) | polygon6.contains(point) | polygon7.contains(point) | polygon35.contains(point) |  polygon_ns1.contains(point) | polygon_ns2.contains(point) |  polygon_ns3.contains(point) | polygon_ns4.contains(point) | polygon_ns5.contains(point) | polygon_ns6.contains(point) | polygon_nc1.contains(point) | polygon_nc2.contains(point) | polygon_nc3.contains(point) | polygon_nc4.contains(point) | polygon_nc5.contains(point) | polygon_nc6.contains(point) | polygon_nc7.contains(point) | polygon_nc8.contains(point) | polygon_nc9.contains(point) | polygon_nc10.contains(point) | polygon_nc11.contains(point) | polygon_nc12.contains(point) | polygon_nc13.contains(point) | polygon15.contains(point):

                        idx_toremove.append(i)

                elif closure_scenario == '4': # Remove A, B & C
                    if polygon5.contains(point) | polygon6.contains(point) | polygon7.contains(point) | polygon35.contains(point) | polygon_ns1.contains(point) | polygon_ns2.contains(point) |  polygon_ns3.contains(point) | polygon_ns4.contains(point) | polygon_ns5.contains(point) | polygon_ns6.contains(point) | polygon_nc1.contains(point) | polygon_nc2.contains(point) | polygon_nc3.contains(point) | polygon_nc4.contains(point) | polygon_nc5.contains(point) | polygon_nc6.contains(point) | polygon_nc7.contains(point) | polygon_nc8.contains(point) | polygon_nc9.contains(point) | polygon_nc10.contains(point) | polygon_nc11.contains(point) | polygon_nc12.contains(point) | polygon_nc13.contains(point) | polygon15.contains(point) | polygon9.contains(point) | polygon14.contains(point) :

                        idx_toremove.append(i)

        # Drop now
        df_temp.drop(df_temp.index[idx_toremove], inplace=True) 
        lons = np.delete(lons,idx_toremove)
        lats = np.delete(lats,idx_toremove)
    
    ## --- fill 3D cube --- ##  
    print('Fill regular cube')
    z = df_temp.columns.values
    V = np.full((lat_reg.size, lon_reg.size, z.size), np.nan)

    # Aggregate on regular grid
    for i, xx in enumerate(lon_reg):
        for j, yy in enumerate(lat_reg):    
            idx = np.where((lons>=xx-dc/2) & (lons<xx+dc/2) & (lats>=yy-dc/2) & (lats<yy+dc/2))
            tmp = np.array(df_temp.iloc[idx].mean(axis=0))
            idx_good = np.argwhere((~np.isnan(tmp)) & (tmp<30))
            if np.size(idx_good)==1:
                V[j,i,:] = np.array(df_temp.iloc[idx].mean(axis=0))
            elif np.size(idx_good)>1: # vertical interpolation between pts
                interp = interp1d(np.squeeze(z[idx_good]), np.squeeze(tmp[idx_good]))
                idx_interp = np.arange(np.int(idx_good[0]),np.int(idx_good[-1]+1))
                V[j,i,idx_interp] = interp(z[idx_interp]) # interpolate only where possible
    
    # horizontal interpolation at each depth
    lon_grid, lat_grid = np.meshgrid(lon_reg,lat_reg)
    lon_vec = np.reshape(lon_grid, lon_grid.size)
    lat_vec = np.reshape(lat_grid, lat_grid.size)
    for k, zz in enumerate(z):
        # Meshgrid 1D data (after removing NaNs)
        tmp_grid = V[:,:,k]
        tmp_vec = np.reshape(tmp_grid, tmp_grid.size)
        # griddata (after removing nans)
        idx_good = np.argwhere(~np.isnan(tmp_vec))
        if idx_good.size>5: # will ignore depth where no data exist
            LN = np.squeeze(lon_vec[idx_good])
            LT = np.squeeze(lat_vec[idx_good])
            TT = np.squeeze(tmp_vec[idx_good])
            zi = griddata((LN, LT), TT, (lon_grid, lat_grid), method='linear')
            V[:,:,k] = zi
        else:
            continue
    print(' -> Done!')    

    # mask using bathymetry (I don't think it is necessary, but make nice figures)
    for i, xx in enumerate(lon_reg):
        for j,yy in enumerate(lat_reg):
            if Zitp[j,i] > -10: # remove shallower than 10m
                V[j,i,:] = np.nan

    # getting bottom temperature
    print('Getting bottom Temp.')    
    Tbot = np.full([lat_reg.size,lon_reg.size], np.nan) 
    for i, xx in enumerate(lon_reg):
        for j,yy in enumerate(lat_reg):
            bottom_depth = -Zitp[j,i] # minus to turn positive
            temp_vec = V[j,i,:]
            ## idx_no_good = np.argwhere(temp_vec>30)
            ## if idx_no_good.size:
            ##     temp_vec[idx_no_good] = np.nan
            idx_good = np.squeeze(np.where(~np.isnan(temp_vec)))
            if idx_good.size>1:
                idx_closest = np.argmin(np.abs(bottom_depth-z[idx_good]))
            else:
                continue

            if np.abs([idx_closest] - bottom_depth) <= 20:
                Tbot[j,i] = temp_vec[idx_good[idx_closest]]
            elif np.abs(z[idx_closest] - bottom_depth) <= 50:
                #print('used data located [30,50]m from bottom')
                Tbot[j,i] = temp_vec[idx_good[idx_closest]]

    print(' -> Done!')

    # Mask data on coastal Labrador
    if lab_mask == True:
        print('Mask coastal labrador')
        contour_mask = np.load('/home/cyrf0006/AZMP/state_reports/bottomT/100m_contour_labrador.npy')
        polygon_mask = Polygon(contour_mask)
        for i, xx in enumerate(lon_reg):
            for j,yy in enumerate(lat_reg):
                point = Point(lon_reg[i], lat_reg[j])
                if polygon_mask.contains(point): # mask data near Labrador in fall
                    Tbot[j,i] = np.nan 

    if nafo_mask == True:
        # Mask data outside Nafo div.
        print('Mask according to NAFO division for ' + season)
        # Polygons
        polygon3K = Polygon(zip(nafo_div['3K']['lon'], nafo_div['3K']['lat']))
        polygon3L = Polygon(zip(nafo_div['3L']['lon'], nafo_div['3L']['lat']))
        polygon3N = Polygon(zip(nafo_div['3N']['lon'], nafo_div['3N']['lat']))
        polygon3O = Polygon(zip(nafo_div['3O']['lon'], nafo_div['3O']['lat']))
        polygon3Ps = Polygon(zip(nafo_div['3Ps']['lon'], nafo_div['3Ps']['lat']))
        polygon2J = Polygon(zip(nafo_div['2J']['lon'], nafo_div['2J']['lat']))

        if season == 'spring':
            for i, xx in enumerate(lon_reg):
                for j,yy in enumerate(lat_reg):
                    point = Point(lon_reg[i], lat_reg[j])
                    if polygon3L.contains(point) | polygon3N.contains(point) | polygon3O.contains(point) | polygon3Ps.contains(point):
                        pass #nothing to do
                    else:
                        Tbot[j,i] = np.nan

        elif season == 'fall':
            for i, xx in enumerate(lon_reg):
                for j,yy in enumerate(lat_reg):
                    point = Point(lon_reg[i], lat_reg[j])
                    if polygon2J.contains(point) | polygon3K.contains(point) | polygon3L.contains(point) | polygon3N.contains(point) | polygon3O.contains(point) | polygon3Ps.contains(point):
                        pass #nothing to do 
                    else:
                        pass

        else:
            print('no division mask, all data taken')
    else:
            print('no division mask, all data taken')

    print(' -> Done!')    

    # Fill dict for output
    dict = {}
    dict['Tbot'] = Tbot
    dict['bathy'] = Zitp
    dict['lon_reg'] = lon_reg
    dict['lat_reg'] = lat_reg
    dict['lons'] = lons
    dict['lats'] = lats
    
    return dict


#### bottom_stats
def bottom_stats(years, season, proj='merc', plot=False, netcdf_path='/home/cyrf0006/data/dev_database/netCDF/', climato_file='', closure_scenario = 'reference'):

    '''
        Function bottom_stats() based on script azmp_bottom_stats.py

        See the latter on how to generate the bottom climatology.
        See it also for specific usage such as Plaice - COSEWIC analysis.

        usage example:
        >> import azmp_report_tools as azrt
        >> import numpy as np
        >> azrt.bottom_stats(years=np.arange(1980, 2020), season='fall')

        *** This needs to be improve because at the moment I need to comment the generation of .pkl file to not over-write when I change my map region.        
                
        For NAFO SA4:
        >> azrt.bottom_stats(years=np.arange(1980, 2020), season='summer', climato_file='Tbot_climato_SA4_summer_0.10.h5')
        
        For COSEWIC:
        >> azrt.bottom_stats(years=np.arange(1980, 2020), season='summer', climato_file='Tbot_climato_2GH_summer_0.10.h5')
        >> azrt.bottom_stats(years=np.arange(1980, 2020), season='summer', climato_file='Tbot_climato_SA45_summer_0.10.h5')

        
        Frederic.Cyr@dfo-mpo.gc.ca - January 2020
    '''

    # load climato
    if len(climato_file) == 0: # climato not provided (default)
        if season == 'fall':
            climato_file = '/home/cyrf0006/AZMP/state_reports/bottomT/Tbot_climato_fall_0.10.h5'
        elif season == 'spring':
            climato_file = '/home/cyrf0006/AZMP/state_reports/bottomT/Tbot_climato_spring_0.10.h5'
        elif season == 'summer':
            climato_file = '/home/cyrf0006/AZMP/state_reports/bottomT/Tbot_climato_summer_0.10.h5'
    else:
        print('Climato file provided')
               
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
    shape_3M = Polygon(zip(nafo_div['3M']['lon'], nafo_div['3M']['lat']))
    shape_3Ps = Polygon(zip(nafo_div['3Ps']['lon'], nafo_div['3Ps']['lat']))
    shape_2G = Polygon(zip(nafo_div['2G']['lon'], nafo_div['2G']['lat']))
    shape_2H = Polygon(zip(nafo_div['2H']['lon'], nafo_div['2H']['lat']))
    shape_2J = Polygon(zip(nafo_div['2J']['lon'], nafo_div['2J']['lat']))
    shape_3K = Polygon(zip(nafo_div['3K']['lon'], nafo_div['3K']['lat']))
    shape_3L = Polygon(zip(nafo_div['3L']['lon'], nafo_div['3L']['lat']))
    shape_3O = Polygon(zip(nafo_div['3O']['lon'], nafo_div['3O']['lat']))
    shape = [shape_2J, shape_2H]
    shape_2HJ = cascaded_union(shape)
    shape = [shape_2G, shape_2H]
    shape_2GH = cascaded_union(shape)

    dict_stats_3LNO = {}
    dict_stats_3M = {}
    dict_stats_3Ps = {}
    dict_stats_3K = {}
    dict_stats_3L = {}
    dict_stats_3O = {}
    dict_stats_2G = {}
    dict_stats_2H = {}
    dict_stats_2J = {}
    dict_stats_2HJ = {}
    dict_stats_2GH = {}

    # Loop on years
    df_list = []
    for year in years:
        print(' ---- ' + np.str(year) + ' ---- ')
        year_file = netcdf_path + np.str(year) + '.nc'
        Tdict = get_bottomT(year_file, season, climato_file, closure_scenario=closure_scenario)    
        Tbot = Tdict['Tbot']
        lons = Tdict['lons']
        lats = Tdict['lats']
        anom = Tbot-Tbot_climato

        # NAFO division stats    
        dict_stats_2GH[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_2GH)
        dict_stats_2G[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_2G)
        dict_stats_2H[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_2H)
        dict_stats_2J[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_2J)
        dict_stats_2HJ[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_2HJ)
        dict_stats_3LNO[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3LNO)
        dict_stats_3M[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3M)
        dict_stats_3Ps[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3Ps)
        dict_stats_3K[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3K)
        dict_stats_3L[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3L)
        dict_stats_3O[np.str(year)] = azu.polygon_temperature_stats(Tdict, shape_3O)

        # Append bottom temperature for multi-index export
        df = pd.DataFrame(index=lat_reg, columns=lon_reg)
        df.index.name='latitude'
        df.columns.name='longitude'
        df[:] = Tbot
        df_list.append(df)

        if plot:
            div_toplot = ['2H', '2J', '3K', '3L', '3N', '3O', '3Ps', '4R', '4Vn', '4Vs', '4W', '4X']
    
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
            for div in div_toplot:
                div_lon, div_lat = m(nafo_div[div]['lon'], nafo_div[div]['lat'])
                m.plot(div_lon, div_lat, 'k', linewidth=2)
                ax.text(np.mean(div_lon), np.mean(div_lat), div, fontsize=12, color='black', fontweight='bold')
            # Save Figure
            fig.set_size_inches(w=7, h=8)
            fig.set_dpi(200)
            outfile = 'bottom_temp_' + season + '_' + np.str(year) + '.png'
            fig.savefig(outfile)
            plt.close('all')

    df_2G = pd.DataFrame.from_dict(dict_stats_2G, orient='index')
    df_2H = pd.DataFrame.from_dict(dict_stats_2H, orient='index')
    df_2J = pd.DataFrame.from_dict(dict_stats_2J, orient='index')
    df_2HJ = pd.DataFrame.from_dict(dict_stats_2HJ, orient='index')
    df_2GH = pd.DataFrame.from_dict(dict_stats_2GH, orient='index')
    df_3Ps = pd.DataFrame.from_dict(dict_stats_3Ps, orient='index')
    df_3LNO = pd.DataFrame.from_dict(dict_stats_3LNO, orient='index')
    df_3M = pd.DataFrame.from_dict(dict_stats_3M, orient='index')
    df_3K = pd.DataFrame.from_dict(dict_stats_3K, orient='index')
    df_3L = pd.DataFrame.from_dict(dict_stats_3L, orient='index')
    df_3O = pd.DataFrame.from_dict(dict_stats_3O, orient='index')

    outname = 'stats_3Ps_' + season + '_' + closure_scenario + '.pkl'
    df_3Ps.to_pickle(outname)
    outname = 'stats_3LNO_' + season + '_' + closure_scenario + '.pkl'
    df_3LNO.to_pickle(outname)
    outname = 'stats_3M_' + season + '_' + closure_scenario + '.pkl'
    df_3M.to_pickle(outname)
    outname = 'stats_3K_' + season + '_' + closure_scenario + '.pkl'
    df_3K.to_pickle(outname)
    outname = 'stats_3L_' + season + '_' + closure_scenario + '.pkl'
    df_3L.to_pickle(outname)
    outname = 'stats_3O_' + season + '_' + closure_scenario + '.pkl'
    df_3O.to_pickle(outname)
    outname = 'stats_2G_' + season + '_' + closure_scenario + '.pkl'
    df_2G.to_pickle(outname)
    outname = 'stats_2H_' + season + '_' + closure_scenario + '.pkl'
    df_2H.to_pickle(outname)
    outname = 'stats_2J_' + season + '_' + closure_scenario + '.pkl'
    df_2J.to_pickle(outname)
    outname = 'stats_2HJ_' + season + '_' + closure_scenario + '.pkl'
    df_2HJ.to_pickle(outname)
    outname = 'stats_2GH_' + season + '_' + closure_scenario + '.pkl'
    df_2GH.to_pickle(outname)

    # Save in multi-index  dataFrame
    year_index = pd.Series(years)
    year_index.name='year'
    df_mindex = pd.concat(df_list,keys=year_index)
    df_mindex.to_pickle(season + '_bottom_temperature_scenario_' + closure_scenario + '.pkl')


def bottom_scorecards(years, clim_year=[1981, 2010]):

    '''
    To generate scorecards of differences in standardized anomalies after removing observations from closures.

    '''

    #### ------------- For fall ---------------- ####
    # 0. - 2H -
    infile0 = 'stats_2H_fall_reference.pkl'
    infile1 = 'stats_2H_fall_1.pkl'
    infile2 = 'stats_2H_fall_2.pkl'
    infile3 = 'stats_2H_fall_3.pkl'
    infile4 = 'stats_2H_fall_4.pkl'

    df0 = pd.read_pickle(infile0).Tmean    
    df1 = pd.read_pickle(infile1).Tmean
    df2 = pd.read_pickle(infile2).Tmean
    df3 = pd.read_pickle(infile3).Tmean
    df4 = pd.read_pickle(infile4).Tmean
    
    df = pd.concat([df0, df1, df2, df3, df4], axis=1, keys=['sc0', 'sc1', 'sc2', 'sc3', 'sc4'])
    df.index = pd.to_datetime(df.index) # update index to datetime
    df = df[(df.index.year>=years[0]) & (df.index.year<=years[-1])]
    df = df.round(1)

    # remove scenarios that are not relevant:
    df[['sc2']] = df[['sc2']]*np.nan
    df[['sc3']] = df[['sc3']]*np.nan
    df[['sc4']] = df[['sc4']]*np.nan

    # Flag bad years (no or weak sampling):
    bad_years = np.array([1980, 1982, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1992, 1993, 1994, 1995, 1996, 2000, 2002, 2003, 2005, 2007, 2009])
    for i in bad_years:
        df[df.index.year==i]=np.nan

    # get year list (only for first scorecards) 
    year_list = df.index.year.astype('str')
    year_list = [i[2:4] for i in year_list] # 2-digit year

    # Calculate std anomalies
    df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
    std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
    std_anom = std_anom.T
        
    # Add 4 rows for % change by case
    std_anom.loc['sc1p'] = (df['sc1'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc2p'] = (df['sc2'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc3p'] = (df['sc3'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc4p'] = (df['sc4'] - df['sc0']) / df['sc0'] * 100
    # add mean and std inm both DataFrames
    std_anom['MEAN'] = df_clim.mean(axis=0)
    std_anom['SD'] = df_clim.std(axis=0)
    
    # Now by-pass std_anom with bottom T values (keep colors according to std anom)
    temperatures = std_anom.copy()
    temperatures.loc['sc0'] = df['sc0']
    temperatures.loc['sc1'] = df['sc1']
    temperatures.loc['sc2'] = df['sc2']
    temperatures.loc['sc3'] = df['sc3']
    temperatures.loc['sc4'] = df['sc4']
    # add mean and std inm both DataFrames
    temperatures['MEAN'] = df_clim.mean(axis=0)
    temperatures['SD'] = df_clim.std(axis=0)
    sd1 = (temperatures.loc['sc1p']).std()
    sd2 = (temperatures.loc['sc2p']).std()
    sd3 = (temperatures.loc['sc3p']).std()
    sd4 = (temperatures.loc['sc4p']).std()    
    temperatures.loc['sc1p']['MEAN'] = np.abs(temperatures.loc['sc1p']).mean()
    temperatures.loc['sc2p']['MEAN'] = np.abs(temperatures.loc['sc2p']).mean()
    temperatures.loc['sc3p']['MEAN'] = np.abs(temperatures.loc['sc3p']).mean()
    temperatures.loc['sc4p']['MEAN'] = np.abs(temperatures.loc['sc4p']).mean()
    temperatures.loc['sc1p']['SD'] = sd1
    temperatures.loc['sc2p']['SD'] = sd2
    temperatures.loc['sc3p']['SD'] = sd3
    temperatures.loc['sc4p']['SD'] = sd4
    # Rename columns
    std_anom.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    temperatures.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    # Rename index
    std_anom = std_anom.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    temperatures = temperatures.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    
    # Get text values +  cell color
    year_list.append(r'$\rm \overline{x}$') # add 2 extra columns
    year_list.append(r'sd')   
    vals = np.around(temperatures.values,1)
    vals[vals==-0.] = 0.
    vals_color = np.around(std_anom.values,1)
    vals_color[vals_color==-0.] = 0.    
    vals_color[-1,] = vals_color[-1,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[-2,] = vals_color[-2,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-3,] = vals_color[-3,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-4,] = vals_color[-4,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[:,-1] = 0 # No color to last two columns (mean and STD)
    vals_color[:,-2] = 0

    # Build the colormap (only for 1st scorecard)
    vmin = -3.49
    vmax = 3.49
    midpoint = 0
    levels = np.linspace(vmin, vmax, 15)
    midp = np.mean(np.c_[levels[:-1], levels[1:]], axis=1)
    colvals = np.interp(midp, [vmin, midpoint, vmax], [-1, 0., 1])
    normal = plt.Normalize(-3.49, 3.49)
    reds = plt.cm.Reds(np.linspace(0,1, num=7))
    blues = plt.cm.Blues_r(np.linspace(0,1, num=7))
    whites = [(1,1,1,1)]*2
    colors = np.vstack((blues[0:-1,:], whites, reds[1:,:]))
    colors = np.concatenate([[colors[0,:]], colors, [colors[-1,:]]], 0)
    cmap, norm = from_levels_and_colors(levels, colors, extend='both')
    cmap_r, norm_r = from_levels_and_colors(levels, np.flipud(colors), extend='both')

    nrows, ncols = temperatures.index.size+1, temperatures.columns.size
    hcell, wcell = 0.5, 0.6
    hpad, wpad = 1, 1    
    fig=plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
    ax = fig.add_subplot(111)
    ax.axis('off')
    #do the table
    header = ax.table(cellText=[['']],
                          colLabels=['-- NAFO division 2H --'],
                          loc='center'
                          )
    header.set_fontsize(13)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=year_list,
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1, 0.5]
                        )
    # change font color to white where needed:
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        elif key[0] == 0: #year's row = no color
            pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')
        elif key[1] in last_columns:
            cell._text.set_color('dimgray')
            cell._text.set_weight('bold')
        elif (key[0] < 6) & ((vals_color[key[0]-1, key[1]]  <= -1.5) | (vals_color[key[0]-1, key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 6:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_fall_2H.png", dpi=300)
    os.system('convert -trim scorecards_fall_2H.png scorecards_fall_2H.png')

    # French table
    temperatures = temperatures.rename({r'$\rm T_{bot}~(^{\circ}C)~-~Reference$' :
                                        r'$\rm T_{fond}~(^{\circ}C)~-~Référence$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~A$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~B$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~AB$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~ABC$',
                                        r'Sc. A (% change)' :
                                        r' Sc. A (% changem.)',
                                        r'Sc. B (% change)' :
                                        r' Sc. B (% changem.)',
                                        r'Sc. AB (% change)' :
                                        r' Sc. AB (% changem.)',
                                        r'Sc. ABC (% change)' :
                                        r' Sc. ABC (% changem.)'})
       
    year_list[-1] = u'ET'
    
    header = ax.table(cellText=[['']],
                          colLabels=['-- Division 2H de l\'OPANO --'],
                          loc='center'
                          )
    header.set_fontsize(13)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=year_list,
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1, 0.5]
                        )
    # change font color to white where needed:
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        elif key[0] == 0: #year's row = no color
            pass
        elif key[1] in last_columns:
            cell._text.set_color('dimgray')
            cell._text.set_weight('bold')
            if (cell_text=='nan'):
                cell._set_facecolor('dimgray')
        elif (key[0] < 6) & ((vals_color[key[0]-1, key[1]]  <= -1.5) | (vals_color[key[0]-1, key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')   
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')
        # Bold face % change
        if key[0] >= 6:
            cell._text.set_weight('bold')

    plt.savefig("scorecards_fall_2H_FR.png", dpi=300)
    os.system('convert -trim scorecards_fall_2H_FR.png scorecards_fall_2H_FR.png')

 ## #  1. - 2J -
 ##    infile0 = 'stats_2J_fall_reference.pkl'
 ##    infile1 = 'stats_2J_fall_1.pkl'
 ##    infile2 = 'stats_2J_fall_2.pkl'
 ##    infile3 = 'stats_2J_fall_3.pkl'
 ##    infile4 = 'stats_2J_fall_4.pkl'

 ##    df0 = pd.read_pickle(infile0).Tmean    
 ##    df1 = pd.read_pickle(infile1).Tmean
 ##    df2 = pd.read_pickle(infile2).Tmean
 ##    df3 = pd.read_pickle(infile3).Tmean
 ##    df4 = pd.read_pickle(infile4).Tmean
    
 ##    df = pd.concat([df0, df1, df2, df3, df4], axis=1, keys=['sc0', 'sc1', 'sc2', 'sc3', 'sc4'])
 ##    df.index = pd.to_datetime(df.index) # update index to datetime
 ##    df = df[(df.index.year>=years[0]) & (df.index.year<=years[-1])]
 ##    df = df.round(1)

 ##    # remove scenarios that are not relevant:
 ##    df[['sc2']] = df[['sc2']]*np.nan
 ##    df[['sc3']] = df[['sc3']]*np.nan
 ##    #df = df.drop(['sc2', 'sc3'], axis=1)

 ##    # Flag bad years (no or weak sampling):
 ##    bad_years = np.array([1980, 1982, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1992, 1993, 1994, 1995, 1996, 2000, 2002, 2003, 2005, 2007, 2009])
 ##    for i in bad_years:
 ##        df[df.index.year==i]=np.nan

 ##    # get year list (only for first scorecards) 
 ##    year_list = df.index.year.astype('str')
 ##    year_list = [i[2:4] for i in year_list] # 2-digit year

 ##    # Calculate std anomalies
 ##    df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
 ##    std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
 ##    std_anom = std_anom.T
        
 ##    # Add 4 rows for % change by case
 ##    std_anom.loc['sc1p'] = (df['sc1'] - df['sc0']) / df['sc0'] * 100
 ##    std_anom.loc['sc2p'] = (df['sc2'] - df['sc0']) / df['sc0'] * 100
 ##    std_anom.loc['sc3p'] = (df['sc3'] - df['sc0']) / df['sc0'] * 100
 ##    std_anom.loc['sc4p'] = (df['sc4'] - df['sc0']) / df['sc0'] * 100
 ##    # add mean and std inm both DataFrames
 ##    std_anom['MEAN'] = df_clim.mean(axis=0)
 ##    std_anom['SD'] = df_clim.std(axis=0)
    
 ##    # Now by-pass std_anom with bottom T values (keep colors according to std anom)
 ##    temperatures = std_anom.copy()
 ##    temperatures.loc['sc0'] = df['sc0']
 ##    temperatures.loc['sc1'] = df['sc1']
 ##    temperatures.loc['sc2'] = df['sc2']
 ##    temperatures.loc['sc3'] = df['sc3']
 ##    temperatures.loc['sc4'] = df['sc4']
 ##    # add mean and std inm both DataFrames
 ##    temperatures['MEAN'] = df_clim.mean(axis=0)
 ##    temperatures['SD'] = df_clim.std(axis=0)
 ##    sd1 = (temperatures.loc['sc1p']).std()
 ##    sd2 = (temperatures.loc['sc2p']).std()
 ##    sd3 = (temperatures.loc['sc3p']).std()
 ##    sd4 = (temperatures.loc['sc4p']).std()    
 ##    temperatures.loc['sc1p']['MEAN'] = np.abs(temperatures.loc['sc1p']).mean()
 ##    temperatures.loc['sc2p']['MEAN'] = np.abs(temperatures.loc['sc2p']).mean()
 ##    temperatures.loc['sc3p']['MEAN'] = np.abs(temperatures.loc['sc3p']).mean()
 ##    temperatures.loc['sc4p']['MEAN'] = np.abs(temperatures.loc['sc4p']).mean()
 ##    temperatures.loc['sc1p']['SD'] = sd1
 ##    temperatures.loc['sc2p']['SD'] = sd2
 ##    temperatures.loc['sc3p']['SD'] = sd3
 ##    temperatures.loc['sc4p']['SD'] = sd4
 ##    # Rename columns
 ##    std_anom.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
 ##    temperatures.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
 ##    # Rename index
 ##    std_anom = std_anom.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
 ##                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
 ##                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
 ##                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
 ##                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
 ##                                 'sc1p': r'Sc. A (% change)',
 ##                                 'sc2p': r'Sc. B (% change)',
 ##                                 'sc3p': r'Sc. AB (% change)',
 ##                                 'sc4p': r'Sc. ABC (% change)'
 ##                                 })
 ##    temperatures = temperatures.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
 ##                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
 ##                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
 ##                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
 ##                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
 ##                                 'sc1p': r'Sc. A (% change)',
 ##                                 'sc2p': r'Sc. B (% change)',
 ##                                 'sc3p': r'Sc. AB (% change)',
 ##                                 'sc4p': r'Sc. ABC (% change)'
 ##                                 })
    
 ##    # Get text values +  cell color
 ##    year_list.append(r'$\rm \overline{x}$') # add 2 extra columns
 ##    year_list.append(r'sd')   
 ##    vals = np.around(temperatures.values,1)
 ##    vals[vals==-0.] = 0.
 ##    vals_color = np.around(std_anom.values,1)
 ##    vals_color[vals_color==-0.] = 0.    
 ##    vals_color[-1,] = vals_color[-1,]*.1 # scale down a factor 10 for last 4 rows
 ##    vals_color[-2,] = vals_color[-2,]*.1 # scale down a factor 10 for last 4 rows        
 ##    vals_color[-3,] = vals_color[-3,]*.1 # scale down a factor 10 for last 4 rows        
 ##    vals_color[-4,] = vals_color[-4,]*.1 # scale down a factor 10 for last 4 rows        
 ##    vals_color[:,-1] = 0 # No color to last two columns (mean and STD)
 ##    vals_color[:,-2] = 0

 ##    # Build the colormap (only for 1st scorecard)
 ##    vmin = -3.49
 ##    vmax = 3.49
 ##    midpoint = 0
 ##    levels = np.linspace(vmin, vmax, 15)
 ##    midp = np.mean(np.c_[levels[:-1], levels[1:]], axis=1)
 ##    colvals = np.interp(midp, [vmin, midpoint, vmax], [-1, 0., 1])
 ##    normal = plt.Normalize(-3.49, 3.49)
 ##    reds = plt.cm.Reds(np.linspace(0,1, num=7))
 ##    blues = plt.cm.Blues_r(np.linspace(0,1, num=7))
 ##    whites = [(1,1,1,1)]*2
 ##    colors = np.vstack((blues[0:-1,:], whites, reds[1:,:]))
 ##    colors = np.concatenate([[colors[0,:]], colors, [colors[-1,:]]], 0)
 ##    cmap, norm = from_levels_and_colors(levels, colors, extend='both')
 ##    cmap_r, norm_r = from_levels_and_colors(levels, np.flipud(colors), extend='both')

 ##    nrows, ncols = temperatures.index.size+1, temperatures.columns.size
 ##    hcell, wcell = 0.5, 0.6
 ##    hpad, wpad = 1, 1    
 ##    fig=plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
 ##    ax = fig.add_subplot(111)
 ##    ax.axis('off')
 ##    #do the table
 ##    header = ax.table(cellText=[['']],
 ##                          colLabels=['-- NAFO division 2H --'],
 ##                          loc='center'
 ##                          )
 ##    header.set_fontsize(13)
 ##    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=year_list,
 ##                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
 ##                        bbox=[0, 0, 1, 0.5]
 ##                        )
 ##    # change font color to white where needed:
 ##    the_table.auto_set_font_size(False)
 ##    the_table.set_fontsize(12.5)
 ##    table_props = the_table.properties()
 ##    table_cells = table_props['child_artists']
 ##    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
 ##    for key, cell in the_table.get_celld().items():
 ##        cell_text = cell.get_text().get_text()
 ##        if is_number(cell_text) == False:
 ##            pass
 ##        elif key[0] == 0: #year's row = no color
 ##            pass
 ##        elif (cell_text=='nan'):
 ##            cell._set_facecolor('lightgray')
 ##            cell._text.set_color('lightgray')        
 ##        elif key[1] in last_columns:
 ##            cell._text.set_color('dimgray')
 ##            cell._text.set_weight('bold')
 ##        elif (key[0] < 6) & ((vals_color[key[0]-1, key[1]]  <= -1.5) | (vals_color[key[0]-1, key[1]] >= 1.5)) :
 ##            cell._text.set_color('white')
 ##        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
 ##            cell._text.set_color('white')
 ##        # Bold face % change
 ##        if key[0] >= 6:
 ##            cell._text.set_weight('bold')
            
 ##    plt.savefig("scorecards_fall_2H.png", dpi=300)
 ##    os.system('convert -trim scorecards_fall_2H.png scorecards_fall_2H.png')

 ##    # French table
 ##    temperatures = temperatures.rename({r'$\rm T_{bot}~(^{\circ}C)~-~Reference$' :
 ##                                        r'$\rm T_{fond}~(^{\circ}C)~-~Référence$',
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$' :
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~A$',
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$' :
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~B$',
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$' :
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~AB$',
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$' :
 ##                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~ABC$',
 ##                                        r'Sc. A (% change)' :
 ##                                        r' Sc. A (% changem.)',
 ##                                        r'Sc. B (% change)' :
 ##                                        r' Sc. B (% changem.)',
 ##                                        r'Sc. AB (% change)' :
 ##                                        r' Sc. AB (% changem.)',
 ##                                        r'Sc. ABC (% change)' :
 ##                                        r' Sc. ABC (% changem.)'})
       
 ##    year_list[-1] = u'ET'
    
 ##    header = ax.table(cellText=[['']],
 ##                          colLabels=['-- Division 2H de l\'OPANO --'],
 ##                          loc='center'
 ##                          )
 ##    header.set_fontsize(13)
 ##    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=year_list,
 ##                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
 ##                        bbox=[0, 0, 1, 0.5]
 ##                        )
 ##    # change font color to white where needed:
 ##    the_table.auto_set_font_size(False)
 ##    the_table.set_fontsize(12.5)
 ##    table_props = the_table.properties()
 ##    table_cells = table_props['child_artists']
 ##    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
 ##    for key, cell in the_table.get_celld().items():
 ##        cell_text = cell.get_text().get_text()
 ##        if is_number(cell_text) == False:
 ##            pass
 ##        elif key[0] == 0: #year's row = no color
 ##            pass
 ##        elif (cell_text=='nan'):
 ##            cell._set_facecolor('lightgray')
 ##            cell._text.set_color('lightgray')        
 ##        elif key[1] in last_columns:
 ##            cell._text.set_color('dimgray')
 ##            cell._text.set_weight('bold')
 ##        elif (key[0] < 6) & ((vals_color[key[0]-1, key[1]]  <= -1.5) | (vals_color[key[0]-1, key[1]] >= 1.5)) :
 ##            cell._text.set_color('white')
 ##        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
 ##            cell._text.set_color('white')   
 ##        # Bold face % change
 ##        if key[0] >= 6:
 ##            cell._text.set_weight('bold')

 ##    plt.savefig("scorecards_fall_2H_FR.png", dpi=300)
 ##    os.system('convert -trim scorecards_fall_2H_FR.png scorecards_fall_2H_FR.png')

 #  1. - 2J -
    infile0 = 'stats_2J_fall_reference.pkl'
    infile1 = 'stats_2J_fall_1.pkl'
    infile2 = 'stats_2J_fall_2.pkl'
    infile3 = 'stats_2J_fall_3.pkl'
    infile4 = 'stats_2J_fall_4.pkl'

    df0 = pd.read_pickle(infile0).Tmean    
    df1 = pd.read_pickle(infile1).Tmean
    df2 = pd.read_pickle(infile2).Tmean
    df3 = pd.read_pickle(infile3).Tmean
    df4 = pd.read_pickle(infile4).Tmean
    
    df = pd.concat([df0, df1, df2, df3, df4], axis=1, keys=['sc0', 'sc1', 'sc2', 'sc3', 'sc4'])
    df.index = pd.to_datetime(df.index) # update index to datetime
    df = df[(df.index.year>=years[0]) & (df.index.year<=years[-1])]
    df.round(1)

    # remove scenarios that are not relevant:
    df[['sc2']] = df[['sc2']]*np.nan
    df[['sc3']] = df[['sc3']]*np.nan
    #df = df.drop(['sc2', 'sc3'], axis=1)

    # Flag bad years (no or weak sampling):
    bad_years = np.array([1995])
    for i in bad_years:
        df[df.index.year==i]=np.nan

    # Calculate std anomalies
    df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
    std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
    std_anom = std_anom.T
        
    # Add 4 rows for % change by case
    std_anom.loc['sc1p'] = (df['sc1'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc2p'] = (df['sc2'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc3p'] = (df['sc3'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc4p'] = (df['sc4'] - df['sc0']) / df['sc0'] * 100
    # add mean and std inm both DataFrames
    std_anom['MEAN'] = df_clim.mean(axis=0)
    std_anom['SD'] = df_clim.std(axis=0)
    
    # Now by-pass std_anom with bottom T values (keep colors according to std anom)
    temperatures = std_anom.copy()
    temperatures.loc['sc0'] = df['sc0']
    temperatures.loc['sc1'] = df['sc1']
    temperatures.loc['sc2'] = df['sc2']
    temperatures.loc['sc3'] = df['sc3']
    temperatures.loc['sc4'] = df['sc4']
    # add mean and std inm both DataFrames
    temperatures['MEAN'] = df_clim.mean(axis=0)
    temperatures['SD'] = df_clim.std(axis=0)
    sd1 = (temperatures.loc['sc1p']).std()
    sd2 = (temperatures.loc['sc2p']).std()
    sd3 = (temperatures.loc['sc3p']).std()
    sd4 = (temperatures.loc['sc4p']).std()    
    temperatures.loc['sc1p']['MEAN'] = np.abs(temperatures.loc['sc1p']).mean()
    temperatures.loc['sc2p']['MEAN'] = np.abs(temperatures.loc['sc2p']).mean()
    temperatures.loc['sc3p']['MEAN'] = np.abs(temperatures.loc['sc3p']).mean()
    temperatures.loc['sc4p']['MEAN'] = np.abs(temperatures.loc['sc4p']).mean()
    temperatures.loc['sc1p']['SD'] = sd1
    temperatures.loc['sc2p']['SD'] = sd2
    temperatures.loc['sc3p']['SD'] = sd3
    temperatures.loc['sc4p']['SD'] = sd4
    # Rename columns
    std_anom.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    temperatures.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    # Rename index
    std_anom = std_anom.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    temperatures = temperatures.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    
    # Get text values +  cell color
    vals = np.around(temperatures.values,1)
    vals[vals==-0.] = 0.
    vals_color = np.around(std_anom.values,1)
    vals_color[vals_color==-0.] = 0.    
    vals_color[-1,] = vals_color[-1,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[-2,] = vals_color[-2,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-3,] = vals_color[-3,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-4,] = vals_color[-4,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[:,-1] = 0 # No color to last two columns (mean and STD)
    vals_color[:,-2] = 0

    # Start drawing
    nrows, ncols = temperatures.index.size, temperatures.columns.size
    fig=plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
    ax = fig.add_subplot(111)
    ax.axis('off')
    #do the table
    header = ax.table(cellText=[['']],
                          colLabels=['-- NAFO division 2J --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.5]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')        
        elif key[1] in last_columns:
             cell._text.set_color('dimgray')
             cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            #print('white')
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_fall_2J.png", dpi=300)
    os.system('convert -trim scorecards_fall_2J.png scorecards_fall_2J.png')

    # French table
    temperatures = temperatures.rename({r'$\rm T_{bot}~(^{\circ}C)~-~Reference$' :
                                        r'$\rm T_{fond}~(^{\circ}C)~-~Référence$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~A$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~B$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~AB$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~ABC$',
                                        r'Sc. A (% change)' :
                                        r' Sc. A (% changem.)',
                                        r'Sc. B (% change)' :
                                        r' Sc. B (% changem.)',
                                        r'Sc. AB (% change)' :
                                        r' Sc. AB (% changem.)',
                                        r'Sc. ABC (% change)' :
                                        r' Sc. ABC (% changem.)'})

    header = ax.table(cellText=[['']],
                          colLabels=['-- Division 2J de l\'OPANO --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.50]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')        
        elif key[1] in last_columns:
             cell._text.set_color('dimgray')
             cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_fall_2J_FR.png", dpi=300)
    os.system('convert -trim scorecards_fall_2J_FR.png scorecards_fall_2J_FR.png')

    # 2. ---- 3K ----
    infile0 = 'stats_3K_fall_reference.pkl'
    infile1 = 'stats_3K_fall_1.pkl'
    infile2 = 'stats_3K_fall_2.pkl'
    infile3 = 'stats_3K_fall_3.pkl'
    infile4 = 'stats_3K_fall_4.pkl'

    df0 = pd.read_pickle(infile0).Tmean    
    df1 = pd.read_pickle(infile1).Tmean
    df2 = pd.read_pickle(infile2).Tmean
    df3 = pd.read_pickle(infile3).Tmean
    df4 = pd.read_pickle(infile4).Tmean
    
    df = pd.concat([df0, df1, df2, df3, df4], axis=1, keys=['sc0', 'sc1', 'sc2', 'sc3', 'sc4'])
    df.index = pd.to_datetime(df.index) # update index to datetime
    df = df[(df.index.year>=years[0]) & (df.index.year<=years[-1])]
    df.round(1)

    # remove scenarios that are not relevant:
    df[['sc2']] = df[['sc2']]*np.nan
    df[['sc3']] = df[['sc3']]*np.nan
    #df = df.drop(['sc2', 'sc3'], axis=1)

    # Flag bad years (no or weak sampling):
    bad_years = np.array([1995])
    for i in bad_years:
        df[df.index.year==i]=np.nan

    # Calculate std anomalies
    df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
    std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
    std_anom = std_anom.T
        
    # Add 4 rows for % change by case
    std_anom.loc['sc1p'] = (df['sc1'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc2p'] = (df['sc2'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc3p'] = (df['sc3'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc4p'] = (df['sc4'] - df['sc0']) / df['sc0'] * 100
    # add mean and std inm both DataFrames
    std_anom['MEAN'] = df_clim.mean(axis=0)
    std_anom['SD'] = df_clim.std(axis=0)
    
    # Now by-pass std_anom with bottom T values (keep colors according to std anom)
    temperatures = std_anom.copy()
    temperatures.loc['sc0'] = df['sc0']
    temperatures.loc['sc1'] = df['sc1']
    temperatures.loc['sc2'] = df['sc2']
    temperatures.loc['sc3'] = df['sc3']
    temperatures.loc['sc4'] = df['sc4']
    # add mean and std inm both DataFrames
    temperatures['MEAN'] = df_clim.mean(axis=0)
    temperatures['SD'] = df_clim.std(axis=0)
    sd1 = (temperatures.loc['sc1p']).std()
    sd2 = (temperatures.loc['sc2p']).std()
    sd3 = (temperatures.loc['sc3p']).std()
    sd4 = (temperatures.loc['sc4p']).std()    
    temperatures.loc['sc1p']['MEAN'] = np.abs(temperatures.loc['sc1p']).mean()
    temperatures.loc['sc2p']['MEAN'] = np.abs(temperatures.loc['sc2p']).mean()
    temperatures.loc['sc3p']['MEAN'] = np.abs(temperatures.loc['sc3p']).mean()
    temperatures.loc['sc4p']['MEAN'] = np.abs(temperatures.loc['sc4p']).mean()
    temperatures.loc['sc1p']['SD'] = sd1
    temperatures.loc['sc2p']['SD'] = sd2
    temperatures.loc['sc3p']['SD'] = sd3
    temperatures.loc['sc4p']['SD'] = sd4
    # Rename columns
    std_anom.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    temperatures.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    # Rename index
    std_anom = std_anom.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    temperatures = temperatures.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    
    # Get text values +  cell color
    vals = np.around(temperatures.values,1)
    vals[vals==-0.] = 0.
    vals_color = np.around(std_anom.values,1)
    vals_color[vals_color==-0.] = 0.    
    vals_color[-1,] = vals_color[-1,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[-2,] = vals_color[-2,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-3,] = vals_color[-3,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-4,] = vals_color[-4,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[:,-1] = 0 # No color to last two columns (mean and STD)
    vals_color[:,-2] = 0

    # Start drawing
    nrows, ncols = temperatures.index.size, temperatures.columns.size
    fig=plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
    ax = fig.add_subplot(111)
    ax.axis('off')
    #do the table
    header = ax.table(cellText=[['']],
                          colLabels=['-- NAFO division 3K --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.5]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')        
        elif key[1] in last_columns:
             cell._text.set_color('dimgray')
             cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            #print('white')
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_fall_3K.png", dpi=300)
    os.system('convert -trim scorecards_fall_3K.png scorecards_fall_3K.png')

    # French table
    temperatures = temperatures.rename({r'$\rm T_{bot}~(^{\circ}C)~-~Reference$' :
                                        r'$\rm T_{fond}~(^{\circ}C)~-~Référence$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~A$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~B$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~AB$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~ABC$',
                                        r'Sc. A (% change)' :
                                        r' Sc. A (% changem.)',
                                        r'Sc. B (% change)' :
                                        r' Sc. B (% changem.)',
                                        r'Sc. AB (% change)' :
                                        r' Sc. AB (% changem.)',
                                        r'Sc. ABC (% change)' :
                                        r' Sc. ABC (% changem.)'})

    header = ax.table(cellText=[['']],
                          colLabels=['-- Division 3K de l\'OPANO --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.50]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')        
        elif key[1] in last_columns:
            cell._text.set_color('dimgray')
            cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_fall_3K_FR.png", dpi=300)
    os.system('convert -trim scorecards_fall_3K_FR.png scorecards_fall_3K_FR.png')


    # 3. ---- 3LNO ----
    infile0 = 'stats_3LNO_fall_reference.pkl'
    infile1 = 'stats_3LNO_fall_1.pkl'
    infile2 = 'stats_3LNO_fall_2.pkl'
    infile3 = 'stats_3LNO_fall_3.pkl'
    infile4 = 'stats_3LNO_fall_4.pkl'

    df0 = pd.read_pickle(infile0).Tmean    
    df1 = pd.read_pickle(infile1).Tmean
    df2 = pd.read_pickle(infile2).Tmean
    df3 = pd.read_pickle(infile3).Tmean
    df4 = pd.read_pickle(infile4).Tmean
    
    df = pd.concat([df0, df1, df2, df3, df4], axis=1, keys=['sc0', 'sc1', 'sc2', 'sc3', 'sc4'])
    df.index = pd.to_datetime(df.index) # update index to datetime
    df = df[(df.index.year>=years[0]) & (df.index.year<=years[-1])]
    df.round(1)

    # remove scenarios that are not relevant:
    df[['sc2']] = df[['sc2']]*np.nan
    df[['sc3']] = df[['sc3']]*np.nan
    df[['sc4']] = df[['sc4']]*np.nan
    #df = df.drop(['sc2', 'sc3'], axis=1)
    
    # Flag bad years (no or weak sampling):
    bad_years = np.array([1995])
    for i in bad_years:
        df[df.index.year==i]=np.nan

    # Calculate std anomalies
    df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
    std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
    std_anom = std_anom.T
        
    # Add 4 rows for % change by case
    std_anom.loc['sc1p'] = (df['sc1'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc2p'] = (df['sc2'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc3p'] = (df['sc3'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc4p'] = (df['sc4'] - df['sc0']) / df['sc0'] * 100
    # add mean and std inm both DataFrames
    std_anom['MEAN'] = df_clim.mean(axis=0)
    std_anom['SD'] = df_clim.std(axis=0)
    
    # Now by-pass std_anom with bottom T values (keep colors according to std anom)
    temperatures = std_anom.copy()
    temperatures.loc['sc0'] = df['sc0']
    temperatures.loc['sc1'] = df['sc1']
    temperatures.loc['sc2'] = df['sc2']
    temperatures.loc['sc3'] = df['sc3']
    temperatures.loc['sc4'] = df['sc4']
    # add mean and std inm both DataFrames
    temperatures['MEAN'] = df_clim.mean(axis=0)
    temperatures['SD'] = df_clim.std(axis=0)
    sd1 = (temperatures.loc['sc1p']).std()
    sd2 = (temperatures.loc['sc2p']).std()
    sd3 = (temperatures.loc['sc3p']).std()
    sd4 = (temperatures.loc['sc4p']).std()    
    temperatures.loc['sc1p']['MEAN'] = np.abs(temperatures.loc['sc1p']).mean()
    temperatures.loc['sc2p']['MEAN'] = np.abs(temperatures.loc['sc2p']).mean()
    temperatures.loc['sc3p']['MEAN'] = np.abs(temperatures.loc['sc3p']).mean()
    temperatures.loc['sc4p']['MEAN'] = np.abs(temperatures.loc['sc4p']).mean()
    temperatures.loc['sc1p']['SD'] = sd1
    temperatures.loc['sc2p']['SD'] = sd2
    temperatures.loc['sc3p']['SD'] = sd3
    temperatures.loc['sc4p']['SD'] = sd4
    # Rename columns
    std_anom.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    temperatures.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    # Rename index
    std_anom = std_anom.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    temperatures = temperatures.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    
    # Get text values +  cell color
    vals = np.around(temperatures.values,1)
    vals[vals==-0.] = 0.
    vals_color = np.around(std_anom.values,1)
    vals_color[vals_color==-0.] = 0.    
    vals_color[-1,] = vals_color[-1,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[-2,] = vals_color[-2,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-3,] = vals_color[-3,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-4,] = vals_color[-4,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[:,-1] = 0 # No color to last two columns (mean and STD)
    vals_color[:,-2] = 0

    # Start drawing
    nrows, ncols = temperatures.index.size, temperatures.columns.size
    fig=plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
    ax = fig.add_subplot(111)
    ax.axis('off')
    #do the table
    header = ax.table(cellText=[['']],
                          colLabels=['-- NAFO division 3LNO --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.5]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')        
        elif key[1] in last_columns:
             cell._text.set_color('dimgray')
             cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            #print('white')
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_fall_3LNO.png", dpi=300)
    os.system('convert -trim scorecards_fall_3LNO.png scorecards_fall_3LNO.png')

    # French table
    temperatures = temperatures.rename({r'$\rm T_{bot}~(^{\circ}C)~-~Reference$' :
                                        r'$\rm T_{fond}~(^{\circ}C)~-~Référence$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~A$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~B$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~AB$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~ABC$',
                                        r'Sc. A (% change)' :
                                        r' Sc. A (% changem.)',
                                        r'Sc. B (% change)' :
                                        r' Sc. B (% changem.)',
                                        r'Sc. AB (% change)' :
                                        r' Sc. AB (% changem.)',
                                        r'Sc. ABC (% change)' :
                                        r' Sc. ABC (% changem.)'})

    header = ax.table(cellText=[['']],
                          colLabels=['-- Division 3LNO de l\'OPANO --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.50]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')        
        elif key[1] in last_columns:
             cell._text.set_color('dimgray')
             cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_fall_3LNO_FR.png", dpi=300)
    os.system('convert -trim scorecards_fall_3LNO_FR.png scorecards_fall_3LNO_FR.png')

    ## Montage of different scorecards
    # English
    os.system('montage  scorecards_fall_2H.png scorecards_fall_2J.png scorecards_fall_3K.png scorecards_fall_3LNO.png -tile 1x4 -geometry +1+1  -background white  scorecards_botT_fall_closures.png') 
    # French
    os.system('montage  scorecards_fall_2H_FR.png scorecards_fall_2J_FR.png scorecards_fall_3K_FR.png scorecards_fall_3LNO_FR.png -tile 1x4 -geometry +1+1  -background white  scorecards_botT_fall_closures_FR.png') 

    
    #### ------------- For Spring ---------------- ####
    # 0. - 3LNO -
    infile0 = 'stats_3LNO_spring_reference.pkl'
    infile1 = 'stats_3LNO_spring_1.pkl'
    infile2 = 'stats_3LNO_spring_2.pkl'
    infile3 = 'stats_3LNO_spring_3.pkl'
    infile4 = 'stats_3LNO_spring_4.pkl'

    df0 = pd.read_pickle(infile0).Tmean    
    df1 = pd.read_pickle(infile1).Tmean
    df2 = pd.read_pickle(infile2).Tmean
    df3 = pd.read_pickle(infile3).Tmean
    df4 = pd.read_pickle(infile4).Tmean
    
    df = pd.concat([df0, df1, df2, df3, df4], axis=1, keys=['sc0', 'sc1', 'sc2', 'sc3', 'sc4'])
    df.index = pd.to_datetime(df.index) # update index to datetime
    df = df[(df.index.year>=years[0]) & (df.index.year<=years[-1])]
    df.round(1)

    # Flag bad years (no or weak sampling):
    # None
    for i in bad_years:
        df[df.index.year==i]=np.nan

    # get year list (only for first scorecards) 
    year_list = df.index.year.astype('str')
    year_list = [i[2:4] for i in year_list] # 2-digit year

    # Calculate std anomalies
    df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
    std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
    std_anom = std_anom.T
        
    # Add 4 rows for % change by case
    std_anom.loc['sc1p'] = (df['sc1'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc2p'] = (df['sc2'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc3p'] = (df['sc3'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc4p'] = (df['sc4'] - df['sc0']) / df['sc0'] * 100
    # add mean and std inm both DataFrames
    std_anom['MEAN'] = df_clim.mean(axis=0)
    std_anom['SD'] = df_clim.std(axis=0)
    
    # Now by-pass std_anom with bottom T values (keep colors according to std anom)
    temperatures = std_anom.copy()
    temperatures.loc['sc0'] = df['sc0']
    temperatures.loc['sc1'] = df['sc1']
    temperatures.loc['sc2'] = df['sc2']
    temperatures.loc['sc3'] = df['sc3']
    temperatures.loc['sc4'] = df['sc4']
    # add mean and std inm both DataFrames
    temperatures['MEAN'] = df_clim.mean(axis=0)
    temperatures['SD'] = df_clim.std(axis=0)
    sd1 = (temperatures.loc['sc1p']).std()
    sd2 = (temperatures.loc['sc2p']).std()
    sd3 = (temperatures.loc['sc3p']).std()
    sd4 = (temperatures.loc['sc4p']).std()    
    temperatures.loc['sc1p']['MEAN'] = np.abs(temperatures.loc['sc1p']).mean()
    temperatures.loc['sc2p']['MEAN'] = np.abs(temperatures.loc['sc2p']).mean()
    temperatures.loc['sc3p']['MEAN'] = np.abs(temperatures.loc['sc3p']).mean()
    temperatures.loc['sc4p']['MEAN'] = np.abs(temperatures.loc['sc4p']).mean()
    temperatures.loc['sc1p']['SD'] = sd1
    temperatures.loc['sc2p']['SD'] = sd2
    temperatures.loc['sc3p']['SD'] = sd3
    temperatures.loc['sc4p']['SD'] = sd4
    # Rename columns
    std_anom.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    temperatures.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    # Rename index
    std_anom = std_anom.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    temperatures = temperatures.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    
    # Get text values +  cell color
    year_list.append(r'$\rm \overline{x}$') # add 2 extra columns
    year_list.append(r'sd')   
    vals = np.around(temperatures.values,1)
    vals[vals==-0.] = 0.
    vals_color = np.around(std_anom.values,1)
    vals_color[vals_color==-0.] = 0.    
    vals_color[-1,] = vals_color[-1,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[-2,] = vals_color[-2,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-3,] = vals_color[-3,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-4,] = vals_color[-4,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[:,-1] = 0 # No color to last two columns (mean and STD)
    vals_color[:,-2] = 0

    # Build the colormap (only for 1st scorecard)
    vmin = -3.49
    vmax = 3.49
    midpoint = 0
    levels = np.linspace(vmin, vmax, 15)
    midp = np.mean(np.c_[levels[:-1], levels[1:]], axis=1)
    colvals = np.interp(midp, [vmin, midpoint, vmax], [-1, 0., 1])
    normal = plt.Normalize(-3.49, 3.49)
    reds = plt.cm.Reds(np.linspace(0,1, num=7))
    blues = plt.cm.Blues_r(np.linspace(0,1, num=7))
    whites = [(1,1,1,1)]*2
    colors = np.vstack((blues[0:-1,:], whites, reds[1:,:]))
    colors = np.concatenate([[colors[0,:]], colors, [colors[-1,:]]], 0)
    cmap, norm = from_levels_and_colors(levels, colors, extend='both')
    cmap_r, norm_r = from_levels_and_colors(levels, np.flipud(colors), extend='both')

    nrows, ncols = temperatures.index.size+1, temperatures.columns.size
    hcell, wcell = 0.5, 0.6
    hpad, wpad = 1, 1    
    fig=plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
    ax = fig.add_subplot(111)
    ax.axis('off')
    #do the table
    header = ax.table(cellText=[['']],
                          colLabels=['-- NAFO division 3LNO --'],
                          loc='center'
                          )
    header.set_fontsize(13)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=year_list,
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1, 0.5]
                        )
    # change font color to white where needed:
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        elif key[0] == 0: #year's row = no color
            pass
        elif key[1] in last_columns:
            cell._text.set_color('dimgray')
            cell._text.set_weight('bold')
        elif (key[0] < 6) & ((vals_color[key[0]-1, key[1]]  <= -1.5) | (vals_color[key[0]-1, key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')
        # Bold face % change
        if key[0] >= 6:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_spring_3LNO.png", dpi=300)
    os.system('convert -trim scorecards_spring_3LNO.png scorecards_spring_3LNO.png')

    # French table
    temperatures = temperatures.rename({r'$\rm T_{bot}~(^{\circ}C)~-~Reference$' :
                                        r'$\rm T_{fond}~(^{\circ}C)~-~Référence$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~A$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~B$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~AB$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~ABC$',
                                        r'Sc. A (% change)' :
                                        r' Sc. A (% changem.)',
                                        r'Sc. B (% change)' :
                                        r' Sc. B (% changem.)',
                                        r'Sc. AB (% change)' :
                                        r' Sc. AB (% changem.)',
                                        r'Sc. ABC (% change)' :
                                        r' Sc. ABC (% changem.)'})
       
    year_list[-1] = u'ET'
    
    header = ax.table(cellText=[['']],
                          colLabels=['-- Division 3LNO de l\'OPANO --'],
                          loc='center'
                          )
    header.set_fontsize(13)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=year_list,
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1, 0.5]
                        )
    # change font color to white where needed:
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        elif key[0] == 0: #year's row = no color
            pass
        elif key[1] in last_columns:
            cell._text.set_color('dimgray')
            cell._text.set_weight('bold')
        elif (key[0] < 6) & ((vals_color[key[0]-1, key[1]]  <= -1.5) | (vals_color[key[0]-1, key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')   
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')
        # Bold face % change
        if key[0] >= 6:
            cell._text.set_weight('bold')

    plt.savefig("scorecards_spring_3LNO_FR.png", dpi=300)
    os.system('convert -trim scorecards_spring_3LNO_FR.png scorecards_spring_3LNO_FR.png')

 #  1. - 3Ps -
    infile0 = 'stats_3Ps_spring_reference.pkl'
    infile1 = 'stats_3Ps_spring_1.pkl'
    infile2 = 'stats_3Ps_spring_2.pkl'
    infile3 = 'stats_3Ps_spring_3.pkl'
    infile4 = 'stats_3Ps_spring_4.pkl'

    df0 = pd.read_pickle(infile0).Tmean    
    df1 = pd.read_pickle(infile1).Tmean
    df2 = pd.read_pickle(infile2).Tmean
    df3 = pd.read_pickle(infile3).Tmean
    df4 = pd.read_pickle(infile4).Tmean
    
    df = pd.concat([df0, df1, df2, df3, df4], axis=1, keys=['sc0', 'sc1', 'sc2', 'sc3', 'sc4'])
    df.index = pd.to_datetime(df.index) # update index to datetime
    df = df[(df.index.year>=years[0]) & (df.index.year<=years[-1])]
    df.round(1)
    
    # remove scenarios that are not relevant:
    df[['sc4']] = df[['sc4']]*np.nan
    
    # Flag bad years (no or weak sampling):
    bad_years = np.array([1980, 1981, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 2006])
    for i in bad_years:
        df[df.index.year==i]=np.nan

    # Calculate std anomalies
    df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
    std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
    std_anom = std_anom.T
        
    # Add 4 rows for % change by case
    std_anom.loc['sc1p'] = (df['sc1'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc2p'] = (df['sc2'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc3p'] = (df['sc3'] - df['sc0']) / df['sc0'] * 100
    std_anom.loc['sc4p'] = (df['sc4'] - df['sc0']) / df['sc0'] * 100
    # add mean and std inm both DataFrames
    std_anom['MEAN'] = df_clim.mean(axis=0)
    std_anom['SD'] = df_clim.std(axis=0)
    
    # Now by-pass std_anom with bottom T values (keep colors according to std anom)
    temperatures = std_anom.copy()
    temperatures.loc['sc0'] = df['sc0']
    temperatures.loc['sc1'] = df['sc1']
    temperatures.loc['sc2'] = df['sc2']
    temperatures.loc['sc3'] = df['sc3']
    temperatures.loc['sc4'] = df['sc4']
    # add mean and std inm both DataFrames
    temperatures['MEAN'] = df_clim.mean(axis=0)
    temperatures['SD'] = df_clim.std(axis=0)
    sd1 = (temperatures.loc['sc1p']).std()
    sd2 = (temperatures.loc['sc2p']).std()
    sd3 = (temperatures.loc['sc3p']).std()
    sd4 = (temperatures.loc['sc4p']).std()    
    temperatures.loc['sc1p']['MEAN'] = np.abs(temperatures.loc['sc1p']).mean()
    temperatures.loc['sc2p']['MEAN'] = np.abs(temperatures.loc['sc2p']).mean()
    temperatures.loc['sc3p']['MEAN'] = np.abs(temperatures.loc['sc3p']).mean()
    temperatures.loc['sc4p']['MEAN'] = np.abs(temperatures.loc['sc4p']).mean()
    temperatures.loc['sc1p']['SD'] = sd1
    temperatures.loc['sc2p']['SD'] = sd2
    temperatures.loc['sc3p']['SD'] = sd3
    temperatures.loc['sc4p']['SD'] = sd4
    # Rename columns
    std_anom.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    temperatures.rename(columns={'MEAN': r'$\rm \overline{x}$', 'SD': r'sd'}, inplace=True)
    # Rename index
    std_anom = std_anom.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    temperatures = temperatures.rename({'sc0': r'$\rm T_{bot}~(^{\circ}C)~-~Reference$',
                                 'sc1': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$',
                                 'sc2': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$',
                                 'sc3': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$',
                                 'sc4': r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$',
                                 'sc1p': r'Sc. A (% change)',
                                 'sc2p': r'Sc. B (% change)',
                                 'sc3p': r'Sc. AB (% change)',
                                 'sc4p': r'Sc. ABC (% change)'
                                 })
    
    # Get text values +  cell color
    vals = np.around(temperatures.values,1)
    vals[vals==-0.] = 0.
    vals_color = np.around(std_anom.values,1)
    vals_color[vals_color==-0.] = 0.    
    vals_color[-1,] = vals_color[-1,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[-2,] = vals_color[-2,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-3,] = vals_color[-3,]*.1 # scale down a factor 10 for last 4 rows        
    vals_color[-4,] = vals_color[-4,]*.1 # scale down a factor 10 for last 4 rows
    vals_color[:,-1] = 0 # No color to last two columns (mean and STD)
    vals_color[:,-2] = 0

    # Start drawing
    nrows, ncols = temperatures.index.size, temperatures.columns.size
    fig=plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
    ax = fig.add_subplot(111)
    ax.axis('off')
    #do the table
    header = ax.table(cellText=[['']],
                          colLabels=['-- NAFO division 3Ps --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.5]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')    
        elif key[1] in last_columns:
             cell._text.set_color('dimgray')
             cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            #print('white')
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_spring_3Ps.png", dpi=300)
    os.system('convert -trim scorecards_spring_3Ps.png scorecards_spring_3Ps.png')

    # French table
    temperatures = temperatures.rename({r'$\rm T_{bot}~(^{\circ}C)~-~Reference$' :
                                        r'$\rm T_{fond}~(^{\circ}C)~-~Référence$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~A$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~A$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~B$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~B$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~AB$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~AB$',
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scenario~ABC$' :
                                        r'$\rm T_{bot}~(^{\circ}C)~-~Scénario~ABC$',
                                        r'Sc. A (% change)' :
                                        r' Sc. A (% changem.)',
                                        r'Sc. B (% change)' :
                                        r' Sc. B (% changem.)',
                                        r'Sc. AB (% change)' :
                                        r' Sc. AB (% changem.)',
                                        r'Sc. ABC (% change)' :
                                        r' Sc. ABC (% changem.)'})

    header = ax.table(cellText=[['']],
                          colLabels=['-- Division 3Ps de l\'OPANO --'],
                          loc='center'
                          )
    header.set_fontsize(12.5)
    the_table=ax.table(cellText=vals, rowLabels=temperatures.index, colLabels=None, 
                        loc='center', cellColours=cmap(normal(vals_color)), cellLoc='center',
                        bbox=[0, 0, 1.0, 0.50]
                        )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12.5)
    # change font color to white where needed:
    table_props = the_table.properties()
    table_cells = table_props['child_artists']
    last_columns = np.arange(vals.shape[1]-2, vals.shape[1]) # last columns
    for key, cell in the_table.get_celld().items():
        cell_text = cell.get_text().get_text()
        if is_number(cell_text) == False:
            pass
        #elif key[0] == 0:# <--- remove when no years
        #    pass
        elif (cell_text=='nan'):
            cell._set_facecolor('lightgray')
            cell._text.set_color('lightgray')        
        elif key[1] in last_columns:
             cell._text.set_color('dimgray')
             cell._text.set_weight('bold')
        elif (key[0] < 5) & ((vals_color[key[0], key[1]]  <= -1.5) | (vals_color[key[0], key[1]] >= 1.5)) :
            cell._text.set_color('white')
        elif (np.float(cell_text) <= -15) | (np.float(cell_text) >= 15) :
            cell._text.set_color('white')
        # Bold face % change
        if key[0] >= 5:
            cell._text.set_weight('bold')
            
    plt.savefig("scorecards_spring_3Ps_FR.png", dpi=300)
    os.system('convert -trim scorecards_spring_3Ps_FR.png scorecards_spring_3Ps_FR.png')
    
    
    plt.close('all')
    # English montage
    os.system('montage  scorecards_spring_3LNO.png scorecards_spring_3Ps.png -tile 1x3 -geometry +1+1  -background white  scorecards_botT_spring.png')
    # French montage
    os.system('montage  scorecards_spring_3LNO_FR.png scorecards_spring_3Ps_FR.png -tile 1x3 -geometry +1+1  -background white  scorecards_botT_spring_FR.png')
