#!/bin/python

###
### By Elim Thompson 08/13/2020
### 
### Combining Flask and dash to build a dash board. This dash board
###  * have a left panel with the most recent water level, water temp, air temp, air pressure,
###    winds, gust, and current local time. Latest data is pulled from data API.
###  * On the right, plots cycles from water level, etc, to wind and back to water level.
### This script points to the assets/ folder for plots.
###
### To do.. 
###  1. Highlight the current item on the left panel
###  2. Add in intro video
### 
### To run: 
###  * install flask, dash, and dash_bootstrap_components
###  * $ git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
###  * download all mp4 / gif from
###        https://drive.google.com/drive/folders/1DzG6dCOlgtjsexzx0y2UKUY49m6B2Gtw?usp=sharing
###    to digital-display/webapp/assets/
###  * run python flaskdashapp.py
###  * open browser and go to http://localhost:8050
###
### If you see the plot below the menu panel, make sure your chrome browser is widen.
### If it gives error messages, keep refreshing the page (or Ctrl-F5).
###
### 08/15/2020:
###   Included an intro video (gif) and highlighting left panel tab as plots rotates
#################################################################################################

#####################################
### Import libraries
#####################################
import flask, dash, requests, pandas
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc 
from dash.dependencies import Output, Input

#####################################
### Define constants
#####################################
## Product query from the API
products = ['water_level', 'water_temperature', 'air_temperature', 'air_pressure', 'wind']

## API template
##  * at Santa Monica 9410840
##  * always retrieve the latest data
##  * local time LST
##  * in English unit (feet, degF, knots, etc)
##  * in JSON for python dictionary
##  * water level at MLLW
mainapi = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + \
          "date=latest&station=9410840&product={0}&datum=MLLW&time_zone=lst&units=english&format=json"

#####################################
### Define functions
#####################################
def get_latest_product (product):

    ''' Get_latest_product() returns the latest data of a specific product from CO-OPS API.
        For water level, water temp, air temp, and air pressure, the key is ['data']['v'].
        For wind, the key is ['data']['s']. Further, wind direction and gust are also
        retrieved from the wind API.

        For whatever reasons, if the retrieval fails, empty strings are returned.

        input param
        -----------
        product (str): Product query - must be in the `products` list

        return params
        -------------
        time  (str): Time of retrieved data
        value (str): Value of retrieved data
        dir   (str): If wind product, wind direction is returned
        gust  (str): If wind product, gust is returned
    '''

    try:
        ## Try to retrieve the latest data
        response = requests.get (mainapi.format (product))
        content = response.json()
        response.close ()
    except:
        ## If any failure, return empty strings so no entries shown on display.
        if product == 'wind': return '', '', ''
        return '', ''

    ## Wind has more info (gust and direction) and keys are different
    if product == 'wind':
        return content['data'][0]['t'], content['data'][0]['s'], content['data'][0]['dr'], content['data'][0]['g']
    ## Other product has only the 'v' key
    return content['data'][0]['t'], content['data'][0]['v']

def get_latest ():

    ''' Get_latest() returns a dictionary of the most recent observed data. This function
        loops through each product in the `products` list, calls the API, and retrieve all
        recent data. Time is reformated to "08/13-2020 02:45 PM". Most product has a time
        stamp and a value. For wind, 3 values are retrived including wind speed, wind
        direction and wind gust.

        return params
        -------------
        latest (dict): The most recent observation data from API
    '''

    latest = {}
    for product in products:
        this = get_latest_product (product)
        ## Re-format and collect time if not already
        if not 'time' in latest:
            latest['time'] = pandas.to_datetime (this[0]).strftime ('%m/%d/%Y %I:%M %p')
        latest[product] = this[1]
        ## For wind, retrieve direction and gust as well
        if product == 'wind':
            latest[product + '_dir'] = this[2]
            latest[product + '_gust'] = this[3]
    return latest

