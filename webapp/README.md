This folder contains the scripts for the web application.

Initial version of micro web uses python Flask. With a template HTML and simple CSS and JS, a local host webpage automatically cycle through several HTML pages from home (video), to water level, to wind, to air temperature, to water temperature, to pressure, and back to home (video). Currently, I am using a short intro video from DDP Google folder and some snapshots of plots from TAC sites for testing.

##### Run

1. $ git clone https://github.com/NOAA-CO-OPS/digital-display.git
2. create virtual environment ddp--change directory to digital-display folder and run
```shell
conda env create -f environment.yml
```
3. activate virtual environment
```shell
conda activate ddp
```	
4. download all mp4 / gif from [webbapp_content_for_test Google folder](https://drive.google.com/drive/folders/1H20lAG-23YuuaqrZyWKHD39qFWGU4E4W?usp=sharing) to digital-display/webapp/assets/
5. change directory to webapp & run flaskdashapp.py
6. open browser and go to http://localhost:8050/

Note: You may have to zoom out for content to display correctly since it is formatted for a 23" monitor.

It will first show an intro video and then loop through each plot within a 12 sec time interval, and then go back to the video.
