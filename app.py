import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp
from datetime import date
import pandas as pd
import os
import sqlite3
import bcrypt

class Carly:
    def __init__(self, title, db_file) -> None:
        self.db = DataBase(db_file)
        self.columns = ('ID', 'Type', 'Brand', 'Model', 'Color', 'Fuel', 'Engine', 'HP', 'Doors', 'Sunroof',
                        'Cases', 'Manufacture Year', 'Status', 'Kilometers', 'Price', 'Date Added')

        self.user_db = UserDB(db_file)
        self.user = None
        
        self.app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME])
        self.app.config.suppress_callback_exceptions = True
        self.app.title = title
        self.app.layout = html.Div([
            dcc.Store(id='cache', storage_type='memory'),   #exists only to trigger callbacks (useless value)
            dcc.Store(id='user', storage_type='memory', data=0), #0: no user, -1: incorrect credentials, >0: user logged in
            dcc.Location(id='url', refresh=False),
            html.Div(id='navbar', children=self.make_navbar()),
            html.Div(id='page-content', className='container'),
        ])

        self.callbacks(self.app)

    def make_navbar(self):
        navbar = dbc.Navbar(
            html.Div([
                dbc.NavItem(dbc.NavbarBrand('Carly', href='/')),
                dbc.NavbarToggler(id='navbar-toggler', n_clicks=0),
                dbc.Collapse([
                    html.Ul([
                        dbc.NavItem(dbc.NavLink('Insert', href='/insert')),
                        dbc.NavItem(dbc.NavLink('Database', href='/database')),
                        dbc.NavItem(dbc.NavLink('Charts', href='/charts')),
                    ], className='navbar-nav'),
                    html.Ul([
                        html.Div(
                            dbc.DropdownMenu(
                                children=[
                                    dbc.DropdownMenuItem('Log out', id='logout', n_clicks=0),
                                ],
                                id='logged-dd',
                                color='secondary',
                                align_end=True,
                            ),
                            id='logged-in',
                            hidden=True,
                        ),
                        html.Div(
                            dbc.NavItem(dbc.Button('Log in', href='/login', color='secondary', id='login-bttn', n_clicks=0)),
                            id='login-bttn-div',
                            hidden=False,
                        ),
                    ], className='navbar-nav ms-md-auto'),
                    ],
                    id='navbar-collapse',
                    is_open=False,
                    navbar=True,
                ),
            ], className='container'),
        color='primary', dark=True, className='fixed-top')
        return navbar

    def home_layout(self):
        welcome = 'Welcome, {}!'.format(self.user) if self.user else 'Welcome!'
        home_layout = html.Div([
            html.H1(welcome),
            html.P('This is the home page of Carly, the car project website :)'),
            html.Br(),
            html.P([
                'Click \'Insert\' if you want to add a new vehicle to the database.', html.Br(),
                'Click \'Database\' if you want to view the database.', html.Br(),
                'Click \'Charts\' if you want to view some database related graphs.'
            ]),
        ])
        return home_layout

    def denied_layout(self):
        home_layout = html.Div([
            html.H1('Denied access'),
            html.P('Please login to view this page.'),
            dbc.Button('Login', href='/login', className='btn btn-primary'),
        ])
        return home_layout

    def error404_layout(self):
        error404_layout = html.Div([
            html.H1('Error 404: Page not found'),
            html.Img(src='https://static.onecms.io/wp-content/uploads/sites/20/2018/05/21042210_264995290674140_8840525631411191808_n.jpg', width=400),
            html.Br(),
            html.Br(),
            html.P(['The page you\'re looking for doesn\'t exist.',  html.Br(), 'How did you even get here?', html.Br(), 'Please leave.....']),
        ])
        return error404_layout

    def login_layout(self):
        login_layout = html.Div([
            html.H1('Log in'),
            dbc.Row([
                dbc.Col(),
                dbc.Col(
                    dbc.Form([
                        dbc.FormFloating([
                            dbc.Input(id='username', type='text', placeholder='username'),
                            dbc.Label('Username', html_for='username'),
                        ], className='mb-3'),
                        dbc.FormFloating([
                            dbc.Input(id='password', type='password', placeholder='password'),
                            dbc.Label('Password', html_for='password'),
                        ], className='mb-3'),
                        html.Div(
                            dbc.Button('Login', id='login-page-bttn', n_clicks=0, type='submit', className='btn btn-lg btn-primary'),
                            className='d-grid gap-2 mb-3'),
                        dbc.Alert(
                            'Incorrect credentials!',
                            id='login-alert',
                            color='danger',
                            is_open=False,
                        ),
                    ]),
                    width=3,
                ),
                dbc.Col([
                    html.I(className='far fa-question-circle', id='hover-info'),
                    dbc.Popover(
                        dcc.Markdown('''Try using \'*user*\' and \'*password*\' ;)'''),
                        target='hover-info',
                        body=True,
                        trigger='hover',
                    ),
                ]),
            ], id='login-row'),
        ])
        return login_layout

    def insert_layout(self):
        label_width = 3
        input_width = ''

        def make_text_input(label_name, inp_id): 
            inp = dbc.Row([
                dbc.Label(label_name, html_for=inp_id, width=label_width),
                dbc.Col(
                    dbc.Input(
                        type='text',
                        id=inp_id,
                        #required=True,
                        #placeholder='Enter {}'.format(label_name)
                    ), width=input_width,
                ),
            ], className='mb-3',)
            return inp

        def make_num_input(label_name, inp_id, inp_max, inp_disabled=False): 
            inp = dbc.Row([
                dbc.Label(label_name, html_for=inp_id, width=label_width),
                dbc.Col(
                    dbc.Input(
                        type='number',
                        id=inp_id,
                        min='0',
                        max=inp_max,
                        disabled=inp_disabled,
                        #required=True,
                        #placeholder='Enter {}'.format(label_name)
                    ), width=input_width,
                ),
            ], className='mb-3',)
            return inp

        def make_selector(label_name, inp_id, inp_options, inp_disabled=False):
            inp = dbc.Row([
                dbc.Label(label_name, html_for=inp_id, width=label_width),
                dbc.Col(
                    dbc.Select(
                        id=inp_id,
                        options=inp_options,
                        disabled=inp_disabled,
                        #required=True,
                        #placeholder='Select {}'.format(label_name),
                    ), width=input_width,
                ),
            ], className='mb-3',)
            return inp

        def make_radios(label_name, inp_id, inp_options):
            inp = dbc.Row([
                dbc.Label(label_name, html_for=inp_id, width=label_width),
                dbc.Col(
                    dbc.RadioItems(
                        id=inp_id,
                        options=inp_options,
                        inline=True,
                        # no required field
                    ), width=input_width,
                ),
            ], className='mb-3',)
            return inp

        type_options = [
            {'label': 'Car', 'value': 'Car'},
            {'label': 'Motorbike', 'value': 'Motorbike'}
        ]
        color_options = [
            {'label': 'beige', 'value': 'beige'},
            {'label': 'black', 'value': 'black'},
            {'label': 'blue', 'value': 'blue'},
            {'label': 'brown', 'value': 'brown'},
            {'label': 'gold', 'value': 'gold'},
            {'label': 'green', 'value': 'green'},
            {'label': 'grey', 'value': 'grey'},
            {'label': 'orange', 'value': 'orange'},
            {'label': 'pink', 'value': 'pink'},
            {'label': 'purple', 'value': 'purple'},
            {'label': 'red', 'value': 'red'},
            {'label': 'silver', 'value': 'silver'},
            {'label': 'turquoise', 'value': 'turquoise'},
            {'label': 'white', 'value': 'white'},
            {'label': 'yellow', 'value': 'yellow'},
        ]
        fuel_options = [
            {'label': 'Petrol', 'value': 'Petrol'},
            {'label': 'Diesel', 'value': 'Diesel'},
            {'label': 'LPG', 'value': 'LPG'},
        ]
        yesno_options = [
            {'label': 'Yes', 'value': 'True'},
            {'label': 'No', 'value': 'False'},
        ]
        status_options = [
            {'label': 'New', 'value': 'New'},
            {'label': 'Used', 'value': 'Used'},
        ]
        curr_year = date.today().year
        year_options = [{'label': x, 'value': x} for x in range(curr_year, 1884, -1)]

        type_input = make_radios('Type', 'type-input', type_options)
        brand_input = make_text_input('Brand', 'brand-input')
        model_input = make_text_input('Model', 'model-input')
        color_input = make_selector('Color', 'color-input', color_options)
        fuel_input = make_radios('Fuel', 'fuel-input', fuel_options)
        engine_input = make_num_input('Engine (cc)', 'engine-input', '6000')
        hp_input = make_num_input('Horsepower', 'hp-input', '600')
        doors_input = make_num_input('Doors', 'doors-input', '10', True)
        sunroof_input = make_selector('Sunroof', 'sunroof-input', yesno_options, True)
        cases_input = make_num_input('Cases', 'cases-input', '5', True)
        manyear_input = make_selector('Manufacture Year', 'manyear-input', year_options)
        status_input = make_radios('Status', 'status-input', status_options)
        km_input = make_num_input('Kilometers', 'km-input', '')
        price_input = make_num_input('Price (€)', 'price-input', '')
        submit_bttn = dbc.Button('Submit', id='submit-bttn', n_clicks=0, className='btn btn-lg btn-primary')

        insert_form = html.Div(
            dbc.Form([
                type_input,
                brand_input,
                model_input,
                color_input,
                fuel_input,
                engine_input,
                hp_input,
                doors_input,
                sunroof_input,
                cases_input,
                manyear_input,
                status_input,
                km_input,
                price_input,
                html.Div(submit_bttn, className='d-grid gap-2')
            ]), className='d-grid gap-2',
        )

        error_modal = dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle('Form error'), close_button=True),
                dbc.ModalBody(['All the fields are required!', html.Br(), 'Please make sure you have filled out all of them.']),
            ],
            id='error-modal',
            centered=True,
            is_open=False,
        )

        choose_modal = dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle('Similar entries found'), close_button=True),
                dbc.ModalBody([
                    html.P('Please select the entries you want to keep in the database:'),
                    dash_table.DataTable(
                        id='same-table',
                        columns=[{'name': i, 'id': i} for i in self.columns],
                        row_selectable='multi',
                        style_table={'display':'block'}
                    )
                ]),
                dbc.ModalFooter([
                    dbc.Button('Select', id='modal-select', className='btn btn-primary', n_clicks=0, title='Keep 0 or more entries'),
                    dbc.Button('Cancel', id='modal-cancel', className='btn btn-secondary', n_clicks=0, title='Keep original entries')
                ]),
            ],
            id='choose-modal',
            centered=True,
            size='xl',
            is_open=False,
        )

        success_modal = dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle('Success!'), close_button=True),
                dbc.ModalBody(['Database updated successfully.']),
            ],
            id='success-modal',
            centered=True,
            is_open=False,
        )

        insert_layout = html.Div([
            html.H1('Insert'),
            error_modal,
            choose_modal,
            success_modal,
            dbc.Col(insert_form, md=8, xl=5)
        ])

        return insert_layout

    def database_layout(self):
        database_layout = html.Div([
            html.H1('Database'),
            dcc.Download(id='download-csv'),
            dbc.Row([
                dbc.Col(
                    dbc.Checklist(
                    options=[{'label': 'Sort', 'value': 'Sort'}, {'label': 'Filter', 'value': 'Filter'}],
                    id='table-switch',
                    switch=True,
                    inline=True),
                    width=2,
                    id='table-switch-col'
                ),
                dbc.Col([
                    dbc.Input(id='custom-filter-input', placeholder='Enter custom filter query', disabled=True),
                    dbc.Tooltip(
                        ['Use the column names between curly brackets', html.Br(), '(e.g. \'{Engine}\')',
                        html.Br(), 'and logical \'and\' and \'or\'.'],
                        target='custom-filter-input',
                        placement='top',
                    ),
                    ], id='custom-filter-col', width=4),
                dbc.Col(dbc.Button('Download', id='download-button'), id='download-button-col')
            ], id='database-options'),            
            dash_table.DataTable(
                id='db-table',
                columns=[{'name': i, 'id': i} for i in self.columns],
                style_cell_conditional=[ {'if': {'column_id': c}, 'textAlign': 'left'} for c in ('Type','Brand','Model','Color','Fuel','Sunroof','Status') ],
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f0f0f0',}],
                page_action='native',
                page_size=100,
            ),
        ])

        return database_layout
    
    def charts_layout(self):
        def _make_type_radios(dd_id):
            options = [
                {'label': 'All Vehicles', 'value': 'All'},
                {'label': 'Only Cars', 'value': 'Car'},
                {'label': 'Only Motorbikes', 'value': 'Motorbike'},
            ]
            return dbc.RadioItems(
                id=dd_id,
                options=options,
                value='All',
                inline=True,
            )

        tab1 = dcc.Tab(
            label='Vehicles Added per Date',
            children=[
                html.Br(),
                html.H3(
                    dbc.Row([
                        dbc.Col('Vehicles Added per', id='tab1-title-col1'),
                        dbc.Col(
                            dcc.Dropdown(
                                id='timeperiod-dropdown',
                                options=[{'label': x, 'value': x} for x in ('Day', 'Week', 'Month', 'Year')],
                                value='Day',
                                searchable=False,
                                clearable=False,
                            ),
                            width=2,
                            align='left',
                            id='tab1-title-col2'
                        ),
                        dbc.Col(width=4)
                    ]),
                ),
                html.P('Choose date range to graph:'),
                dcc.DatePickerRange(
                    id='my-date-picker-range',
                    display_format='DD/MM/YY',
                    max_date_allowed=date.today(),
                    end_date=date.today()
                ),
                html.Div(id='output-container-date-picker-range'),
                dcc.Graph(id='count-date', config={'displayModeBar': False})
            ],
        )

        tab2 = dcc.Tab(
            label='Vehicles Added (Range Slider)',
            children=[
                html.Br(),
                html.H3('Vehicles Added (Range Slider)', className='centered-title'),
                dcc.Graph(id='count-rangeslider', config={'displayModeBar': False}),
            ],
        )

        tab3 = dcc.Tab(
            label='Percentage per Type & Fuel',
            children=[
                html.Br(),
                html.H3('Percentage of Vehicles per Type and Fuel', className='centered-title'),
                dcc.Graph(id='count-typefuel', config={'displayModeBar': False})
            ],
        )

        tab4 = dcc.Tab(
            label='Km Per Manuf. Year',
            children=[
                html.Br(),
                html.H3('Kilometers Per Manufacture Year', className='centered-title'),
                _make_type_radios('type-radios1'),
                dcc.Graph(id='km-per-manyear', config={'displayModeBar': False}),
            ],
        )

        tab5 = dcc.Tab(
            label='Percentage per Price Range',
            children=[
                html.Br(),
                html.H3('Percentage of Vehicles per Price Range (10k€ intervals)', className='centered-title'),
                dcc.Graph(id='price-range-pie', config={'displayModeBar': False}),
            ],
        )

        tab6 = dcc.Tab(
            label='Average Price per Type',
            children=[
                html.Br(),
                html.H3('Average Prices per Type', className='centered-title'),
                dcc.Graph(id='avg-price-per-type-status', config={'displayModeBar': False}),
            ],
        )

        tab7 = dcc.Tab(
            label='Average Price per Brand',
            children=[
                html.Br(),
                html.H3('Average Price per Brand', className='centered-title'),
                _make_type_radios('type-radios2'),
                dcc.Graph(id='avg-price-per-brand', config={'displayModeBar': False})
            ],
        )

        tab8 = dcc.Tab(
            label='Maximum Engine per Brand',
            children=[
                html.Br(),
                html.H3('Maximum Engine Capacity per Brand', className='centered-title'),
                dcc.Graph(id='max-engine-per-brand', config={'displayModeBar': False}),
            ],
        )

        tab9 = dcc.Tab(
            label='Count per Color',
            children=[
                html.Br(),
                html.H3('Count Vehicles per Color', className='centered-title'),
                dcc.Graph(id='count-color', config={'displayModeBar': False})
            ],
        )

        tab10 = dcc.Tab(
            label='Count per Field',
            children=[
                html.Br(),
                html.H3('Count Vehicles per Field', className='centered-title'),
                _make_type_radios('type-radios3'),
                dbc.Row([
                    dbc.Col('Choose field to graph:', width=2),
                    dbc.Col(
                        dcc.Dropdown(
                            id='field-dropdown',
                            value='Brand',
                            searchable=False,
                            clearable=False,
                        ),
                        width=2,
                    ),
                ]),
                dcc.Graph(id='count-per-typefield', config={'displayModeBar': False}),  #'scrollZoom': True
            ],
        )

        charts_layout = html.Div([
            html.H1('Charts'),
            html.Div([
                dcc.Tabs([
                    tab1,
                    tab2,
                    tab3,
                    tab4,
                    tab5,
                    tab6,
                    tab7,
                    tab8,
                    tab9,
                    tab10,
                ],)
            ])
        ])

        return charts_layout

    def callbacks(self, app):
        @app.callback(
            Output('navbar-collapse', 'is_open'),
            Input('navbar-toggler', 'n_clicks'),
            State('navbar-collapse', 'is_open'))
        def toggle_navbar_collapse(n_clicks, is_open):
            if n_clicks:
                return not is_open
            return is_open

        @app.callback(
            Output('page-content', 'children'),
            Input('url', 'pathname'))
        def display_page(pathname):
            if pathname == '/':
                return self.home_layout()
            elif pathname == '/login':
                return self.login_layout()
            elif pathname == '/insert' and self.user:
                return self.insert_layout()
            elif pathname == '/database' and self.user:
                return self.database_layout()
            elif pathname == '/charts' and self.user:
                return self.charts_layout()
            elif pathname in ('/insert', '/database', '/charts') and not self.user:
                return self.denied_layout()
            else:
                return self.error404_layout()

        @app.callback(
            [Output('user', 'data'), Output('login-alert', 'is_open')],
            Input('login-page-bttn', 'n_clicks'),
            [State('username', 'value'), State('password', 'value')],
            prevent_initial_call=True)
        def login(login, username, password):
            if login and not self.user:
                if username and password:
                    if self.user_db.check_password(username, password):
                        self.user = username
                        return 1, False
                return -1, True
            return 0, False

        @app.callback(
            [Output('logged-in', 'hidden'), Output('logged-dd', 'label'), Output('login-bttn-div', 'hidden'), Output('url', 'pathname')],
            [Input('user', 'data'), Input('logout', 'n_clicks')],
            State('url', 'pathname'))
        def logout(user_data, logout, url):
            triggered_id = dash.callback_context.triggered[0]['prop_id']
            if 'logout.n_clicks' == triggered_id and logout:
                self.user = None
                return True, None, False, '/'
            if self.user:
                if user_data > 0 or url == '/login':
                    # if JUST logged in: redirect to homepage with username
                    # OR tried to use login page again
                    return False, self.user, True, '/'
                # logged in: don't redirect
                return False, self.user, True, dash.no_update
            # if not logged in: don't redirect
            return True, None, False, dash.no_update

        @app.callback(
            [Output('doors-input', 'disabled'), Output('sunroof-input', 'disabled'), Output('cases-input', 'disabled')],
            Input('type-input', 'value'))
        def disable_inputs(veh_type):
            if veh_type == 'Car':
                return False, False, True
            elif veh_type == 'Motorbike':
                return True, True, False
            else:
                return True, True, True

        @app.callback(
            [Output('cache', 'data'), Output('error-modal', 'is_open'), Output('choose-modal', 'is_open'), Output('same-table', 'data'), Output('success-modal', 'is_open')],
            [Input('submit-bttn', 'n_clicks'), Input('choose-modal', 'is_open'), Input('modal-select', 'n_clicks'), Input('modal-cancel', 'n_clicks'),],
            [State('type-input', 'value'), State('brand-input', 'value'), State('model-input', 'value'), State('color-input', 'value'),
            State('fuel-input', 'value'), State('engine-input', 'value'), State('hp-input', 'value'), State('doors-input', 'value'),
            State('sunroof-input', 'value'), State('cases-input', 'value'), State('manyear-input', 'value'), State('status-input', 'value'),
            State('km-input', 'value'), State('price-input', 'value'),
            State('same-table', 'derived_virtual_selected_rows'), State('same-table', 'data')],
            prevent_initial_call=True)
        def form_trigger_regulator(submit, modal_open, modal_select, modal_cancel, type, brand, model, color, fuel, engine, hp, doors, sunroof, cases, manyear, status, km, price, selected, table_data):
            triggered_id = dash.callback_context.triggered[0]['prop_id']
            if 'submit-bttn.n_clicks' == triggered_id and submit:
                # triger: submit button
                return submit_form(type, brand, model, color, fuel, engine, hp, doors, sunroof, cases, manyear, status, km, price)
            elif 'modal-select.n_clicks' == triggered_id and modal_select:
                # trigger: select button inside choose_modal
                return modal_form(selected, table_data)
            elif ('modal-cancel.n_clicks' == triggered_id and modal_cancel) or ('choose-modal.is_open' == triggered_id and not modal_open and table_data):
                # trigger: cancel modal OR close modal w/o select button
                # if modal is closed without selecting, select all table data except last to put back into the df
                select = list(range(len(table_data)-1))
                return modal_form(select, table_data)
            else:
                return False, False, False, None, False

        def submit_form(type, brand, model, color, fuel, engine, hp, doors, sunroof, cases, manyear, status, km, price):    
            if not type:
                return False, True, False, None, False
            elif type == 'Car' and None in (type, brand, model, color, fuel, engine, hp, doors, sunroof, manyear, status, km, price):
                return False, True, False, None, False
            elif type == 'Motorbike' and None in (type, brand, model, color, fuel, engine, hp, cases, manyear, status, km, price):
                return False, True, False, None, False
            
            id = self.db.get_max_of('id') + 1
            date_added = self.db.get_curr_date()
            veh_tup = (id, type, brand, model, color, fuel, engine, hp, doors, sunroof, cases, manyear, status, km, price, date_added)
            
            
            similar_df = pd.DataFrame(self.db.find_similar('similars', veh_tup), columns=self.columns)
            self.db.drop_table('similars')
            if len(similar_df) > 1:
                return True, False, True, similar_df.to_dict('records'), False

            self.db.add_row(veh_tup)
            return True, False, False, None, True

        def modal_form(selected, table_data):
            keep_rows = [tuple(table_data[i].values()) for i in selected]
            dont_keep_rows = [tuple(table_data[i].values()) for i in range(len(table_data)) if i not in selected]

            for keeper in keep_rows:
                self.db.add_row(keeper)
            for not_keeper in dont_keep_rows:
                self.db.delete_row(not_keeper)

            return True, False, False, None, True

        @app.callback(
            Output('db-table', 'data'),
            Input('cache', 'data'))
        def update_table(cache):
            df = pd.DataFrame(self.db.get_all(), columns=self.columns)
            return df.to_dict('records')

        @app.callback(
            Output('db-table', 'style_data_conditional'),
            Input('db-table', 'active_cell'),
            State('db-table', 'style_data_conditional'))
        def style_active_row(active_cell, style_cond):
            if not active_cell:
                return style_cond
                
            active_row_id = active_cell['row']
            new_style_cond = [d for d in style_cond if not (d['backgroundColor'] == '#ff413633')]
            new_style_cond.append({'if': {'row_index': active_row_id}, 'backgroundColor': '#ff413633',})
            return new_style_cond
        
        @app.callback(
            [Output('db-table', 'sort_action'),
            Output('db-table', 'filter_action'),
            Output('custom-filter-input', 'disabled')],
            Input('table-switch', 'value'),)
        def filter_sort_action(switch):
            to_sort = 'none'
            to_filter = 'none', True
            if not switch:
                return to_sort, *to_filter
            
            if 'Sort' in switch:
                to_sort = 'native'
            if 'Filter' in switch:
                to_filter = 'native', False
            return to_sort, *to_filter

        @app.callback(
            Output('db-table', 'filter_query'),
            Input('custom-filter-input', 'value'))
        def write_query(query):
            if query is None:
                return ''
            return query

        @app.callback(
            Output('download-csv', 'data'),
            Input('download-button', 'n_clicks'),
            prevent_initial_call=True)
        def export_csv(n_clicks):
            df = pd.DataFrame(self.db.get_all(), columns=self.columns)
            return dcc.send_data_frame(df.to_csv, 'database.csv', index=False, header=True, columns=self.columns)

        @app.callback(
            [Output('my-date-picker-range', 'min_date_allowed'),
            Output('my-date-picker-range', 'start_date')],
            Input('cache', 'data'))
        def update_output(cache):
            minDate = self.db.get_min_of('date')
            return minDate, minDate

        @app.callback(
            Output('count-date', 'figure'),
            [Input('cache', 'data'),
            Input('timeperiod-dropdown', 'value'),
            Input('my-date-picker-range', 'start_date'),
            Input('my-date-picker-range', 'end_date')])
        def count_per_freq(cache, timeperiod, start, end):
            freq_calc = { 'Day': 'date',
                          'Week': 'date(date, "weekday 0", "-6 days")',
                          'Month': 'strftime("%Y-%m-01", date)',
                          'Year': 'strftime("%Y-01-01", date)' }
            ticks = { 'Day': '%d %b <br>%Y', 'Week': 'Week %V <br>%Y', 'Month': '%b <br>%Y', 'Year': '%Y' }

            query_type = '''SELECT {} AS freq, type, COUNT(id) FROM {}
                WHERE "{}" <= date and date <= "{}"
                GROUP BY freq, type ORDER BY freq;
            '''.format(freq_calc[timeperiod], '{}', start, end)
            dfCoundFreqType = pd.DataFrame(self.db.custom_query(query_type), columns=[timeperiod, 'Type', 'Count'])
            
            query_all = '''SELECT {} AS freq, COUNT(id) FROM {}
                WHERE "{}" <= date and date <= "{}"
                GROUP BY freq ORDER BY freq;
            '''.format(freq_calc[timeperiod], '{}', start, end)
            dfCoundFreqAll = pd.DataFrame(self.db.custom_query(query_all), columns=[timeperiod, 'Count'])

            lineDateType = px.line(dfCoundFreqType, x=timeperiod, y='Count', color='Type', category_orders = {'Type': ['Car', 'Motorbike']})
            lineDateType.add_scatter(x=dfCoundFreqAll[timeperiod], y=dfCoundFreqAll['Count'], line_color='black', name='All')
            lineDateType.update_traces(mode='markers+lines', hovertemplate=None)
            lineDateType.update_layout(hovermode='x unified')
            lineDateType.update_xaxes(nticks=len(dfCoundFreqAll), tickformat=ticks[timeperiod])

            return lineDateType

        @app.callback(
            Output('count-rangeslider', 'figure'),
            Input('cache', 'data'))
        def count_rangeslider(cache):
            tempdfAll = pd.DataFrame(self.db.count_field('date'), columns=('Date', 'Count'))
            lineRangeSlider = px.line(tempdfAll, x='Date', y='Count')
            lineRangeSlider.update_xaxes(
                rangeslider_visible=True,
                rangeselector=dict(
                    buttons=list([
                        dict(step='all'),
                        dict(count=1, label='1y', step='year', stepmode='backward'),
                        dict(count=6, label='6m', step='month', stepmode='backward'),
                        dict(count=3, label='3m', step='month', stepmode='backward'),
                        dict(count=1, label='1m', step='month', stepmode='backward'),
                        dict(count=7, label='1w', step='day', stepmode='backward'),
                        #dict(count=1, label='1d', step='day', stepmode='backward'),
                        
                        #dict(count=1, label='Current Year', step='year', stepmode='todate'),
                        #dict(count=6, label='Current Semester', step='month', stepmode='todate'),
                        #dict(count=3, label='Current Trimester', step='month', stepmode='todate'),
                        #dict(count=1, label='Current Month', step='month', stepmode='todate'),
                    ])
                )
            )

            return lineRangeSlider

        @app.callback(
            Output('count-typefuel', 'figure'),
            Input('cache', 'data'))
        def count_per_typefuel(cache):
            dfCountTypeFuel = pd.DataFrame(self.db.count_field('type, fuel'), columns=('Type', 'Fuel', 'Count'))
            dfCountCarFuel = dfCountTypeFuel.loc[dfCountTypeFuel['Type']=='Car']
            dfCountMotoFuel = dfCountTypeFuel.loc[dfCountTypeFuel['Type']=='Motorbike']
            
            pies = sp.make_subplots(1,3, specs=[[{'type':'domain'}, {'type':'domain'}, {'type':'domain'}]],
                                    subplot_titles=['Count Vehicles', 'Car Fuel', 'Motorbike Fuel'])
            pies.add_trace(go.Pie(labels=dfCountTypeFuel['Type'], values=dfCountTypeFuel['Count'], text=dfCountTypeFuel['Type'], scalegroup='one', name=''), 1, 1)
            pies.add_trace(go.Pie(labels=dfCountCarFuel['Fuel'], values=dfCountCarFuel['Count'], text=dfCountCarFuel['Fuel'], scalegroup='one', name=''), 1, 2)
            pies.add_trace(go.Pie(labels=dfCountMotoFuel['Fuel'], values=dfCountMotoFuel['Count'], text=dfCountMotoFuel['Fuel'], scalegroup='one', name=''), 1, 3)

            return pies

        @app.callback(
            Output('km-per-manyear', 'figure'),
            [Input('cache', 'data'),
            Input('type-radios1', 'value')])
        def km_per_manyear(cache, selected_type):
            filtered_db = self.db.select_type(selected_type) if selected_type != 'All' else self.db.get_all()
            filtered_df = pd.DataFrame(filtered_db, columns=self.columns)
            
            scatterKmPerManYear = px.scatter(filtered_df, x='Manufacture Year', y='Kilometers', size='Price', color='Brand', custom_data=('Brand', 'Model', 'Price'))
            scatterKmPerManYear.update_traces(hovertemplate='<b>%{customdata[0]} %{customdata[1]}</b> <br><br>Manufacture Year=%{x}<br>Kilometers=%{y}<br>Price=%{customdata[2]}<extra></extra>')
            return scatterKmPerManYear

        @app.callback(
            Output('price-range-pie', 'figure'),
            Input('cache', 'data'))
        def count_per_pricerange(cache):
            query = 'SELECT FLOOR(price / 10000) as floor, COUNT(id) FROM {} GROUP BY floor'

            range_list = [("[{}0k, {}0k)".format(i, i+1), c) for i, c in self.db.custom_query(query)]
            if '[00k' in range_list[0][0]:
                range_list[0] = ('[0, 10k)', range_list[0][1])
            dfPriceRange = pd.DataFrame(range_list, columns=['Price Range', 'Count'])
            
            piePriceRange = px.pie(dfPriceRange, values='Count', names='Price Range', color='Price Range')
            piePriceRange.update_traces(sort=False, textinfo='percent+label', hovertemplate='Price Range=%{label}<br>Count=%{value}</br>Percent=%{percent}')
            #piePriceRange.update_traces(sort=False, textposition='inside', textinfo='percent+label', hovertemplate='Price Range=%{label}<br>Count=%{value}</br>Percent=%{percent}')
            #piePriceRange.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
            
            return piePriceRange

        @app.callback(
            Output('avg-price-per-type-status', 'figure'),
            Input('cache', 'data'))
        def avg_price_per_typestatus(cache):
            query_type = 'SELECT type, status, AVG(price) FROM {} GROUP BY type, status'
            query_all = 'SELECT status, AVG(price) FROM {} GROUP BY status'

            tempdfTypeMean = pd.DataFrame(self.db.custom_query(query_type), columns=('Type', 'Status', 'Average Price'))
            tempdfAllMean = pd.DataFrame(self.db.custom_query(query_all), columns=('Status', 'Average Price'))
            tempdfAllMean.insert(0, 'Type', ['All', 'All'], True)
            dfAvgPricePerTypeStatus = tempdfTypeMean.append(tempdfAllMean, ignore_index=True)
            barAvgPricePerTypeStatus = px.bar(dfAvgPricePerTypeStatus, x='Type', y='Average Price', color='Status', barmode='group', text='Status')
            barAvgPricePerTypeStatus.update_traces(texttemplate='%{text}<br>%{value:.2s}€', textfont_size=12, textangle=0, textposition='inside', cliponaxis=False)
            barAvgPricePerTypeStatus.update_layout(showlegend=False)

            return barAvgPricePerTypeStatus

        @app.callback(
            Output('avg-price-per-brand', 'figure'),
            [Input('cache', 'data'),
            Input('type-radios2', 'value')])
        def avg_price_per_brand(cache, selected_type):
            query = 'SELECT brand, AVG(price) FROM {} GROUP BY brand'
            if selected_type != 'All':
                query = query.format('{} WHERE type = "%s"' % (selected_type))

            dfAvgPricePerBrand = pd.DataFrame(self.db.custom_query(query), columns=('Brand', 'Average Price'))
            barAvgPrice = px.bar(dfAvgPricePerBrand, x='Brand', y='Average Price', color='Brand', text_auto='.2s')
            barAvgPrice.update_traces(textfont_size=12, textangle=0, textposition='outside', cliponaxis=False)
            barAvgPrice.update_layout(hovermode=False)

            return barAvgPrice

        @app.callback(
            Output('max-engine-per-brand', 'figure'),
            Input('cache', 'data'))
        def max_engine_per_brand(cache):
            query = 'SELECT brand, MAX(engine) FROM {} GROUP BY brand'
            
            dfMaxEnginePerBrand = pd.DataFrame(self.db.custom_query(query), columns=('Brand', 'Maximum Engine'))
            barMaxEnginePerBrand = px.bar(dfMaxEnginePerBrand, x='Brand', y='Maximum Engine', color='Brand')
            barMaxEnginePerBrand.update_traces(texttemplate='%{y}cc', textfont_size=12, textangle=0, textposition='outside', cliponaxis=False)
            barMaxEnginePerBrand.update_layout(hovermode=False)

            return barMaxEnginePerBrand

        @app.callback(
            Output('count-color', 'figure'),
            Input('cache', 'data'))
        def count_per_color(cache):
            Colormap = {
                'black':'black',
                'brown':'brown',
                'blue':'blue',
                'green':'green',
                'grey':'grey',
                'light blue':'lightblue',
                'orange':'orange',
                'red':'red',
                'turquoise':'turquoise',
                'white':'whitesmoke',
                'yellow':'gold',  
            }

            dfCountColors = pd.DataFrame(self.db.count_field('color'), columns=('Color', 'Count'))
            barColor = px.bar(dfCountColors, x='Color', y='Count', color='Color', text='Count', color_discrete_map=Colormap)
            barColor.update_traces(textfont_size=12, textangle=0, textposition='outside', cliponaxis=False)
            barColor.update_layout(hovermode=False)


            return barColor

        @app.callback(
            [Output('field-dropdown', 'options'),
            Output('field-dropdown', 'value')],
            Input('type-radios3', 'value'))
        def set_field_options(selected_type):
            all_options = {
                'All': ['Brand', 'Model', 'Color', 'Fuel', 'Engine', 'HP', 'Manufacture Year', 'Status', 'Kilometers', 'Price', 'Date'],
                'Car': ['Brand', 'Model', 'Color', 'Fuel', 'Engine', 'HP', 'Doors', 'Sunroof', 'Manufacture Year', 'Status', 'Kilometers', 'Price', 'Date'],
                'Motorbike': ['Brand', 'Model', 'Color', 'Fuel', 'Engine', 'HP', 'Cases', 'Manufacture Year', 'Status', 'Kilometers', 'Price', 'Date'],
            }
            options = [{'label': i, 'value': i} for i in all_options[selected_type]]
            return options, options[0]['value']

        @app.callback(
            Output('count-per-typefield', 'figure'),
            [Input('cache', 'data'),
            Input('type-radios3', 'value'),
            Input('field-dropdown', 'value')])
        def count_per_field(cache, selected_type, selected_field):
            fields_dict = {'ID': 'id', 'Type': 'type', 'Brand': 'brand', 'Model': 'model', 'Color': 'color',
                           'Fuel': 'fuel', 'Engine': 'engine', 'HP': 'hp', 'Doors': 'doors', 'Sunroof': 'sunroof',
                           'Cases': 'cases', 'Manufacture Year': 'manufacture_year', 'Status': 'status',
                           'Kilometers': 'kilometers', 'Price': 'price', 'Date Added': 'date'}
            
            field = fields_dict[selected_field]
            if selected_type == 'All':
                dfCountPerField = pd.DataFrame(self.db.count_field('{}, type'.format(field)), columns=(selected_field, 'Type', 'Count'))
                colorfield = 'Type'
                catorder = {'Type': ['Car', 'Motorbike']}
            else:
                dfCountPerField = pd.DataFrame(self.db.count_field(field, selected_type), columns=(selected_field, 'Count'))
                colorfield = None
                catorder = {}

            fig = px.bar(dfCountPerField, x=selected_field, y='Count', color=colorfield, category_orders=catorder)
            if selected_field in {'Engine', 'Kilometers', 'Price'}:
                # make bad plots into scatter
                fig = px.scatter(dfCountPerField, x=selected_field, y='Count', color=colorfield, category_orders=catorder)
            elif selected_field in {'Model'}:
                fig.update_yaxes(dtick=1)
            elif selected_field in {'Doors', 'Cases'}:
                fig.update_xaxes(dtick=1, tickformat='d', type='category')
            
            return fig

