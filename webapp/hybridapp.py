#!/bin/python37

##
## By Elim Thompson 09/09/2020
##
## This script generates a webapp that follows CODE DDP team mock-up. This
## script must be run with run_plot_schedule.py in order for the GIF plots to
## be updated.
## 
## To run: 
## * install flask, dash, and dash_bootstrap_components
## * git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
## * download all mp4 / gif from
##   https://drive.google.com/drive/folders/1DzG6dCOlgtjsexzx0y2UKUY49m6B2Gtw?usp=sharing
##   to digital-display/webapp/assets/
## * run python hybridapp.py
## * open browser and go to http://localhost:8050
##
## If you see the plot below the menu panel, make sure your chrome browser is
## wide. If it gives error messages, keep refreshing the page (or Ctrl-F5).
##
## Potential work for future:
##  * Move all "style" to a separate CSS file
##  * Add plotly to generate plots instead of GIF
##
##############################################################################

#####################################
### Import libraries
#####################################
## Standard packages
import flask, dash, pandas, pytz, os, time
import datetime as dt

## Packages for webapp
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc 
from dash.dependencies import Output, Input
from flask_caching.backends import FileSystemCache
from dash_extensions.callback import CallbackCache

## Custom packages to get the latest data
from plotter.water_level import water_level
from plotter.met import met

#####################################
### Define constants
#####################################
## Define products for this app
#  Hybrid app has only water level and met products
product_names = ['water_level', 'met']
#  Hybrid app loops through 4 pages in the following order
product_pages = ['intro_video', 'water_level', 'sea_level_trend', 'met']
#  If null data for N hours, loop through 2 pages in the following order
default_pages = ['intro_video', 'sea_level_trend']

## Define keys in latest data for left panel
LATEST_KEYS = ['air_temp', 'water_temp', 'air_pressure', 'wind_speed', 
               'wind_cardinal', 'gust_speed', 'gust_cardinal', 'water_level_obs']

## Time format
TIDE_TABLE_TIME_FORMAT = '%I:%M %p'
TIME_FORMAT = '%m/%d/%Y %I:%M %p'

## Panel style
PANEL_STATION_FONTSIZE = 30
PANEL_HEADER_FONTSIZE = 25
PANEL_DATA_FONTSIZE = 20
PANEL_TIDE_FONTSIZE = 20
PANEL_QR_FONTSIZE = 20

PANEL_WIDTH = 3
PANEL_BG_COLOR = '#ffffff'
PANEL_EDGELINE_COLOR = '#0080ff'
PANEL_EDGELINE_WIDTH = 2

#####################################
### Define products
#####################################
## Initialize met product
met_product = met ()
met_product.plot_path = 'plotter/plots/mets/'
met_product.assets_path = 'assets/'

## Initialize water level product
water_level_product = water_level ()
water_level_product.plot_path = 'plotter/plots/water_levels/'
water_level_product.assets_path = 'assets/'

#####################################
### Define functions
#####################################
def update_products ():
    
    ''' Function to update products. Expected to be called every 6 minutes. If
        nan data is detected in the past N hours (N_HOURS_NULL_DATA defined in
        product.py), a string is returned indicating no data is available.

        Elim was hoping to add the 'gif-making' process in this function as
        well, but the animation (specifically the "frames[0].save()" seems to 
        break the site. So the 'gif-making' process is moved to a separate
        script called run_plot_schedule.py. One day, when we move to plotly,
        this function is where the plotly step should live.

        return params
        -------------
        latest (dict): Dict storing all latest data for left panel
        today_tides (pandas.DataFrame): previous and next two tides
    '''

    ## Define the "now" time - same across all products
    now = dt.datetime.now (pytz.timezone('US/Pacific'))

    ## Update all products
    #  Met
    met_product.now = now
    met_product._load_data()
    #  Water level
    water_level_product.now = now
    water_level_product._load_data()

    ## Does any of the above products has all NaN data?
    has_all_nan = met_product.has_all_nan or water_level_product.has_all_nan
    print (now)
    print ('has all NaN? {0}'.format (has_all_nan))

    ## Bundle up the latest observation data
    latest = {'time': met_product.latest_obs_time.strftime (TIME_FORMAT)}
    for key in LATEST_KEYS:
        # default NaN
        value = 'Data is temporarily unavailable'
        # if we have data, get the latest observation
        if not has_all_nan:
            value = met_product.latest_air_temp if key=='air_temp' else \
                    met_product.latest_water_temp if key=='water_temp' else \
                    met_product.latest_air_pressure if key=='air_pressure' else \
                    met_product.latest_wind_speed if key=='wind_speed' else \
                    met_product.latest_wind_cardinal if key=='wind_cardinal' else \
                    met_product.latest_gust_speed if key=='gust_speed' else \
                    met_product.latest_gust_cardinal if key=='gust_cardinal' else \
                    water_level_product.latest_obs # key=='water_level_obs'
        # add value to dict
        latest[key] = value

    ## Bundle up hi-lo predictions: time, tide, height
    today_tides = water_level_product.get_today_tides()
    return latest, today_tides

