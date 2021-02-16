This folder contains the scripts for the web application.

Web application uses python Flask & Dash (hybridapp.py). A local host webpage automatically cycles through several plots from introduction (video), to water level (GIF), to sea level trends (video), to MET (GIF) and back to intro (video). For the GIFs, a separate python script (plotter/run_plot_schedule.py) is written to generate GIFs every 6 minutes using the different product sub-classes.

## Setup


### Set up on laptop
1. Clone repo using your favorite prompt (cmd, Git Bash, WindowsPowerShell, etc)
```shell
cd C:/Users/first.lastname/Documents
git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
```
2. Create virtual environment ddp
```shell
conda create --name ddp 
```
3. Activate virtual environment
```shell
conda activate ddp
```
3. Install packages
First, install pip if it is not already installed
```shell
conda install pip
```
Then install packages
```shell
pip install -r requirement.txt
```
4. Download static graphics from webapp_content folder in Station Digital Display Project google drive and save in assets folder in local directory.

### Set up on raspberry pi
1. Install git & python software (if needed)

a) Run updates
```shell
sudo apt update
```
b) Install Git
```shell
sudo apt install git
```
c) Install Python
```shell
sudo apt install python3 idle3
```
2. Clone GitHub repository to Desktop
```shell
cd /home/pi/Desktop
git clone https://github.com/NOAA-CO-OPS/digital-display.git digital-display
```
3. Create virtual environment

a) First, install virtualenv
```shell
sudo pip install virtualenv
```
b) Create virtual env using python3
```shell
virtualenv -p /usr/bin/python3.7 ddp 
```
Note: Replace /usr/bin/python3.7 with your path--find path for python3 using which python 3.7

4. Activate virtual environment
```shell
cd ddp
source bin/activate
```
5. Install required packages
```shell
cd /home/pi/Desktop/digital-display
python3 -m pip install -r requirement.txt
```
6. Download static graphics from webapp_content folder in Station Digital Display Project google drive and save in assets folder in local directory.

### Pull the latest updates to the GitHub repository
1.  Open Git Bash or Anaconda Powershell Prompt
2.  Change directories to the digital-display repository folder on your local computer
3.  Enter 'git pull origin master' 

### Run web application

1. Open command prompt (cmd prompt, WindowsPowerShell, Anaconda prompt, etc)
2. Activate ddp environment
```shell
Laptop: 
conda activate ddp
Raspberry pi: 
cd /home/pi/Desktop/ddp
source bin/activate
```
3. Navigate to the webapp folder

4. Begin generating GIFs
```shell
python run_plot_schedule.py
```
5. Run web application code

a) Open another command prompt

b) Activate ddp environment

c) Navigate to the webapp folder

d) Run web app code
```shell
python hybridapp.py
```
Note: Command prompts must remain open while running web application.

### Launch web application

You will see the following message in your command prompt running hybridapp.py...
```shell
 * Serving Flask app "hybridapp" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
```
When you see the above message, open a new web browser tab and type in URL http://localhost:8050/.

Note: You may have to zoom out for content to display correctly since it is formatted for a 23" monitor.

### When you are done working on ddp
You should have 2 prompts opened. Make sure you close them both to avoid unnecessary background processing.

### Troubleshooting

1. If you receive an import error (ImportError: libf77blas.so.3: cannot open shared object file: No such file or directory), update NumPy dependencies:
```shell
sudo apt-get install libatlas-base-dev
```
More on Numpy dependency issues: https://numpy.org/devdocs/user/troubleshooting-importerror.html