import pandas as pd

def load_data(equipment_path, details_path, switchover_path, production_path):
    equipment = pd.read_csv(equipment_path)
    details = pd.read_csv(details_path)
    switchover = pd.read_csv(switchover_path)
    production = pd.read_csv(production_path)
    return equipment, details, switchover, production

def calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef):
    # Merge production with details to get relevant info
    merged = production.merge(details, on='product_code', suffixes=('', '_details'))
    
    # Emissions for production
    merged['emissions_electricity'] = merged['total_electricity_consumed'] * elec_ef
    merged['emissions_steam'] = merged['total_steam_consumed'] * steam_ef
    
    # Switchover emissions
    switch_emissions = []
    prev_prod = None
    for i, row in merged.iterrows():
        if i == 0:
            switch_emissions.append({'emissions_electricity': 0, 'emissions_steam': 0, 'switchover_type': None})
        else:
            curr_prod = row['product_code']
            prev_prod = merged.iloc[i-1]['product_code']
            if curr_prod == prev_prod:
                sw_type = 'batch'
            else:
                sw_type = 'product'
            sw_row = switchover[(switchover['product_code'] == curr_prod) & (switchover['switch_type'] == sw_type)]
            if not sw_row.empty:
                sw_elec = sw_row['electricity'].values[0]
                sw_steam = sw_row['steam'].values[0]
            else:
                sw_elec = 0
                sw_steam = 0
            switch_emissions.append({
                'emissions_electricity': sw_elec * elec_ef,
                'emissions_steam': sw_steam * steam_ef,
                'switchover_type': sw_type
            })
    switchover_df = pd.DataFrame(switch_emissions)
    merged['switchover_emissions_electricity'] = switchover_df['emissions_electricity']
    merged['switchover_emissions_steam'] = switchover_df['emissions_steam']
    merged['switchover_type'] = switchover_df['switchover_type']

    merged['total_emissions'] = merged['emissions_electricity'] + merged['emissions_steam'] + merged['switchover_emissions_electricity'] + merged['switchover_emissions_steam']
    return merged

def total_emissions(df):
    return df['total_emissions'].sum()