class DataBase:
    def __init__(self, input_file) -> None:
        self.sql_file = os.path.join(os.path.dirname(__file__), input_file)

        self.tb_name = 'vehicles'
        self.columns = ('id', 'type', 'brand', 'model', 'color', 'fuel', 'engine', 'hp', 'doors', 'sunroof', 'cases',
            'manufacture_year', 'status', 'kilometers', 'price', 'date')
        
        self.make_sql(os.path.dirname(__file__)+'/assets/vehicles.csv')

    @staticmethod
    def connect_to_db(func):
        def wrapper(*args, **kw):
            self = args[0]
            with sqlite3.connect(self.sql_file) as self.con:
                #self.cur = self.con.cursor()
                return func(*args, **kw)
        return wrapper

    @connect_to_db
    def make_sql(self, csv_file) -> None:
        # one time use only bc my original database was in csv format
        # not necessarily optimized!
        cur = self.con.cursor()
        cur.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="{}";'.format(self.tb_name))
        if cur.fetchone():
            # table already exists
            return

        column_types = {
            'id': 'INTEGER PRIMARY KEY',
            'type': 'TEXT',
            'brand': 'TEXT',
            'model': 'TEXT',
            'color': 'TEXT',
            'fuel': 'TEXT',
            'engine': 'INTEGER',
            'hp': 'INTEGER',
            'doors': 'INTEGER',
            'sunroof': 'TEXT',
            'cases': 'INTEGER',
            'manufacture_year': 'INTEGER',
            'status': 'TEXT',
            'kilometers': 'INTEGER',
            'price': 'INTEGER',
            'date': 'DATE'}

        df = pd.read_csv(csv_file)
        df.to_sql(self.tb_name, self.con, index=False, dtype=column_types)
        cur = self.con.cursor()
        cur.execute('UPDATE {} SET sunroof="True" WHERE sunroof="1";'.format(self.tb_name))
        cur = self.con.cursor()
        cur.execute('UPDATE {} SET sunroof="False" WHERE sunroof="0";'.format(self.tb_name))

    @connect_to_db
    def get_all(self) -> list:
        cur = self.con.cursor()
        cur.execute('SELECT * FROM {};'.format(self.tb_name))
        return cur.fetchall()

    @connect_to_db
    def add_row(self, output) -> None:
        cur = self.con.cursor()
        cur.execute('SELECT * FROM {} WHERE id = {};'.format(self.tb_name, output[0]))
        if not cur.fetchone():
            # if not found in db, add it
            veh = str(output).replace('None', 'null')
            cur.execute('INSERT INTO {}{} VALUES{};'.format(self.tb_name, self.columns, veh))

    @connect_to_db
    def delete_row(self, veh_tup) -> None:
        cur = self.con.cursor()
        cur.execute('DELETE FROM {} WHERE id = {};'.format(self.tb_name, veh_tup[0]))

    @connect_to_db
    def custom_query(self, query) -> list:
        cur = self.con.cursor()
        cur.execute(query.format(self.tb_name))
        return cur.fetchall()

    @connect_to_db
    def select_type(self, value) -> list:
        if value not in ('Car', 'Motorbike'):
            return []
        cur = self.con.cursor()
        cur.execute('SELECT * FROM {} WHERE type = "{}";'.format(self.tb_name, value))
        return cur.fetchall()

    @connect_to_db
    def count_field(self, field, type=None) -> list:
        cur = self.con.cursor()
        if not type:
            cur.execute('SELECT {}, Count(id) FROM {} GROUP BY {};'.format(field, self.tb_name, field))
        else:
            cur.execute('SELECT {}, Count(id) FROM {} WHERE type = "{}" GROUP BY {};'.format(field, self.tb_name, type, field))
        return cur.fetchall()
    
    @connect_to_db
    def get_curr_date(self) -> str:
        cur = self.con.cursor()
        cur.execute('SELECT date(\'now\');')
        return cur.fetchone()[0]
    
    @connect_to_db
    def get_min_of(self, field) -> str:
        cur = self.con.cursor()
        cur.execute('SELECT MIN({}) FROM {};'.format(field, self.tb_name))
        return cur.fetchone()[0]

    @connect_to_db
    def get_max_of(self, field) -> int:
        cur = self.con.cursor()
        cur.execute('SELECT MAX({}) FROM {};'.format(field, self.tb_name))
        return cur.fetchone()[0]

    @connect_to_db
    def find_similar(self, similar_table, veh_tup) -> list:
        cur = self.con.cursor()
        cur.execute('CREATE TABLE {} AS SELECT * FROM {} WHERE type = "{}" AND brand = "{}" AND model = "{}";'.format(similar_table, self.tb_name, veh_tup[1], veh_tup[2], veh_tup[3]))
        veh = str(veh_tup).replace('None', 'null')
        cur.execute('INSERT INTO {}{} VALUES{};'.format(similar_table, self.columns, veh))
        cur.execute('SELECT * FROM {}'.format(similar_table))
        return cur.fetchall()
    
    @connect_to_db
    def drop_table(self, similar_table) -> None:
        cur = self.con.cursor()
        cur.execute('DROP TABLE {};'.format(similar_table))

