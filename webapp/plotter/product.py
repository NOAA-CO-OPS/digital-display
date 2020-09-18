#!/bin/python37

##
## By Julia Engdahl 09/08/2020
## Modified by Elim Thompson 09/09/2020
##
## This script is only a class and should not be called by itself. To use
## this library, check out generate_plot_standalone.py
##
## Julia's original script, ddp_plots.py, contains functions to generate water
## level, temperature, wind, pressure plots and to concatenate them into GIF. 
##  * water level: time-series with prediction and observation
##  * temperature: both water and air temp as time-series and thermometers
##  * wind       : polar plot (i.e. no time-series)
##  * pressure   : time-series with a barometer
##
## Elim's modification:
##  * Turned ddp_plots.py into a product and their children classes
##  * Added ability to do both time-series + object and object alone
##  * Included a MET product to group temp, wind, pressure together
##
## Example snippet to use data_cleaner class
## +------------------------------------------------------------------
## # Initialize a new product class
## import product
## product_name = 'water_level'
## aproduct = product.product(product_name)
##
## # Set up the paths for individual plots
## aproduct.plot_path = 'plots/pressures/'
## # Set up the paths for animated GIF
## aproduct.assets_path = '../assets/'
##
## # Set up "current time"
## import datetime, pytz
## aproduct.now = datetime.datetime.now (pytz.timezone('US/Pacific'))
##
## # Generate GIF with the latest data on API
## aproduct.create_gif ()
## +------------------------------------------------------------------
##############################################################################

###############################################
## Import libraries
###############################################
import requests, pytz, glob, os
import numpy as np
import pandas as pd
import datetime as dt
from PIL import Image, ImageDraw

import matplotlib
matplotlib.use ('Agg')
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
plt.rc ('text', usetex=False)
plt.rc ('font', family='sans-serif')
plt.rc ('font', serif='Computer Modern Roman')

###############################################
## Define constants
###############################################
## Acceptable product name
PRODUCT_NAMES = ['water_level', 'temperature', 'air_pressure', 'wind', 'met']

## API template
##  * at Santa Monica 9410840
##  * local time LST/DST
##  * in English unit (feet, degF)
##  * in JSON for python dictionary
##  * water level at MLLW
API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + \
      "begin_date={begin_date}&end_date={end_date}&station=9410840" + \
      "&product={product}&interval={interval}&datum=MLLW&time_zone=lst_ldt" + \
      "&units=english&format=json"

## Time zone of Santa Monica
STATION_TIME_ZONE = 'US/Pacific'

## General current time label / format for display
#  "current time" means the most recent data time
TIME_FORMAT = '%m/%d/%Y %I:%M %p'
CURRENT_TIME_LABEL = 'Current Time'

## Number of hours before and after current time for data pulling and plotting
HOURS_PAD_BEFORE = 12
HOURS_PAD_AFTER = 3

## GIF formatting
GIF_LOOP = 1               # Loop once only. 0 for infinite loop
GIF_TOTAL_DURATION_SEC = 3 # Total duration in sec for the plot
TOGGLE_UNITS_FREQ = 1000   # Number of frames for unit toggling. Set it to
                           # super large to have no toggling

## General plotting style
DPI = 96 # Dots per inch
FIG_SIZE = (1400/DPI, 1000/DPI) # Figure size based on dots per inch
FONTSIZE = 17 # Font size of text 

## Styling for time-series plots
N_YTICKS = 8
LINEWIDTH = 5
MARKERSIZE = 100
XTICKLABEL_TIME_FORMAT = '%m-%d %H'
XTICKLABEL_HOURS = np.linspace (0, 22, 12) # X-ticks at even hours

## Number of continuous bad data to trigger no-plotting
N_HOURS_NULL_DATA = 4

## Acceptable number types
NUMBER_TYPES = [float, int, np.float, np.float16, np.float32, np.float64,
                np.int, np.int0, np.int8, np.int16, np.int32, np.int64]

