from flask import Flask,render_template,request #,redirect
import os
from subprocess import call
import base64
from io import BytesIO
import requests
import pandas as pd
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.dates import num2date
from matplotlib.ticker import FuncFormatter
from matplotlib.dates import AutoDateLocator
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


data_url = 'https://covidtracking.com/api/states/daily.csv'
data_path = 'daily.csv' #assuming the file is in the same directory as the notebook
name_path = 'states_info.csv'
now = dt.datetime.now()
if os.path.isfile(data_path):
    csv_time = dt.datetime.fromtimestamp(os.lstat(data_path).st_mtime)
else:
    csv_time = now - dt.timedelta(1)
# lstat gives me the modification time.

if now - csv_time > dt.timedelta(0.25):
    call(['rm', 'daily.csv'])
    call(['wget', data_url])
    print('Downloaded an updated dataset')


class StateNames():
    def __init__(self, name_path):
        self.name = {}
        self.capita ={} #per capita
        for line in open(name_path):
            n, m, p = line.strip('\n').split(',')
            self.name[m] = n
            self.capita[m] = int(p)
    def fname(self, abr):
        return self.name[abr]
    def spop(self, abr): #state population
        return self.capita[abr]


def str_to_date(x):
    return dt.datetime.strptime(str(x),'%Y%m%d')


def select_state(abr):
    # abbreivation
    # postiveIncrease >= 10 to not worry about log(0)
    state = df[(df['state'] == abr) & (df['positive'] >= 10)].sort_values('date')
    return state


def ticks_log(x, pos):
    # two args are the value and tick position
    if x < 3:
        return '{:1.0f}'.format(10**x)
    elif x >= 6:
        return '{:1.0f}M'.format(10**x/1e6)
    return '{:1.0f}K'.format(10**x/1000)


def ticks_line(x, pos):
    # two args are the value and tick position
    if x < 1000:
        return '{:1.0f}'.format(x)
    return '{:1.0f}K'.format(x/1000)


def xticks_date(x, pos):
    # two args are the value and tick position
    # i had to use num2date as the dateobject is converted to numpy array at some point
    return '{}'.format(dt.datetime.strftime(num2date(x),'%b %d'))


##### Setting up class and dataframe ######
sn = StateNames(name_path)
df = pd.read_csv(data_path, converters={'date': str_to_date})


def plot_totdaily(state_abr, log=True, deaths=False, web=False, sn=sn):
    feature = 'positive'
    feature_inc = 'positiveIncrease'
    titles = 'Cases'

    if deaths:
        feature = 'death'
        feature_inc = 'deathIncrease'
        titles = 'Deaths'

    state = select_state(state_abr)
    name = sn.fname(state_abr)

    x = state['date']
    y_daily = state[feature_inc]
    if log is True:
        y_tot = np.log10(state[feature])
    else:
        y_tot = state[feature]

    if web:
        fig = Figure(figsize=(8, 6))
        ax1 = fig.subplots()
    else:
        fig, ax1 = plt.subplots(figsize=(8, 6))

    color = 'tab:red'
    ax1.set_ylabel(f'New {titles}', color=color)  # we already handled the x-label with ax1
    ax1.bar(x, y_daily, color=color, alpha=0.7)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel(f'Cumulative {titles}', color=color)
    ax2.plot(x, y_tot, color=color, lw=3)
    ax2.tick_params(axis='y', labelcolor=color)

    if log is True:
        formatter = FuncFormatter(ticks_log)
    else:
        formatter = FuncFormatter(ticks_line)
    ax2.yaxis.set_major_formatter(formatter)

    # if you modify ax2, the ax1 defaults seem to overwrite them
    xformatter = FuncFormatter(xticks_date)
    ax1.xaxis.set_major_formatter(xformatter)
    ax1.tick_params(axis='x', rotation=60)
    # xlocator is there to most likely deal with a jupyter bug
    xlocator = AutoDateLocator(interval_multiples=False)
    ax1.xaxis.set_major_locator(xlocator)

    ax2.set_title(f'Coronavirus Cases in {name}')
    # fig.tight_layout()  # otherwise the right y-label is slightly clipped

    if web:
        buffer = BytesIO()
        fig.savefig(buffer, format='png')
        data = base64.b64encode(buffer.getbuffer()).decode("ascii")
        #return f"<img src='data:image/png;base64,{data}'/>"
        return f"{data}"
    return


