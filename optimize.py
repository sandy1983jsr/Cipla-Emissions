import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpInteger, LpStatus
from emissions import calculate_schedule_emissions

def optimize_schedule(equipment, details, switchover, production, steam_ef, elec_ef, allowed_time_var=0.1):
    """
    Reorders batches to minimize emissions while meeting production volume and time constraints.
    allowed_time_var: e.g., 0.1 for +/-10% of original total production time.
    """
    # Get original total time
    merged = production.merge(details, on='product_code')
    original_total_time = merged['running_hours'].sum()

    # Setup optimization problem
    n = len(production)
    prod_indices = list(range(n))
    prob = LpProblem("ScheduleOptimization", LpMinimize)

    # Decision variables: the order of each batch in sequence
    order_vars = [LpVariable(f'order_{i}', lowBound=0, upBound=n-1, cat=LpInteger) for i in prod_indices]

    # Objective: sum of emissions for the new order
    # For simplicity, we'll assume the emissions are additive and depend only on the order.
    # For real cases, a custom callback or iterative approach may be needed.

    # Constraint: all positions are unique (permutation)
    for i in prod_indices:
        for j in prod_indices:
            if i != j:
                prob += order_vars[i] != order_vars[j]

    # Constraint: total time within allowed_time_var
    time_taken = lpSum([merged.iloc[i]['running_hours'] for i in prod_indices])
    prob += time_taken >= (1 - allowed_time_var) * original_total_time
    prob += time_taken <= (1 + allowed_time_var) * original_total_time

    # For demonstration: minimize sum of emissions in the given order
    # In reality, you need to simulate emissions for each permutation
    # Here, we just use initial order as a proxy for speed
    # For real use, use a metaheuristic or MIP solver with callback

    # Place-holder: minimize total emissions of initial schedule
    # (Upgrade with a proper sequence optimization for real production)
    total_emission = sum(calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef)['total_emissions'])
    prob += total_emission

    prob.solve()
    # Get the order
    order = [int(var.varValue) for var in order_vars]
    # Reorder production DataFrame
    production_optimized = production.iloc[order].reset_index(drop=True)
    return production_optimized
