import numpy as np
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import requests, pytz
from PIL import Image, ImageDraw
import glob
import os
import matplotlib
import matplotlib.cm as cm

###################################################################################################################################
##                                         WATER LEVELS                                                                          ##
###################################################################################################################################


## Start plotting!
meters_to_feet = 3.28084
fontsize = 30 
markersize = 360 
linewidth = 4

## Note that both the actual time (for slicing) and the index (for filename) are partsed 
def WL_plot(dot_time, index, now, merged,doFeet=False):
    
    
    ## Define the unit - either feet or meters
    yunit ='ft' if doFeet else 'm' 
    factor = meters_to_feet if doFeet else 1.
    
    ## Create a huuuge canvas!
    plt.figure (figsize=(32,16))
    
    ## 1. Plot prediction up to the dot_time
    before_dot_pred = merged[merged.index <= dot_time]
    plt.plot(before_dot_pred.index, before_dot_pred.predicted, c='blue', label='Predicted', linewidth=linewidth)    
    ## 2. Same for observation
    before_dot_obs = merged[np.logical_and (merged.index <= dot_time, ~merged.observed.isna())]
    plt.plot(before_dot_obs.index, before_dot_obs.observed, c='red', label='Observed', linewidth=linewidth)
    ## 3. Show the H / L markers as letters before the dot time with their predicted tide values
    before_dot_hilo = merged[np.logical_and (merged.index <= dot_time, ~merged.predicted_hilo.isna())]
    if len (before_dot_hilo) > 0:
        ## Deal with H
        xvalues = before_dot_hilo[before_dot_hilo.event=='H'].index
        yvalues = before_dot_hilo[before_dot_hilo.event=='H'].predicted_hilo
        plt.scatter (xvalues, yvalues, marker='$H$', c='black', s=markersize*3)
        for (x, y) in zip (xvalues, yvalues):
            text = '{0:.2f} {1}'.format (y*factor, yunit)
            plt.annotate (text, (x, y), xycoords='data', xytext=(x, y+0.1), color='blue',
                          fontsize=fontsize, horizontalalignment='center', verticalalignment='bottom')
        ## Deal with L
        xvalues = before_dot_hilo[before_dot_hilo.event=='L'].index
        yvalues = before_dot_hilo[before_dot_hilo.event=='L'].predicted_hilo
        plt.scatter (xvalues, yvalues, marker='$L$', c='black', s=markersize*3)
        for (x, y) in zip (xvalues, yvalues):
            text = '{0:.2f} {1}'.format (y*factor, yunit)
            plt.annotate (text, (x, y), xycoords='data', xytext=(x, y-0.1), color='blue',
                          fontsize=fontsize, horizontalalignment='center', verticalalignment='top')

    ## Add vertical line for "now" in LST
    plt.axvline (now, c='green',label='Current Time: '+ now.strftime('%Y-%m-%d %H:%M:00'), linewidth=linewidth)
    
    ## Add red dot for obs
    latest_obs = before_dot_obs.tail(1)
    plt.scatter (latest_obs.index[0], latest_obs['observed'][0], c='red', s=markersize, alpha=0.7)
    ## Add blue dot for pred
    latest_pred = before_dot_pred.tail(1)
    plt.scatter (latest_pred.index[0], latest_pred['predicted'][0], c='blue', s=markersize, alpha=0.7)
    
    ## Add grid lines
    plt.xlim(merged.index[0],merged.index[-1])
    plt.ylim([merged.min().min()-0.1, merged.max().max()+0.1])    
    for ytick in plt.yticks()[0]:
        plt.axhline (y=ytick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)
    for xtick in plt.xticks()[0]:
        plt.axvline (x=xtick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)

    ## Format axes
    plt.xticks(rotation=50, fontsize=fontsize)
    plt.xlabel('Date time', fontsize=fontsize)
    plt.ylabel('Water Level ({0}) above MLLW'.format (yunit), fontsize=fontsize)
    ylabels = plt.yticks()[0]*factor
    ylabels = ['{0:.2f}'.format (y) for y in ylabels]
    plt.yticks (ticks=plt.yticks()[0], labels=ylabels, fontsize=fontsize)
    
    ## Format title / layout
    plt.title('9410840 Santa Monica: '+ dot_time.strftime('%Y-%m-%d %H:%M:00'), fontsize=fontsize)
    lgd=plt.legend (bbox_to_anchor=(1, 1), loc='upper left', fontsize=fontsize)
    plt.tight_layout()
    plt.savefig('./frames/frame_' + str(index).zfill(4) + '.jpg',bbox_extra_artists=(lgd,), bbox_inches='tight')
    
    ## Properly close the window for the next plot
    plt.close ('all')
    return





