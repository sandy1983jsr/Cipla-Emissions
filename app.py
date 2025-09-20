import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from emissions import calculate_batch_emissions, total_facility_emissions
from optimize import optimize_batch_schedule

st.title("Facility CO₂ Emissions Optimizer (Batch Level)")

st.header("Step 1: Data Source")
mode = st.radio("Choose data source:", ["Upload CSV files", "Use Sample Data"])

def generate_sample_data():
    # Sample equipment (not used in calculation, kept for completeness)
    equipment = pd.DataFrame({
        'equipment': [f'Machine-{i+1}' for i in range(4)],
        'electricity_consumption': np.random.choice([10, 20], 4),
        'steam_consumption': np.random.choice([0, 5], 4)
    })
    # Sample details
    details = pd.DataFrame({
        'product_code': ['P001', 'P002', 'P003'],
        'name': ['Product A', 'Product B', 'Product C'],
        'running_hours': [10, 12, 8],
        'total_electricity_consumed': [800, 950, 500],
        'total_steam_consumed': [150, 180, 80],
        'batch_size': [500, 600, 400],
        'batch_unit': ['kg', 'kg', 'kg']
    })
    # Sample switchover
    switchover = pd.DataFrame({
        'product_code': ['P001', 'P001', 'P002', 'P002', 'P003', 'P003'],
        'switch_type': ['batch', 'product'] * 3,
        'switchover_time': [1, 2, 1, 2, 1, 2],
        'electricity': [10, 20, 12, 22, 8, 18],
        'steam': [2, 5, 3, 6, 1, 4]
    })
    # Sample production
    production = pd.DataFrame({
        'product_code': ['P001', 'P002', 'P003'],
        'number_of_batches': [4, 3, 2]
    })
    return equipment, details, switchover, production

# --- Emission Factor Inputs ---
st.header("Step 2: Enter Emission Factors & Constraint")
col3, col4, col5 = st.columns(3)
with col3:
    elec_ef = st.number_input("Electricity Emission Factor (kg CO₂/kWh)", value=0.9, min_value=0.0)
with col4:
    steam_ef = st.number_input("Steam Emission Factor (kg CO₂/kg steam)", value=0.5, min_value=0.0)
with col5:
    allowed_time_var = st.slider("Allowed Schedule Time Variation (%)", 0, 50, 10, 1) / 100

# --- Data Load ---
if mode == "Upload CSV files":
    st.header("Step 3: Upload Data")
    col1, col2 = st.columns(2)
    with col1:
        equipment_file = st.file_uploader("Upload equipment.csv", type="csv")
        details_file = st.file_uploader("Upload details.csv", type="csv")
    with col2:
        switchover_file = st.file_uploader("Upload switchover.csv", type="csv")
        production_file = st.file_uploader("Upload production.csv", type="csv")

    data_ready = all([details_file, switchover_file, production_file])
    if data_ready:
        equipment = pd.read_csv(equipment_file) if equipment_file else pd.DataFrame()
        details = pd.read_csv(details_file)
        switchover = pd.read_csv(switchover_file)
        production = pd.read_csv(production_file)
    else:
        st.info("Please upload all required files (equipment optional).")
        st.stop()

else:
    equipment, details, switchover, production = generate_sample_data()
    st.success("Sample data loaded.")

# --- Base Emissions ---
batch_df = []
for _, row in production.iterrows():
    for i in range(int(row['number_of_batches'])):
        batch_df.append({'product_code': row['product_code'], 'batch_num': i+1})
batch_df = pd.DataFrame(batch_df)
base_schedule = batch_df.copy()
base_emissions_df = calculate_batch_emissions(base_schedule, details, switchover, steam_ef, elec_ef)
base_total = total_facility_emissions(base_emissions_df)

# --- Optimized Emissions ---
best_schedule, best_emissions_df = optimize_batch_schedule(
    details, switchover, production, steam_ef, elec_ef, allowed_time_var
)
opt_total = total_facility_emissions(best_emissions_df)

st.header("Step 4: Emissions Comparison")
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Base Schedule")
    st.metric("Total Facility Emissions (kg CO₂)", f"{base_total:.2f}")
    st.dataframe(base_emissions_df[['product_code','batch_num','total_emissions']])
    fig = px.bar(
        base_emissions_df,
        x='batch_num',
        y='total_emissions',
        color='product_code',
        title="Emissions per Batch (Base)",
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Optimized Schedule")
    st.metric("Total Facility Emissions (kg CO₂)", f"{opt_total:.2f}")
    st.dataframe(best_emissions_df[['product_code','batch_num','total_emissions']])
    fig2 = px.bar(
        best_emissions_df,
        x='batch_num',
        y='total_emissions',
        color='product_code',
        title="Emissions per Batch (Optimized)"
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.download_button(
        "Download Optimized Schedule as CSV",
        best_schedule.to_csv(index=False),
        file_name="optimized_batch_schedule.csv",
        mime="text/csv"
    )

st.markdown(
    """
    ---
    _Tip: The optimizer rearranges batches of all products to minimize total CO₂ emissions, including both process and switchover emissions, while keeping total schedule time within the allowed variation._
    """
)