def make_layout():

    ''' Make_layout() returns the layout of the dash. The lay out has 1 row and 2 columns.
        The left column is a panel listing the most recent data, and the right column cycles
        from intro video, water level, water temp, air temp, air pressure, wind, and back
        to intro video.

        For the left panel, data is retrieved every 6 minutes. Retrival is triggered by the
        dcc.Interval which fires a call to execute update_latest(), which updates the values
        by element IDs. The observable that is currently displayed on the right is highlighted.

        Each of the 6 plots on the right has its own HTML div, and their display keys in
        their style dicts switches between 'none' and 'block'. Rotation is triggered by a
        separate dcc.Interval which fires a call to execute update_plot. The number of
        intervals are counted to determine which plot to show on the display.

        return param
        ------------
        HTML div (html.Div): Display layout
    '''

    return html.Div([
    # Left column - data
    dbc.Row([dbc.Col(
        html.Div([
        dcc.Markdown (id='latest_time', style={'fontSize':25}),
        dcc.Markdown (id='latest_water_level', style={'backgroundColor':'#ffffff'}),
        dcc.Markdown (id='latest_water_temp', style={'backgroundColor':'#ffffff'}),
        dcc.Markdown (id='latest_air_temp', style={'backgroundColor':'#ffffff'}),
        dcc.Markdown (id='latest_air_pressure', style={'backgroundColor':'#ffffff'}),
        dcc.Markdown (id='latest_winds', style={'backgroundColor':'#ffffff'}),
        dcc.Markdown (id='latest_gust', style={'backgroundColor':'#ffffff'}),
        ], style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18})
    , width=3),
    # Right column - plots
    ## 0. intro video
    html.Div([
        html.Img(src=app.get_asset_url('introVideo.gif'), style={'width':2000, 'height':1000})
    ], id='intro_video', style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18,'display':'block'}),

    ## 1. water level
    html.Div([
        html.Div ([
            dcc.Markdown ('**Water Level**', style={'fontSize':25, 'textAlign':'center'}),
            dcc.Markdown (id='title_water_level', style={'fontSize':20, 'textAlign':'center'}),
        ], style={'backgroundColor':'#E0FFFF', 'textAlign':'center'}),
        html.Img(src=app.get_asset_url('water_level.gif'), style={'width':2000, 'height':1000})
    ], id='water_level', style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18,'display':'none'}),

    ## 2. water temp
    html.Div([
        html.Div ([
            dcc.Markdown ('**Water Temperature**', style={'fontSize':25, 'textAlign':'center'}),
            dcc.Markdown (id='title_water_temp',  style={'fontSize':20, 'textAlign':'center'}),
        ], style={'backgroundColor':'#E0FFFF', 'textAlign':'center'}),
        html.Img(src=app.get_asset_url('water_temp.gif'), style={'width':2000, 'height':1000})
    ], id='water_temp', style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18, 'display':'none'}),
    
    ## 3. air temp
    html.Div([
        html.Div ([
            dcc.Markdown ('**Air Temperature**', style={'fontSize':25, 'textAlign':'center'}),
            dcc.Markdown (id='title_air_temp', style={'fontSize':20, 'textAlign':'center'}),
        ], style={'backgroundColor':'#E0FFFF', 'textAlign':'center'}),
        html.Img(src=app.get_asset_url('air_temp.gif'), style={'width':2000, 'height':1000})
    ], id='air_temp', style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18, 'display':'none'}),
    
    ## 4. Barometric Pressure
    html.Div([
        html.Div ([
            dcc.Markdown ('**Air Pressure**', style={'fontSize':25, 'textAlign':'center'}),
            dcc.Markdown (id='title_air_pressure', style={'fontSize':20, 'textAlign':'center'}),
        ], style={'backgroundColor':'#E0FFFF', 'textAlign':'center'}),
        html.Img(src=app.get_asset_url('pressure.gif'), style={'width':2000, 'height':1000})
    ], id='air_pressure', style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18, 'display':'none'}),
    
    ## 5. Winds
    html.Div([
        html.Div ([
            dcc.Markdown ('**Winds**', style={'fontSize':25, 'textAlign':'center'}),
            dcc.Markdown (id='title_winds', style={'fontSize':20, 'textAlign':'center'}),
        ], style={'backgroundColor':'#E0FFFF', 'textAlign':'center'}),
        html.Img(src=app.get_asset_url('winds.gif'), style={'width':2000, 'height':1000})
    ], id='winds', style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18, 'display':'none'}), 

    ]), 
    ## Interval to switch between plots - 12 sec
    dcc.Interval(
        id='interval-component',
        interval=12*1000, 
        n_intervals = 0
    ),
    ## Interval to retrive data - 6 min
    dcc.Interval(
        id='interval-latest-data',
        interval=36*1000, ## 6 min
        n_intervals = 0
    )
    ])

