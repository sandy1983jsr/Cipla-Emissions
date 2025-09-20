import dash
from dash import html, dcc, Input, Output, State, dash_table
import pandas as pd
import plotly.express as px
from emissions import load_data, calculate_schedule_emissions, total_emissions
from optimize import optimize_schedule

app = dash.Dash(__name__)
app.title = "Emissions Dashboard - Indore Unit 4"

app.layout = html.Div([
    html.H1("Indore-Unit-4 Emissions Forecast & Optimization"),
    html.H2("Data Upload"),
    dcc.Upload(id='upload-equipment', children=html.Button('Upload equipment.csv'), multiple=False),
    dcc.Upload(id='upload-details', children=html.Button('Upload details.csv'), multiple=False),
    dcc.Upload(id='upload-switchover', children=html.Button('Upload switchover.csv'), multiple=False),
    dcc.Upload(id='upload-production', children=html.Button('Upload production.csv'), multiple=False),
    html.Div(id='file-status'),
    html.Hr(),

    html.H2("Emissions Factors & Constraints"),
    html.Label("Electricity Emission Factor (kg CO2 / kWh)"),
    dcc.Input(id='elec-ef', type='number', value=0.9, step=0.01),
    html.Label("Steam Emission Factor (kg CO2 / kg steam)"),
    dcc.Input(id='steam-ef', type='number', value=0.5, step=0.01),
    html.Label("Allowed Schedule Time Variation (+/- %, default 10%)"),
    dcc.Slider(id='time-var', min=0, max=0.5, step=0.01, value=0.1, marks={0:'0%',0.1:'10%',0.2:'20%',0.5:'50%'}),
    html.Br(),

    html.Button("Calculate Emissions", id='calc-btn', n_clicks=0),
    html.Button("Optimize Schedule", id='opt-btn', n_clicks=0),
    html.Hr(),

    html.Div(id='summary-table'),
    dcc.Graph(id='emissions-graph'),
])

# Store uploaded files as global (for demo; use dcc.Store for production apps)
data_dict = {}

def parse_contents(contents):
    content_type, content_string = contents.split(',')
    import base64, io
    decoded = base64.b64decode(content_string)
    return pd.read_csv(io.StringIO(decoded.decode('utf-8')))

@app.callback(
    Output('file-status', 'children'),
    [Input('upload-equipment', 'contents'),
     Input('upload-details', 'contents'),
     Input('upload-switchover', 'contents'),
     Input('upload-production', 'contents')]
)
def update_file_status(equip, det, sw, prod):
    files = []
    if equip: 
        data_dict['equipment'] = parse_contents(equip)
        files.append("Equipment Loaded")
    if det: 
        data_dict['details'] = parse_contents(det)
        files.append("Details Loaded")
    if sw: 
        data_dict['switchover'] = parse_contents(sw)
        files.append("Switchover Loaded")
    if prod: 
        data_dict['production'] = parse_contents(prod)
        files.append("Production Loaded")
    return ", ".join(files) if files else "No files uploaded yet."

@app.callback(
    [Output('summary-table', 'children'),
     Output('emissions-graph', 'figure')],
    [Input('calc-btn', 'n_clicks'),
     Input('opt-btn', 'n_clicks')],
    [State('elec-ef', 'value'),
     State('steam-ef', 'value'),
     State('time-var', 'value')]
)
def run_emissions(calc_clicks, opt_clicks, elec_ef, steam_ef, time_var):
    if not all(key in data_dict for key in ['equipment','details','switchover','production']):
        return "Please upload all files.", {}
    trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    production = data_dict['production']
    equipment = data_dict['equipment']
    details = data_dict['details']
    switchover = data_dict['switchover']

    if trigger == 'opt-btn':
        production = optimize_schedule(equipment, details, switchover, production, steam_ef, elec_ef, allowed_time_var=time_var)
    results = calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef)
    total = total_emissions(results)
    table = dash_table.DataTable(
        data=results[['product_code','name','batch_size','total_emissions']].to_dict('records'),
        columns=[{'name':i, 'id':i} for i in ['product_code','name','batch_size','total_emissions']],
        style_table={'overflowX':'auto'}
    )
    fig = px.bar(results, x='product_code', y=['emissions_electricity','emissions_steam','switchover_emissions_electricity','switchover_emissions_steam'],
                 title=f'Total Emissions by Product (Total: {total:.2f} kg CO2)')
    return table, fig

if __name__ == '__main__':
    app.run_server(debug=True)
