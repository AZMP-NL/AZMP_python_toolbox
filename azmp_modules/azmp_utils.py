"""Some utilitary tools to for AZMP

Contains following functions:
- get_nafo_divisions()
- get_bottomT_climato(INFILES, LON_REG,  LAT_REG, year_lims=[1981, 2010], season=[], zlims=[10, 1000], dz=5, h5_outputfile=[])
- bottomT_quickplot(h5_outputfile, figure_file=[])
- Tbot_to_GIS_ascii(h5file, ascfile)
-

** idea: add function 'plot_nafo_division(dict)'

----------

Atlantic Zone Monitoring Program @NAFC:
https://azmp-nl.github.io/

"""

__author__ = 'Frederic.Cyr@dfo-mpo.gc.ca'
__version__ = '0.1'


import h5py
import os
import sys
import netCDF4
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
from mpl_toolkits.basemap import Basemap
from scipy.interpolate import griddata
from scipy.interpolate import interp1d  # to remove NaNs in profiles


    
def get_nafo_divisions():
    """ Will generate a dict with NAFO division shapes.
    Example to access info:
    In [14]: dict['2J']['lat']
    Out[14]: [55.33, 55.33, 52.25, 52.25]

    ** Needs to be expanded with other divisions **

    """

    # 2J
    xlon = [-59.778, -47.529, -42, -55.712]
    xlat = [55.33, 55.33, 52.25, 52.25]
    div2J = {'lat' : xlat, 'lon' : xlon}

    # 3K
    xlon = [-55.425, -55.425, -42, -42, -53.466]
    xlat = [51.583, 52.25, 52.25, 49.25, 49.25]
    div3K = {'lat' : xlat, 'lon' : xlon}

    # 3L
    xlon = [-53.466, -46.5, -46.5, -54.5, -54.198]
    xlat = [49.25, 49.25, 46, 46, 46.815]
    div3L = {'lat' : xlat, 'lon' : xlon}

    # 3N
    xlon = [-51, -46.5, -46.5, -50, -51, -51]
    xlat = [46, 46, 39, 39, 39.927, 46]
    div3N = {'lat' : xlat, 'lon' : xlon}

    # 3O
    xlon = [-54.5, -51, -51, -54.4, -54.5]
    xlat = [46, 46, 39.927, 43.064, 46]
    div3O = {'lat' : xlat, 'lon' : xlon}

    #3Ps
    xlon = [-57.523, -58.82, -54.5, -54.5, -54.2]
    xlat = [47.631, 46.843, 43.064, 46, 46.817]
    div3Ps = {'lat' : xlat, 'lon' : xlon}
    
    dict = {}
    dict['2J'] = div2J
    dict['3K'] = div3K
    dict['3L'] = div3L
    dict['3O'] = div3O
    dict['3Ps'] = div3Ps

    return dict