###################################################################################################################################
##                                               TEMPERATURE                                                                     ##
###################################################################################################################################




## Define global constants for plot styling
fontsize = 30 
markersize = 360 
linewidth = 4

## Define global constants for a thermometer
tubescale = 60
tubeheight = tubescale + 3 # Tube is slightly taller than the data scale
#  Position of air and water thermometer on plot
#  [x-coordinate (lower left), y-coordinate (lower left), width, height]
airThermoPos = [0.84, 0.05, 0.1, 0.7]
waterThermoPos = [0.96, 0.05, 0.1, 0.7]

## Short function to convert units and normalize data
from_C_to_F = lambda tempC: tempC*9/5 + 32
normalized_temp = lambda temp, tmax, tmin: (temp - tmin) / (tmax - tmin) * tubescale




def TEMP_plot (dot_time, index, now,merged, doEnglish=False):
    
    ## Define constants for this plot
    #  1. Unit for this plot
    yunit ='$^\circ$F' if doEnglish else '$^\circ$C' 
    #  2. Y-range - offset-ed by 0.5 degC 
    ylim = [np.floor (merged.min().min())-0.5, np.ceil(merged.max().max())+0.5]
    #  3. Y-ticks - always show 8 ticks only
    yticks = np.linspace (ylim[0], ylim[1], 8)
    #  4. Y-ticklabels - convert to degF if doing English unit
    yticklabels = from_C_to_F (yticks) if doEnglish else yticks   
    
    ## Create a huuuge canvas!
    fig, axis = plt.subplots (1, 1, figsize=(32,16))
    
    ## 1. Plot air temp up to the dot_time
    before_dot_atemp = merged[np.logical_and (merged.index <= dot_time, ~merged.atemp.isna())]
    axis.plot(before_dot_atemp.index, before_dot_atemp.atemp, c='red', label='Air Temperature', linewidth=linewidth)
    #  a. Add red dot for air temp at the dot
    latest_atemp = before_dot_atemp.tail(1)
    axis.scatter (latest_atemp.index[0], latest_atemp['atemp'][0], c='red', s=markersize, alpha=0.7)    
    #  b. Add in subplot for air thermometer 
    color = '#f94f60' # Softer red
    axbulb = add_subplot_axes (axis, airThermoPos, color, yticks,
                               doEnglish=doEnglish, isAir=True, showScale=True) # Show y-scale only for air thermo
    #  c. Fill up thermometer based on latest dot
    #     Normalize latest point to w.r.t. the thermometer scale
    height = normalized_temp (latest_atemp['atemp'][0], ylim[1], ylim[0]) 
    #     Create a new tube up to the current air temperature
    tube = matplotlib.patches.FancyBboxPatch ((-3.5,0), 7, height, linewidth=3, facecolor=color, edgecolor=color)
    axbulb.add_patch (tube)    
    #     Print out the current air temperature below the bulb
    temp = from_C_to_F (latest_atemp['atemp'][0]) if doEnglish else latest_atemp['atemp'][0]
    tempStr = '{0:.1f}'.format (temp) + yunit    
    axbulb.annotate (tempStr, xy=(0, -10), fontsize=fontsize-3, ha="center", va="center", color=color)    

    ## 2. Repeat for water temp
    before_dot_wtemp = merged[np.logical_and (merged.index <= dot_time, ~merged.wtemp.isna())]
    axis.plot(before_dot_wtemp.index, before_dot_wtemp.wtemp, c='blue', label='Water Temperature', linewidth=linewidth)
    #  a. Add red dot for air temp at the dot
    latest_wtemp = before_dot_wtemp.tail(1)
    axis.scatter (latest_wtemp.index[0], latest_wtemp['wtemp'][0], c='blue', s=markersize, alpha=0.7)
    #  b. Add in subplot for air thermometer 
    color = '#007bae' # Softer blue
    axbulb = add_subplot_axes (axis, waterThermoPos, color, yticks,
                               doEnglish=doEnglish, isAir=False, showScale=False) # Skip y-scale for water thermo
    #  c. Fill up thermometer based on latest dot
    #     Normalize latest point to w.r.t. the thermometer scale    
    height = normalized_temp (latest_wtemp['wtemp'][0], ylim[1], ylim[0]) 
    #     Create a new tube up to the current water temperature
    tube = matplotlib.patches.FancyBboxPatch ((-3.5,0), 7, height, linewidth=3, facecolor=color, edgecolor=color)
    axbulb.add_patch (tube)  
    #     Print out the current water temperature below the bulb
    temp = from_C_to_F (latest_wtemp['wtemp'][0]) if doEnglish else latest_wtemp['wtemp'][0]
    tempStr = '{0:.1f}'.format (temp) + yunit       
    axbulb.annotate (tempStr, xy=(0, -10), fontsize=fontsize-3, ha="center", va="center", color=color)    

    ## 3. Add vertical line for "now" in LST
    axis.axvline (now, c='green',label='Current Time: '+ now.strftime('%Y-%m-%d %H:%M:00'), linewidth=linewidth)
    
    # Format y-axis on left
    axis.set_ylim(ylim)
    axis.set_yticks (yticks)
    axis.set_ylabel('Observed Temperature ({0})'.format (yunit), fontsize=fontsize)
    ylabels = ['{0:4.1f}'.format (y) for y in yticklabels]
    axis.set_yticklabels (labels=ylabels, fontsize=fontsize)

    # Format x-axis
    axis.set_xlim (merged.index[0],merged.index[-1])
    xticks = merged.index[np.logical_and (merged.index.hour%6==0, merged.index.minute==0 )]
    axis.set_xticks (xticks)
    axis.set_xticklabels (xticks.strftime ('%m-%d\n%H:%M'), rotation=50, fontsize=fontsize)
    axis.set_xlabel('Date time', fontsize=fontsize)
    
    ## Add grid lines
    for ytick in axis.get_yticks():
        axis.axhline (y=ytick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)
    for xtick in axis.get_xticks():
        axis.axvline (x=xtick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)
    
    ## Format title / layout
    axis.set_title('9410840 Santa Monica: '+ dot_time.strftime('%Y-%m-%d %H:%M:00'), fontsize=fontsize)
    lgd = axis.legend (bbox_to_anchor=(1, 1), loc='upper left', fontsize=fontsize)        
    plt.tight_layout()
    fig.savefig('./frames/frame_' + str(index).zfill(4) + '.jpg',bbox_extra_artists=(lgd,), bbox_inches='tight')
    
    ## Properly close the window for the next plot
    plt.close ('all')
    return




