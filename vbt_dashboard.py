 ## Load Libraries
import numpy as np
import pandas as pd
import vectorbtpro as vbt
from datetime import datetime, date
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, dash_table
import dash.dash_table.FormatTemplate as FormatTemplate
from dash.dependencies import Input, Output

# region - LOAD VBT PICKLE FILE OBJECTS
## Load pickle files of saved results from VBT
price_data = vbt.Config.load('data/price_data.pickle')
vbt_indicators_data = vbt.Config.load('data/vbt_indicators_data.pickle')
pandas_indicators_data = vbt.Config.load('data/pandas_indicator_data.pickle')
entries_exits_data = vbt.Config.load('data/entries_exits_data.pickle')
pf = vbt.Portfolio.load('data/pf_sim.pickle') ## Portfolio Simulation Results
symbols = list(pf.trade_history['Column'].unique())
# print(type(vbt_indicators_data), vbt_indicators_data["m15_rsi_bbands"]["GBPUSD"].lowerband)

stats_df = pd.concat([pf.stats()] + [pf[symbol].stats() for symbol in symbols], axis = 1)
stats_df.loc['Avg Winning Trade Duration'] = [x.floor('s') for x in stats_df.iloc[21]]
stats_df.loc['Avg Losing Trade Duration'] = [x.floor('s') for x in stats_df.iloc[22]]
stats_df = stats_df.reset_index().astype(str)
stats_df.rename(inplace = True, columns = {'agg_stats':'WholePortfolio','index' : 'Metrics'})      
print(stats_df)

resample_time_periods = ['15m', '4h']
sel_symbol = symbols[0]
sel_period = resample_time_periods[1]

## Load data from pickle files 
## m15_data
m15_data = price_data["m15_data"]
m15_open  = m15_data.get('Open')
m15_close = m15_data.get('Close')
m15_high  = m15_data.get('High')
m15_low   = m15_data.get('Low')

## h4 data
h4_data = price_data["h4_data"]
h4_open  = h4_data.get('Open')
h4_close = h4_data.get('Close')
h4_high  = h4_data.get('High')
h4_low   = h4_data.get('Low')

m15_bbands_price = vbt_indicators_data["m15_price_bbands"]
h4_bbands_price  = vbt_indicators_data["h4_price_bbands"]

m15_rsi = pandas_indicators_data["m15_rsi"]
h4_rsi = pandas_indicators_data["h4_rsi"]
m15_bbands_rsi = vbt_indicators_data["m15_rsi_bbands"]
h4_bbands_rsi  = vbt_indicators_data["h4_rsi_bbands"]

clean_entries = entries_exits_data['clean_entries']
clean_exits = entries_exits_data['clean_exits']
clean_entries_h4 = clean_entries.vbt.resample_apply("4h", "any", wrap_kwargs=dict(dtype=bool))
clean_exits_h4 = clean_exits.vbt.resample_apply("4h", "any", wrap_kwargs=dict(dtype=bool))
# endregion

## GLOBAL VARIABLES
app = Dash(__name__, meta_tags=[{"name": "viewport", "contentZ": "width=device-width, initial-scale=1"}])
app.title = "VectorBT Dashboard"
server = app.server
app.config["suppress_callback_exceptions"] = True


## Global VBT Plot Settings
vbt.settings.set_theme("dark")
vbt.settings['plotting']['layout']['width'] = 1200

def build_banner():
    return html.Div(
        id="banner",
        className="banner",
        children=[
            html.Div(
                id="banner-text",
                children=[
                    html.H5("VectorBT Dashboard"),
                    html.H6("Portfolio Simulation (Backtest) Results and Strategy Visualizer"),
                ],
            ),
            html.Div(
                id="banner-logo",
                children=[html.A(html.Img(id="logo",src=app.get_asset_url("vbt_logo.png")),href="https://vectorbt.pro"),
                ],
            ),
        ],
    )


def build_tabs():
    return html.Div(id="tabs", className="tabs", 
    children=[dcc.Tabs(id="app-tabs",value="tab1",className="custom-tabs",
             children=[dcc.Tab(id="sim-res-tab", label="Portfolio Simulation", value="tab1",className="custom-tab",
                        selected_className="custom-tab--selected" ),
                       dcc.Tab(id="strategy-viz-tab", label="Strategy Visualizer", value="tab2", className="custom-tab",
                        selected_className="custom-tab--selected" )
                ],
            )
        ],
    )


