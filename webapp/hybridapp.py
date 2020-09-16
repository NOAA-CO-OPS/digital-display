#!/bin/python37

##
## By Elim Thompson 09/09/2020
##
## This script generates a webapp that follows CODE DDP team mock-up.
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
##############################################################################

#####################################
### Import libraries
#####################################
import flask, dash, pandas, pytz, os, time
import datetime as dt

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc 
from dash.dependencies import Output, Input
from flask_caching.backends import FileSystemCache
from dash_extensions.callback import CallbackCache

from plotter.water_level import water_level
from plotter.met import met

#####################################
### Define constants
#####################################
## Define pages
product_names = ['water_level', 'met']
product_pages = ['intro_video', 'water_level', 'sea_level_trend', 'met']

## Time format
TIDE_TABLE_TIME_FORMAT = '%I:%M %p'
TIME_FORMAT = '%m/%d/%Y %I:%M %p'
TIMEOUT = 20 # sec

## Panel style
PANEL_STATION_FONTSIZE = 30
PANEL_HEADER_FONTSIZE = 25
PANEL_DATA_FONTSIZE = 20
PANEL_TIDE_FONTSIZE = 20
PANEL_QR_FONTSIZE = 20

PANEL_WIDTH = 2
PANEL_BG_COLOR = '#ffffff'
PANEL_EDGELINE_COLOR = '#000f64'
PANEL_EDGELINE_WIDTH = 3

## 

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
    
    now = dt.datetime.now (pytz.timezone('US/Pacific'))
    print (now)

    ## Update all products
    #  Met
    met_product.now = now
    met_product._load_data()
    #  Water level
    water_level_product.now = now
    water_level_product._load_data()

    ## Bundle up the latest observation data
    latest = {'time': met_product.latest_obs_time.strftime (TIME_FORMAT),
              'air_temp': met_product.latest_air_temp,
              'water_temp': met_product.latest_water_temp,
              'air_pressure': met_product.latest_air_pressure,
              'wind_speed': met_product.latest_wind_speed,
              'wind_cardinal': met_product.latest_wind_cardinal,
              'gust_speed': met_product.latest_gust_speed,
              'gust_cardinal': met_product.latest_gust_cardinal,
              'water_level_obs': water_level_product.latest_obs}

    ## Bundle up hi-lo predictions: time, tide, height
    today_tides = water_level_product.get_today_tides()
    return latest, today_tides

def generate_table (dataframe, max_rows=3):

    dataframe['Time'] = dataframe.index.strftime (TIDE_TABLE_TIME_FORMAT)
    dataframe['Tide'] = ['High' if e == 'H' else 'Low' for e in dataframe.event]
    dataframe['Height'] = ['{0:.2f} ft'.format (float (v)) for v in dataframe.height]
    dataframe = dataframe.drop (axis=1, columns=['event', 'height'])

    return dbc.Table.from_dataframe(dataframe, striped=True, borderless=True,
            style={'width':400, 'height':150, 'marginBottom':30, 'marginTop':5, 'marginLeft':10})

def panel_layout():

    return dbc.Col(
        html.Div([
            ## NOAA TAC logo
            dbc.Row ([html.Img (src='/assets/noaa_logo.png',
                                style={'width':100, 'height':100, 'marginBottom': 30, 'marginTop': 10, 'marginLeft':10}),
                      html.Img (src='/assets/tac_logo.jpeg',
                                style={'width':230, 'height':90, 'marginBottom': 30, 'marginTop': 10, 'marginLeft':10})]),
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
                          style={'fontSize':PANEL_HEADER_FONTSIZE, 'marginBottom': 10, 'marginTop': 20, 'marginLeft':0}),
            html.Table(id='tide_table'),

            ## QR code
            dbc.Row ([html.Img (src='/assets/qr_code.jpg',
                                style={'width':130, 'height':130, 'marginBottom': 30, 'marginTop': 10, 'marginLeft':10}),
                      html.P ('This NOAA tide station measures local water level & meteorological conditions. '+
                              'Scan the QR code for more information!', 
                              style={'width':300, 'height':130, 'marginBottom': 30, 'marginTop': 15, 'marginLeft':10})
            ])
        ], style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18,
                  "border-right":"2px #007bae solid"})
    , width=PANEL_EDGELINE_WIDTH)

def hybrid_layout():

    return html.Div([
        # Left column - panel
        dbc.Row ([panel_layout(),
        # Right column - plots
        html.Div([
            html.Img(id='image',
                     style={'width':1400, 'height':1000})
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
app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP])
cc = CallbackCache()  # create callback cache
app.layout = hybrid_layout

@cc.callback ([Output('image', 'src')],
              [Input('interval-page', 'n_intervals')])
def update_plot(n_pages):

    print ('cycling page: {0}'.format (n_pages))
    n_pages = (n_pages) % len (product_pages)
    ## Add in a random part to URL to force browser to refresh every time
    random_string = dt.datetime.now ().strftime ('%Y%m%d%H%M%S')
    image = app.get_asset_url(product_pages[n_pages] + '.gif?random=' + random_string)
    return image

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

    print ('re-loading data: {0}'.format (n_updates))

    ## Update products and get the latest info
    latest, today_tides = update_products ()
    ## Define the text on the left panel
    latest_time = '{0} Local Time'.format (latest['time'])
    latest_water_level = '**Water Level**: {0:.3f} ft Above MLLW'.format (latest['water_level_obs'])
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

    ## Define the different products
    app.run_server(debug=True)