###################################################################################################################################
##                                               WIND                                                                            ##
###################################################################################################################################

cardinal_names = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N']

def get_cardinal_direction (degNArr):
    ## Each direction spans 360/16 = 22.5 degree range - 11.25 before the direction to 11.25 after 
    indices = [np.floor ((degN + 11.25) / 22.5).astype (int) for degN in degNArr]
    return [cardinal_names [index] for index in indices]

def convert_angle (degNc):
    # Convert input from "clockwise from north" to "counter-clockwise from east"
    # Added 180 - wind direction is "from" not "to" a certain direction
    degEcc = 360 - (degNc - 90) + 180
    # Make sure degEcc is within 360
    while degEcc < 0: degEcc += 360
    while degEcc >= 360: degEcc -= 360
    # Convert from degree to radian for plotting
    return degEcc * np.pi / 180

## Define global constants for plot styling
meterPerSec_to_knots = 1 / 0.5144
fontsize = 40 
linewidth = 4
## Define global constants for polar plot
rscale = 60
rboard = rscale + 10 # dart board is slightly larger than the largest possible radius
xticks = np.array ([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi, 5*np.pi/4, 3*np.pi/2, 7*np.pi/4])
xticklabels = ['E','NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']


## Short function to convert units and normalize data
normalized_wind = lambda wind, wmax, wmin: (wind - wmin) / (wmax - wmin) * rscale


