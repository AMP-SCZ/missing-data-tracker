#!/usr/bin/env python

import base64, io
import dash
from dash import dcc, html, dash_table, Dash, callback_context, MATCH, ALL
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.dash_table import DataTable

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

for n in 'PRONET PRESCIENT AMPSCZ'.split():
    sites2.append({'label':n, 'value':n})

sites=sites2.copy()


visits='baseline,month_2,month_6,month_12,month_24'.split(',')
datatypes='mri,eeg,avl,cnb'.split(',')


column_type={
'subject_id':'text',
'mri_score':'numeric',
'mri_data':'numeric',
'mri_protocol':'numeric',
'mri_date':'datetime',
'mri_missing':'text',
'eeg_score':'numeric',
'eeg_data':'numeric',
'eeg_protocol':'numeric',
'eeg_date':'datetime',
'eeg_missing':'text',
'avl_score':'numeric',
'avl_data':'numeric',
'avl_protocol':'numeric',
'avl_date':'datetime',
'avl_missing':'text',
'cnb_score':'numeric',
'cnb_data':'numeric',
'cnb_protocol':'numeric',
'cnb_date':'datetime',
'cnb_missing':'text'
}

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

https://github.com/AMP-SCZ/missing-data-tracker &nbsp
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
            dbc.Col(html.Div([dcc.Input(id='days_low',placeholder='days_low'),
                html.Br(),
                'Days low'
                ]),
                width=1
            ),

            dbc.Col(html.Div([dcc.Input(id='days_high',placeholder='days_high'),
                html.Br(),
                'Days high'
                ]),
                width=1
            ),
        ]),

        html.Br(),

        dbc.Row([
            # datatype filter
            dbc.Col(html.Div(dcc.Dropdown(id='datatype', className='ddown',
                options=datatypes,
                value=datatypes,
                multi=True)),
                width=2
            ),

            # visit filter
            dbc.Col(html.Div(dcc.Dropdown(id='visit', className='ddown',
                options=visits,
                value=visits)),
                width=2
            ),

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
            dcc.Download(id='download-csv')],
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


# render table
@app.callback(Output('table','children'),
    [Input('site','value'),
    Input('visit','value'),
    Input('datatype','value'),
    Input('passwd','value'),
    Input('filter','n_clicks')])
def filter(site,visit,_datatypes,passwd,click):

    changed = [p['prop_id'] for p in callback_context.triggered][0]
    if not ('filter' in changed and site and visit):
        raise PreventUpdate


    # verify password
    if passwd==_passwd.loc['dpacc','passwd']:
        pass
    elif passwd==_passwd.loc[site,'passwd']:
        pass
    else:
        raise PreventUpdate


    # select file to load
    file=f'combined-{site}-data_{visit}-day1to1.csv'
    if site=='AMPSCZ':
        path=f'{ROOTDIR}/{file}'
    else:
        path=f'{ROOTDIR}/Pronet_status/{file}'
        
        if not isfile(path):
            path=f'{ROOTDIR}/Prescient_status/{file}'

    _df=pd.read_csv(path,dtype=str)
    
    # filter columns for datatype
    # MRI, EEG, AVL, CNB
    columns=['subject_id']
    for d in _datatypes:
        for c in _df.columns:
            if d in c:
                columns.append(c)
        
    df=_df[columns]
    

    # render selected columns/rows
    return DataTable(
        id='dataframe',
        columns=[{'name': f'{i}',
                  'id': i,
                  'hideable': True,
                  'type': column_type[i],
                  } for i in columns],
        data=df.to_dict('records'),
        filter_action='native',
        sort_action='native',
        page_size=df.shape[0],
        style_cell={
            'textAlign': 'left',
            'whiteSpace': 'pre-wrap',
            'width': '20px'
        },

        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },

        style_data_conditional=[
            {
                'if': {
                    'column_id': 'mri_missing',
                    'filter_query': f'{{mri_missing}} > ""',
                },
                'backgroundColor': 'red',
                'color': 'black',
            },
            {
                'if': {
                    'column_id': 'mri_data',
                    'filter_query': f'{{mri_data}} < 0',
                },
                'backgroundColor': 'red',
                'color': 'black',
            },
        ],
        )


# download filtered data
@app.callback(Output('download-csv','data'),
    [Input('table','children'),
    Input('site','value'),
    Input('visit','value'),
    Input('datatype','value'),
    Input('download','n_clicks')],
    prevent_initial_call=True)
def download(table,site,visit,datatype,click):

    if not click:
        raise PreventUpdate

    filtered=table['props']['derived_virtual_data']
    df=pd.DataFrame.from_dict(filtered)

    datestamp=datetime.now().strftime('%Y%m%d-%H%M')
    dtype='-'.join(datatype)
    
    return dcc.send_data_frame(df.to_csv,f'{site}-{visit}-{dtype}-{datestamp}.csv',index=False)


if __name__=='__main__':
    # debug=None allows control via DASH_DEBUG variable
    app.run_server(debug=None, host='localhost')