symbols_dropdown = html.Div([
                        html.P('Select Symbol:',style={"font-weight":"bold"}),
                        dcc.Dropdown(id = 'select-symbol-dropdown',
                        options = list({'label': symbol, 'value': symbol} for symbol in symbols),
                        style = {'width':'60%','text-align': 'left'},
                        value = sel_symbol, optionHeight = 25)
                        ])

time_periods_tab1 = html.Div([
                        html.P('(Resample) Time period:',style={"font-weight":"bold"}),
                        dcc.Dropdown(id = 'select-resample-dropdown',
                        options = list({'label': period, 'value': period} for period in ['15m','4h', '1d']),
                        style = {'width':'60%','text-align': 'left'},
                        value = '1d', optionHeight = 25)
                        ])       

time_periods_tab2 = html.Div([
                        html.P('Chart TimeFrame:',style={"font-weight":"bold"}),
                        dcc.Dropdown(id = 'select-resample-dropdown',
                        options = list({'label': period, 'value': period} for period in resample_time_periods),
                        style = {'width':'60%','text-align': 'left'},
                        value = sel_period, optionHeight = 25)
                        ])   


## Simulation Performance Statistics
stats_datatable = dash_table.DataTable(id='simulation_stats_table',
                                    data = stats_df.to_dict(orient = 'records'),
                                    columns =  [{'id': c, 'name': c} for c in stats_df.columns], 
                                    fill_width=True,
                                    style_as_list_view = True,                                    
                                    style_table={'minWidth': '95%'},
                                    fixed_columns={'headers': True, 'data': 1},                                    
                                    style_data={'backgroundColor': 'black', 'color': 'white'},                                    
                                    # style_cell={'textAlign': 'center','height': 'auto', 'width': '100px', 
                                    #             'maxWidth': '200px','whiteSpace': 'normal'},                                                                        
                                    style_header={'backgroundColor': 'rgb(30,30,30)',
                                                    'color': 'white', 'fontWeight': 'bold'}
                                    )

def build_tab_1():
    dd_plt_kwargs = {"title_text" : f"Drawdowns Plot for {sel_symbol}"}
    uw_plt_kwargs = {"title_text" : f"Underwater Plot for {sel_symbol}"}
    return [
        dbc.Row([dbc.Col([symbols_dropdown],style={'width': '50%', 'display': 'inline-block'}), 
                 dbc.Col([time_periods_tab1], style={'width': '50%', 'display': 'inline-block'})] 
                    ),        
        html.Div(children = [
            dcc.Graph(id = 'pf-orders', figure = pf[sel_symbol].resample(sel_period).plot()),
            dcc.Graph(id = 'drawdown-plot', figure =  pf[sel_symbol].drawdowns.plot(**dd_plt_kwargs)),
            dcc.Graph(id = 'underwater-plot', figure =  pf[sel_symbol].plot_underwater(**uw_plt_kwargs)),
            html.Hr(style = {'borderColor':'white'}),
            html.Div(children = [html.H5('Portfolio Simulation Statistics', 
                                          style={"font-weight":"bold",'display' : 'flex','justifyContent': 'center'}),
                                stats_datatable ])
                ])
        ]

## Add Markdown table for Simulation results

# callback for Tab 1
# ------------------------------------------------------------
@app.callback(
    [Output('pf-orders', 'figure'),
     Output('drawdown-plot', 'figure'),
     Output('underwater-plot', 'figure')],
    Input('select-symbol-dropdown', 'value'),
    Input('select-resample-dropdown', 'value')
    )
def render_symbol_charts(symbol, period):
    order_plt_kwargs = {"title_text" : f"{symbol} - {period}"}
    drawdown_plt_kwargs = {"title_text" : f"Drawdowns Plot for {symbol}",'title_x': 0.5}
    underwater_plt_kwargs = {"title_text" : f"Underwater Plot for {symbol}",'title_x': 0.5}
    order_plot = pf[symbol].resample(period).plot(**order_plt_kwargs)
    drawdown_plot = pf[symbol].drawdowns.plot(**drawdown_plt_kwargs)
    underwater_plt_kwargs = pf[symbol].plot_underwater(**underwater_plt_kwargs)
    return [order_plot, drawdown_plot, underwater_plt_kwargs]