def create_a_compass (df, dot_time, index, now, cmap, arrowstyle, doCurve=False, doEnglish=False):
    
    yticks = np.linspace (0, 60, 6)[1:]
    yticklabels = [y / rscale * df.speed.max() for y in yticks]

    ## Define constants for this plot
    #  1. Unit for this plot
    runit =' knots' if doEnglish else ' m/s' 
    #  2. Y-ticklabels - convert to knots if doing English unit
    if doEnglish: yticklabels = [y*meterPerSec_to_knots for y in yticklabels]
    
    ## Gather the dataframe and the current time for this plot 
    before_dot = df[np.logical_and (df.index <= dot_time, ~df.speed.isna())]
    latest = before_dot.tail(1)

    ## Create a huuuge canvas!
    fig, ax = plt.subplots(subplot_kw=dict(polar=True),figsize=(32,16))
    
    ## 1. Plot previous winds
    #  Define data point
    angles = before_dot.angle.apply (convert_angle).values[-10:]
    speeds = normalized_wind (before_dot.speed.values[-10:], df.speed.max(), df.speed.min()) 
    #  Define array style
    arrowprops = dict(width=15, headwidth=50, alpha=0.5)
    #  Plot arrow 
    norm = matplotlib.colors.Normalize(vmin=0, vmax=len (speeds)*2)
    for i, (angle, speed) in enumerate (zip (angles[:-1], speeds[:-1])):
        if doCurve:
            ## Do fading curve
            ax.plot ([angle, angles[i+1]], [speed, speeds[i+1]], linewidth=4, color=cmap(norm(i)))
        else: 
            ## Do fading arrow
            arrow = matplotlib.patches.FancyArrowPatch((0, 0), (angle, speed), arrowstyle=arrowstyle,
                                                       color=cmap(norm(i)), edgecolor=cmap(norm(i)))
            ax.add_patch(arrow)   
    
    ## 2. Plot wind arrow at dot time
    #  Define data point
    angle = convert_angle (latest.angle[0])
    speed = normalized_wind (latest.speed[0], df.speed.max(), df.speed.min()) 
    #  Define array style
    arrow = matplotlib.patches.FancyArrowPatch((0, 0), (angle, speed), arrowstyle=arrowstyle,
                                               color='blue', edgecolor='blue', alpha=1.0)
    ax.add_patch(arrow)
    
    ## Styling
    ax.spines["polar"].set_visible(False)
    ## Format radius
    ax.set_ylim(0, rboard)
    ax.set_thetagrids(xticks*180/np.pi, labels=xticklabels, fontsize=fontsize)
    ax.xaxis.grid(True, color='black', linestyle='-', linewidth=1)
    ax.tick_params(axis='x', width=2, length=10, pad=15)
    ## Format angle
    yticklabels = ['{0:.2f}'.format (y) for y in yticklabels]
    ax.set_rgrids(yticks, labels=yticklabels, angle=0, fontsize=fontsize*0.5, ha='center')
    ax.text(np.radians(ax.get_rlabel_position()-5), ax.get_rmax()/2., runit, fontsize=fontsize*0.5,
             rotation=ax.get_rlabel_position(), ha='center',va='center')
    ax.yaxis.grid(True, color='black', linestyle=':', linewidth=0.7, alpha=0.6)
    ax.set_title("Santa Monica "+str(dot_time.strftime ('%Y-%m-%d %H:%M:00')), fontsize=fontsize+10, pad=60)
    
    ## 3. Text box on the right
    factor = meterPerSec_to_knots if doEnglish else 1.0
    for i, v in enumerate (['Wind Direction', 'Wind Speed', 'Gust Speed']):
        vformat = '{0:.2f}' if 'Speed' in v else '{0:3}'
        value = latest.cardinal[0] if 'Direction' in v else \
                latest.speed[0] if 'Wind' in v else latest.gust[0]
        if doEnglish and 'Speed' in v: value *= factor
        text = '{0}: '.format (v) + vformat.format (value)
        if 'Speed' in v: text += runit
        y = -5 if i==0 else 0 if i==1 else 5
        x = 40 if i==1 else 40.75 if i==2 else 40.25
        ax.text(np.radians(ax.get_rlabel_position()-y), ax.get_rmax() + x, text, fontsize=fontsize*0.7,
                rotation=ax.get_rlabel_position(), ha='left',va='center')        
    
    
    plt.tight_layout()
    #plt.show()
    fig.savefig('./frames/frame_' + str(index).zfill(4) + '.jpg')
    
    ## Properly close the window for the next plot
    plt.close ('all')
    return


