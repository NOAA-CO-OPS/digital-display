import datetime as dt
import pytz

from plotter import product
from plotter.air_pressure import air_pressure
from plotter.temperature import temperature
from plotter.water_level import water_level
from plotter.wind import wind
from plotter.met import met

## Define now - same across all products
now = dt.datetime.now (pytz.timezone('US/Pacific'))
print (now)

## Initialize met product
met = met ()
met.plot_path = 'plotter/plots/mets/'
met.assets_path = 'assets/'
met.now = now
met.create_gif (doWindNeedle=False, three_columns=False)

# Initialize pressure product
pressure_product = air_pressure ()
pressure_product.plot_path = 'plotter/plots/pressures/'
pressure_product.assets_path = 'assets/'
pressure_product.now = now
pressure_product.create_gif ()

## Initialize temperature product
temp_product = temperature ()
temp_product.plot_path = 'plotter/plots/temps/'
temp_product.assets_path = 'assets/'
temp_product.now = now
temp_product.create_gif ()

## Initialize wind product
wind_product = wind ()
wind_product.plot_path = 'plotter/plots/winds/'
wind_product.assets_path = 'assets/'
wind_product.now = now
wind_product.create_gif (doNeedle=False)

# Initialize water level product
water_level_product = water_level ()
water_level_product.plot_path = 'plotter/plots/water_levels/'
water_level_product.assets_path = 'assets/'
water_level_product.now = now
water_level_product.create_gif()