date_picker_range = html.Div([
    html.Label("Select Date Range:"),
    dcc.DatePickerRange(
        id='date-picker',
        clearable=True,
        reopen_calendar_on_clear=True,
        persistence=False,
        min_date_allowed = m15_open.index[0].date(),
        max_date_allowed = m15_close.index[-1].date(),
        initial_visible_month = m15_open.index[0].date(),
        start_date = h4_open.index[0].date(),
        end_date= h4_close.index[200].date())
])


# callback for Tab 2
# ------------------------------------------------------------
@app.callback(
    Output('ohlcv-plot', 'figure'),
    [Input(component_id = 'date-picker', component_property = 'start_date'),
     Input(component_id = 'date-picker', component_property = 'end_date'),
     Input('select-symbol-dropdown', 'value'),
     Input('select-resample-dropdown', 'value')]
    )
def main_chart(start_date, end_date, symbol, time_period):
    start_date_txt = datetime.strptime(start_date, '%Y-%m-%d').strftime("%b %d, %Y")
    end_date_txt = datetime.strptime(end_date, '%Y-%m-%d').strftime("%b %d, %Y")
    start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y.%m.%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y.%m.%d')
    bb_line_style = dict(color="white",width=1, dash="dot")
    fig_kwargs = { "title_font_size" : 18, 'title_x': 0.5, "height" : 720,
                  "legend" : dict(yanchor="top",y=0.99, xanchor="left",x= 0.1)}
    

    # print("START DATE:", start_date, '||', "END DATE:", end_date)
    if time_period == '4h':
        fig_kwargs["title_text"] = f"H4 OHLCV with BBands for {symbol} from {start_date_txt} to {end_date_txt}"
        df_ohlc = pd.concat([h4_open[symbol], h4_high[symbol], h4_low[symbol], h4_close[symbol] ], 
                            axis =  1, keys= ['Open', 'High', 'Low', 'Close'])
        bb_bands = h4_bbands_price
    elif time_period == '15m':
        fig_kwargs["title_text"] = f"m15 OHLCV with BBands for {symbol} from {start_date_txt} to {end_date_txt}"
        df_ohlc = pd.concat([m15_open[symbol], m15_high[symbol], m15_low[symbol], m15_close[symbol] ], 
                            axis =  1, keys= ['Open', 'High', 'Low', 'Close'])
        bb_bands = m15_bbands_price
    ## Filter Data according to date slice
    df_slice = df_ohlc[["Open", "High", "Low", "Close"]][start_date : end_date]
    ## Retrieve datetime index of rows where price data is NULL
    # retrieve the dates that are in the original datset
    dt_obs = df_slice.index.to_list()
    # Drop rows with missing values
    dt_obs_dropped = df_slice['Close'].dropna().index.to_list()
    # Store dates with missing values
    dt_breaks = [d for d in dt_obs if d not in dt_obs_dropped]

    fig =  df_slice.vbt.ohlcv.plot(**fig_kwargs) 
     ## Plots Long Entries / Exits and Short Entries / Exits
    pf[symbol][start_date:end_date].plot_trade_signals(fig=fig, plot_close=False, plot_positions="lines")

    # bb_bands[symbol].plot(fig=fig,
    #             lowerband_trace_kwargs=dict(fill=None, name = 'BB_Price_Lower', connectgaps=True, line = bb_line_style), 
    #             upperband_trace_kwargs=dict(fill=None, name = 'BB_Price_Upper', connectgaps=True, line = bb_line_style),
    #             middleband_trace_kwargs=dict(fill=None, name = 'BB_Price_Middle', connectgaps=True))    


    
    ## Plot Trade Profit or Loss Boxes
    pf[symbol].trades.direction_long[start_date : end_date].plot(fig=fig,plot_close = False, plot_markers = False)
    pf[symbol].trades.direction_short[start_date : end_date].plot(fig=fig,plot_close = False, plot_markers = False)
    fig.update_xaxes(rangebreaks=[dict(values=dt_breaks)])
    return fig


