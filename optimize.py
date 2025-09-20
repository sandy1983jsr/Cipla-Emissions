import pandas as pd
import numpy as np
from itertools import permutations

def schedule_total_time(schedule, details):
    merged = schedule.merge(details, on='product_code')
    return merged['running_hours'].sum()

def calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef):
    merged = production.merge(details, on='product_code')
    merged['emissions_electricity'] = merged['total_electricity_consumed'] * elec_ef
    merged['emissions_steam'] = merged['total_steam_consumed'] * steam_ef

    switch_electricity = []
    switch_steam = []
    prev_prod = None
    for i, row in merged.iterrows():
        if i == 0:
            switch_electricity.append(0)
            switch_steam.append(0)
        else:
            curr_prod = row['product_code']
            prev_prod = merged.iloc[i-1]['product_code']
            sw_type = 'product' if curr_prod != prev_prod else 'batch'
            sw_row = switchover[
                (switchover['product_code'] == curr_prod) & (switchover['switch_type'] == sw_type)
            ]
            if not sw_row.empty:
                sw_elec = sw_row['electricity'].values[0]
                sw_steam = sw_row['steam'].values[0]
            else:
                sw_elec = 0
                sw_steam = 0
            switch_electricity.append(sw_elec * elec_ef)
            switch_steam.append(sw_steam * steam_ef)
    merged['switchover_emissions_electricity'] = switch_electricity
    merged['switchover_emissions_steam'] = switch_steam
    merged['total_emissions'] = (
        merged['emissions_electricity'] + merged['emissions_steam'] +
        merged['switchover_emissions_electricity'] + merged['switchover_emissions_steam']
    )
    return merged

def optimize_schedule(
    equipment, details, switchover, production, steam_ef, elec_ef, allowed_time_var=0.1
):
    n = len(production)
    if n > 7:
        raise ValueError("Too many products for brute-force optimization.")
    original_time = schedule_total_time(production, details)
    min_time = original_time * (1 - allowed_time_var)
    max_time = original_time * (1 + allowed_time_var)

    # Calculate base emissions for reference
    base_emissions_df = calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef)
    base_total_emissions = base_emissions_df['total_emissions'].sum()

    best_emissions = base_total_emissions
    best_schedule = production.copy()

    prod_rows = production.to_dict('records')
    for perm in permutations(prod_rows):
        test_schedule = pd.DataFrame(list(perm))
        test_time = schedule_total_time(test_schedule, details)
        if not (min_time <= test_time <= max_time):
            continue
        emissions_df = calculate_schedule_emissions(equipment, details, switchover, test_schedule, steam_ef, elec_ef)
        total_emissions = emissions_df['total_emissions'].sum()
        if total_emissions < best_emissions:
            best_emissions = total_emissions
            best_schedule = test_schedule.copy()

    return best_schedule.reset_index(drop=True)
