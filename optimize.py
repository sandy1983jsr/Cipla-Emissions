import pandas as pd
import numpy as np
from typing import Tuple, List

def batch_expand(production: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    # Expand each product into individual batches
    all_batches = []
    for _, row in production.iterrows():
        prod_code = row['product_code']
        n_batches = int(row['number_of_batches'])
        for batch_num in range(n_batches):
            all_batches.append({
                'product_code': prod_code,
                'batch_num': batch_num + 1
            })
    return pd.DataFrame(all_batches)

def calculate_batch_emissions(
    batch_schedule: pd.DataFrame,
    details: pd.DataFrame,
    switchover: pd.DataFrame,
    steam_ef: float,
    elec_ef: float
) -> pd.DataFrame:
    # Attach details for each batch
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

def total_running_time(df: pd.DataFrame) -> float:
    return df['running_hours'].sum()

def greedy_schedule(
    all_batches: pd.DataFrame,
    details: pd.DataFrame,
    switchover: pd.DataFrame,
    steam_ef: float,
    elec_ef: float,
) -> List[int]:
    remaining = all_batches.index.tolist()
    schedule = []
    last_prod = None

    while remaining:
        min_emissions = np.inf
        min_idx = None
        for idx in remaining:
            batch = all_batches.loc[[idx]]
            merged = batch.merge(details, on='product_code', how='left')
            if not schedule:
                sw_elec = sw_steam = 0
            else:
                curr_prod = merged.iloc[0]['product_code']
                sw_type = 'batch' if curr_prod == last_prod else 'product'
                sw_row = switchover[
                    (switchover['product_code'] == curr_prod) & (switchover['switch_type'] == sw_type)
                ]
                if not sw_row.empty:
                    sw_elec = sw_row.iloc[0]['electricity'] * elec_ef
                    sw_steam = sw_row.iloc[0]['steam'] * steam_ef
                else:
                    sw_elec = sw_steam = 0
            elec = merged.iloc[0]['total_electricity_consumed'] * elec_ef
            steam = merged.iloc[0]['total_steam_consumed'] * steam_ef
            total_e = elec + steam + sw_elec + sw_steam
            if total_e < min_emissions:
                min_emissions = total_e
                min_idx = idx
        schedule.append(min_idx)
        last_prod = all_batches.loc[min_idx]['product_code']
        remaining.remove(min_idx)
    return schedule

def two_opt_local_search(
    schedule: List[int],
    all_batches: pd.DataFrame,
    details: pd.DataFrame,
    switchover: pd.DataFrame,
    steam_ef: float,
    elec_ef: float,
    allowed_time_var: float,
    orig_time: float
) -> List[int]:
    improved = True
    best_schedule = schedule.copy()
    best_emissions = calculate_batch_emissions(
        all_batches.loc[best_schedule].reset_index(drop=True),
        details, switchover, steam_ef, elec_ef
    )['total_emissions'].sum()
    min_time = orig_time * (1 - allowed_time_var)
    max_time = orig_time * (1 + allowed_time_var)

    while improved:
        improved = False
        for i in range(len(best_schedule)-1):
            for j in range(i+1, len(best_schedule)):
                new_schedule = best_schedule.copy()
                new_schedule[i], new_schedule[j] = new_schedule[j], new_schedule[i]
                candidate = all_batches.loc[new_schedule].reset_index(drop=True)
                candidate_emissions_df = calculate_batch_emissions(candidate, details, switchover, steam_ef, elec_ef)
                total_time = candidate_emissions_df['running_hours'].sum()
                total_emissions = candidate_emissions_df['total_emissions'].sum()
                if (min_time <= total_time <= max_time) and (total_emissions < best_emissions):
                    best_schedule = new_schedule
                    best_emissions = total_emissions
                    improved = True
        # If no improvement, loop exits
    return best_schedule

def optimize_batch_schedule(
    details: pd.DataFrame,
    switchover: pd.DataFrame,
    production: pd.DataFrame,
    steam_ef: float,
    elec_ef: float,
    allowed_time_var: float = 0.1,
):
    # 1. Expand production into batches
    batch_df = batch_expand(production, details)
    # 2. Calculate original emissions and total time
    orig_schedule = batch_df.copy()
    orig_emissions_df = calculate_batch_emissions(orig_schedule, details, switchover, steam_ef, elec_ef)
    orig_total_time = orig_emissions_df['running_hours'].sum()
    # 3. Greedy solution
    greedy_idx = greedy_schedule(batch_df, details, switchover, steam_ef, elec_ef)
    # 4. Local search (2-opt)
    best_idx = two_opt_local_search(
        greedy_idx, batch_df, details, switchover, steam_ef, elec_ef, allowed_time_var, orig_total_time
    )
    best_schedule_df = batch_df.loc[best_idx].reset_index(drop=True)
    best_emissions_df = calculate_batch_emissions(best_schedule_df, details, switchover, steam_ef, elec_ef)
    return best_schedule_df, best_emissions_df