def generate_table (dataframe):

    ''' Function to reformat tide table for display. The column names are the
        table headers on the display. This function also uses dbc to nicely
        display the table. See this site for different styling & options:
        https://dash-bootstrap-components.opensource.faculty.ai/docs/components/table/

        input param
        -----------
        dataframe (pandas.DataFrame): previous and next two tides

        return param
        ------------
        dbc.Table: formatted table ready to be displayed
    '''

    dataframe['Time'] = dataframe.index.strftime (TIDE_TABLE_TIME_FORMAT)
    dataframe['Tide'] = ['High' if e == 'H' else 'Low' for e in dataframe.event]
    dataframe['Height'] = ['{0:.2f} ft'.format (float (v)) for v in dataframe.height]
    dataframe = dataframe.drop (axis=1, columns=['event', 'height'])

    return dbc.Table.from_dataframe(dataframe, striped=True, borderless=True,
            style={'width':400, 'height':150, 'marginBottom':30, 'marginTop':5, 'marginLeft':10})

def panel_layout():

    ''' Function to define panel layout on the left. From top to bottom:
            * NOAA + TAC logo
            * station name and ID
            * header for "Recent Data"
                * time stamp
                * water level
                * water temperature
                * air temperature
                * air pressure
                * wind speed + direction
                * gust speed + direction
            * header for "Today's Tides"
                * table with 1 previous and 2 next tides
            * QR code + text
        
        To move the ordering, adjust the "dcc.Markdown" with the different IDs
        to the order of your liking.

        return param
        ------------
        dbc.Col: Column of left panel layout
    '''

    return dbc.Col(
        html.Div([
            ## 1 row with 2 items: NOAA logo + TAC logo
            dbc.Row ([html.Img (src='/assets/noaa_logo.png',
                                style={'width':100, 'height':100, 'marginBottom':30, 'marginTop':10, 'marginLeft':10}),
                      html.Img (src='/assets/coops_logo.jpeg',
                                style={'width':384, 'height':69, 'marginBottom':30, 'marginTop':10, 'marginLeft':10})]),
            ## Station header
            dcc.Markdown ('**Santa Monica, CA** 9410840', style={'fontSize':PANEL_STATION_FONTSIZE}),
            ## Most recent data
            dcc.Markdown ('**Recent Data** as of', style={'fontSize':PANEL_HEADER_FONTSIZE}),
            dcc.Markdown (id='latest_time', style={'fontSize':PANEL_HEADER_FONTSIZE}),
            dcc.Markdown (id='latest_water_level', style={'backgroundColor':'#ffffff'}),
            dcc.Markdown (id='latest_water_temp', style={'backgroundColor':'#ffffff'}),
            dcc.Markdown (id='latest_air_temp', style={'backgroundColor':'#ffffff'}),
            dcc.Markdown (id='latest_air_pressure', style={'backgroundColor':'#ffffff'}),
            dcc.Markdown (id='latest_winds', style={'backgroundColor':'#ffffff'}),
            dcc.Markdown (id='latest_gust', style={'backgroundColor':'#ffffff'}),
            ##  Today's tide table
            dcc.Markdown ('**Today\'s Tides**',
                          style={'fontSize':PANEL_HEADER_FONTSIZE, 'marginBottom':10, 'marginTop':20, 'marginLeft':0}),
            html.Table(id='tide_table'),
            ## 1 row with 2 columns: QR code + text
            dbc.Row ([html.Img (src='/assets/qr_code.jpg',
                                style={'width':130, 'height':130, 'marginBottom':30, 'marginTop':10, 'marginLeft':10}),
                      html.P ('This NOAA tide station measures local water level & meteorological conditions. ' +
                              'Scan the QR code for more information!', 
                              style={'width':300, 'height':130, 'marginBottom':30, 'marginTop':15, 'marginLeft':10})
            ])
        ], 
        ## Border line
        style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18,
               "border-right":"{0}px {1} solid".format (PANEL_EDGELINE_WIDTH, PANEL_EDGELINE_COLOR),
               "backgroundColor":PANEL_BG_COLOR})
    , width=PANEL_WIDTH)