###################################################################################################################################
##                                               PRESSURE                                                                        ##
###################################################################################################################################

## Define global constants for plot styling
fontsize = 30 
markersize = 360 
linewidth = 4
## Define global constants for a barometer
angleScale = 270
baroRadius = 60 
#  Position of barometer on plot
#  [x-coordinate (lower left), y-coordinate (lower left), width, height]
baroPos = [0.65, 0.05, 0.6, 0.6]
## Define color scaling for time - max 10 timestamps before dot time

#arrowstyle = "fancy,head_length=28,head_width=40,tail_width=20" # mushroom arrow
arrowstyle = "fancy,head_length=10,head_width=5,tail_width=20" # needle

## Short function to convert data to angle
normalized_pressure = lambda p, pmax, pmin: (p - pmin) / (pmax - pmin) * angleScale
cmap = cm.Blues
np.linspace (0, 2*np.pi, 25)*180/np.pi

xsubticks = np.linspace (0, 2*np.pi, 25)
xsubticks = xsubticks[np.logical_or (xsubticks<5*np.pi/4, xsubticks>7*np.pi/4)]
xsubticks *180/np.pi

def convert_presangle (pressure, pmax, pmin):
    # Normalize pressure to 270 degree range - i.e. from +ve x-axis to -ve y-axis
    angle = normalized_pressure (pressure, pmax, pmin)
    # Rotate the point s.t. it is between -45 degree to 225 degree
    angle -= 45
    # Make sure angle is within 360
    while angle < 0: angle += 360
    while angle >= 360: angle -= 360
    # Convert from degree to radian for plotting
    return angle * np.pi / 180

def convert_pressure (angle, pmax, pmin):
    print (angle)
    angle *= 180 / np.pi
    angle -= 45
    return (angle) / angleScale * (pmax-pmin) + pmin

xticks = np.array ([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi, 5*np.pi/4, 7*np.pi/4])

