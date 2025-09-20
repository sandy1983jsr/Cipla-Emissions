import dash
from dash import html, dcc, Input, Output, State, dash_table, callback_context
import pandas as pd
import plotly.express as px
from emissions import calculate_schedule_emissions, total_emissions
from optimize import optimize_schedule
import base64
import io

app = dash.Dash(__name__)
app.title = "Emissions Dashboard - Indore Unit 4"

# App layout
app.layout = html.Div([
    html.H1("Indore-Unit-4 Emissions Forecast & Optimization"),
    html.H2("Upload Your Data (.csv)"),
    html.Div([
        html.Div([
            dcc.Upload(
                id='upload-equipment',
                children=html.Button('Upload equipment.csv', className="upload-btn"),
                multiple=False
            ),
            dcc.Store(id='store-equipment'),
        ], style={'display': 'inline-block', 'margin-right': '20px'}),
        html.Div([
            dcc.Upload(
                id='upload-details',
                children=html.Button('Upload details.csv', className="upload-btn"),
                multiple=False
            ),
            dcc.Store(id='store-details'),
        ], style={'display': 'inline-block', 'margin-right': '20px'}),
        html.Div([
            dcc.Upload(
                id='upload-switchover',
                children=html.Button('Upload switchover.csv', className="upload-btn"),
                multiple=False
            ),
            dcc.Store(id='store-switchover'),
        ], style={'display': 'inline-block', 'margin-right': '20px'}),
        html.Div([
            dcc.Upload(
                id='upload-production',
                children=html.Button('Upload production.csv', className="upload-btn"),
                multiple=False
            ),
            dcc.Store(id='store-production'),
        ], style={'display': 'inline-block'}),
    ]),
    html.Div(id='file-status', style={'margin': '10px 0'}),
    html.Hr(),

    html.H2("Emissions Factors & Constraints"),
    html.Label("Electricity Emission Factor (kg CO2 / kWh)", style={'margin-top': '10px'}),
    dcc.Input(id='elec-ef', type='number', value=0.9, step=0.01, style={'margin-right': '30px'}),
    html.Label("Steam Emission Factor (kg CO2 / kg steam)"),
    dcc.Input(id='steam-ef', type='number', value=0.5, step=0.01, style={'margin-right': '30px'}),
    html.Label("Allowed Schedule Time Variation (+/- %, default 10%)"),
    dcc.Slider(
        id='time-var',
        min=0,
        max=0.5,
        step=0.01,
        value=0.1,
        marks={'0': '0%', '0.1': '10%', '0.2': '20%', '0.5': '50%'},
        tooltip={"placement": "bottom", "always_visible": True},
        style={'width': '350px', 'display': 'inline-block', 'verticalAlign': 'middle'}
    ),
    html.Br(),

    html.Button("Calculate Emissions", id='calc-btn', n_clicks=0, className='main-btn'),
    html.Button("Optimize Schedule", id='opt-btn', n_clicks=0, className='main-btn'),
    html.Hr(),

    html.Div(id='summary-table'),
    dcc.Graph(id='emissions-graph'),
    # Hidden stores to persist uploaded data
    dcc.Store(id='session-data', storage_type='session')
])

# Helper for parsing uploaded files
def parse_contents(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    return pd.read_csv(io.StringIO(decoded.decode('utf-8')))

# Upload callbacks for each file
@app.callback(
    Output('store-equipment', 'data'),
    Input('upload-equipment', 'contents')
)
def store_equipment(contents):
    if contents:
        df = parse_contents(contents)
        return df.to_json(date_format='iso', orient='split')
    return None

@app.callback(
    Output('store-details', 'data'),
    Input('upload-details', 'contents')
)
def store_details(contents):
    if contents:
        df = parse_contents(contents)
        return df.to_json(date_format='iso', orient='split')
    return None

@app.callback(
    Output('store-switchover', 'data'),
    Input('upload-switchover', 'contents')
)
def store_switchover(contents):
    if contents:
        df = parse_contents(contents)
        return df.to_json(date_format='iso', orient='split')
    return None

@app.callback(
    Output('store-production', 'data'),
    Input('upload-production', 'contents')
)
def store_production(contents):
    if contents:
        df = parse_contents(contents)
        return df.to_json(date_format='iso', orient='split')
    return None

# Update file status message
@app.callback(
    Output('file-status', 'children'),
    Input('store-equipment', 'data'),
    Input('store-details', 'data'),
    Input('store-switchover', 'data'),
    Input('store-production', 'data')
)
def update_file_status(equip, det, sw, prod):
    files = []
    if equip: files.append("Equipment Loaded")
    if det: files.append("Details Loaded")
    if sw: files.append("Switchover Loaded")
    if prod: files.append("Production Loaded")
    return ", ".join(files) if files else "No files uploaded yet."

# Main emissions and optimization callback
@app.callback(
    [Output('summary-table', 'children'),
     Output('emissions-graph', 'figure')],
    [Input('calc-btn', 'n_clicks'),
     Input('opt-btn', 'n_clicks')],
    [State('store-equipment', 'data'),
     State('store-details', 'data'),
     State('store-switchover', 'data'),
     State('store-production', 'data'),
     State('elec-ef', 'value'),
     State('steam-ef', 'value'),
     State('time-var', 'value')]
)
def run_emissions(calc_clicks, opt_clicks, equip, det, sw, prod, elec_ef, steam_ef, time_var):
    ctx = callback_context
    if not (equip and det and sw and prod):
        return "Please upload all required files.", {}
    equipment = pd.read_json(equip, orient='split')
    details = pd.read_json(det, orient='split')
    switchover = pd.read_json(sw, orient='split')
    production = pd.read_json(prod, orient='split')

    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'opt-btn':
        production = optimize_schedule(equipment, details, switchover, production, steam_ef, elec_ef, allowed_time_var=time_var)
    results = calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef)
    total = total_emissions(results)
    table = dash_table.DataTable(
        data=results[['product_code','name','batch_size','total_emissions']].to_dict('records'),
        columns=[{'name':i, 'id':i} for i in ['product_code','name','batch_size','total_emissions']],
        style_table={'overflowX':'auto'},
        style_header={'backgroundColor': '#FFE5CC', 'fontWeight': 'bold', "color": "#3C3C3B"},
        style_data={'backgroundColor': '#FFFFFF', "color": "#3C3C3B"},
    )
    fig = px.bar(
        results,
        x='product_code',
        y=['emissions_electricity','emissions_steam','switchover_emissions_electricity','switchover_emissions_steam'],
        title=f'Total Emissions by Product (Total: {total:.2f} kg CO2)',
        color_discrete_sequence=["#FF7900", "#BABABA", "#FFB380", "#3C3C3B"]
    )
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font_color="#3C3C3B"
    )
    return table, fig

if __name__ == '__main__':
    app.run_server(debug=True)
