#!/bin/python

###
### By Elim Thompson 08/13/2020
### 
### Combining Flask and dash to build a dash board. This dash board
###  * have a left panel with the most recent water level, water temp, air temp, air pressure,
###    winds, gust, and current local time. Latest data is pulled from data API.
###  * The dash script is reloaded to capture the latest data by default.
###  * Currently only showing water level. 
###
### To do.. 
###  1. Combine this with flaskapp.py to refresh the plot on the right every so often
###  2. Figure out how to do do width / height based on monitor size (%)
###  3. Highlight the current item on the left panel
### 
### To run: 
###  * install flask,. dash, and dash_bootstrap_components
###  * $ git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
###  * download all mp4 / gif from
###        https://drive.google.com/drive/folders/1DzG6dCOlgtjsexzx0y2UKUY49m6B2Gtw?usp=sharing
###    to digital-display/webapp/assets/
###  * run python flaskdashapp.py
###  * open browser and go to http://localhost:8050
###
### If you see the plot below the menu panel, make sure your chrome browser is widen.
### If it gives error messages, keep refreshing the page (or Ctrl-F5).
#################################################################################################

import flask, dash, requests, pandas, time
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc 
from dash.dependencies import Output, Input

products = ['water_level', 'water_temperature', 'air_temperature', 'air_pressure', 'wind']
mainapi = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + \
          "date=latest&station=9410840&product={0}&datum=MLLW&time_zone=lst&units=english&format=json"

#####################################
### Define functions
#####################################
def get_latest_product (product):
    response = requests.get (mainapi.format (product))
    content = response.json()
    response.close ()
    ## Wind has more info (gust and direction) and keys are different
    if product == 'wind':
        return content['data'][0]['t'], content['data'][0]['s'], content['data'][0]['dr'], content['data'][0]['g']
    ## Other product has only the 'v' key
    return content['data'][0]['t'], content['data'][0]['v']

def get_latest ():
    latest = {}
    for product in products:
        this = get_latest_product (product)
        ## Re-format and collect time if not already
        if not 'time' in latest:
            latest['time'] = pandas.to_datetime (this[0]).strftime ('%m/%d/%Y %I:%M %p')
        latest[product] = this[1]
        if product == 'wind':
            latest[product + '_dir'] = this[2]
            latest[product + '_gust'] = this[3]
    return latest


#####################################
### Define variables
#####################################
## Define dashboard layout 
def make_layout(page_name):

    return html.Div([
    # Left column - data
    dbc.Row([dbc.Col(
        html.Div([
        dcc.Markdown (id='latest_time', style={'fontSize':25}),
        dcc.Markdown (id='latest_water_level'),
        dcc.Markdown (id='latest_water_temp'),
        dcc.Markdown (id='latest_air_temp'),
        dcc.Markdown (id='latest_air_pressure'),
        dcc.Markdown (id='latest_winds'),
        dcc.Markdown (id='latest_gust'),
        ], style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18})
    , width=3),
    # Right column - plot
    ## 1. water level
    html.Div([
        html.Div ([
            dcc.Markdown ('**Water Level**', style={'fontSize':25, 'textAlign':'center'}),
            dcc.Markdown (id='title_water_level', style={'fontSize':20, 'textAlign':'center'}),
        ], style={'backgroundColor':'#E0FFFF', 'textAlign':'center'}),
        html.Img(src=app.get_asset_url('water_level.gif'), style={'width':2000, 'height':1000})
    ], id='water_level', style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18,'display':'block'}),

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
            dcc.Interval(
            id='interval-component',
            interval=12*1000, 
            n_intervals = 0
        ),
            dcc.Interval(
            id='interval-latest-data',
            interval=36*1000, ## 6 min
            n_intervals = 0
        )
    ])

## Define a new dashboard with bootstrap
app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP])
app.layout = make_layout ('water_level')

@app.callback ([Output('water_level', 'style'),
                Output('water_temp', 'style'),
                Output('air_temp', 'style'),
                Output('air_pressure', 'style'),
                Output('winds', 'style')],
              [Input('interval-component', 'n_intervals')])
def update_plot(n_reloads):
    base_style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'fontSize':18}
    print (n_reloads)
    n_reloads = (n_reloads) % 5
    styles = []
    for index, page in enumerate (['water_level', 'water_temp', 'air_temp', 'air_pressure', 'winds']):
        display = 'block' if index==n_reloads else 'none'
        styles.append ({**{'display':display}, **base_style})
    return styles

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

    latest = get_latest()

    latest_time = '**Recent Data** as of ' + latest['time'] + ' Local Time'
    latest_water_level = '**Water Level**: ' + latest['water_level'] + ' ft Above MLLW'
    latest_water_temp = '**Water Temp**: ' + latest['water_temperature'] + ' F'
    latest_air_temp = '**Air Temp**: ' + latest['air_temperature'] + ' F'
    latest_air_pressure = '**Barometric Pressure**: ' + latest['air_pressure'] + ' mb'
    latest_winds = '**Winds**: ' + latest['wind'] + ' kts from '+ latest['wind_dir']
    latest_gust = '**Gusting to**: ' + latest['wind_gust'] + ' kts from '+ latest['wind_dir']

    title_water_level = latest['water_level'] + ' ft Above MLLW'
    title_water_temp = latest['water_temperature'] + ' F'
    title_air_temp = latest['air_temperature'] + ' F'
    title_air_pressure = latest['air_pressure'] + ' mb'
    title_winds = latest['wind'] + ' kts from '+ latest['wind_dir']
    
    return latest_time, latest_water_level, latest_water_temp, latest_air_temp, latest_air_pressure, \
           latest_winds, latest_gust, title_water_level, title_water_temp, title_air_temp, \
           title_air_pressure, title_winds

if __name__ == '__main__':
    app.run_server(debug=True)