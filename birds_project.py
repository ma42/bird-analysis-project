import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import math
from datetime import datetime, timezone, date, timedelta
from time import time
from astral import Astral

a = Astral()
location = a['Stockholm']

data = pd.read_csv('bird_jan25jan16.txt', sep="    |   |  ", header=None, engine='python')
data.columns = ["date", "movement",]

# Convert date to datetime objects. Deletes rows with faulty formatting

data['date'] = pd.to_datetime(data['date']).dt.tz_localize('UTC').dt.tz_convert('Europe/Stockholm')

def old_to_datetime():
    dates = data.date
    dates_list = []
    idx = 0

    for date in dates:
        try:
            date = datetime.fromisoformat(date).replace(tzinfo=timezone.utc).astimezone(tz=None)
            dates_list.append(date)
        except ValueError:
            data = data.drop(index=data.index[idx])
        idx += 1
    data['date'] = dates_list

data = data.dropna()
movements = data.movement
movement_inc = []
movement_list = []
prev = 70 
prev_time = data['date'].iloc[0]
idx_2 = 0 

for row in data.movement:
    curr_time = data.iloc[idx_2, 0]

    # If movement value in the textfile is not zero
    if row != 0:
        mov_inc = row - prev
        if mov_inc < 4.0:
            movement_inc.append(mov_inc) 

        # If movement increses with more than one between two values. 
        # Determines if there has been an movement increase with more than 4 movements per minute. 
        # If not, value is added, if bird has been fluttering, the value is deleted. 
    
        else: 
            time_difference = curr_time - prev_time
            time_difference = int(round(time_difference.total_seconds() / 60))
            try: 
                mov_per_minute = mov_inc / time_difference
            except ZeroDivisionError:
                mov_per_minute = mov_inc
            if mov_per_minute <= 4:
                movement_inc.append(float(mov_inc))
            else:
                data = data.drop(index=data.index[idx_2])
                idx_2 -= 1
        prev = row

    # If movement value in textfile restarts counting from 0 
    else: 
        prev = 0
        movement_inc.append(float(prev))

    idx_2 += 1
    prev_time = curr_time
data['movement'] = movement_inc
data.query('movement >= 0', inplace=True)
data.set_index('date', drop=False, inplace=True, verify_integrity=True)

# Takes input for which dates to analyze.
# ------------------------------------------------------------------------

print("Choose which dates to anaylyse. Write a start date in format YYYY-MM-DD between 2015-01-25 and 2016-01-16.")
start_date = input()
print("Write a end date in format YYYY-MM-DD between 2015-01-25 and 2016-01-16.")
end_date = input()

# Slices dataframe based on dates to analyze. 
# ------------------------------------------------------------------------

data = data.sort_index()
sliced_data = data.index.slice_locs(start=start_date, end=end_date, kind='getitem')
sliced_data = data.iloc[sliced_data[0]:sliced_data[1]]
dates = sliced_data.index.date
dates = np.unique(dates)

# Computes sunrise and sunset times for specific days. 
# ------------------------------------------------------------------------

