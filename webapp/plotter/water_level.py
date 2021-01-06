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
## Time format for display
TIME_FORMAT = '%m/%d/%Y %I:%M %p'

## For plotting style
N_YTICKS = product.N_YTICKS

## Unit conversion factors
FEET_TO_METERS = 1 / 3.28084

## Monitor dpi
DPI = product.DPI

## Number of continuous bad data to trigger no-plot-shown
N_HOURS_NULL_DATA = product.N_HOURS_NULL_DATA

###############################################
## Define short lambda functions
###############################################
convert_feet_to_meters = lambda feet: feet * FEET_TO_METERS

###############################################
## Define water level child class
###############################################
class water_level (product.product):

    def __init__ (self):

        ''' To initialize a water level product instance '''

        super().__init__('water_level')

    def __repr__ (self):
        pass

    # +------------------------------------------------------------
    # | Getters & setters
    # +------------------------------------------------------------

    # +------------------------------------------------------------
    # | Collect water level data
    # +------------------------------------------------------------
    def get_today_tides (self):

        ## Covers long enough period to ensure at least 3 tides are available
        begin_date = self.now - dt.timedelta (hours=24)
        end_date   = self.now + dt.timedelta (hours=36)

        ## Pull dataframe
        hilo_df = self._load_latest (is_hilo=True, is_predictions=True,
                                     begin_date=begin_date, end_date=end_date)
        hilo_df.columns = ['height', 'event']
        hilo_df = hilo_df[~hilo_df.event.isna()]
        hilo_df['height'] = hilo_df.height.astype (float)

        ## Select 1 before and 2 after now
        now = pd.to_datetime (self._now.strftime ('%Y-%m-%d %H:%M:%S'))
        time_diff = abs (hilo_df.index - now).total_seconds()
        min_index = time_diff.argmin ()
        #  If the min difference is positive, collect 2 next tides
        #  If it is negative, collect 1 next tide
        n_before = 0 if time_diff[min_index] > 0 else 2
        n_after = 3 if time_diff[min_index] > 0 else 1
        return hilo_df.iloc[min_index-n_before:min_index+n_after, :]

    def _load_data (self):

        ## Make sure "now" time is set
        if self._now is None:
            raise IOError ("Please define now time before loading data.")

        ## Get 6-min observation time-series: v, f
        obs_df = self._load_latest(is_hilo=False, is_predictions=False)
        obs_df = obs_df.drop(axis=1, columns=[col for col in obs_df.columns if not col=='v'])
        obs_df.columns = ['observed']

        ## Get 1-min prediction time-series: v, f
        pred_df = self._load_latest (is_hilo=False, is_predictions=True)
        pred_df.columns = ['predicted']

        ## Get hi-lo prediction: Have 2 columns v, type
        hilo_df = self._load_latest (is_hilo=True, is_predictions=True)
        hilo_df.columns = ['predicted_hilo', 'event']

        ## Merge all three dataframe into 1
        df = pd.merge(pred_df, obs_df, right_index=True, left_index=True, how='outer')
        df = pd.merge(df, hilo_df, right_index=True, left_index=True, how='outer')

        ## Rows before now: only keep those with valid obs or predicted_hilo 
        keep_before = np.logical_or(~df.observed.isna(), ~df.predicted_hilo.isna())
        ## Rows after now : only keep 6, 12, 18, etc i.e. the 6-min steps
        keep_after = df.index > pd.to_datetime(self._now.strftime(TIME_FORMAT))
        keep_after = np.logical_and(keep_after, df.index.minute.isin (list (range (0, 59, 6))))

        ## Throw away any rows that are not needed
        df = df[np.logical_or (keep_before, keep_after)]

        ## Go through each column to convert them to float type
        df['observed'] = df.observed.astype (float)
        df['predicted'] = df.predicted.astype (float)
        df['predicted_hilo'] = df.predicted.astype (float)

        ## Store it as internal variable
        self._latest_data_df = df

    # +------------------------------------------------------------
    # | Plot functions
    # +------------------------------------------------------------
    def _generate_one_plot (self, dot_time, doMetric=False):
        
        ## Make sure data is available
        df = self._latest_data_df
        if df is None: raise IOError ("Please load data before plotting.")
        ## Define the unit - either feet or meters        
        yunit ='m' if doMetric else 'ft'
        
        ## Create a huuuge canvas with 1 subplot.
        fig = plt.figure(figsize=self.fig_size, dpi=DPI)
        gs = gridspec.GridSpec (ncols=1, nrows=1, bottom=0.15, top=0.85)
        axis = fig.add_subplot(gs[0])

        # 1. Plot entire prediction time-series
        axis.plot(df.index.values, df.predicted.values, color='blue',
                  label='Predicted', linewidth=self._linewidth, alpha=0.7)

        # 2. Plot standard observed time-series
        ylimits = [df.min().min()-0.4, df.max().max()+0.4]
        yticks = np.linspace (ylimits[0], ylimits[1], N_YTICKS)
        yticklabels = convert_feet_to_meters (yticks) if doMetric else yticks 
        ylabel = 'Water level ({0}) above MLLW'.format (yunit)
        self._plot_obs_time_series (axis, df, dot_time, ylimits, yticks,
                                    yticklabels, ylabel, do_1_decimal_place=False)

        # 3. Show all predicted high / lows with H / L markers
        for etype in ['H', 'L']:
            xvalues = df[df.event==etype].index
            yvalues = df[df.event==etype].predicted_hilo
            axis.scatter (xvalues, yvalues, marker='${0}$'.format (etype),
                          c='black', s=self._markersize*3,zorder=3)
            for (x, y) in zip (xvalues, yvalues):
                yloc = y + 0.1 if etype=='H' else y - 0.15
                text = '{0:.2f} {1}'.format (y, yunit)
                verticalalignment = 'bottom' if etype=='H' else 'top'
                axis.annotate (text, (x, y), xycoords='data', xytext=(x, yloc),
                               color='blue', fontsize=self._fontsize,
                               horizontalalignment='center',
                               verticalalignment=verticalalignment)

        # 10. Format title / layout
        axis.set_title('Water Level', fontsize=self._fontsize*3, loc='left', pad=37)
        lgd = axis.legend (bbox_to_anchor=(0., 1, 1, 0), 
                           loc='lower right', fontsize=self._fontsize)
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
        ## Toggle from feet to meters and back every N frames
        doMetric = True # Start with Feet
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
