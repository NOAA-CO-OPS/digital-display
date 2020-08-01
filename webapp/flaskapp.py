#!/bin/python

###
### By Elim Thompson 07/31/2020
### 
### Initial version of micro web using Flask, going from home (video), to
### water level, to wind, to air temperature, to water temperature, to
### pressure, and back to home (video). Currently using a 5-min video from
### DDP Google folder. 
### 
### To run: 
###  * install flask
###  * $ git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
###  * download all mp4 / gif from
###        https://drive.google.com/drive/folders/1DzG6dCOlgtjsexzx0y2UKUY49m6B2Gtw?usp=sharing
###    to digital-display/webapp/static/
###  * run python flaskapp.py
###  * open browser and go to http://localhost:5000/home
###
### If data is downloaded to the static folder, it will first show a 5-min
### video and then loop through each plot with in a 10 min time interval,
### and then go back to the video.
#################################################################################################

from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/water_level')
def water_level():
    return render_template('water_level.html')

@app.route('/winds')
def winds():
    return render_template('winds.html')

@app.route('/air_temp')
def air_temp():
    return render_template('air_temp.html')

@app.route('/water_temp')
def water_temp():
    return render_template('water_temp.html')

@app.route('/pressure')
def pressure():
    return render_template('pressure.html')

if __name__ == "__main__":
    app.run (debug=True)
