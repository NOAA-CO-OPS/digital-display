This folder contains the scripts for the web application.

Initial version of micro web uses python Flask. With a template HTML and simple CSS and JS, a local host webpage automatically cycle through several HTML pages from home (video), to water level, to wind, to air temperature, to water temperature, to pressure, and back to home (video). Currently, I am using a 5-min video from DDP Google folder and some snapshots of plots from TAC sites for testing.

##### Run

1. install flask
2. $ git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
3. download all mp4 / gif from
    https://drive.google.com/drive/folders/1DzG6dCOlgtjsexzx0y2UKUY49m6B2Gtw?usp=sharing
    to digital-display/webapp/static/
4. run python flaskapp.py
5. open browser and go to http://localhost:5000/home

If data is downloaded to the static folder, it will first show a 5-min video and then loop through each plot with in a 10 min time interval, and then go back to the video.