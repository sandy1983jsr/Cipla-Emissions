def optimize_batch_schedule(
    details: pd.DataFrame,
    switchover: pd.DataFrame,
    production: pd.DataFrame,
    steam_ef: float,
    elec_ef: float,
    allowed_time_var: float = 0.1,
):
    batch_df = batch_expand(production, details)
    # Base schedule (original order)
    base_schedule = batch_df.copy()
    base_emissions_df = calculate_batch_emissions(base_schedule, details, switchover, steam_ef, elec_ef)
    base_total_emissions = base_emissions_df['total_emissions'].sum()
    orig_total_time = base_emissions_df['running_hours'].sum()

    # Greedy + local search schedule
    greedy_idx = greedy_schedule(batch_df, details, switchover, steam_ef, elec_ef)
    best_idx = two_opt_local_search(
        greedy_idx, batch_df, details, switchover, steam_ef, elec_ef, allowed_time_var, orig_total_time
    )
    opt_schedule_df = batch_df.loc[best_idx].reset_index(drop=True)
    opt_emissions_df = calculate_batch_emissions(opt_schedule_df, details, switchover, steam_ef, elec_ef)
    opt_total_emissions = opt_emissions_df['total_emissions'].sum()

    # Ensure optimized emissions is not worse than base
    if opt_total_emissions < base_total_emissions:
        return opt_schedule_df, opt_emissions_df
    else:
        return base_schedule, base_emissions_df