def pressure_compass (ax, rect, df, dot_time, index, yunit, yticks, yticklabels, cmap, arrowstyle):
    
    ## Create and locate a new thermomenter figure 
    fig = plt.gcf()    
    box = ax.get_position()
    width, height = box.width, box.height
    inax_position  = ax.transAxes.transform(rect[0:2])
    transFigure = fig.transFigure.inverted()
    infig_position = transFigure.transform(inax_position)    
    x = infig_position[0]
    y = infig_position[1]
    width *= rect[2]
    height *= rect[3]
        
        
    pmin, pmax = 1050,940
    
    ## Get the axes handler for this figure
    subax = fig.add_axes([x,y,width,height], polar=True)             
        
    ## Gather the dataframe and the current time for this plot 
    before_dot = df[np.logical_and (df.index <= dot_time, ~df.pressure.isna())].iloc[-10:]
    latest = before_dot.tail(1)
    
    ## 1. Plot previous pressure
    #  Define data point
    angles = before_dot.pressure.apply (convert_presangle, args=(pmax, pmin,)).values
    #  Plot arrow 
    norm = matplotlib.colors.Normalize(vmin=0, vmax=len (df)*2)
    for i, angle in enumerate (angles[:-1]):
        ## Do fading arrow
        arrow = matplotlib.patches.FancyArrowPatch((0, 0), (angle, baroRadius), arrowstyle=arrowstyle,
                                                   color=cmap(norm(i)), edgecolor=cmap(norm(i)))
        subax.add_patch(arrow)
    
    ## 2. Plot pressure arrow at dot time
    #  Define data point
    angle = convert_presangle (latest.pressure[0], pmax, pmin)
    #  Define array style
    arrow = matplotlib.patches.FancyArrowPatch((0, 0), (angle, baroRadius), arrowstyle=arrowstyle,
                                               color='#013896', edgecolor='#013896', alpha=1.0)
    subax.add_patch(arrow)

    ## Styling
    subax.spines["polar"].set_visible(False)
    ## Format radius
    subax.set_ylim(0, baroRadius+5)
    xticks = np.array ([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi, 5*np.pi/4, 7*np.pi/4])
    xticklabels = np.linspace (pmin, pmax, len (xticks))
    xticklabels = np.roll (xticklabels, -1)
    xticklabels = [round (x, 1) for x in xticklabels]
    subax.set_thetagrids(xticks*180/np.pi, labels=xticklabels, fontsize=fontsize)
    subax.tick_params(axis='x', width=2, length=10, pad=15)
    tick = [subax.get_rmax(),subax.get_rmax()*0.95]
    for t in xticks: subax.plot([t,t], tick, lw=2, color="black")
    xsubticks = np.linspace (0, 2*np.pi, 41)
    xsubticks = xsubticks[np.logical_or (xsubticks<5*np.pi/4, xsubticks>7*np.pi/4)]        
    for t in xsubticks: subax.plot([t,t], tick, lw=0.75, color="k")
    ## Format angle
    #yticklabels = ['{0:.2f}'.format (y) for y in yticklabels]
    #subax.set_rgrids(yticks, labels=yticklabels, angle=0, fontsize=fontsize*0.5, ha='center')
    #subax.text(np.radians(subax.get_rlabel_position()-5), subax.get_rmax()/2., yunit, fontsize=fontsize*0.5,
    #         rotation=subax.get_rlabel_position(), ha='center',va='center')

    subax.grid(False)
    return

