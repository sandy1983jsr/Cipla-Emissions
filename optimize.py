import pandas as pd
import numpy as np

def calculate_total_emissions(schedule, details, switchover, steam_ef, elec_ef):
    # Use your existing calculate_batch_emissions logic here!
    emissions_df = calculate_batch_emissions(schedule, details, switchover, steam_ef, elec_ef)
    return emissions_df['total_emissions'].sum(), emissions_df

def simulated_annealing_optimizer(
    batch_df, details, switchover, steam_ef, elec_ef, allowed_time_var, orig_time,
    max_iter=2000, initial_temp=1000, cooling_rate=0.995, min_temp=1e-3
):
    # Initial solution (random shuffle)
    current_idx = batch_df.index.to_numpy()
    np.random.shuffle(current_idx)
    current_schedule = batch_df.loc[current_idx].reset_index(drop=True)
    current_emissions, current_emissions_df = calculate_total_emissions(
        current_schedule, details, switchover, steam_ef, elec_ef
    )
    best_schedule = current_schedule.copy()
    best_emissions = current_emissions
    best_emissions_df = current_emissions_df.copy()

    temp = initial_temp
    for i in range(max_iter):
        # Swap two random batches to create a neighbor
        neighbor_idx = current_idx.copy()
        a, b = np.random.choice(len(neighbor_idx), 2, replace=False)
        neighbor_idx[a], neighbor_idx[b] = neighbor_idx[b], neighbor_idx[a]
        neighbor_schedule = batch_df.loc[neighbor_idx].reset_index(drop=True)
        neighbor_emissions, neighbor_emissions_df = calculate_total_emissions(
            neighbor_schedule, details, switchover, steam_ef, elec_ef
        )
        total_time = neighbor_emissions_df['running_hours'].sum()
        min_time = orig_time * (1 - allowed_time_var)
        max_time = orig_time * (1 + allowed_time_var)
        # Only accept neighbor if within allowed time window
        if min_time <= total_time <= max_time:
            delta = neighbor_emissions - current_emissions
            if delta < 0 or np.random.rand() < np.exp(-delta / temp):
                current_idx = neighbor_idx
                current_schedule = neighbor_schedule
                current_emissions = neighbor_emissions
                current_emissions_df = neighbor_emissions_df
                if current_emissions < best_emissions:
                    best_schedule = current_schedule.copy()
                    best_emissions = current_emissions
                    best_emissions_df = current_emissions_df.copy()
        temp *= cooling_rate
        if temp < min_temp:
            break

    return best_schedule, best_emissions_df

def optimize_batch_schedule(
    details, switchover, production, steam_ef, elec_ef, allowed_time_var=0.1,
):
    # Expand all batches
    batch_df = batch_expand(production, details)

    # Base emissions and time
    base_schedule = batch_df.copy()
    base_emissions_df = calculate_batch_emissions(base_schedule, details, switchover, steam_ef, elec_ef)
    base_total_emissions = base_emissions_df['total_emissions'].sum()
    orig_total_time = base_emissions_df['running_hours'].sum()

    # Run simulated annealing optimizer
    best_schedule, best_emissions_df = simulated_annealing_optimizer(
        batch_df, details, switchover, steam_ef, elec_ef, allowed_time_var, orig_total_time
    )
    best_total_emissions = best_emissions_df['total_emissions'].sum()

    # Ensure optimized is not worse than base
    if best_total_emissions < base_total_emissions:
        return best_schedule, best_emissions_df
    else:
        return base_schedule, base_emissions_df