def rsi_indicator(start_date, end_date, rsi, bb_rsi, entries, exits, fig_kwargs):
    start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y.%m.%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y.%m.%d')
    rsi = rsi[start_date : end_date]
    bb_rsi = bb_rsi[start_date : end_date]
    fig = rsi.rename("RSI").vbt.plot(trace_kwargs = dict(connectgaps=True), **fig_kwargs)
    bb_line_style = dict(color="white",width=1, dash="dot")
    # bb_rsi.plot(fig=fig,
    #             lowerband_trace_kwargs=dict(fill=None, name = 'BB_RSI_Lower', connectgaps=True,line = bb_line_style), 
    #             upperband_trace_kwargs=dict(fill=None, name = 'BB_RSI_Upper', connectgaps=True,line = bb_line_style),
    #             middleband_trace_kwargs=dict(fill=None, name = 'BB_RSI_Middle', connectgaps=True, visible = False))  
    
    if (entries is not None) & (exits is not None):
        ## Slice Entries and Exits
        entries = entries[start_date : end_date]
        exits = exits[start_date : end_date]
        ## Add Entries and Long Exits on RSI in lower subplot
        entries.vbt.signals.plot_as_entries(rsi, fig = fig,
                                            trace_kwargs=dict(name = "Long Entry", marker=dict(color="limegreen") ))  
        exits.vbt.signals.plot_as_exits(rsi, fig = fig, 
                                        trace_kwargs=dict(name = "Short Entry",  marker=dict(color="red"),
                                                        # showlegend = False ## To hide this from the legend
                                                        ))     
    return fig

@app.callback(
    Output('indicator1', 'figure'),
    [Input(component_id = 'date-picker', component_property = 'start_date'),
     Input(component_id = 'date-picker', component_property = 'end_date'),
     Input('select-symbol-dropdown', 'value'),
     Input('indicator-resampler', 'value')])

def contruct_rsi(start_date, end_date, symbol, time_period):
    if time_period == "15m":
        rsi = m15_rsi[symbol]
        bb_rsi = m15_bbands_rsi[symbol]
        entries = clean_entries[symbol]
        exits = clean_exits[symbol]
    elif time_period == "4h":
        rsi = h4_rsi[symbol]
        bb_rsi = h4_bbands_rsi[symbol]
        entries = clean_entries_h4[symbol]
        exits = clean_exits_h4[symbol]
    fig_kwargs = {"title_text" : f"RSI plot for {symbol} on {time_period} time period",'title_x': 0.5}
    fig = rsi_indicator(start_date, end_date, rsi, bb_rsi, entries, exits, fig_kwargs)
    return fig

def build_tab_2():
    return [
        html.Br(),
        dbc.Row([dbc.Col([symbols_dropdown],style={'width': '50%', 'display': 'inline-block'}), 
                dbc.Col([time_periods_tab2],style={'width': '50%', 'display': 'inline-block', 'float': 'left'})]),
        html.Br(),
        date_picker_range,
        html.Br(),
        html.Div(children = [ dcc.Graph(id = 'ohlcv-plot') ] ),
        html.Div([
                html.Label("RSI Time-Period:"),
                dcc.Dropdown(id = 'indicator-resampler', style = {'width':'40%','text-align': 'left'},
                options = list({'label': period, 'value': period} for period in resample_time_periods),
                value = "15m", optionHeight = 25)
                ]),
        html.Div(children = [html.P(id = 'rsi_label',style={"font-weight":"bold"}),
                             dcc.Graph(id = 'indicator1') ])
    ]

dummy_content = html.Div([
    html.Div([html.P("Column 1")], style={'width': '33%', 'display': 'inline-block' }),
    html.Div([html.P("Column 2")], style={'width': '33%', 'display': 'inline-block', 'float': 'right'})
    ])

@app.callback(Output("app-content", "children"), Input("app-tabs", "value"))

def render_tab_content(tab):
    if tab == "tab1":
        return build_tab_1()        
        # return html.Div(children = [html.P(f"Welcome to {tab.upper()}"), html.Br(), dummy_content])       

    elif tab == "tab2":
        return build_tab_2()        
        # return html.Div(children = [html.P(f"Welcome to {tab.upper()}"), html.Br(), dummy_content])   



app.layout = html.Div(
    children=[
        build_banner(),
        build_tabs(),
        # Main app
        html.Div(id='app-content', className='container scalable')
    ]
)

# Run the App
if __name__ == "__main__":
    app.run_server(port=8001,debug=True)