def PRES_plot (df, dot_time, index, now):
    
    ## Define constants for this plot
    #  1. Unit for this plot
    yunit ='millibar'
    #  2. Y-range - offset-ed by 0.5 degC 
    ylim = [np.floor (df.pressure.min())-0.5, np.ceil(df.pressure.max())+0.5]
    #  3. Y-ticks - always show 8 ticks only
    yticks = np.linspace (ylim[0], ylim[1], 8)
    yticklabels = yticks   
    
    ## Create a huuuge canvas!
    fig, axis = plt.subplots (1, 1, figsize=(32,16))
    
    ## 1. Plot pressure up to the dot_time
    before_dot = df[np.logical_and (df.index <= dot_time, ~df.pressure.isna())]
    axis.plot(before_dot.index, before_dot.pressure, c='blue', label='Air Pressure', linewidth=linewidth)
    #  a. Add blue dot for pressure at the dot
    latest = before_dot.tail(1)
    axis.scatter (latest.index[0], latest['pressure'][0], c='blue', s=markersize, alpha=0.7)    
    #  b. Add in subplot for barometer
    pressure_compass (axis, baroPos, df, dot_time, index, yunit, yticks, yticklabels, cmap, arrowstyle)
       

    ## 2. Add vertical line for "now" in LST
    nowstr = now.strftime('%Y-%m-%d %H:%M:00')
    axis.axvline (pd.to_datetime (nowstr), c='green',label='Current Time: '+ nowstr, linewidth=linewidth)
    
    # Format y-axis on left
    axis.set_ylim(ylim)
    axis.set_yticks (yticks)
    axis.set_ylabel('Observed Air Pressure ({0})'.format (yunit), fontsize=fontsize)
    ylabels = ['{0:4.1f}'.format (y) for y in yticklabels]
    axis.set_yticklabels (labels=ylabels, fontsize=fontsize)

    # Format x-axis
    axis.set_xlim (df.index[0],df.index[-1])
    xticks = df.index[np.logical_and (df.index.hour%6==0, df.index.minute==0 )]
    axis.set_xticks (xticks)
    axis.set_xticklabels (xticks.strftime ('%m-%d\n%H:%M'), rotation=50, fontsize=fontsize)
    axis.set_xlabel('Date time', fontsize=fontsize)
    
    ## Add grid lines
    for ytick in axis.get_yticks():
        axis.axhline (y=ytick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)
    for xtick in axis.get_xticks():
        axis.axvline (x=xtick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)
    
    ## Format title / layout
    axis.set_title('9410840 Santa Monica: '+ dot_time.strftime('%Y-%m-%d %H:%M:00'), fontsize=fontsize)
    lgd = axis.legend (bbox_to_anchor=(1, 1), loc='upper left', fontsize=fontsize)        
    plt.tight_layout()
    fig.savefig('./frames/frame_' + str(index).zfill(4) + '.jpg',bbox_extra_artists=(lgd,), bbox_inches='tight')
    
    
#     im = plt.imread (noaa_file)
#     plt.imshow (im)       
    
    ## Properly close the window for the next plot
    plt.close ('all')
    return


###################################################################################################################################
##                                               SUBPLOT                                                                         ##
###################################################################################################################################



