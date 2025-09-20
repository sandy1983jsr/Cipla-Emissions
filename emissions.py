import pandas as pd

def calculate_batch_emissions(
    batch_schedule: pd.DataFrame,
    details: pd.DataFrame,
    switchover: pd.DataFrame,
    steam_ef: float,
    elec_ef: float
) -> pd.DataFrame:
    merged = batch_schedule.merge(details, on='product_code', how='left')
    merged['emissions_electricity'] = merged['total_electricity_consumed'] * elec_ef
    merged['emissions_steam'] = merged['total_steam_consumed'] * steam_ef

    switchover_electricity = []
    switchover_steam = []
    for i, row in merged.iterrows():
        if i == 0:
            switchover_electricity.append(0)
            switchover_steam.append(0)
        else:
            curr_prod = row['product_code']
            prev_prod = merged.iloc[i-1]['product_code']
            sw_type = 'batch' if curr_prod == prev_prod else 'product'
            sw_row = switchover[
                (switchover['product_code'] == curr_prod) & (switchover['switch_type'] == sw_type)
            ]
            if not sw_row.empty:
                sw_elec = sw_row.iloc[0]['electricity']
                sw_steam = sw_row.iloc[0]['steam']
            else:
                sw_elec = 0
                sw_steam = 0
            switchover_electricity.append(sw_elec * elec_ef)
            switchover_steam.append(sw_steam * steam_ef)
    merged['switchover_emissions_electricity'] = switchover_electricity
    merged['switchover_emissions_steam'] = switchover_steam
    merged['total_emissions'] = (
        merged['emissions_electricity'] +
        merged['emissions_steam'] +
        merged['switchover_emissions_electricity'] +
        merged['switchover_emissions_steam']
    )
    return merged

def total_facility_emissions(emissions_df: pd.DataFrame) -> float:
    return emissions_df['total_emissions'].sum()
