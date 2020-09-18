#!/bin/python37

##
## By Julia Engdahl 09/08/2020
## Modified by Elim Thompson 09/09/2020
##
## This script is only a class and should not be called by itself. To use
## this library, check out plot_data.py
##
## Julia's original script ddp_plots.py:
## This script contains functions to generate water level, temperature, wind,
## pressure plots and to concatenate them into GIF. 
##  * water level: time-series with prediction and observation
##  * temperature: both water and air temp as time-series and thermometers
##  * wind       : polar plot (i.e. no time-series)
##  * pressure   : time-series with a barometer
##
## Elim's modification:
##  * Turned ddp_plots.py into a product and their children classes
##  * Added ability to do both time-series + object and object alone
##############################################################################

###############################################
## Import libraries
###############################################
import requests, pytz, glob, os, sys
import numpy as np
import pandas as pd
import datetime as dt
from . import product

import matplotlib
matplotlib.use ('Agg')
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LightSource
plt.rc ('text', usetex=False)
plt.rc ('font', family='sans-serif')
plt.rc ('font', serif='Computer Modern Roman')

###############################################
## Define constants
###############################################
## Monitor dpi
DPI = product.DPI

## Number of continuous bad data to trigger no-plot-shown
N_HOURS_NULL_DATA = product.N_HOURS_NULL_DATA

## Time format for display
TIME_FORMAT = '%m/%d/%Y %I:%M %p'

## Unit conversion factors
KNOTS_TO_MPERSEC = 1 / 0.514444

## For wind 
## Define global constants for polar plot
WIND_RSCALE = 60
WIND_RBOARD = WIND_RSCALE + 10 # dart board is slightly larger
WIND_XTICKS = np.array ([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi, 5*np.pi/4, 3*np.pi/2, 7*np.pi/4])
WIND_XTICKLABELS = ['E','NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']
CARDINAL_NAMES = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S',
                  'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N']
WIND_LEGEND = ['Latest Data at', 'Wind Speed', 'Wind Direction',
               'Gust Speed', 'Gust Direction']

###############################################
## Define short lambda functions
###############################################
convert_knots_to_mPerSec = lambda knots: knots * KNOTS_TO_MPERSEC