def get_bottomT_climato(INFILES, LON_REG,  LAT_REG, year_lims=[1981, 2010], season=[], zlims=[10, 1000], dz=5, h5_outputfile=[]):
    """ Generate and returns the climatological bottom temperature map.
    This script uses GEBCO dada. User should update the path below.
    Maybe this is something I could work on...

    If the pickled filename exists, the function will by-pass the processing and return only saved climatology.
    
    Usage ex:
    import numpy as np
    import azmp_utils as azu
    dc = .1
    lonLims = [-60, -44] # fish_hab region
    latLims = [39, 56]
    lon_reg = np.arange(lonLims[0]+dc/2, lonLims[1]-dc/2, dc)
    lat_reg = np.arange(latLims[0]+dc/2, latLims[1]-dc/2, dc)
    Tbot, lon_reg, lat_reg = azu.get_bottomT_climato('/home/cyrf0006/data/dev_database/*.nc', lon_reg, lat_reg, season='fall', h5_outputfile='Tbot_climato_fall.h5')
    
    """
    
    ## ---- Check if H5 file exists ---- ##        
    if os.path.isfile(h5_outputfile):
        print [h5_outputfile + ' exist! Reading directly']
        h5f = h5py.File(h5_outputfile,'r')
        Tbot = h5f['Tbot'][:]
        lon_reg = h5f['lon_reg'][:]
        lat_reg = h5f['lat_reg'][:]
        h5f.close()

    else:

        ## ---- Region parameters ---- ##
        #    add_path('/home/cyrf0006/data/GEBCO/')
        dataFile = '/home/cyrf0006/data/GEBCO/GRIDONE_1D.nc' # Maybe find a better way to handle this file
        lonLims = [LON_REG[0], LON_REG[-1]]
        latLims = [LAT_REG[0], LAT_REG[-1]]
        zmin = zlims[0] # do try to compute bottom temp above that depth
        zmax = zlims[1] # do try to compute bottom temp below that depth
        lon_reg = LON_REG
        lat_reg = LAT_REG
        lon_grid, lat_grid = np.meshgrid(lon_reg,lat_reg)
        dc = np.round(np.diff(lon_reg[0:2]), 3)[0]

        ## ---- Bathymetry ---- ####
        print('Load and grid bathymetry')
        # Load data
        dataset = netCDF4.Dataset(dataFile)
        # Extract variables
        x = dataset.variables['x_range']
        y = dataset.variables['y_range']
        spacing = dataset.variables['spacing']
        # Compute Lat/Lon
        nx = int((x[-1]-x[0])/spacing[0]) + 1  # num pts in x-dir
        ny = int((y[-1]-y[0])/spacing[1]) + 1  # num pts in y-dir
        lon = np.linspace(x[0],x[-1],nx)
        lat = np.linspace(y[0],y[-1],ny)
        # interpolate data on regular grid (temperature grid)
        # Reshape data
        zz = dataset.variables['z']
        Z = zz[:].reshape(ny, nx)
        Z = np.flipud(Z) # <------------ important!!!
        # Reduce data according to Region params
        idx_lon = np.where((lon>=lonLims[0]) & (lon<=lonLims[1]))
        idx_lat = np.where((lat>=latLims[0]) & (lat<=latLims[1]))
        Z = Z[idx_lat[0][0]:idx_lat[0][-1]+1, idx_lon[0][0]:idx_lon[0][-1]+1]
        lon = lon[idx_lon[0]]
        lat = lat[idx_lat[0]]
        # interpolate data on regular grid (temperature grid)
        lon_grid_bathy, lat_grid_bathy = np.meshgrid(lon,lat)
        lon_vec_bathy = np.reshape(lon_grid_bathy, lon_grid_bathy.size)
        lat_vec_bathy = np.reshape(lat_grid_bathy, lat_grid_bathy.size)
        z_vec = np.reshape(Z, Z.size)
        Zitp = griddata((lon_vec_bathy, lat_vec_bathy), z_vec, (lon_grid, lat_grid), method='linear')
        print(' -> Done!')

        ## ---- Get CTD data --- ##
        print('Get historical data')
        ds = xr.open_mfdataset(INFILES)
        # Selection of a subset region
        ds = ds.where((ds.longitude>lonLims[0]) & (ds.longitude<lonLims[1]), drop=True)
        ds = ds.where((ds.latitude>latLims[0]) & (ds.latitude<latLims[1]), drop=True)
        # Select time (save several options here)
        if season == 'summer':
            ds = ds.sel(time=ds['time.season']=='JJA')
        elif season == 'spring':
            ds = ds.sel(time=ds['time.season']=='MAM')
        elif season == 'fall':
            ds = ds.sel(time=ds['time.season']=='SON')
        else:
            print('!! no season specified, used them all! !!')

        # Time period for climatology
        ds = ds.sel(time=ds['time.year']>=year_lims[0])
        ds = ds.sel(time=ds['time.year']<=year_lims[1])
        ds = ds.sel(level=ds['level']<zmax)
        # Vertical binning (on dataArray; more appropriate here
        da_temp = ds['temperature']
        bins = np.arange(dz/2.0, ds.level.max(), dz)
        da_temp = da_temp.groupby_bins('level', bins).mean(dim='level')
        #To Pandas Dataframe
        df_temp = da_temp.to_pandas()
        df_temp.columns = bins[0:-1] #rename columns with 'bins'
        print(' -> Done!')


        ## --- fill 3D cube --- ##  
        print('Fill regular cube')
        lons = np.array(ds.longitude)
        lats = np.array(ds.latitude)
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
            #print 'interpolate depth layer ' + np.str(k) + ' / ' + np.str(z.size) 
            # griddata (after removing nans)
            idx_good = np.argwhere(~np.isnan(tmp_vec))
            if idx_good.size: # will ignore depth where no data exist
                LN = np.squeeze(lon_vec[idx_good])
                LT = np.squeeze(lat_vec[idx_good])
                TT = np.squeeze(tmp_vec[idx_good])
                zi = griddata((LN, LT), TT, (lon_grid, lat_grid), method='linear')
                V[:,:,k] = zi
            else:
                continue
        print(' -> Done!')    

        # mask using bathymetry
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

        # Save data for further use
        if np.size(h5_outputfile):
            h5f = h5py.File(h5_outputfile, 'w')
            h5f.create_dataset('Tbot', data=Tbot)
            h5f.create_dataset('lon_reg', data=lon_reg)
            h5f.create_dataset('lat_reg', data=lat_reg)
            h5f.create_dataset('Zitp', data=Zitp)
            h5f.close()

    return Tbot, lon_reg, lat_reg
    
