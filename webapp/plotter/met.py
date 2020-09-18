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
from .temperature import temperature
from .air_pressure import air_pressure
from .wind import wind

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
## Time format for display
TIME_FORMAT = '%m/%d/%Y %I:%M %p'

## Monitor dpi
DPI = product.DPI
FIG_SIZE = (1400/DPI, 1000/DPI)

## For plotting style
N_YTICKS = product.N_YTICKS

## Number of continuous bad data to trigger no-plot-shown
N_HOURS_NULL_DATA = product.N_HOURS_NULL_DATA

## Unit conversion factors
FEET_TO_METERS = 1 / 3.28084
KNOTS_TO_MPERSEC = 1 / 0.514444

## For met
MET_LEGEND = ['Data at' , 'Wind Direction'   , 'Wind Speed',
              'Air Temperature', 'Water Temperature', 'Air Pressure']

## For thermometer - longer
TEMP_BULB_RADIUS = 7
TEMP_TUBE_SCALE = 70
TEMP_TUBE_HEIGHT = TEMP_TUBE_SCALE + 5 # Tube is slightly taller
TEMP_SCALE_PAD = 15
#  Position of air and water thermometer on time-series plot
#  [x-coordinate (lower left), y-coordinate (lower left), width, height]
TEMP_AIR_THERMO_POS = [0.0, 0.0, 0.5, 1]
TEMP_WATER_THERMO_POS = [0.5, 0.0, 0.5, 1]

## For general plotting
FONTSIZE = 20
LINEWIDTH = 3

###############################################
## Define short lambda functions
###############################################
convert_feet_to_meters = lambda feet: feet * FEET_TO_METERS
convert_defF_to_defC = lambda degF: (degF - 32) * 5/9
convert_knots_to_mPerSec = lambda knots: knots * KNOTS_TO_MPERSEC