###############################################
## Define wind child class
###############################################
class wind (product.product):

    def __init__ (self):

        ''' To initialize a wind product instance '''

        super().__init__('wind')

        ## Wind polar plot parameters - FIXED!
        self._rscale = WIND_RSCALE 
        self._rboard = WIND_RSCALE + 10 # dart board is slightly larger
        self._rticks = np.linspace (0, self._rscale, 4)[1:] # 4 ticks along radius

        ## Theta axis parameters
        self._tticks = WIND_XTICKS
        self._tticklabels = WIND_XTICKLABELS

        ## Fading arrows or ticks
        self._colorarrow = 'Blue'
        self._colormap = cm.Blues
        self._needle_style = "fancy,head_length=10,head_width=5,tail_width=20"
        #self._arrow_style  = "fancy,head_length=28,head_width=40,tail_width=20"
        self._arrow_style  = "fancy,head_length=20,head_width=30,tail_width=15"        

    def __repr__ (self):
        pass

    # +------------------------------------------------------------
    # | Getters & setters
    # +------------------------------------------------------------  
    @property
    def latest_obs_time (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.wind_speed.isna()
        return self._latest_data_df.wind_speed.index[not_na][-1]

    @property
    def latest_wind_speed (self): 
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.wind_speed.isna()
        return self._latest_data_df.wind_speed.values[not_na][-1]

    @property
    def latest_gust_speed (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.gust_speed.isna()
        return self._latest_data_df.gust_speed.values[not_na][-1]

    @property
    def latest_wind_cardinal (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.wind_cardinal.isna()
        return self._latest_data_df.wind_cardinal.values[not_na][-1]

    @property
    def latest_gust_cardinal (self):
        return self.latest_wind_cardinal

    @property
    def has_all_nan (self):
        ## If dataframe is None -> no past data
        if self._latest_data_df is None: return False
        ## Slice out observed data from N hours before obs time
        begin_time = self.latest_obs_time - pd.offsets.Hour (N_HOURS_NULL_DATA)
        end_time = self.latest_obs_time
        observed = self._latest_data_df.loc[begin_time:end_time,].wind_speed
        ## Check if all observed data in this time window is invalid
        return observed.isna().all()

    # +------------------------------------------------------------
    # | Collect & handle wind data
    # +------------------------------------------------------------
    def _get_cardinal_direction (self, degNArr):
        ## Each direction spans 360/16 = 22.5 degree range
        ## i.e. 11.25 before the direction to 11.25 after 
        indices = [np.floor ((degN + 11.25) / 22.5).astype (int) for degN in degNArr]
        return [CARDINAL_NAMES[index] for index in indices]

    def _convert_angle (self, degNc):
        ## Convert input from "clockwise from N" to "counter-clockwise from E"
        ## Added 180 - wind direction is "from" not "to" a certain direction
        degEcc = 360 - (degNc - 90) + 180
        # Make sure degEcc is within 360
        while degEcc < 0: degEcc += 360
        while degEcc >= 360: degEcc -= 360
        # Convert from degree to radian for plotting
        return degEcc * np.pi / 180

    def _normalize_wind_speed (self, df):

        wmin = 0
        wmax = df.wind_speed.max()
        return (df.wind_speed - wmin) / (wmax - wmin) * self._rscale

    def _load_data (self):

        ## Make sure "now" time is set
        if self._now is None:
            raise IOError ("Please define now time before loading data.")

        ## Get 6-min observation time-series: t, s, d, dr, g
        obs_df = self._load_latest()
        obs_df = obs_df.drop(axis=1, columns=['f'])
        obs_df.columns = ['wind_speed', 'wind_direction', 'wind_cardinal', 'gust_speed']

        ## Go through each column to convert them to float type
        obs_df['wind_speed'] = obs_df.wind_speed.astype (float)
        obs_df['wind_direction'] = obs_df.wind_direction.astype (float)
        obs_df['gust_speed'] = obs_df.gust_speed.astype (float)

        ## Convert wind speed & direction to polar coordinate
        obs_df['wind_radius'] = self._normalize_wind_speed (obs_df)
        obs_df['wind_theta'] = [self._convert_angle (theta)
                           for theta in obs_df.wind_direction]

        ## Store it as internal variable
        self._latest_data_df = obs_df

    # +------------------------------------------------------------
    # | Plot functions
    # +------------------------------------------------------------
    def _create_wind_rose (self, axis, dot_time, doNeedle=False):
        
        ## Define constants for this plot
        df = self._latest_data_df
        #  1. Unit for this plot
        runit = 'kts'
        #  2. Radius ticks from 0 knots to the maximum speed in the data
        rticklabels = [y / self._rscale * df.wind_speed.max() for y in self._rticks]
        #     Format it with 1 decimal places
        rticklabels = ['{0:.1f}'.format (r) for r in rticklabels]

        ## Collect data to be plotted - last 10 timestamps up to dot time
        before_dot = df[df.index <= dot_time].tail (10)
        radii = before_dot.wind_radius.values
        thetas = before_dot.wind_theta.values

        ## 1. Plot previous winds
        #  Define arrow style based on user inputs
        arrowstyle = self._needle_style if doNeedle else self._arrow_style
        #  Normalize arrow colors based on time to get fading effect
        norm = matplotlib.colors.Normalize (vmin=0, vmax=len (radii)*2)
        #  Loop through the first 9 timestamps and draw the arrow
        for i, (theta, radius) in enumerate (zip (thetas[:-1], radii[:-1])):
            # Exclude data point with invalid speed / direction
            if not np.isfinite (radius) or not np.isfinite (theta): continue
            # Define the color of this arrow
            color = self._colormap(norm(i))
            # Draw the arrow
            arrow = matplotlib.patches.FancyArrowPatch((0, 0), (theta, radius),
                        arrowstyle=arrowstyle, color=color)
            axis.add_patch(arrow)  
        
        ## Format theta axis in circular direction (i.e. x-axis)
        #  1. Remove the outer most circle axis
        axis.spines["polar"].set_visible(False)
        #  2. Set and label tick marks with angles
        axis.set_thetagrids (self._tticks*180/np.pi, labels=self._tticklabels,
                             fontsize=self._fontsize-5)
        axis.tick_params (axis='x', width=2, length=10, pad=5)
        #  3. 
        axis.xaxis.grid(True, color='k', linestyle='-', linewidth=1, alpha=0.7)

        ## Format axis along radial direction (i.e. y-axis)
        ## 1. Set limits in radius
        axis.set_ylim(0, self._rboard)
        #  2. Set and label tick marks with speeds
        axis.set_rgrids (self._rticks, labels=rticklabels, angle=0,
                         fontsize=self._fontsize*0.5,
                         horizontalalignment='center')
        #  3. Write the unit of speed labels
        axis.text(np.radians(axis.get_rlabel_position()-5),
                  axis.get_rmax()/2., runit, fontsize=self._fontsize*0.5,
                  rotation=axis.get_rlabel_position(),
                  horizontalalignment='center', verticalalignment='center')
        #  4.  
        axis.yaxis.grid (True, color='black', linestyle=':', linewidth=0.7, alpha=0.6)
        
        ## 2. Plot wind arrow at dot time if it is valid
        radius = before_dot.wind_radius.values[-1]
        theta  = before_dot.wind_theta.values[-1]
        if np.isfinite (radius) and np.isfinite (theta): 
            arrow = matplotlib.patches.FancyArrowPatch((0, 0), (theta, radius),
                arrowstyle=arrowstyle, color=self._colorarrow, alpha=1.0)
            axis.add_patch(arrow)

        return axis

    def _write_wind_legend (self, axis, at_dot):

        ## Loop through each label to be printed
        for index, label in enumerate (WIND_LEGEND[::-1]):
            llabel = label.lower()
            # Get value in English
            value_fmt = '{0:.2f}' if 'speed' in llabel else \
                        '{0:3}' if 'direction' in llabel else '{0}'
            value = at_dot.wind_speed.values[0] if llabel == 'wind speed' else \
                    at_dot.gust_speed.values[0] if llabel == 'gust speed' else \
                    at_dot.wind_cardinal.values[0] if 'direction' in llabel else \
                    at_dot.index[0].strftime (TIME_FORMAT)
            text = label + ': ' + value_fmt.format (value) 
            # For speed, add in value in Metric
            if 'speed' in llabel:
                value = convert_knots_to_mPerSec (value)
                text += ' kts (' + value_fmt.format (value) + ' m/s)'
            axis.annotate (text, (0, index), color='black', fontsize=self._fontsize*0.8)

        ## Format axis
        axis.set_ylim ([0, len (WIND_LEGEND)*2.5])
        axis.axis ('off')

    def _generate_one_plot (self, dot_time, doNeedle=False):
        
        ## Make sure data is available
        if self._latest_data_df is None:
            raise IOError ("Please load data before plotting.")

        ## Create a huuuge canvas with 2 subplots.
        fig = plt.figure(figsize=self.fig_size)
        gs = gridspec.GridSpec (ncols=2, nrows=1, width_ratios=[3, 1])
        gs.update (top=0.8, wspace=0.05)

        ## Right: Polar plot
        axis = fig.add_subplot(gs[0], polar=True)
        self._create_wind_rose (axis, dot_time, doNeedle=doNeedle)
        axis.set_title('Wind', fontsize=self._fontsize*3, loc='left')

        ## Left: Regular cartesian for text box
        axis = fig.add_subplot(gs[1])
        at_dot = self._latest_data_df[self._latest_data_df.index == dot_time].tail (1)
        self._write_wind_legend (axis, at_dot)

        ## Format title / layout
        plt.savefig(self._plot_path + '/' + dot_time.strftime ('%Y%m%d%H%M') + '.jpg')
        
        ## Properly close the window for the next plot
        plt.close ('all')

    def create_gif (self, doNeedle=False):

        ## Make sure "now" time is set
        if self._now is None:
            raise IOError ("Please define now time before creating gif.")
        
        ## Remove everything in the plot path
        if os.path.exists (self.plot_path):
            all_files = glob.glob (self.plot_path + '/*.jpg')
            for afile in all_files: os.remove (afile)

        ## Gather data
        self._load_data()

        ## Generate every other time step until the last observation point
        ## Toggle from m/sec to knots and back every N frames
        end_time = self.latest_obs_time
        timestamps = list (self._latest_data_df.iloc[::10, :].index) + [end_time]
        for index, dot_time in enumerate (sorted (timestamps)):
            # If there is no more valid observation points, exit the loop
            if dot_time > end_time: break
            # Generate the plot for this time stamp
            self._generate_one_plot (dot_time, doNeedle=doNeedle)

        ## Create gif
        self._make_gif()