def hybrid_layout():

    ''' Function to define webapp layout: panel on left + gif on right. Two
        firings are defined: 
            * interval-page = fire a switch of slide (default 18s)
                              i.e. update_plot()
                              Make sure it matches the video's
            * interval-panel = fire a new data download (default 6min)
                               i.e. update_latest()

        return param
        ------------
        html.div: webapp layout + firing events
    '''

    return html.Div([
        ## Left column - panel
        dbc.Row ([panel_layout(),
        ## Right column - plots
        html.Div([
            html.Img(id='image', style={'width':1400, 'height':1000})
        ], style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15,
                  'marginRight':5, 'fontSize':18,'display':'block'}),
        ]), 
        ## Interval to switch between plots - 18 sec - must match intro video
        dcc.Interval(
            id='interval-page',
            interval=18*1000, 
            n_intervals = 0
        ),
        ## Interval to retrive data - 6 min = 6*60 = 360 sec
        dcc.Interval(
            id='interval-panel',
            interval=360000,
            n_intervals = 0
        )
    ])

#####################################
### Define new App
#####################################
## App with cache to make sure new plots are always pulled
app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP])
cc = CallbackCache() 
app.layout = hybrid_layout

@cc.callback ([Output('image', 'src')],
              [Input('interval-page', 'n_intervals')])
def update_plot(n_pages):

    ''' Function to update plot. Input n_pages is from n_intervals attribute
        in interval-page (dcc.Interval) object. N_pages counts from 0 to inf.
        Everytime interval-page fires, n_pages is incremented by 1 i.e. n_pages
        counts how many times interval-page is fired.
        
        N_pages is used to determine which page to show. Normally, its remainder
        when divided by # pages determines which of the gif files to show. If
        the global variable has_all_nan is True, it will only toggle between
        intro_video and sea_level_trend gifs.

        input params
        ------------
        n_pages (int): counter of how many times interval-page is fired

        output params
        -------------
        image: the image to be displayed pulled from the asset folder
    '''

    ## Do we have all NaN data?
    has_all_nan = met_product.has_all_nan or water_level_product.has_all_nan
    print ('cycling page (has all nan?): {0} ({1})'.format (n_pages, has_all_nan))

    ## Define pages based on has_all_nan
    pages = default_pages if has_all_nan else product_pages
    ## Get the remainder to define the index of images to be pulled
    n_pages = (n_pages) % len (pages)
    ## Add in a random part to URL to force browser to refresh every time
    random_string = dt.datetime.now ().strftime ('%Y%m%d%H%M%S')
    ## Pull the image from asset folder
    return app.get_asset_url(pages[n_pages] + '.gif?random=' + random_string)

@cc.callback ([Output('latest_time', 'children'),
                Output('latest_water_level', 'children'),
                Output('latest_water_temp', 'children'),
                Output('latest_air_temp', 'children'),
                Output('latest_air_pressure', 'children'),
                Output('latest_winds', 'children'),
                Output('latest_gust', 'children'),
                Output('tide_table', 'children')],
              [Input('interval-panel', 'n_intervals')])
def update_latest(n_updates):

    ''' Function to update the latest data on the left panel. Input n_updates
        counts the number of times data is being updated. When no data is valid
        for N hours, a string is displayed.

        input params
        ------------
        n_updates (int): counter of how many times interval-panel is fired

        output params
        -------------
        latest_time (str): Latest Local DST timestamp
        latest_water_level (str): Latest observed water level
        latest_water_temp (str): Latest water temperature
        latest_air_temp (str): Latest air temperature
        latest_air_pressure (str): Latest air pressure
        latest_wind (str): Latest wind speed and direction
        latest_gust (str): Latest gust speed and direction
        tide_table (dbc.table): Latest tide table ready to be displayed
    '''

    print ('re-loading data: {0}'.format (n_updates))

    ## Update products and get the latest info
    latest, today_tides = update_products ()

    ## Define the text on the left panel
    latest_time = '{0} Local Time'.format (latest['time'])
    latest_water_level = '**Water Level**: {0:.2f} ft Above MLLW'.format (latest['water_level_obs'])
    latest_water_temp = '**Water Temp**: {0:.0f}&deg;F'.format (latest['water_temp'])
    latest_air_temp = '**Air Temp**: {0:.0f}&deg;F'.format (latest['air_temp'])
    latest_air_pressure = '**Barometric Pressure**: {0:.1f} mb'.format (latest['air_pressure'])
    latest_winds = '**Winds**: {0:.2f} kts from {1}'.format (latest['wind_speed'], latest['wind_cardinal'])
    latest_gust = '**Gusting to**: {0:.2f} kts from {1}'.format (latest['gust_speed'], latest['gust_cardinal'])

    return latest_time, latest_water_level, latest_water_temp, latest_air_temp, \
           latest_air_pressure, latest_winds, latest_gust, generate_table (today_tides)

cc.register(app)
#####################################
### Script starts here!
#####################################
if __name__ == '__main__':

    ## Run app with debug!
    #  dev_tools_hot_reload = False prevents reloading of website when
    #  files in assets are modified
    app.run_server(debug=True, dev_tools_hot_reload=False)