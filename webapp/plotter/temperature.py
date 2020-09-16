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

sys.path.append('C:\\Users\\elim.thompson\\Documents\\ddp\\webapp\\plotter\\')
import product

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

## Time format for display
TIME_FORMAT = '%m/%d/%Y %I:%M %p'
CURRENT_TIME_LABEL = 'Current Time'

## For plotting style
XTICKLABEL_TIME_FORMAT = product.XTICKLABEL_TIME_FORMAT
XTICKLABEL_HOURS = product.XTICKLABEL_HOURS
N_YTICKS = product.N_YTICKS

## For temperature
TEMP_BULB_RADIUS = 6
TEMP_TUBE_SCALE = 60
TEMP_TUBE_HEIGHT = TEMP_TUBE_SCALE + 3 # Tube is slightly taller
#  Position of air and water thermometer on time-series plot
#  [x-coordinate (lower left), y-coordinate (lower left), width, height]
TEMP_AIR_THERMO_POS = [0.0, 0.0, 0.4, 1]
TEMP_WATER_THERMO_POS = [0.5, 0.0, 0.4, 1]
TEMP_SCALE_PAD = 20

###############################################
## Define short lambda functions
###############################################
convert_defF_to_defC = lambda degF: (degF - 32) * 5/9

###############################################
## Define temperature child class
###############################################
class temperature (product.product):

    def __init__ (self):

        ''' To initialize a temperature product instance '''

        super().__init__('temperature')

        ## Thermometer parameters
        self._tube_scale = TEMP_TUBE_SCALE
        self._tube_height = TEMP_TUBE_HEIGHT
        self._bulb_radius = TEMP_BULB_RADIUS
        self._scale_pad = TEMP_SCALE_PAD

        #  For time-series plot specifically
        self._air_thermo_pos = TEMP_AIR_THERMO_POS
        self._water_thermo_pos = TEMP_WATER_THERMO_POS

    def __repr__ (self):
        pass

    # +------------------------------------------------------------
    # | Getters & setters
    # +------------------------------------------------------------    
    @property
    def latest_obs (self): return self.latest_air_temp

    @property
    def latest_obs_time (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.air.isna()
        return self._latest_data_df.air.index[not_na][-1]

    @property
    def latest_air_temp (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.air.isna()
        return self._latest_data_df.air.values[not_na][-1]

    @property
    def latest_water_temp (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.water.isna()
        return self._latest_data_df.water.values[not_na][-1]

    @property 
    def min_temp (self):
        if self._latest_data_df is None: return None
        return self._latest_data_df.loc[:, ['air', 'water']].min().min()

    @property 
    def max_temp (self):
        if self._latest_data_df is None: return None
        return self._latest_data_df.loc[:, ['air', 'water']].max().max()

    @property
    def tube_scale (self): return self._tube_scale
    @tube_scale.setter
    def tube_scale (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is 0 or positive
        if number < 0:
            raise IOError ('Tube Scale must be >= 0.')
        self._tube_scale = number

    @property
    def tube_height (self): return self._tube_height
    @tube_height.setter
    def tube_height (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is 0 or positive
        if number < 0:
            raise IOError ('Tube Height must be >= 0.')
        self._tube_height = number

    @property
    def bulb_radius (self): return self._bulb_radius
    @bulb_radius.setter
    def bulb_radius (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is 0 or positive
        if number < 0:
            raise IOError ('Bulb radius must be >= 0.')
        self._bulb_radius = number

    @property
    def scale_pad (self): return self._scale_pad
    @scale_pad.setter
    def scale_pad (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is 0 or positive
        if number < 0:
            raise IOError ('Padding between tick and scale must be >= 0.')
        self._scale_pad = number

    @property
    def air_thermo_pos (self): return self._air_thermo_pos
    @air_thermo_pos.setter
    def air_thermo_pos (self, array):
        ## Make sure input is a number array with 4 values
        self._check_is_array (array, length=4)
        ## Make sure the elements are numbers
        for elem in array: self._check_is_number (elem)        
        self._air_thermo_pos = array

    @property
    def water_thermo_pos (self): return self._water_thermo_pos
    @water_thermo_pos.setter
    def water_thermo_pos (self, array):
        ## Make sure input is a number array with 4 values
        self._check_is_array (array, length=4)
        ## Make sure the elements are numbers
        for elem in array: self._check_is_number (elem)        
        self._water_thermo_pos = array

    # +------------------------------------------------------------
    # | Collect & handle temp data
    # +------------------------------------------------------------
    def _normalize_temperature (self, temp):

        tmin = self.min_temp - 5
        tmax = self.max_temp + 5
        return (temp - tmin) / (tmax - tmin) * self._tube_scale

    def _load_data (self):

        ## Make sure "now" time is set
        if self._now is None:
            raise IOError ("Please define now time before loading data.")

        ## Get 6-min air temp observation time-series: v, f
        air_df = self._load_latest(product_name = 'air_temperature')
        air_df = air_df.drop(axis=1, columns=['f'])
        air_df.columns = ['air']

        ## Get 6-min water temp observation time-series: v, f
        water_df = self._load_latest(product_name = 'water_temperature')
        water_df = water_df.drop(axis=1, columns=['f'])
        water_df.columns = ['water']

        ## Merge two into one
        obs_df = pd.merge (air_df, water_df, right_index=True, left_index=True, how='outer')

        ## Go through each column to convert them to float type
        obs_df['air'] = obs_df.air.astype (float)
        obs_df['water'] = obs_df.water.astype (float)
        self._latest_data_df = obs_df

        ## Convert temperature to tube height
        obs_df['air_height'] = self._normalize_temperature (obs_df.air)
        obs_df['water_height'] = self._normalize_temperature (obs_df.water)

        ## Add in extra hours with nan temp for time-series plots
        end_date = self.now + pd.offsets.Hour (self._hours_pad[1])
        obs_df.loc[end_date.strftime('%Y-%m-%d %H:%M:%S')] = \
            pd.Series ([np.NaN]*len (obs_df.columns), obs_df.columns)
        obs_df = obs_df.asfreq ('6min')

        ## Store it as internal variable
        self._latest_data_df = obs_df

    # +------------------------------------------------------------
    # | Plot functions
    # +------------------------------------------------------------
    def _plot_obs_time_series (self, axis, df, dot_time, ylimits,
                               yticks, yticklabels, ylabel):

        # Define data to be plotted up to dot-time
        valid_points = np.logical_or (~df.air.isna(), ~df.water.isna())
        before_dot_obs = df[np.logical_and (df.index <= dot_time, valid_points)]
        latest_obs = before_dot_obs.tail(1)

        # 1. Plot air temp observation up to dot time
        axis.plot(before_dot_obs.index, before_dot_obs.air, c='red',
                  label='Air temperature', linewidth=self._linewidth)
        #    Add red dot for air temp 
        axis.scatter (latest_obs.index[0], latest_obs['air'][0], c='red',
                      s=self._markersize, alpha=0.7)

        # 2. Plot water temp observation up to dot time
        axis.plot(before_dot_obs.index, before_dot_obs.water, c='blue',
                  label='Water temperature', linewidth=self._linewidth)
        #    Add blue dot for water temp 
        axis.scatter (latest_obs.index[0], latest_obs['water'][0], c='blue',
                      s=self._markersize, alpha=0.7)

        # 3. Add vertical line for recent data time in LST/LDT
        axis.axvline (self._now.strftime ('%Y-%m-%d %H:%M'), color='green',
                      label=CURRENT_TIME_LABEL, linewidth=self._linewidth)

        # 4. Format x-axis based on hours-pad
        axis.set_xlim(df.index[0], df.index[-1])
        xticks = df.index [np.logical_and (df.index.hour.isin (XTICKLABEL_HOURS), df.index.minute==0)] 
        axis.set_xticks (xticks)
        xticklabels = [x.strftime (XTICKLABEL_TIME_FORMAT) for x in xticks]
        axis.set_xticklabels (xticklabels, rotation=25, fontsize=self._fontsize)
        axis.set_xlabel('Date time', fontsize=self._fontsize, labelpad = 23)
        
        # 5. Format y-axis
        axis.set_ylim (ylimits)
        axis.set_yticks (yticks)
        yticklabels = ['{0:.1f}'.format (y) for y in yticklabels]
        axis.set_yticklabels (yticklabels, fontsize=self._fontsize)
        axis.set_ylabel (ylabel, fontsize=self._fontsize, labelpad = 23)
        
        # 6. Add grid lines
        for ytick in axis.get_yticks():
            axis.axhline (y=ytick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)
        for xtick in axis.get_xticks():
            axis.axvline (x=xtick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)

    def _create_a_thermometer_on_main_axis (self, axis, temp_height, yticks,    
                                            isAir=False):
        
        ## Define constants based on air or water thermometers
        color = '#f94f60' if isAir else '#007bae'
        rect = self._air_thermo_pos if isAir else self._water_thermo_pos

        ## Create a new matplotlib figure and map the coordinate with main axis
        fig = plt.gcf()
        box = axis.get_position()
        width, height = box.width, box.height
        inax_position  = axis.transAxes.transform(rect[0:2])
        transFigure = fig.transFigure.inverted()
        infig_position = transFigure.transform(inax_position)    

        ## Remove rectangle grid
        axis.axis ('off')

        ## Create a sub-axis in the rectangle defined
        x = infig_position[0]
        y = infig_position[1]
        width *= rect[2]
        height *= rect[3]
        subax = fig.add_axes([x,y,width,height])

        ## Create a thermometer in the sub-axis
        self._create_a_thermometer (subax, temp_height, yticks, color, isAir=isAir)
        
    def _create_a_thermometer (self, axis, height, yticks, color, isAir=False):

        ## Format x & y axes
        #  1. x-axis centered at (0,0) i.e. center of bulb with a diameter of 6
        axis.set_xlim (-10,10)
        #  2. y-axis ends at tube height
        axis.set_ylim (-10, self._tube_height)
        #  Normalize input yticks to be within tube scale
        normalized_yticks = [(y-min(yticks)) / (max(yticks)-min(yticks))*self._tube_scale
                             for y in yticks]
        axis.set_yticks (normalized_yticks)
        
        ## Format spines 
        axis.spines['top'].set_visible(False)
        axis.spines['right'].set_visible(False)
        axis.xaxis.set_ticks([])
        axis.spines['bottom'].set_color('none') 

        ## Show scale only if air thermometer
        if isAir: 
            # Show left spine
            axis.yaxis.set_ticks_position('left')
            # Define y ticklabdels to be the same as main plot (instead of tube scale)
            ylabels = ['{0:.0f}$^\circ$F'.format (y) for y in yticks]
            axis.set_yticklabels (ylabels, fontsize=self._fontsize-7)
            # Format the spine line and ticks
            axis.spines['left'].set_linewidth(3)
            axis.tick_params(axis='y', width=2, length=10, pad=self._scale_pad)
        else:
            # Do not show left spine
            axis.yaxis.set_ticks([])
            axis.spines['left'].set_color('none') 
                
        ## Draw the tube as a patch, with round corners, aligned with bulb's center
        tube_width = self._bulb_radius + 1
        tube_loc = (-1 *tube_width / 2, 0)
        tube = matplotlib.patches.FancyBboxPatch (tube_loc, tube_width, self._tube_height,
                        linewidth=3, edgecolor=color, facecolor='none',
                        boxstyle="round,pad=0,rounding_size=3.5",
                        capstyle='round', joinstyle="round")
        ## Anchor this tube patch to this thermometer subplot
        axis.add_patch (tube)

        ## Draw the bulb as a patch centered at (0, 0) 
        circle = plt.Circle ((0, 0), radius=self._bulb_radius, color=color)
        axis.add_patch (circle)
        
        ## Write temp type in the bulb with shadow
        tempType = 'Air' if isAir else 'Water'
        axis.annotate (tempType, xy=(0.1, -0.2), fontsize=self._fontsize-3,
                        ha="center", va="center", color='#E8E8E8')
        axis.annotate (tempType, xy=(0, 0), fontsize=self._fontsize-3,
                        ha="center", va="center", color='black')
        
        ## Fill in data in tube with data at dot-time
        if np.isfinite (height):
            #     Create a new tube up to the current temperature
            tube = matplotlib.patches.FancyBboxPatch (tube_loc, tube_width, height,
                            linewidth=3, facecolor=color, edgecolor=color)
            axis.add_patch (tube)

        return axis

    def _generate_one_plot (self, dot_time, doMetric=False):

        ## Make sure df time is set
        df = self._latest_data_df
        if df is None: raise IOError ("Please load data before plotting.")        
        
        ## Define the unit - either degF or defC
        yunit = '$^\circ$C' if doMetric else '$^\circ$F'
        
        ## Create a huuuge canvas with 2 subplots.
        fig = plt.figure(figsize=self.fig_size, dpi=DPI)
        gs = gridspec.GridSpec (ncols=2, nrows=1, width_ratios=[3, 1], bottom=0.15, top=0.85)
        gs.update (top=0.8)

        ## Left: Time-series plot
        axis = fig.add_subplot(gs[0])
        ylimits = [self.min_temp-5, self.max_temp+5]
        yticks = np.linspace (ylimits[0], ylimits[1], N_YTICKS)
        yticklabels = convert_defF_to_defC (yticks) if doMetric else yticks 
        ylabel = 'Temprature ({0})'.format (yunit)
        self._plot_obs_time_series (axis, df, dot_time, ylimits, yticks, yticklabels, ylabel)
        lgd = axis.legend (bbox_to_anchor=(0, 1, 1, 0), loc='lower right', fontsize=self._fontsize)
        axis.set_title('Temperature', fontsize=self._fontsize*3, loc='left', pad=37)

        ## Right: Thermometers
        subgs = gs[1].subgridspec (2, 1, height_ratios=[1, 4])
        axis = fig.add_subplot(subgs[1])
        at_dot = df[df.index == dot_time].tail (1)
        air_height = at_dot.air_height.values[0]
        self._create_a_thermometer_on_main_axis (axis, air_height, yticks, isAir=True)
        water_height = at_dot.water_height.values[0]
        self._create_a_thermometer_on_main_axis (axis, water_height, yticks, isAir=False)

        ## Format title / layout
        plt.savefig(self._plot_path + '/' + dot_time.strftime ('%Y%m%d%H%M') + '.jpg',
                    bbox_extra_artists=(lgd,), dpi=DPI)
        
        ## Properly close the window for the next plot
        plt.close ('all')

    def create_gif (self):

        ## Make sure "now" time is set
        if self._now is None:
            raise IOError ("Please define now time before creating gif.")
        
        ## Remove everything in the plot path
        if os.path.exists (self.plot_path):
            all_files = glob.glob (self.plot_path + '/*.jpg')
            for afile in all_files: os.remove (afile)

        ## Gather data
        self._load_data()

        ## Generate each time step until the last observation point
        ## Toggle from degF to degC and back every N frames
        doMetric = True # Start with knots
        end_time = self.latest_obs_time
        timestamps = list (self._latest_data_df.iloc[::10, :].index) + [end_time]
        for index, dot_time in enumerate (sorted (timestamps)):
            # If there is no more valid observation points, exit the loop
            if dot_time > end_time: break
            # Toggle units
            if index % self._toggle_units_freq == 0: doMetric = not doMetric
            # Generate the plot for this time stamp
            self._generate_one_plot (dot_time, doMetric=doMetric)

        ## Create gif
        self._make_gif()
