import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import StringIO

st.title("Indore-Unit-4 Emissions Forecast & Optimization")

# --- Sample Data Generation ---
def generate_sample_data():
    equipment = pd.DataFrame({
        'equipment': [f'Machine-{i+1}' for i in range(5)],
        'electricity_consumption': np.random.choice([10, 20, 30, 40], 5),
        'steam_consumption': np.random.choice([0, 5, 10], 5)
    })
    details = pd.DataFrame({
        'product_code': [f'P{i+1:03d}' for i in range(3)],
        'name': ['Product A', 'Product B', 'Product C'],
        'machine_sequence': [['Machine-1', 'Machine-2'], ['Machine-2', 'Machine-3'], ['Machine-1', 'Machine-3']],
        'running_hours': [10, 12, 8],
        'total_electricity_consumed': [800, 950, 500],
        'total_steam_consumed': [150, 180, 80],
        'batch_size': [500, 600, 400],
        'batch_unit': ['kg', 'kg', 'kg']
    })
    switchover = pd.DataFrame({
        'product_code': np.repeat([f'P{i+1:03d}' for i in range(3)], 2),
        'switch_type': ['batch', 'product'] * 3,
        'switchover_time': [1, 2] * 3,
        'electricity': [10, 20, 12, 22, 8, 18],
        'steam': [2, 5, 3, 6, 1, 4]
    })
    production = pd.DataFrame({
        'product_code': [f'P{i+1:03d}' for i in range(3)],
        'number_of_batches': [4, 3, 2]
    })
    return equipment, details, switchover, production

# --- Data Upload/Selection ---
mode = st.radio("Choose data source:", ["Upload CSV files", "Use Sample Data"])

def get_uploaded_df(label):
    file = st.file_uploader(label, type="csv")
    if file:
        return pd.read_csv(file)
    return None

if mode == "Upload CSV files":
    st.info("Upload all four CSV files to proceed.")
    equipment = get_uploaded_df("Upload equipment.csv")
    details = get_uploaded_df("Upload details.csv")
    switchover = get_uploaded_df("Upload switchover.csv")
    production = get_uploaded_df("Upload production.csv")
    if not all([equipment, details, switchover, production]):
        st.warning("Please upload all required files.")
        st.stop()
else:
    equipment, details, switchover, production = generate_sample_data()
    st.success("Sample data loaded.")

# --- Emission Factors & Constraints ---
elec_ef = st.number_input("Electricity Emission Factor (kg CO2 / kWh)", value=0.9)
steam_ef = st.number_input("Steam Emission Factor (kg CO2 / kg steam)", value=0.5)
allowed_time_var = st.slider(
    "Allowed Schedule Time Variation (+/- %, default 10%)", min_value=0, max_value=50, value=10, step=1
) / 100

# --- Emissions Calculation ---
def calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef):
    merged = production.merge(details, on='product_code', suffixes=('', '_details'))
    merged['emissions_electricity'] = merged['total_electricity_consumed'] * elec_ef
    merged['emissions_steam'] = merged['total_steam_consumed'] * steam_ef

    # Switchover emissions (very simple logic: always add product switchover for 2nd+ product)
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
            sw_row = switchover[
                (switchover['product_code'] == curr_prod) & (switchover['switch_type'] == sw_type)
            ]
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
    merged['total_emissions'] = (
        merged['emissions_electricity']
        + merged['emissions_steam']
        + merged['switchover_emissions_electricity']
        + merged['switchover_emissions_steam']
    )
    return merged

def total_emissions(df):
    return df['total_emissions'].sum()

# --- Optimization Stub ---
def optimize_schedule(equipment, details, switchover, production, steam_ef, elec_ef, allowed_time_var=0.1):
    # For demo, just reverse order. Replace with actual logic!
    return production.iloc[::-1].reset_index(drop=True)

# --- Main Actions ---
if st.button("Calculate Emissions"):
    results = calculate_schedule_emissions(equipment, details, switchover, production, steam_ef, elec_ef)
    total = total_emissions(results)
    st.subheader("CO2 Emissions for Current Schedule")
    st.dataframe(results[['product_code', 'name', 'number_of_batches', 'total_emissions']])
    fig = px.bar(
        results,
        x='product_code',
        y=['emissions_electricity', 'emissions_steam', 'switchover_emissions_electricity', 'switchover_emissions_steam'],
        title=f'Total Emissions by Product (Total: {total:.2f} kg CO2)',
        barmode='group'
    )
    st.plotly_chart(fig, use_container_width=True)

if st.button("Optimize Schedule & Calculate Emissions"):
    opt_production = optimize_schedule(equipment, details, switchover, production, steam_ef, elec_ef, allowed_time_var)
    results_opt = calculate_schedule_emissions(equipment, details, switchover, opt_production, steam_ef, elec_ef)
    total_opt = total_emissions(results_opt)
    st.subheader("Optimized Production Schedule")
    st.dataframe(opt_production)
    csv = opt_production.to_csv(index=False)
    st.download_button("Download Optimized Schedule as CSV", csv, file_name="optimized_production.csv", mime="text/csv")
    st.subheader("CO2 Emissions for Optimized Schedule")
    st.dataframe(results_opt[['product_code', 'name', 'number_of_batches', 'total_emissions']])
    fig_opt = px.bar(
        results_opt,
        x='product_code',
        y=['emissions_electricity', 'emissions_steam', 'switchover_emissions_electricity', 'switchover_emissions_steam'],
        title=f'Total Emissions by Product (Optimized: {total_opt:.2f} kg CO2)',
        barmode='group'
    )
    st.plotly_chart(fig_opt, use_container_width=True)
