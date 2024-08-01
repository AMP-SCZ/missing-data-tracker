!/usr/bin/env python

import base64, io
import dash
from dash import dcc, html, dash_table, Dash, callback_context, MATCH, ALL
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from os.path import isfile, isdir, abspath, join as pjoin, dirname, splitext, basename
from os import makedirs, getenv, remove, listdir

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from glob import glob
import json

from flask import Flask
server=Flask(__name__)

SCRIPTDIR=dirname(abspath(__file__))

ROOTDIR= getenv("NDA_ROOT")
URL_PREFIX= getenv("DASH_URL_BASE_PATHNAME",'')
if not ROOTDIR:
    print('Define env var NDA_ROOT and try again')
    exit(1)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css',dbc.themes.BOOTSTRAP,'styles.css']
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True, title='Missing Data Tracker', \
    assets_folder=ROOTDIR, assets_url_path="/",server=server)
log= logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

with open('subject-id-gen/sites.json') as f:
    sites= json.load(f)

sites2=[]
for s in sites:
    sites2.append({'label':s['id']+' | '+s['name'], 'value':s['id']})
sites=sites2.copy()


visits='baseline,month_2,month_6,month_12,month_24'.split(',')
datatypes='mri,eeg,avl,cnb'.split(',')


app.layout= html.Div(
    children= [
        html.Details([html.Summary('Collapse/Expand Introduction'),
        html.Br(),
        dbc.Row([
            dbc.Col(html.Img(src='https://avatars.githubusercontent.com/u/75388309?s=400&u=0d32212fdb2b3bf3854ed6624ce9f011ca6de29c&v=4', id='ampscz'),width=2),
            dbc.Col([
                dbc.Row(dcc.Markdown("""
### AMP-SCZ Missing Data Tracker
Developed by Tashrif Billah and Sylvain Bouix

https://github.com/AMP-SCZ/missing-data-tracker
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.13151571.svg)]
(https://doi.org/10.5281/zenodo.13151571)
            """)),
                dbc.Row([
                    dbc.Col(dcc.Markdown("""
* Provide value in the box(es) and click `FILTER`
* Click `DOWNLOAD` to download shown table
* Enter date as `yyyy/mm/dd`
                """),width='auto'),
                    dbc.Col(dcc.Markdown("""
* Example of `site`: LA, PA, ME
* Refresh browser to reset all filters
                """),width='auto')
                ])
            ])
        ])], open=True),


        html.Br(),

        dbc.Row([
            # date filter
            # show one month of images as default
            dbc.Col([
                dcc.Input(id='start',placeholder='yyyy/mm/dd',debounce=True),
                html.Br(),
                'Earliest'
            ], width='auto'),

            dbc.Col('←—→', style={'margin-top':'10px'}, width='auto'),

            dbc.Col([
                dcc.Input(id='end',placeholder='yyyy/mm/dd',debounce=True),
                html.Br(),
                'Latest'
            ], width='auto'),


            # site filter
            dbc.Col(html.Div(dcc.Dropdown(id='site',placeholder='site',
                options=sites,
                value='')),
                width=2
            ),

            # password for site
            dbc.Col(html.Div(dcc.Input(id='passwd',placeholder='password',
                type='password',
                debounce=True)),
                width=1
            ),

            # row order
            dbc.Col(html.Div([dcc.Dropdown(id='sort-order', className='ddown',
                options=['Latest first','Earliest first','Alphabetical'],
                value='Latest first'),
                'Sort order'
                ]),
                width=2
            ),

            # days filter
            dbc.Col(html.Div([dcc.Dropdown(id='days_low', className='ddown', placeholder='days_low',
                options=score_options),
                'Days low'
                ]),
                width=2
            ),

            dbc.Col(html.Div([dcc.Dropdown(id='days_high', className='ddown', placeholder='days_high',
                options=score_options),
                'Days high'
                ]),
                width=2
            ),
        ]),

        html.Br(),

        dbc.Row([
            # datatype filter
            dbc.Col(html.Div(dcc.Dropdown(id='datatype', className='ddown',
                options=datatypes,
                value=datatypes,
                multi=True)),
                width=8
            ),

            # visit filter
            dbc.Col(html.Div(dcc.Dropdown(id='visit', className='ddown',
                options=visits,
                value=visits,
                multi=True)),
                width=8
            ),

        ]),

        html.Br(),

        dbc.Row([
            # filter button
            dbc.Col(html.Button('Filter', id='filter', n_clicks=0))

        ]),

        dbc.Row(dcc.ConfirmDialog(id='verify', message='Invalid password for the site, try again')),

        html.Br(),
        dcc.Loading(html.Div(id='loading'),type='cube'),
        html.Br(),


        # html.Br(),
        # html.Br(),

        html.Div(id='table'),
        html.Br(),

        dcc.Store(id='properties'),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),

        dbc.Navbar([html.Button('Download', id='download', n_clicks=0),
            fixed='bottom',
            color='white'
        )


    ]

)

_passwd=pd.read_csv('.passwd')
_passwd.set_index('site',inplace=True)


# verify password
@app.callback(Output('verify','displayed'),
       [Input('site','value'),
       Input('passwd','value')])
def verify_passwd(site,passwd):

    if site and passwd:
        if passwd==_passwd.loc['dpacc','passwd']:
            pass
        elif passwd==_passwd.loc[site,'passwd']:
            pass
        else:
            # return f'Invalid password for site {site}, try again'
            return True

if __name__=='__main__':
    # debug=None allows control via DASH_DEBUG variable
    app.run_server(debug=None, host='localhost')