#####################################
### Define new App
#####################################
app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP])
app.layout = make_layout ()

@app.callback ([Output('intro_video', 'style'),
                Output('water_level', 'style'),
                Output('water_temp', 'style'),
                Output('air_temp', 'style'),
                Output('air_pressure', 'style'),
                Output('winds', 'style'),
                Output('latest_water_level', 'style'),
                Output('latest_water_temp', 'style'),
                Output('latest_air_temp', 'style'),
                Output('latest_air_pressure', 'style'),
                Output('latest_winds', 'style')],
              [Input('interval-component', 'n_intervals')])
def update_plot(n_reloads):
    ''' Update_plot() returns the style dictionaries for all divs. N_reloads counts the
        intervals as dcc.Interval fires events. Given 6 plots to rotate, if the reminder
        of n_reloads / 6 determines which plot to be shown on the display. For the rest
        of the div, their display keys are set as 'none' to hide their div. 

        The tabs on the left panel are highlighted depending on the current plot on the
        right. So, the styling of those divs are also updated. Together, there are a
        total of 6 + 5 = 11 styling dictionaries.

        input param
        -----------
        n_reloads (int): Number of intervals so far - counted by dcc.Interval()

        return param
        ------------
        styles (list): A list of 11 dictionaries, each of which determines whether the
                       corresponding div should be shown or highlighted.
    '''
    base_style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18}
    n_reloads = (n_reloads) % (len (products) + 1)
    plot_styles, panel_styles = [], []
    for index, page in enumerate (['intro_video', 'water_level', 'water_temp', 'air_temp', 'air_pressure', 'winds']):
        display = 'block' if index==n_reloads else 'none'
        color = '#E0FFFF' if index==n_reloads else '#ffffff'
        plot_styles.append ({**{'display':display}, **base_style})
        if not page == 'intro_video': panel_styles.append ({'backgroundColor':color})
    return plot_styles + panel_styles

@app.callback ([Output('latest_time', 'children'),
                Output('latest_water_level', 'children'),
                Output('latest_water_temp', 'children'),
                Output('latest_air_temp', 'children'),
                Output('latest_air_pressure', 'children'),
                Output('latest_winds', 'children'),
                Output('latest_gust', 'children'),
                Output('title_water_level', 'children'),
                Output('title_water_temp', 'children'),
                Output('title_air_temp', 'children'),
                Output('title_air_pressure', 'children'),
                Output('title_winds', 'children')],
              [Input('interval-latest-data', 'n_intervals')])
def update_latest(n_reloads):

    ''' Update_latest() returns the inline HTML text for the left panel and the title on
        the right. The latest data is retrieved from the API.

        input param
        -----------
        n_reloads (int): Number of intervals so far - not actually used.

        return param
        ------------
        styles (list): A list of 5 dictionaries, each of which determines whether the
                       corresponding div should be shown
    '''    
    ## Get the latest data from API
    latest = get_latest()
    ## Define the text on the left panel
    latest_time = '**Recent Data** as of ' + latest['time'] + ' Local Time'
    latest_water_level = '**Water Level**: ' + latest['water_level'] + ' ft Above MLLW'
    latest_water_temp = '**Water Temp**: ' + latest['water_temperature'] + ' F'
    latest_air_temp = '**Air Temp**: ' + latest['air_temperature'] + ' F'
    latest_air_pressure = '**Barometric Pressure**: ' + latest['air_pressure'] + ' mb'
    latest_winds = '**Winds**: ' + latest['wind'] + ' kts from '+ latest['wind_dir']
    latest_gust = '**Gusting to**: ' + latest['wind_gust'] + ' kts from '+ latest['wind_dir']
    ## Define the title on the right panel
    title_water_level = latest['water_level'] + ' ft Above MLLW'
    title_water_temp = latest['water_temperature'] + ' F'
    title_air_temp = latest['air_temperature'] + ' F'
    title_air_pressure = latest['air_pressure'] + ' mb'
    title_winds = latest['wind'] + ' kts from '+ latest['wind_dir']
    
    return latest_time, latest_water_level, latest_water_temp, latest_air_temp, latest_air_pressure, \
           latest_winds, latest_gust, title_water_level, title_water_temp, title_air_temp, \
           title_air_pressure, title_winds

#####################################
### Script starts here!
#####################################
if __name__ == '__main__':
    app.run_server(debug=True)