## Acceptable array types
ARRAY_TYPES = [list, tuple, np.ndarray]

###############################################
## Define product parent class
###############################################
class product (object):

    ''' This class encapsulates common functions for all products in DDP '''

    def __init__ (self, product_name):

        ''' To initialize a product instance '''

        ## Product is initialized by a product name. 
        ## Acceptable names are listed in PRODUCT_NAMES.
        self._check_product_name (product_name)
        self._product_name = product_name

        ## Variables storing the most recent 6-minute data
        self._now = None
        self._latest_data_df = None
        self._hours_pad = [HOURS_PAD_BEFORE, HOURS_PAD_AFTER]

        ## GIF settings
        self._do_animation = True
        self._gif_loop = GIF_LOOP
        self._gif_total_duration_sec = GIF_TOTAL_DURATION_SEC
        self._toggle_units_freq = TOGGLE_UNITS_FREQ

        ## Plot settings
        self._fontsize = FONTSIZE
        self._fig_size = FIG_SIZE
        self._linewidth = LINEWIDTH
        self._markersize = MARKERSIZE

        ## Plots locations
        self._plot_path = None
        self._assets_path = None

    # +------------------------------------------------------------
    # | Getters & setters
    # +------------------------------------------------------------
    @property
    def is_met (self): return self._product_name != 'water_level'

    @property
    def latest_obs (self):
        if self._latest_data_df is None: return None
        if not 'observed' in self._latest_data_df: return None
        not_na = ~self._latest_data_df.observed.isna()
        return self._latest_data_df.observed.values[not_na][-1]

    @property
    def latest_obs_time (self):
        if self._latest_data_df is None: return None
        not_na = ~self._latest_data_df.observed.isna()
        return self._latest_data_df.observed.index[not_na][-1]

    @property
    def has_all_nan (self):
        ## If dataframe is None -> no past data
        if self._latest_data_df is None: return False
        ## Slice out observed data from N hours before obs time
        begin_time = self.latest_obs_time - pd.offsets.Hour (N_HOURS_NULL_DATA)
        end_time = self.latest_obs_time
        observed = self._latest_data_df.loc[begin_time:end_time,].observed
        ## Check if all observed data in this time window is invalid
        return observed.isna().all()

    @property
    def now (self): return self._now
    @now.setter
    def now (self, aDateTime):
        ## Make sure input is a datetime object with station time zone
        self._check_is_valid_date_time (aDateTime)  
        self._now = aDateTime

    @property
    def plot_path (self): return self._plot_path
    @plot_path.setter
    def plot_path (self, apath):
        ## Make new folder if it doesn't exist
        if not os.path.exists (apath): os.mkdir (apath)
        self._plot_path = apath

    @property
    def assets_path (self): return self._assets_path
    @assets_path.setter
    def assets_path (self, apath):
        ## Make sure input path exists
        self._check_file_path_existence (apath)
        self._assets_path = apath

    @property
    def product_name (self): return self._product_name
    @product_name.setter
    def product_name (self, name):
        ## Make sure product name is one of the accepted options
        self._check_product_name (name)
        self._product_name = name

    @property
    def hours_pad_before (self): return self._hours_pad[0]
    @hours_pad_before.setter
    def hours_pad_before (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is positive, non-zero
        if number <= 0:
            message = 'Number of pad hours, {0}, cannot be 0 or -ve.'.format (number)
            raise IOError (message)
        self._hours_pad[0] = number

    @property
    def hours_pad_after (self): return self._hours_pad[1]
    @hours_pad_after.setter
    def hours_pad_after (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is positive
        if number < 0:
            message = 'Number of pad hours, {0}, cannot be -ve.'.format (number)
            raise IOError (message)      
        self._hours_pad[1] = number        

    @property
    def fig_size (self): return self._fig_size
    @fig_size.setter
    def fig_size (self, fig_size):
        ## Make sure input is an array of 2 elements
        self._check_is_array (fig_size, length=2)
        ## Make sure the elements are numbers
        for elem in fig_size: self._check_is_number (elem)
        self._fig_size = fig_size

    @property
    def linewidth (self): return self._linewidth
    @linewidth.setter
    def linewidth (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is 0 or positive
        if number < 0:
            raise IOError ('Linewidth must be >= 0.')
        self._linewidth = number

    @property
    def markersize (self): return self._markersize
    @markersize.setter
    def markersize (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is positive
        if number < 0:
            raise IOError ('Markersize must be positive.')
        self._markersize = number

    @property
    def fontsize (self): return self._fontsize
    @fontsize.setter
    def fontsize (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        ## Make sure this number is positive
        if number < 0:
            raise IOError ('Fontsize must be positive.')
        self._fontsize = number

    @property
    def do_animation (self): return self._do_animation
    @do_animation.setter
    def do_animation (self, aBoolean):
        ## Make sure input is a boolean
        if not isinstance (aBoolean, bool):
            raise IOError ('Please provide a boolean for do_animation.')
        self._do_animation = aBoolean

    @property
    def gif_loop (self): return self._gif_loop
    @gif_loop.setter
    def gif_loop (self, anInt):
        ## Make sure input is a number
        self._check_is_number (anInt)
        ## Make sure input is either 0 or 1
        if not anInt == 0 and not anInt == 1:
            raise IOError ('Please provide either 0 or 1 for git_loop.')
        self._gif_loop = anInt

    @property
    def gif_total_duration_sec (self): return self._gif_total_duration_sec
    @gif_total_duration_sec.setter
    def gif_total_duration_sec (self, number):
        ## Make sure input is a number
        self._check_is_number (number)
        self._gif_total_duration_sec = number
    
    @property
    def toggle_units_freq (self): return self._toggle_units_freq
    @toggle_units_freq.setter
    def toggle_units_freq (self, anInt):
        ## Make sure input is an integer
        if not isinstance (anInt, int):
            raise IOError ('Please provide an integer for toggle_units_freq.')
        self._toggle_units_freq = anInt

    # +------------------------------------------------------------
    # | Misc functions
    # +------------------------------------------------------------
    def _check_file_path_existence (self, afilepath):

        ''' A private function to check if an input file path exists. If it
            doesn't a FileNotFoundError is raised.
            
            input param
            -----------
            afilepath (str): A folder to be checked
        '''

        if not os.path.exists (afilepath):
            message = 'Path or file, {0}, does not exist!'.format (afilepath)
            self._logger.fatal (message)
            raise FileNotFoundError (message)

    def _check_product_name (self, name):
    
        ''' A private function to check if an input name is one of the good
            PRODUCT_NAMES. If it isn't, an IOError is raised.
            
            input param
            -----------
            name (str): A name to be checked
        '''

        if not name in PRODUCT_NAMES:
            message = 'Product name, {0}, is not accepted.'
            message += 'Please provide one of the followings: {1}'
            raise IOError (message.format (name, PRODUCT_NAMES))

    def _check_is_number (self, number):
    
        ''' A private function to check if an input number is a float or int
            with a finite, valid value. If it doesn't an IOError is raised.
            
            input param
            -----------
            number (anything): A value to be checked
        '''

        if not type (number) in NUMBER_TYPES:
            message = 'Input, {0}, is not a float or int.'.format (number)
            raise IOError (message)

        if not np.isfinite (number):
            message = 'Input, {0}, cannot be nan or infinite.'.format (number)
            raise IOError (message)

    def _check_is_valid_date_time (self, aDateTime):

        ''' A private function to check if an input number is a valid date time
            object at Santa Monica. If it doesn't an IOError is raised.
            
            input param
            -----------
            aDateTime (anything): A value to be checked
        '''

        if not isinstance (aDateTime, dt.datetime):
            message = 'Date-time, {0}, is not a datetime object.'.format (aDateTime)
            raise IOError (message)

        if not aDateTime.tzinfo.zone == STATION_TIME_ZONE:
            message = 'Date-time, {0}, is not at station time zone of {1}.'
            raise IOError (message.format (aDateTime, STATION_TIME_ZONE))

    def _check_is_array (self, array, length=None):
    
        ''' A private function to check if an input array is a numpy array, a
            list, or a tuple. If it isn't, an IOError is raised. If length is
            provided, check if the input array has the required length.
            
            input param
            -----------
            array (anything): A value to be checked
            length (int): Required length of the input array
        '''

        ## 1. Check if input array is a valid array type.
        if not type (array) in ARRAY_TYPES:
            message = 'Input, {0}, is not an array / list / tuple.'.format (array)
            self._logger.fatal (message)
            raise IOError (message)

        ## Leave if no specific (integer) length required
        if length is None: return
        if not isinstance (length, int): return

        ## 2. Check if input array has a specific length
        if not len (array) == length:
            message = 'Input, {0}, does not have a length of {1}.'
            self._logger.warn (message.format (array, length))

    # +------------------------------------------------------------
    # | Pull latest data
    # +------------------------------------------------------------
    def _pull_data (self, product_name, interval, begin_date, end_date):

        # Fill in the template to get the actual API
        api = API.format (**{'product':product_name, 'interval':interval,
                             'begin_date':begin_date, 'end_date':end_date})
        # Get the response of the API
        response = requests.get (api)
        # If the status code of the response is anything but 200, return nothing
        if not response.status_code == 200:
            print ('Connection failed with {0}.'.format (response.status_code))
            return None
        
        # Get the content of the API as JSON
        content = response.json()
        # If the content is an error message, something is wrong with the input params.
        # Print the error and return nothing.
        if 'error' in content:
            print ('Error encountered: {0}.'.format (content['error']['message']))
            return None
        # If no data is available, tell user to check the API itself and return nothing.
        if len (content) == 0:
            print ('Empty content encountered. Please check API:\n{0}.'.format (api))
            return None
        # Content must have either data or predictions. If neither, return None.
        if not 'data' in content and not 'predictions' in content:
            print ('Either data or predictions keys are available. Please check API:\n{0}.'.format (api))
            return None

        return content

    def _transform_api_data (self, api_data):

        ## If no data is available, raise an error
        if len (api_data) == 0:
            print ('No data / predictions are available.')
            return None

        ## Extract the keys in data to be column names later
        columns = api_data[0].keys()
        #  If 't' key doesn't exist, something must be wrong with the API
        if not 't' in columns:
            print ('Time column \'t\' is not available from API.')
            return None

        ## Convert the data from JSON object to arrays of arrays
        data = np.array ([[value for key, value in aTime.items()]
                           for aTime in api_data]).T

        ## Populate arrays into dataframe with column name = keys from API
        dataframe = pd.DataFrame ({key:value for key, value in zip (columns, data)})
        #  Replace any empty string by nan
        dataframe = dataframe.replace ('', np.nan)
        #  Convert dataframe into a time-series dataframe
        dataframe.index = pd.to_datetime (dataframe['t'])
        dataframe = dataframe.drop (axis=1, columns='t')
        return dataframe

    def _load_latest (self, is_hilo=False, is_predictions=False, product_name=None,
                      begin_date=None, end_date=None):

        ## Flags are only valid if this product is water level
        if self.is_met and (is_hilo or is_predictions):
            raise IOError ('Cannot obtain HiLo or predictions for met data.')
        ## If it is hi-lo, it must be predictions
        if is_hilo: is_predictions = True

        ## Define parameters for API
        interval = 'hilo' if is_hilo else '1' if is_predictions else '6'
        if product_name is None:
            product_name = 'predictions' if is_predictions else self.product_name
        if begin_date is None:
            begin_date = self._now - dt.timedelta (hours=self._hours_pad[0])
        if end_date is None:
            end_date   = self._now + dt.timedelta (hours=self._hours_pad[1])

        ## Pull latest data around now
        content = self._pull_data (product_name, interval, 
                                   begin_date.strftime ('%Y%m%d'),
                                   end_date.strftime ('%Y%m%d'))

        ## If key "predictions" is available, this is a request to pull water
        ## level predictions. Otherwise, it is pulling data with 'data' key.
        data_key = 'predictions' if is_predictions else 'data'

        ## Convert the data into time-series dataframe
        df = self._transform_api_data (content[data_key])

        ## Trim off hours. Some how API doesn't work well with yyyymmdd HH:MM
        ## with 24 hour notation.
        df = df[df.index >= begin_date.strftime ('%Y%m%d %H:%M')]
        df = df[df.index <= end_date.strftime ('%Y%m%d %H:%M')]

        return df

    # +------------------------------------------------------------
    # | Plot & animation
    # +------------------------------------------------------------
    def _plot_obs_time_series (self, axis, df, dot_time, ylimits, yticks,
                               yticklabels, ylabel, do_1_decimal_place=False):

        ## Do not plot time-series if wind
        if self.product_name == 'wind':
            raise IOError ('No time-series plot for wind product!')

        # 1. Plot observation up to dot time
        before_dot_obs = df[np.logical_and (df.index <= dot_time, ~df.observed.isna())]
        axis.plot(before_dot_obs.index, before_dot_obs.observed, c='red',
                  label='Observed', linewidth=self._linewidth, alpha=0.7)

        # 2. Add red dot for obs
        latest_obs = before_dot_obs.tail(1)
        if np.isfinite (latest_obs['observed'][0]):
            axis.scatter (latest_obs.index[0], latest_obs['observed'][0], c='red',
                        s=self._markersize, alpha=0.7)

        # 3. Add vertical line for recent data time in LST/LDT
        axis.axvline (self._now.strftime ('%Y-%m-%d %H:%M'), color='green',
                      label=CURRENT_TIME_LABEL, linewidth=self._linewidth, alpha=0.7)

        # 4. Format x-axis
        axis.set_xlim(df.index[0],df.index[-1])
        xticks = df.index [np.logical_and (df.index.hour.isin (XTICKLABEL_HOURS), df.index.minute==0)] 
        axis.set_xticks (xticks)
        xticklabels = [x.strftime (XTICKLABEL_TIME_FORMAT) for x in xticks]
        axis.set_xticklabels (xticklabels, rotation=25, fontsize=self._fontsize)
        axis.set_xlabel('Date time', fontsize=self._fontsize, labelpad = 23)
        
        # 5. Format y-axis
        axis.set_ylim (ylimits)
        axis.set_yticks (yticks)
        yfmt = '{0:.1f}' if do_1_decimal_place else '{0:.2f}'
        yticklabels = [yfmt.format (y) for y in yticklabels]
        axis.set_yticklabels (yticklabels, fontsize=self._fontsize)
        axis.set_ylabel (ylabel, fontsize=self._fontsize, labelpad = 23)
        
        # 6. Add grid lines
        for ytick in axis.get_yticks():
            axis.axhline (y=ytick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)
        for xtick in axis.get_xticks():
            axis.axvline (x=xtick, color='gray', alpha=0.7, linestyle=':', linewidth=1.0)

    def _make_gif (self):
        
        ## Collect input JPEG images
        img_files = glob.glob (self.plot_path + '/*.jpg')
        
        ## Output gif to assets folder
        gif_file = self.assets_path + '/' + self.product_name + '.gif'

        ## Gather all frames and make sure files are all properly closed.
        frames = []
        for img_file in img_files:
            with open (img_file, 'rb') as f:
                image = Image.open(f)
                frames.append (image.copy())
            image.close()
            f.close()

        ## If don't do animation, store the last frame as '.gif' for
        ## consistency with webapp code.
        if not self.do_animation:
           frames[-1].save (gif_file, format='GIF')
           return

        # Calculate time (ms) per frame
        duration_ms = self.gif_total_duration_sec / len (frames) * 1000

        frames[0].save (gif_file, format='GIF', append_images=frames[1:],
                        save_all=True, duration=duration_ms, loop=self.gif_loop)