###############################################
## Define met class
###############################################
class met (product.product):

    def __init__ (self):

        ''' To initialize a meteorological product instance '''

        super().__init__('met')

        ## Different met products
        self._wind = None
        self._temperature = None
        self._air_pressure = None

        self._fig_size = FIG_SIZE
        self._fontsize = FONTSIZE
        self._linewidth= LINEWIDTH

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
    def latest_air_pressure (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.pressure.isna()
        return self._latest_data_df.pressure.values[not_na][-1]

    @property
    def latest_wind_speed (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.wind_speed.isna()
        return self._latest_data_df.wind_speed.values[not_na][-1]

    @property
    def latest_wind_cardinal (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.wind_cardinal.isna()
        return self._latest_data_df.wind_cardinal.values[not_na][-1]

    @property
    def latest_gust_speed (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.gust_speed.isna()
        return self._latest_data_df.gust_speed.values[not_na][-1]

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
    # | Handle different products
    # +------------------------------------------------------------
    def _define_a_product (self, product_name):

        if product_name == 'water_level':
            raise IOError ('Water level is not one of MET products.')

        try:
            aproduct = eval (product_name + '()')
        except:
            message = 'Failed to recognize product name, {0}.'.format (product_name)
            message += '\nPlease provide one of the products: {0}'.format (PRODUCT_NAMES)
            raise IOError (message)

        aproduct.hours_pad_before = self._hours_pad[0]
        aproduct.hours_pad_after = self._hours_pad[1]

        ## GIF settings
        aproduct.do_animation = self._do_animation
        aproduct.gif_loop = self._gif_loop
        aproduct.gif_total_duration_sec = self._gif_total_duration_sec
        aproduct.toggle_units_freq = self._toggle_units_freq

        ## Plot settings
        aproduct.fig_size = self._fig_size
        aproduct.linewidth = self._linewidth
        aproduct.markersize = self._markersize
        aproduct.fontsize = self._fontsize

        if product_name == 'temperature':
            aproduct.tube_scale = TEMP_TUBE_SCALE
            aproduct.tube_height = TEMP_TUBE_HEIGHT 
            aproduct.bulb_radius = TEMP_BULB_RADIUS
            aproduct.scale_pad = TEMP_SCALE_PAD
            aproduct.air_thermo_pos = TEMP_AIR_THERMO_POS
            aproduct.water_thermo_pos = TEMP_WATER_THERMO_POS

        return aproduct

    def define_products (self):

        self._wind = self._define_a_product ('wind')
        self._temperature = self._define_a_product ('temperature')
        self._air_pressure = self._define_a_product ('air_pressure')
    
    def _load_data (self):
    
        ## Make sure "now" time is set
        if self._now is None:
            raise IOError ("Please define now time before loading data.")

        ## Make sure the individual products are initialized 
        if self._wind is None or self._temperature is None or self._air_pressure is None:
            self.define_products()

        ## Update new "now" time
        self._wind.now = self._now
        self._temperature.now = self._now
        self._air_pressure.now = self._now

        ## Load individual data
        #  1. Wind: ['wind', 'degN', 'wind_cardinal', 'gust', 'radius', 'theta']
        self._wind._load_data()
        wind_df = self._wind._latest_data_df 
        wind_df.columns = ['wind_speed', 'wind_direction', 'wind_cardinal',
                           'gust_speed', 'wind_radius', 'wind_theta']
        #  2. Temperature: ['air', 'water', 'air_height', 'water_height']
        self._temperature._load_data()
        temp_df = self._temperature._latest_data_df
        #  3. Pressure: ['observed', 'theta']
        self._air_pressure._load_data()
        pres_df = self._air_pressure._latest_data_df 
        pres_df.columns = ['pressure', 'pressure_theta']

        ## Merge all met data into 1 dataframe
        df = pd.merge (wind_df, temp_df, right_index=True, left_index=True, how='outer')
        df = pd.merge (df, pres_df, right_index=True, left_index=True, how='outer')

        ## Store it as internal variable
        self._latest_data_df = df

    # +------------------------------------------------------------
    # | Plot functions
    # +------------------------------------------------------------
    def _write_legend (self, axis, at_dot):

        ## Loop through each label to be printed
        for index, label in enumerate (MET_LEGEND[::-1]):
            llabel = label.lower()
            # Gather value in English
            value_fmt = '{0}' if 'data' in llabel else \
                        '{0:3}' if 'direction' in llabel else '{0:.1f}'
            value = at_dot.wind_cardinal.values[0] if 'direction' in llabel else \
                    at_dot.wind_speed.values[0] if 'speed' in llabel else \
                    at_dot.air.values[0] if 'air temperature' in llabel else \
                    at_dot.water.values[0] if 'water' in llabel else \
                    at_dot.pressure.values[0] if 'pressure' in llabel else \
                    at_dot.index[0].strftime (TIME_FORMAT)
            unit = ' kts' if 'speed' in llabel else \
                   '$^\circ$F' if 'temperature' in llabel else \
                   ' mb' if 'pressure' in llabel else '' 
            text = label + ': ' + value_fmt.format (value) + unit
            # For speed, add in value in m/s
            if 'speed' in llabel:
                value = convert_knots_to_mPerSec (value)
                text += ' (' + value_fmt.format (value) + ' m/s)'
            # For temperature, add in values in degC
            if 'temperature' in llabel:
                value = convert_defF_to_defC (value)
                text += ' (' + value_fmt.format (value) + '$^\circ$C)'
            if not isinstance (value, str) and not np.isfinite (value):
                value_fmt, value = '{0}', 'n/a'
            axis.annotate (text, (0, index), color='black', fontsize=self._fontsize-6)

        ## Format axis
        axis.set_ylim ([0, len (MET_LEGEND)])
        axis.axis ('off')

    def _generate_1plot_2columns (self, dot_time, doWindNeedle=False):
        
        ## Make sure df time is set
        df = self._latest_data_df
        if df is None: raise IOError ("Please load data before plotting.")
        
        ## Create a huuuge canvas with 2 subplots.
        fig = plt.figure(figsize=self.fig_size, dpi=DPI)
        gs = gridspec.GridSpec (ncols=3, nrows=1, width_ratios=[2, 0.5, 1])
        gs.update (wspace=0.3)

        ## Left: wind and pressure
        subgs = gs[0].subgridspec (2, 1, height_ratios=[1, 1])
        #  Top: wind
        axis = fig.add_subplot(subgs[0], polar=True)
        self._wind._create_wind_rose (axis, dot_time, doNeedle=doWindNeedle)
        #  Bottom: pressure
        axis = fig.add_subplot(subgs[1])
        before_dot = df[df.index <= dot_time].tail (10)
        pressure_thetas = before_dot.pressure_theta.values
        self._air_pressure._create_a_barometer_on_main_axis (axis, pressure_thetas)

        ## Right: temperature and legend
        subgs = gs[2].subgridspec (2, 1, height_ratios=[2.5, 1])
        #  Top: temperature
        axis = fig.add_subplot(subgs[0])
        ylimits = [self._temperature.min_temp-5, self._temperature.max_temp+5]
        yticks = np.linspace (ylimits[0], ylimits[1], N_YTICKS)        
        at_dot = df[df.index == dot_time].tail (1)
        air_height = at_dot.air_height.values[0]
        self._temperature._create_a_thermometer_on_main_axis (axis, air_height, yticks, isAir=True)
        water_height = at_dot.water_height.values[0]
        self._temperature._create_a_thermometer_on_main_axis (axis, water_height, yticks, isAir=False)
        #  Bottom: legend
        axis = fig.add_subplot(subgs[1])
        self._write_legend (axis, at_dot)

        ## Format title / layout
        plt.savefig(self._plot_path + '/' + dot_time.strftime ('%Y%m%d%H%M') + '.jpg', dpi=DPI)
        
        ## Properly close the window for the next plot
        plt.close ('all')

    def _generate_1plot_3columns (self, dot_time, doWindNeedle=False):
        
        ## Make sure df time is set
        df = self._latest_data_df
        if df is None: raise IOError ("Please load data before plotting.")
        
        ## Create a huuuge canvas with 2 subplots.
        fig = plt.figure(figsize=self.fig_size)
        gs = gridspec.GridSpec (ncols=3, nrows=1, width_ratios=[0.9, 1, 1])
        gs.update (wspace=0.2, bottom=0.25)

        ## Left: temperature
        axis = fig.add_subplot(gs[0])
        ylimits = [self._temperature.min_temp-5, self._temperature.max_temp+5]
        yticks = np.linspace (ylimits[0], ylimits[1], N_YTICKS)        
        at_dot = df[df.index == dot_time].tail (1)
        air_height = at_dot.air_height.values[0]
        self._temperature._create_a_thermometer_on_main_axis (axis, air_height, yticks, isAir=True)
        water_height = at_dot.water_height.values[0]
        self._temperature._create_a_thermometer_on_main_axis (axis, water_height, yticks, isAir=False)

        ## Middle: wind
        axis = fig.add_subplot(gs[1], polar=True)
        self._wind._create_wind_rose (axis, dot_time, doNeedle=doWindNeedle)
        
        ## Right: pressure + legend
        #  Top: pressure
        subgs = gs[2].subgridspec (2, 1, height_ratios=[3, 1])
        axis = fig.add_subplot(subgs[0])
        before_dot = df[df.index <= dot_time].tail (10)
        pressure_thetas = before_dot.pressure_theta.values
        self._air_pressure._create_a_barometer_on_main_axis (axis, pressure_thetas)
        #  Bottom: legend
        axis = fig.add_subplot(subgs[1])
        self._write_legend (axis, at_dot)

        ## Format title / layout
        plt.savefig(self._plot_path + '/' + dot_time.strftime ('%Y%m%d%H%M') + '.jpg')
        
        ## Properly close the window for the next plot
        plt.close ('all')

    def _generate_one_plot (self, dot_time, doWindNeedle=False,
                            three_columns=False):

        if three_columns:
            self._generate_1plot_3columns (dot_time, doWindNeedle=doWindNeedle)
            return

        self._generate_1plot_2columns (dot_time, doWindNeedle=doWindNeedle)        

    def create_gif (self, doWindNeedle=False, three_columns=False):

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
        doMetric = True # Start with English
        end_time = self.latest_obs_time
        timestamps = list (self._latest_data_df.iloc[::10, :].index) + [end_time]
        for index, dot_time in enumerate (sorted (timestamps)):
            # If there is no more valid observation points, exit the loop
            if dot_time > end_time: break
            # Toggle units
            if index % self._toggle_units_freq == 0: doMetric = not doMetric            
            # Generate the plot for this time stamp
            self._generate_one_plot (dot_time, doWindNeedle=doWindNeedle,
                                     three_columns=three_columns)

        ## Create gif
        self._make_gif()
