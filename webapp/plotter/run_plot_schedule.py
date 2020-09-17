import datetime as dt
import pytz, sys, schedule, time
sys.path.append('C:\\Users\\elim.thompson\\Documents\\ddp\\webapp\\plotter\\')

from air_pressure import air_pressure
from temperature import temperature
from water_level import water_level
from wind import wind
from met import met


def create_gifs ():

    ## Define now - same across all products
    now = dt.datetime.now (pytz.timezone('US/Pacific'))
    print (now)

    ## Initialize met product
    met_product = met ()
    met_product.plot_path = 'plots/mets/'
    met_product.assets_path = '../assets/'
    met_product.now = now
    met_product.create_gif (doWindNeedle=False, three_columns=False)

    ## Initialize pressure product
    # pressure_product = air_pressure ()
    # pressure_product.plot_path = 'plots/pressures/'
    # pressure_product.assets_path = '../assets/'
    # pressure_product.now = now
    # pressure_product.create_gif ()

    # ## Initialize temperature product
    # temp_product = temperature ()
    # temp_product.plot_path = 'plots/temps/'
    # temp_product.assets_path = '../assets/'
    # temp_product.now = now
    # temp_product.create_gif ()

    # ## Initialize wind product
    # wind_product = wind ()
    # wind_product.plot_path = 'plots/winds/'
    # wind_product.assets_path = '../assets/'
    # wind_product.now = now
    # wind_product.create_gif (doNeedle=False)

    # # Initialize water level product
    water_level_product = water_level ()
    water_level_product.plot_path = 'plots/water_levels/'
    water_level_product.assets_path = '../assets/'
    water_level_product.now = now
    water_level_product.create_gif()



if __name__ == '__main__':

    ## Create the latest GIFs when this script is called
    create_gifs()

    ## Create GIFs every 6 minutes afterwards
    schedule.every(6).minutes.do(create_gifs)

    while 1:
        schedule.run_pending()
        time.sleep(1)