def plot_comp(states_abr, log=True, deaths=False, per_capita=False, web=False, sn=sn):
    if len(states_abr) > 5:
        print('Please Enter 5 Or Less States')
        return

    feature = 'positive'
    titles = 'Cases'
    if deaths:
        feature = 'death'
        titles = 'Deaths'

    if per_capita:
        titles = titles + ' per Million People'

    st = {'full': {},
          'cases': {},
          'date': {}}
    colors = ['tab:blue', 'tab:red', 'tab:green', 'tab:orange', 'tab:pink']

    for state in states_abr:
        st_df = select_state(state)
        st['full'][state] = sn.fname(state)
        st['date'][state] = st_df['date']

        if per_capita:
            pc = 1e6 / sn.spop(state)
        else:
            pc = 1

        if not log:
            st['cases'][state] = st_df[feature] * pc
        else:
            st['cases'][state] = np.log10(st_df[feature] * pc)

    if web:
        fig = Figure(figsize=(8, 6))
        ax1 = fig.subplots()
    else:
        fig, ax1 = plt.subplots(figsize=(8, 6))

    for n, state in enumerate(states_abr):
        ax1.plot(st['date'][state], st['cases'][state], color=colors[n], label=f"{st['full'][state]}", lw=2)

    linecol = 'gainsboro'
    labelcol = 'dimgray'

    ax1.set_title(f'Coronavirus {titles} Comparison', color=labelcol, fontsize=14)
    ax1.set_ylabel(f'Cumalative {titles}', color=labelcol, fontsize=14)

    ax1.tick_params(axis='y', color=linecol, labelcolor=labelcol, labelsize=12)

    xformatter = FuncFormatter(xticks_date)
    ax1.xaxis.set_major_formatter(xformatter)
    ax1.tick_params(axis='x', rotation=60, color=linecol, labelcolor=labelcol, labelsize=12)
    xlocator = AutoDateLocator(interval_multiples=False)
    ax1.xaxis.set_major_locator(xlocator)
    ax1.set_ylim(bottom=0)

    if log is True:
        formatter = FuncFormatter(ticks_log)
    else:
        formatter = FuncFormatter(ticks_line)
    ax1.yaxis.set_major_formatter(formatter)

    ax1.grid(which='major', color=linecol)
    for sides in ax1.spines:
        ax1.spines[sides].set_color(None)
    ax1.spines['bottom'].set_color(linecol)

    leg = ax1.legend(frameon=False, loc='lower left')
    plt.setp(leg.get_texts(), color=labelcol)

    if web:
        buffer = BytesIO()
        fig.savefig(buffer, format='png')
        data = base64.b64encode(buffer.getbuffer()).decode("ascii")
        #return f"<img src='data:image/png;base64,{data}'/>"
        return f"{data}"
    return


app_covid = Flask(__name__)


@app_covid.route('/', methods=['GET', 'POST'])
def covid_site():

    if request.method == 'GET':
        return render_template('index_form.html')
    else:
        # Request was a POST
        chart = request.form['chart_type']
        st = [request.form['state1'], request.form['state2'], request.form['state3'],
                     request.form['state4'], request.form['state5']]

        to_remove = []
        for i, j in enumerate(st):
            if not j:
                to_remove.append(i)
        for i in to_remove[::-1]:
            del st[i]
        print(st)


        case_type = bool(request.form['case_type'])
        if request.form.get('per_capita'):
            capita = True
        else:
            capita = False
        scale = bool(request.form['scale'])


        if chart == 'comparison':
            gen_figure = plot_comp(st, log=scale, deaths=case_type, per_capita=capita, web=True)
        elif chart == 'daily':
            gen_figure = plot_totdaily(st[0], log=scale, deaths=case_type, web=True)

        #return redirect('/index_quand')
        return render_template('covid.html',
                               web_figure = gen_figure )



if __name__ == "__main__":
    app_covid.run()