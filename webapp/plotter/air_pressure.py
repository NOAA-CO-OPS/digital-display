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

## For plotting style
N_YTICKS = product.N_YTICKS

## Number of continuous bad data to trigger no-plot-shown
N_HOURS_NULL_DATA = product.N_HOURS_NULL_DATA

## For pressure
PRESSURE_THETA_RANGE = 270 ## bottom 90 degree is un-used
PRESSURE_RADIUS = 60
#  Position of barometer on plot
#  [x-coordinate (lower left), y-coordinate (lower left), width, height]
PRESSURE_BAROMETER_POS = [0.88, 0.05, 0.4, 0.4]
PRESSURE_XTICKS = np.array ([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi, 5*np.pi/4, 7*np.pi/4])
PRESSURE_XTICKLABELS = np.array ([1040, 1020, 1000, 980, 960, 940, 1060])

###############################################
## Define pressure child class
###############################################
class air_pressure (product.product):

    def __init__ (self):

        ''' To initialize a pressure product instance '''

        super().__init__('air_pressure')

        ## Wind polar plot parameters - FIXED!
        self._theta_range = PRESSURE_THETA_RANGE
        self._rradius = PRESSURE_RADIUS
        self._rboard = PRESSURE_RADIUS + 5

        ## Theta axis parameters
        self._tscale = PRESSURE_THETA_RANGE
        self._tticks = PRESSURE_XTICKS
        self._tticklabels = PRESSURE_XTICKLABELS

        ## For time-series plot specifically
        self._barometer_pos = PRESSURE_BAROMETER_POS

        ## Needle (without fading)
        self._needle_color = 'black'
        self._colormap = cm.Greys
        self._needle_style = "fancy,head_length=10,head_width=5,tail_width=20"

    def __repr__ (self):
        pass

    # +------------------------------------------------------------
    # | Getters & setters
    # +------------------------------------------------------------

    # +------------------------------------------------------------
    # | Collect & handle pressure data
    # +------------------------------------------------------------
    def _normalize_pressure (self, pressure):
    
        # From 0 degree to 270 degrees -> From 1050 mb to 940 mb i.e. reversed!
        pmin = max (self._tticklabels)
        pmax = min (self._tticklabels)
        return (pressure - pmin) / (pmax - pmin) * self._tscale

    def _convert_to_angle (self, pressure):
        # Normalize pressure to 270 degree range - i.e. from +ve x-axis to -ve y-axis
        angle = self._normalize_pressure (pressure)
        # Rotate the point s.t. it is between -45 degree to 225 degree
        angle -= 45
        # Make sure angle is within 360
        while angle < 0: angle += 360
        while angle >= 360: angle -= 360
        # Convert from degree to radian for plotting
        return angle * np.pi / 180

    def _load_data (self):

        ## Make sure "now" time is set
        if self._now is None:
            raise IOError ("Please define now time before loading data.")

        ## Get 6-min observation time-series: v, f
        obs_df = self._load_latest()
        obs_df = obs_df.drop(axis=1, columns=['f'])
        obs_df.columns = ['observed']

        ## Go through each column to convert them to float type
        obs_df['observed'] = obs_df.observed.astype (float)

        ## Convert wind speed & direction to polar coordinate
        obs_df['theta'] = [self._convert_to_angle (p)
                           for p in obs_df.observed]

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
    def _create_a_barometer_on_main_axis (self, axis, pressure_thetas):
        
        ## Define constants based on air or water thermometers
        rect = [0.125, 0.125, 0.75, 0.75]

        ## Create a new matplotlib figure and map the coordinate with main axis
        fig = plt.gcf()
        box = axis.get_position()
        width, height = box.width, box.height
        inax_position  = axis.transAxes.transform(rect[0:2])
        transFigure = fig.transFigure.inverted()
        infig_position = transFigure.transform(inax_position)    

        ## Draw a cicle
        circle = plt.Circle ((0.5, 0.5), radius=0.50, color='#cd7f32')
        axis.add_patch (circle)        
        circle = plt.Circle ((0.5, 0.5), radius=0.48, color='white')
        axis.add_patch (circle)

        ## Make sure axis is a square
        axis.set_aspect('equal')
        ## Remove rectangle grid
        axis.axis ('off')

        ## Create a sub-axis in the rectangle defined
        x = infig_position[0]
        y = infig_position[1]
        width *= rect[2]
        height *= rect[3]
        subax = fig.add_axes([x,y,width,height], polar=True)

        ## Create a thermometer in the sub-axis
        self._create_a_barometer (subax, pressure_thetas)
        
    def _create_a_barometer (self, axis, pressure_thetas):

        ## Format theta axis in circular direction (i.e. x-axis)
        #  1. Remove the outer most circle axis
        axis.spines["polar"].set_visible(False)
        axis.set_rticks([]) 

        ## Format axis along radial direction (i.e. y-axis)
        #  1. Set limits in radius
        axis.set_ylim(0, self._rboard)
        #  2. Set theta major tick labels
        axis.set_thetagrids(self._tticks*180/np.pi, labels=self._tticklabels)
        axis.tick_params(axis='x', width=2, length=10, pad=20)
        for index, (label, angle) in enumerate (zip (axis.get_xticklabels(), self._tticks*180/np.pi)):
            # Write tick label
            ticklabel = self._tticklabels[index]
            x,y = label.get_position()
            lab = axis.text(x,y+0.22, ticklabel, transform=label.get_transform(),
                        ha=label.get_ha(), va=label.get_va(), fontsize=self._fontsize-7)
            lab.set_rotation(angle-90)
            # Add Rain, Change, Fair
            if ticklabel in [980, 1000, 1020]:
                text = 'Rain' if ticklabel==980 else 'Change' if ticklabel==1000 else 'Fair'
                xoffset = 0.3 if ticklabel==980 else 0 if ticklabel==1000 else -0.3
                lab = axis.text (x+xoffset, y+0.7, text, family='fantasy', transform=label.get_transform(),
                                ha=label.get_ha(), va=label.get_va(), fontsize=self._fontsize-7)
                lab.set_rotation((x+xoffset)*180/np.pi-90)

        axis.set_xticklabels([])

        #  3. Set theta major ticks
        tick = [axis.get_rmax(), axis.get_rmax()*0.95]
        for t in self._tticks: axis.plot([t,t], tick, lw=3, color="black")
        #  4. Set theta minor ticks
        xsubticks = np.linspace (0, 2*np.pi, 41)
        xsubticks = xsubticks[np.logical_or (xsubticks<5*np.pi/4, xsubticks>7*np.pi/4)]        
        for t in xsubticks: axis.plot([t,t], tick, lw=0.75, color="k")

        #  Add "Air pressure mb"
        lab = axis.text(3*np.pi/2-17/180*np.pi,y+0.1, 'Air pressure\nmb', transform=label.get_transform(),
                        ha='center', va='bottom', fontsize=self._fontsize-7)        
        lab.set_rotation(0)

        #  5. Draw an inner line
        thetas = np.linspace (-45*np.pi/180, 225*np.pi/180, 500)
        radii = [53] * 500
        axis.plot (thetas, radii, lw=1, color="k")

        ## 1. Plot previous pressured
        #  Normalize arrow colors based on time to get fading effect
        norm = matplotlib.colors.Normalize (vmin=0, vmax=len (pressure_thetas)*2)
        #  Loop through the first 9 timestamps and draw the arrow
        for i, theta in enumerate (pressure_thetas[:-1]):
            # Exclude data point with invalid pressure
            if not np.isfinite (theta): continue
            # Define the color of this arrow
            color = self._colormap(norm(i))
            # Draw the arrow
            arrow = matplotlib.patches.FancyArrowPatch((0, 0), (theta, self._rradius),
                        arrowstyle=self._needle_style, color=color)
            axis.add_patch(arrow)

        ## 2. Plot pressure arrow at dot time
        if np.isfinite (pressure_thetas[-1]):
            arrow = matplotlib.patches.FancyArrowPatch((0, 0), (pressure_thetas[-1], self._rradius),
                                                arrowstyle=self._needle_style,
                                                color=self._needle_color, alpha=1.0)
            axis.add_patch(arrow)

        ## Turn off all grid
        axis.grid(False)   

        return axis

    def _generate_one_plot (self, dot_time):
        
        ## Make sure df time is set
        df = self._latest_data_df
        if df is None: raise IOError ("Please load data before plotting.")
        
        ## Create a huuuge canvas with 2 subplots.
        fig = plt.figure(figsize=self.fig_size, dpi=DPI)
        gs = gridspec.GridSpec (ncols=2, nrows=1, width_ratios=[3, 1], bottom=0.15, top=0.85)
        gs.update (wspace=0.03)

        ## Left: Time-series plot
        axis = fig.add_subplot(gs[0])
        ylimits = [df.observed.min()-5, df.observed.max()+5]
        yticks = np.linspace (ylimits[0], ylimits[1], N_YTICKS)
        ylabel = 'Air pressure (mb)'
        self._plot_obs_time_series (axis, df, dot_time, ylimits, yticks,
                                    yticks, ylabel, do_1_decimal_place=True)
        lgd = axis.legend (bbox_to_anchor=(0, 1, 1, 0), loc='lower right', fontsize=self._fontsize)
        axis.set_title('Air pressure', fontsize=self._fontsize*3, loc='left', pad=37)

        ## Bottom right: Barometer
        subgs = gs[1].subgridspec (2, 1, height_ratios=[1, 1.7])
        axis = fig.add_subplot(subgs[1])
        before_dot = df[df.index <= dot_time].tail (10)
        pressure_thetas = before_dot.theta.values
        self._create_a_barometer_on_main_axis (axis, pressure_thetas)

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
        end_time = self.latest_obs_time
        timestamps = list (self._latest_data_df.iloc[::10, :].index) + [end_time]
        for index, dot_time in enumerate (sorted (timestamps)):
            # If there is no more valid observation points, exit the loop
            if dot_time > end_time: break
            # Generate the plot for this time stamp
            self._generate_one_plot (dot_time)

        ## Create gif
        self._make_gif()