def add_subplot_axes (ax, rect, color, yticks, isAir=False, showScale=False, doEnglish=False):
    
    ''' Function to create a standalone plot for a thermometer within an input axis.
    
        input params
        ------------
        ax (matplotlib.Axes): Axis to which this subplot is attached
        rect          (list): Position of subplot on main ax [x-coordinate, y-coordinate, width, height]
        color          (str): Color of thermometer bulb and tube
        yticks       (array): Y-tick values in degree C
        isAir      (boolean): If True, air temp is shown. Otherwise, water temp.
        showScale  (boolean): If True, shows a y-scale. Otherwise, no axis spines are shown.
        doEnglish  (boolean): If True, convert yticks from C to F. 
        
        return params
        -------------
        subax (matplotlib.Axes): Axis for the thermometer
    '''
    
    ## Create and locate a new thermomenter figure 
    fig = plt.gcf()    
    box = ax.get_position()
    width, height = box.width, box.height
    inax_position  = ax.transAxes.transform(rect[0:2])
    transFigure = fig.transFigure.inverted()
    infig_position = transFigure.transform(inax_position)    
    x = infig_position[0]
    y = infig_position[1]
    width *= rect[2]
    height *= rect[3]
    
    ## Get the axes handler for this figure
    subax = fig.add_axes([x,y,width,height])
    
    ## Format x & y axes
    subax.set_xlim(-10,10)
    subax.set_ylim(-10,tubeheight)
    #  Normalize input yticks to be within tube scale
    normalized_yticks = [normalized_temp (y, yticks[-1], yticks[0]) for y in yticks]
    subax.set_yticks (normalized_yticks)
    
    ## Format spines - Only left spine if asked
    #ax[0].axes.axis('off')
    subax.spines['top'].set_visible(False)
    subax.spines['right'].set_visible(False)
    subax.xaxis.set_ticks([])
    subax.spines['bottom'].set_color('none') 
    if showScale: 
        # Show left spine
        subax.yaxis.set_ticks_position('left')
        # Define y ticklabdels to be the same as main plot (instead of tube scale)
        yticklabels = from_C_to_F (yticks) if doEnglish else yticks      
        yunit ='$^\circ$F' if doEnglish else '$^\circ$C'
        ylabels = ['{0:4.1f}{1}'.format (y, yunit) for y in yticklabels]        
        subax.set_yticklabels (ylabels, fontsize=fontsize-5)
        # Format the spine line and ticks
        subax.spines['left'].set_linewidth(3)
        subax.tick_params(axis='y', width=2, length=10, pad=20)
    else:
        # Do not show left spine
        subax.yaxis.set_ticks([])
        subax.spines['left'].set_color('none') 
            
    ## Draw the tube as a patch, with round conrners, aligned with bulb's center
    #ax[0].plot([0,15],[100,100],c='black')
    #ax[0].plot([15,15],[0,100],c='black')
    #ax[0].plot([0,0],[0,100],c='black')    
    tube = matplotlib.patches.FancyBboxPatch ((-3.5,0), 7, tubeheight, linewidth=3, edgecolor=color, facecolor='none',
                                              boxstyle="round,pad=0,rounding_size=3.5", capstyle='round', joinstyle="round")
    ## Anchor this tube patch to this thermometer subplot
    subax.add_patch (tube)

    ## Draw the bulb as a patch centered at (0, 0) 
    #ax[0].scatter(7.3,-9,c='red',s=1500,edgecolor='black') #air     
    circle = plt.Circle ((0, 0), radius = 6, color=color)
    subax.add_patch (circle)
    
    ## Write temp type in the bulb with shadow
    tempType = 'Air' if isAir else 'Water'
    subax.annotate (tempType, xy=(0.1, -0.2), fontsize=fontsize-3, ha="center", va="center", color='#E8E8E8')
    subax.annotate (tempType, xy=(0, 0), fontsize=fontsize-3, ha="center", va="center", color='black')
    
    return subax







###################################################################################################################################
##                                               GIF                                                                             ##
###################################################################################################################################

def gif_maker(merged,gif_filename, plotType='waterLevel'):
    now = dt.datetime.now()
    last = now + dt.timedelta(hours=3)
    doFeet=True
    doEnglish=True
    for index, dot_time in enumerate (merged.index):
        doFeet = not doFeet
        if plotType == 'waterLevel':
            WL_plot(dot_time,index,now,merged,doFeet=doFeet)
        elif plotType == 'temp':
            TEMP_plot(dot_time,index,now,merged,doEnglish=doEnglish)
        elif plotType == 'wind':
            create_a_compass (df, dot_time, index, now, cmap, arrowstyle, doCurve=False, doEnglish=False)
        elif plotType == 'press':
            PRES_plot (df, dot_time, index, now)
            
        
        
    frames=[]
    imgs= glob.glob('./frames/*jpg')
    for i in imgs:
        new_frame=Image.open(i)
        frames.append(new_frame)
    frames[0].save(gif_filename, format='GIF', append_images=frames[1:],
               save_all=True, duration=8, loop=0)
#speed up time = small duration, slow down = large duration; duration is in miliseconds

# files = glob.glob('./frames/*jpg')
# for f in files:
#     os.remove(f)