def bottomT_quickplot(h5_outputfile, figure_file=[]):
    """ Using h5 file created by get_bottomT_climato, this function plots the bottom temperature using basemap.
    
    Usage ex:
    import azmp_utils as azu
    azu.bottomT_quickplot('Tbot_climato_fall.h5')
    
    """

    ## ---- Load data ---- ##    
    h5f = h5py.File(h5_outputfile,'r')
    Tbot = h5f['Tbot'][:]
    lon_reg = h5f['lon_reg'][:]
    lat_reg = h5f['lat_reg'][:]
    #Zitp = h5f['Zitp'][:]
    h5f.close()

    ## ---- Derive some parameters ---- ##    
    lon_0 = np.round(np.mean(lon_reg))
    lat_0 = np.round(np.mean(lat_reg))
    lonLims = [lon_reg[0], lon_reg[-1]]
    latLims = [lat_reg[0], lat_reg[-1]]
        
    ## ---- Plot map ---- ##
    fig, ax = plt.subplots(nrows=1, ncols=1)
    m = Basemap(ax=ax, projection='merc',lon_0=lon_0,lat_0=lat_0, llcrnrlon=lonLims[0],llcrnrlat=latLims[0],urcrnrlon=lonLims[1],urcrnrlat=latLims[1], resolution='h')
    levels = np.linspace(0, 15, 16)
    xi, yi = m(*np.meshgrid(lon_reg, lat_reg))
    #lon_casts, lat_casts = m(lons[idx], lats[idx])
    c = m.contourf(xi, yi, Tbot, levels, cmap=plt.cm.RdBu_r, extend='both')
        #c = m.pcolor(xi, yi, Tbot, levels, cmap=plt.cm.RdBu_r, extend='both')
    #    x,y = m(*np.meshgrid(lon,lat))
    #    cc = m.contour(x, y, -Z, [100, 500, 1000, 4000], colors='grey');
    m.fillcontinents(color='tan');
    
    m.drawparallels([40, 45, 50, 55, 60], labels=[1,0,0,0], fontsize=12, fontweight='normal');
    m.drawmeridians([-60, -55, -50, -45], labels=[0,0,0,1], fontsize=12, fontweight='normal');

    cax = plt.axes([0.85,0.15,0.04,0.7])
    cb = plt.colorbar(c, cax=cax, ticks=levels)
    cb.set_label(r'$\rm T(^{\circ}C)$', fontsize=12, fontweight='normal')
    #plt.subplots_adjust(left=.07, bottom=.07, right=.93, top=.9, wspace=.2, hspace=.2)


    #### ---- Save Figure ---- ####
    if np.size(figure_file):
        fig.set_size_inches(w=6, h=9)
        fig.set_dpi(200)
        fig.savefig(figure_file)
        print [figure_file + ' saved!']

    plt.show()
        
        

def Tbot_to_GIS_ascii(h5file, ascfile):
    """ Read bottom temperature H5 file and export it to ascii readagle for GIS
    
    Usage ex:
    import azmp_utils as azu
    Tbot_to_GIS_ascii('Tbot_climato_fall.h5', 'bottom_temp.asc'):
    
    """    

    ## ---- Load data ---- ##    
    h5f = h5py.File(h5file,'r')
    Tbot = h5f['Tbot'][:]
    lon_reg = h5f['lon_reg'][:]
    lat_reg = h5f['lat_reg'][:]
    h5f.close()

    #### ---- Save CSV data ---- ####
    # Replace NaNs by -9999
    idx_nan = np.where(np.isnan(Tbot))
    Tbot[idx_nan] = -9999
    # define header
    Tbot_flip = np.flipud(Tbot)
    header = '{0:^1s} {1:^1s}\n{2:^1s} {3:^1s}\n{4:^1s} {5:^1s}\n{6:^1s} {7:^1s}\n{8:^1s} {9:^1s}\n{10:^1s} {11:^1s}'.format('NCOLS', np.str(lon_reg.size), 'NROWS', np.str(lat_reg.size), 'XLLCORNER', np.str(lon_reg.min()), 'YLLCORNER', np.str(lat_reg.min()), 'CELLSIZE', np.str(dc), 'NODATA_VALUE', '-9999')
    np.savetxt(ascfile, Tbot_flip, delimiter=" ", header=header, fmt='%5.2f', comments='')

    
