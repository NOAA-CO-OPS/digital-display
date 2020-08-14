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

import flask, dash, requests, pandas
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc 

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
## Latest data
latest = get_latest()
## Define a new dashboard with bootstrap
app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP])

## Define dashboard layout 
app.layout = html.Div([
    # Left column - data
    dbc.Row([dbc.Col(
        html.Div([
        dcc.Markdown('**Recent Data** as of ' + latest['time'] + ' Local Time', style={'font-size':25}),
        dcc.Markdown ('**Water Level**: ' + latest['water_level'] + ' ft Above MLLW'),
        dcc.Markdown ('**Water Temp**: ' + latest['water_temperature'] + ' F'),
        dcc.Markdown ('**Air Temp**: ' + latest['air_temperature'] + ' F'),
        dcc.Markdown ('**Barometric Pressure**: ' + latest['air_pressure'] + ' mb'),
        dcc.Markdown ('**Winds**: ' + latest['wind'] + ' kts from '+ latest['wind_dir']),
        dcc.Markdown ('**Gusting to**: ' + latest['wind_gust'] + ' kts from '+ latest['wind_dir']),
        ], style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'font-size':18})
    , width=3),
    # Right column - plot
    html.Div([
        html.Div ([
            dcc.Markdown ('**Water Level**', style={'font-size':25, 'text-align':'center'}),
            dcc.Markdown (latest['water_level'] + ' ft Above MLLW', style={'font-size':20, 'text-align':'center'}),
        ], style={'background-color':'#E0FFFF', 'text-align':'center'}),
        html.Img(src=app.get_asset_url('water_level.gif'), style={'width':2000, 'height':1200})
    ], style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15, 'font-size':18})
    ])
    
    ])

if __name__ == '__main__':
    app.run_server(debug=True)