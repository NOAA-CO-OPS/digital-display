#!/bin/python37

##
## By Elim Thompson 09/09/2020
##
## This script is a cron-like script to generate GIF files every 6 minutes. This
## script must be run together with hybridapp.py in order to have a webapp with
## plots updated.
## 
## To test plotter script, it is recommended to use generate_plots_standalone.py
## which is the same as this script minus the cron-like scheduling. This can
## remove the GIF generation every 6 mintues.
## 
## To run: 
##  $ python run_plot_schedule.py
## 
##############################################################################

#####################################
### Import libraries
#####################################
## Standard packages
import pytz, sys, schedule, time
import datetime as dt

## Custom packages to create gif
from plotter import product
from plotter.air_pressure import air_pressure
from plotter.temperature import temperature
from plotter.water_level import water_level
from plotter.wind import wind
from plotter.met import met

def create_gifs ():

    ## Define now - same across all products
    now = dt.datetime.now (pytz.timezone('US/Pacific'))
    print (now)

    ## Initialize met product
    met_product = met ()
    met_product.plot_path = 'plotter/plots/mets/'
    met_product.assets_path = 'assets/'
    met_product.now = now
    met_product.create_gif (doWindNeedle=False, three_columns=False)

    ## Initialize pressure product
    # pressure_product = air_pressure ()
    # pressure_product.plot_path = 'plotter/plots/pressures/'
    # pressure_product.assets_path = 'assets/'
    # pressure_product.now = now
    # pressure_product.create_gif ()

    # ## Initialize temperature product
    # temp_product = temperature ()
    # temp_product.plot_path = 'plotter/plots/temps/'
    # temp_product.assets_path = 'assets/'
    # temp_product.now = now
    # temp_product.create_gif ()

    # ## Initialize wind product
    # wind_product = wind ()
    # wind_product.plot_path = 'plotter/plots/winds/'
    # wind_product.assets_path = 'assets/'
    # wind_product.now = now
    # wind_product.create_gif (doNeedle=False)

    # # Initialize water level product
    water_level_product = water_level ()
    water_level_product.plot_path = 'plotter/plots/water_levels/'
    water_level_product.assets_path = 'assets/'
    water_level_product.now = now
    water_level_product.create_gif()

if __name__ == '__main__':

    ## Create the latest GIFs when this script is called
    create_gifs()

    ## Create GIFs every 6 minutes afterwards
    schedule.every(6).minutes.do(create_gifs)

    while 1:
        schedule.run_pending()
        time.sleep(1)