class UserDB:
    def __init__(self, input_file) -> None:
        self.users_file = os.path.join(os.path.dirname(__file__), input_file)

        self.tb_name = 'users'
        self.columns = ('username', 'password')

        self.salt = bcrypt.gensalt()

        self.create_table()

    @staticmethod
    def connect_to_db(func):
        def wrapper(*args, **kw):
            self = args[0]
            with sqlite3.connect(self.users_file) as self.con:
                #self.cur = self.con.cursor()
                return func(*args, **kw)
        return wrapper
    
    @connect_to_db
    def create_table(self) -> None:
        cur = self.con.cursor()
        cur.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="{}";'.format(self.tb_name))
        if cur.fetchone():
            # table already exists
            return

        column_types = 'username TEXT PRIMARY KEY, password TEXT'
        cur.execute('CREATE TABLE {} ({});'.format(self.tb_name, column_types))

        initial_users = [
            ('anina', 'mimini'),
            ('user', 'password'),
            ('admin', 'stronger'),
        ]
        for user in initial_users:
            self.add_user(user)

    @connect_to_db
    def add_user(self, user) -> None:
        cur = self.con.cursor()
        pass_hashed = bcrypt.hashpw(user[1].encode(), self.salt)
        user_hashed = (user[0], pass_hashed.decode())
        cur.execute('INSERT INTO {}{} VALUES{};'.format(self.tb_name, self.columns, user_hashed))

    @connect_to_db
    def check_password(self, username, password) -> list:
        cur = self.con.cursor()
        cur.execute('SELECT * FROM {} WHERE username = "{}";'.format(self.tb_name, username))
        user = cur.fetchone()
        if user:
            return bcrypt.checkpw(password.encode(), user[1].encode())
        return False

if __name__ == '__main__':
    web = Carly(title='Carly: My Car Project', db_file='database.db')
    web.app.run_server()