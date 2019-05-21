'''
To generate AZMP score cards for bottom temperature

Uses pickled object generated by azmp_bottom_stats.py

'''

import numpy as  np
import matplotlib.pyplot as plt
import pandas as pd
import os
import unicodedata

# Parameters 
path = '/home/cyrf0006/AZMP/state_reports/bottomT/'
clim_year = [1981, 2010]

#### -------------1. bottom temperature ---------------- ####
## 2J fall
infile = path + 'stats_2J_fall.pkl'
df = pd.read_pickle(infile)
df.index = pd.to_datetime(df.index) # update index to datetime
# compute std anom
df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
# std anom for temperature
df['std_anom'] = std_anom['Tmean']
# keep only 2 columns
df = df[['Tmean', 'std_anom']]
df.index = df.index.year
df.to_csv('BT_2J_fall.dat', header=False, sep = ' ', float_format='%.2f')

## 3K fall
infile = path + 'stats_3K_fall.pkl'
df = pd.read_pickle(infile)
df.index = pd.to_datetime(df.index) # update index to datetime
# compute std anom
df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
# std anom for temperature
df['std_anom'] = std_anom['Tmean']
# keep only 2 columns
df = df[['Tmean', 'std_anom']]
df.index = df.index.year
df.to_csv('BT_3K_fall.dat', header=False, sep = ' ', float_format='%.2f')

## 3LNO fall
infile = path + 'stats_3LNO_fall.pkl'
df = pd.read_pickle(infile)
df.index = pd.to_datetime(df.index) # update index to datetime
# compute std anom
df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
# std anom for temperature
df['std_anom'] = std_anom['Tmean']
# keep only 2 columns
df = df[['Tmean', 'std_anom']]
df.index = df.index.year
df.to_csv('BT_3LNO_fall.dat', header=False, sep = ' ', float_format='%.2f')

## 3LNO spring
infile = path + 'stats_3LNO_spring.pkl'
df = pd.read_pickle(infile)
df.index = pd.to_datetime(df.index) # update index to datetime
# compute std anom
df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
# std anom for temperature
df['std_anom'] = std_anom['Tmean']
# keep only 2 columns
df = df[['Tmean', 'std_anom']]
df.index = df.index.year
df.to_csv('BT_3LNO_spring.dat', header=False, sep = ' ', float_format='%.2f')

## 3Ps spring 
infile = path + 'stats_3Ps_spring.pkl'
df = pd.read_pickle(infile)
df.index = pd.to_datetime(df.index) # update index to datetime
# compute std anom
df_clim = df[(df.index.year>=clim_year[0]) & (df.index.year<=clim_year[1])]
std_anom = (df-df_clim.mean(axis=0))/df_clim.std(axis=0)
# std anom for temperature
df['std_anom'] = std_anom['Tmean']
# keep only 2 columns
df = df[['Tmean', 'std_anom']]
df.index = df.index.year
df.to_csv('BT_3Ps_spring.dat', header=False, sep = ' ', float_format='%.2f')

#### ------------- 2. winter NAO ---------------- ####
nao_file = '/home/cyrf0006/data/AZMP/indices/data.csv'
df = pd.read_csv(nao_file, header=1)
# Set index
df = df.set_index('Date')
df.index = pd.to_datetime(df.index, format='%Y%m')
# Select only DJF
df_winter = df[(df.index.month==12) | (df.index.month==1) | (df.index.month==2)]
# Start Dec-1950
df_winter = df_winter[df_winter.index>pd.to_datetime('1950-10-01')]
# Average 3 consecutive values (DJF average); We loose index.
df_winter = df_winter.groupby(np.arange(len(df_winter))//3).mean()
# Reset index using years only
year_unique = pd.unique(df.index.year)[1:,]
df_winter = df_winter.iloc[np.arange(0, year_unique.size)] # reduce if last month is december (belongs to following year)
df_winter.index = year_unique
df_winter.to_csv('NAO_DJF.dat', header=False, sep = ' ', float_format='%.2f')

#### ------------- 3. CIL ---------------- ####
# see /home/cyrf0006/AZMP/state_reports/ColbourneStuff/CIL_AZMP_SPRING_SUMMER_FALL.xlsx


#### ------------- 4. Stn 27 ---------------- ####
# see /home/cyrf0006/AZMP/S27/station_27_stratification.xlsx



# zip SAR_azmp-nl_2018.zip *.dat