sunrise_times = []
sunset_times = []
for date in dates: 
    sun = location.sun(local=True, date=date)
    sunrise = sun['sunrise']
    sunrise = sunrise.replace(second=0, microsecond=0, minute=0, hour=sunrise.hour) + timedelta(hours=sunrise.minute//30)
    sunrise_times.append(sunrise)
    sunset = sun['sunset']
    sunrise = sunset.replace(second=0, microsecond=0, minute=0, hour=sunrise.hour) + timedelta(hours=sunrise.minute//30)
    sunset_times.append(sunset)

rise_index = []
set_index = []
# Finds index for row in dataframe which has datetime nearest sunrise/sunset time.  
for rise_time in sunrise_times:
    idx = sliced_data.index.get_loc(rise_time, method='nearest')
    rise_index.append(idx)
for set_time in sunset_times:
    idx = sliced_data.index.get_loc(set_time, method='nearest')
    set_index.append(idx)

date_newdf = []
mov_newdf = []
mov_while_light = pd.DataFrame(columns=['date', 'movement'])

# Creates a new dataframe containing datetime objects and movements for when the sun is up. 
# ------------------------------------------------------------------------

def movement_daylight():
    for index_rise, index_set in zip(rise_index, set_index):
        mov = sliced_data.iloc[index_rise:index_set].movement.sum()
        date = sliced_data.iloc[index_rise].date
        date = datetime(year=date.year, month=date.month, day=date.day)
        date_newdf.append(date)
        mov_newdf.append(mov)  
    mov_while_light['date'] = date_newdf
    mov_while_light['movement'] = mov_newdf

# Functions for plotting
# ------------------------------------------------------------------------

def plt_mov_dark():
    movement_daylight()
    total_mov = sliced_data.movement.sum()
    day_move = mov_while_light.movement.sum()
    night_move = total_mov - day_move
    fig, ax = plt.subplots()
    ax.pie([day_move, night_move], colors=['#FFFF7F', '#7A7A7A'], labels=('Daytime movements', 'Nighttime movements'), autopct='%1.1f%%', shadow=True, startangle=90)
    ax.axis('equal')
    plt.show()

def plt_mov_year():
    data_plt = data.resample('D').sum()
    fig, ax = plt.subplots()
    ax.plot(data_plt, color='black')
    ax.set_ylim(bottom=0)
    MFmt = mdates.DateFormatter('%b')
    #DFmt = mdates.DateFormatter('%d')
    ax.xaxis.set_major_formatter(MFmt)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
   # ax.xaxis.set_minor_formatter(DFmt)
    ax.xaxis.set_minor_locator(mdates.DayLocator(interval=7))
    ax.xaxis.grid(True)
    ax.axvspan(datetime(year=2015, month=5, day=1), datetime(year=2015, month=6, day=1), alpha=0.4, facecolor='yellow')
    ax.axvspan(datetime(year=2015, month=6, day=1), datetime(year=2015, month=6, day=16), alpha=0.4, facecolor='blue')
    ax.axvspan(datetime(year=2015, month=6, day=16), datetime(year=2015, month=7, day=8), alpha=0.4, facecolor='green')
    ax.set_title('Bird movements over year')
    ax.set_xlabel('Date and time')
    ax.set_ylabel('Movements')
    plt.show()

def plt_hour():
    movement_daylight()
    plt_mov = sliced_data.resample('H').sum()
    
    fig, ax = plt.subplots()
    ax.plot(plt_mov, color='black')
    ax.set_ylim(bottom=0)
    DFmt = mdates.DateFormatter('%m/%d')
    HFmt = mdates.DateFormatter('%H')
    ax.xaxis.set_major_formatter(DFmt)
    ax.xaxis.set_minor_formatter(HFmt)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=range(0,24,1), interval=3))
    ax.tick_params(pad=10, labelrotation=45)
    ax.xaxis.grid(True)
    ax.set_title('Analysis of bird movement on an hourly basis')
    ax.set_xlabel('Date and time')
    ax.set_ylabel('Movements')
    for rise, down in zip(sunrise_times, sunset_times):
        ax.axvspan(rise, down, alpha=0.5, facecolor='yellow')
    plt.show()

def plt_mov_sun_relation():
    test = sliced_data.resample('H').sum()
    HFmt = mdates.DateFormatter('%H')
    DFmt = mdates.DateFormatter('%m/%d')
    fig, ax = plt.subplots()
    ax.plot(test, color='black')
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_formatter(DFmt)
    ax.xaxis.set_minor_formatter(HFmt)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=range(0,24,1), interval=12))
    ax.tick_params(pad=10, labelrotation=45)
    ax.xaxis.grid(True)
    ax.set_title('Relation between bird movement and sunrise/sunset')
    ax.set_xlabel('Date and time')
    ax.set_ylabel('Movements')
    for rise, down in zip(sunrise_times, sunset_times):
        ax.axvspan(rise, down, alpha=0.5, facecolor='yellow')
    plt.show()


plt_mov_dark()
plt_mov_year()
plt_hour()
plt_mov_sun_relation()

