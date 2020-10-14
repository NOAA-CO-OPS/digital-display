This folder contains the scripts for the web application.

Initial version of micro web uses python Flask & Dash (hybridapp.py). A local host webpage automatically cycle through several plots from home (video), to water level (GIF), to sea level trend (video), to MET (GIF) and back to home (video). Currently, I am using a short intro and sea-level-trend videos from DDP Google folder. For the GIFs, a separate python script (plotter/run_plot_schedule.py) is written to generate GIFs every 6 minutes using the different product sub-classes.

### Preparation

1. Clone repo using your favorite prompt (cmd, Git Bash, WindowsPowerShell, etc)
```shell
$ cd C:/Users/first.lastname/Documents
$ git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
```
2. create virtual environment ddp--change directory to digital-display folder and run
```shell
conda env create -f environment.yml
```
3. activate virtual environment
```shell
conda activate ddp
```	
4. download all mp4 / gif from [webbapp_content_for_test Google folder](https://drive.google.com/drive/folders/1H20lAG-23YuuaqrZyWKHD39qFWGU4E4W?usp=sharing) to digital-display/webapp/assets/

### To pull the latest updates to the GitHub repository
1.  Open Git Bash
2.  Change directories to the digital-display repository folder on your local computer (*remember that Git Bash only accepts FORWARD slashes)
3.  Enter 'git pull origin master'

### To update your virtual environment
1.  Open your favorite prompt window and navigate to the digital-display folder
2.  Activate the virtual environment: conda activate ddp
3.  Update the environment by entering: pip install -r requirement.txt  

### When you start working on ddp

#### Start generating GIFs
1. Open your favorite prompt (cmd prompt, WindowsPowerShell, Anaconda prompt, etc)
2. Execute run_plot_schedule.py
```shell
$ cd C:\\Users\\first.lastname\\ddp\\digital-display\\webapp\\plotter\\
$ python run_plot_schedule.py
```
Do not close this prompt until you are done with ddp work.

#### Start digital display
3. Open another prompt.
4. Execute hybridapp.py
```shell
$ cd C:\\Users\\first.lastname\\ddp\\digital-display\\webapp\\
$ python hybridapp.py
```
Do not close this prompt until you are done with ddp work.
You will see the following message from your prompt ...
```shell
 * Serving Flask app "hybridapp" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
```
5. When you see the above message, open a new web browser tab and type in URL http://localhost:8050/.

Note: You may have to zoom out for content to display correctly since it is formatted for a 23" monitor.

### When you are done working on ddp
You should have 2 prompts opened. Make sure you close them both to avoid unnecessary background processing.

