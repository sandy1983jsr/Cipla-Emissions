import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from emissions import calculate_batch_emissions, total_facility_emissions
from optimize import optimize_batch_schedule

def generate_random_large_sample(num_products=40, min_batches=10, max_batches=40, random_seed=42):
    np.random.seed(random_seed)
    products = [f"P{str(i+1).zfill(4)}" for i in range(num_products)]
    product_names = [f"Product {i+1}" for i in range(num_products)]

    details = pd.DataFrame({
        'product_code': products,
        'name': product_names,
        'running_hours': np.random.randint(2, 16, size=num_products),
        'total_electricity_consumed': np.random.randint(400, 1200, size=num_products),
        'total_steam_consumed': np.random.randint(50, 250, size=num_products),
        'batch_size': np.random.randint(200, 1000, size=num_products),
        'batch_unit': ['kg'] * num_products
    })

    switchover_rows = []
    for p in products:
        for sw_type in ['batch', 'product']:
            switchover_rows.append({
                'product_code': p,
                'switch_type': sw_type,
                'switchover_time': np.random.randint(1, 4),
                'electricity': np.random.randint(10, 50),
                'steam': np.random.randint(2, 15)
            })
    switchover = pd.DataFrame(switchover_rows)

    production = pd.DataFrame({
        'product_code': products,
        'number_of_batches': np.random.randint(min_batches, max_batches+1, size=num_products)
    })

    # For preview: shuffled list of batches
    batches = []
    for i, row in production.iterrows():
        prod = row['product_code']
        for b in range(row['number_of_batches']):
            batches.append({'product_code': prod, 'batch_num': b+1})
    batch_df = pd.DataFrame(batches)
    shuffled_df = batch_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)

    return details, switchover, production, shuffled_df

st.title("Facility CO₂ Emissions Optimizer (Batch Level)")

st.header("Step 1: Data Source")
mode = st.radio("Choose data source:", ["Upload CSV files", "Use Random Large Sample"])

# --- Emission Factor Inputs ---
st.header("Step 2: Enter Emission Factors & Constraint")
col3, col4, col5 = st.columns(3)
with col3:
    elec_ef = st.number_input("Electricity Emission Factor (kg CO₂/kWh)", value=0.9, min_value=0.0)
with col4:
    steam_ef = st.number_input("Steam Emission Factor (kg CO₂/kg steam)", value=0.5, min_value=0.0)
with col5:
    allowed_time_var = st.slider("Allowed Schedule Time Variation (%)", 0, 50, 10, 1) / 100

if mode == "Upload CSV files":
    st.header("Step 3: Upload Data")
    col1, col2 = st.columns(2)
    with col1:
        details_file = st.file_uploader("Upload details.csv", type="csv")
        switchover_file = st.file_uploader("Upload switchover.csv", type="csv")
    with col2:
        production_file = st.file_uploader("Upload production.csv", type="csv")

    data_ready = all([details_file, switchover_file, production_file])
    if data_ready:
        details = pd.read_csv(details_file)
        switchover = pd.read_csv(switchover_file)
        production = pd.read_csv(production_file)
        batches = []
        for i, row in production.iterrows():
            prod = row['product_code']
            for b in range(row['number_of_batches']):
                batches.append({'product_code': prod, 'batch_num': b+1})
        batch_df = pd.DataFrame(batches)
        shuffled_df = batch_df.sample(frac=1, random_state=42).reset_index(drop=True)
    else:
        st.info("Please upload all required files.")
        st.stop()
else:
    details, switchover, production, shuffled_df = generate_random_large_sample()
    st.success("Random large sample data generated and loaded.")

# --- Show sample of the shuffled batch schedule ---
st.header("Step 3: Initial (Shuffled) Batch Schedule Preview")
st.dataframe(shuffled_df.head(30))
st.write(f"Total batches: {len(shuffled_df)}")

# --- Base Emissions (using shuffled_df as base order) ---
base_schedule = shuffled_df.copy()
base_emissions_df = calculate_batch_emissions(base_schedule, details, switchover, steam_ef, elec_ef)
base_total = total_facility_emissions(base_emissions_df)

# --- Optimized Emissions ---
@st.cache_data
def run_optimizer(details, switchover, production, steam_ef, elec_ef, allowed_time_var):
    return optimize_batch_schedule(details, switchover, production, steam_ef, elec_ef, allowed_time_var)

st.write("Optimizing schedule...please wait for large datasets.")
best_schedule, best_emissions_df = run_optimizer(details, switchover, production, steam_ef, elec_ef, allowed_time_var)
opt_total = total_facility_emissions(best_emissions_df)

st.header("Step 4: Emissions Comparison")
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Base (Shuffled) Schedule")
    st.metric("Total Facility Emissions (kg CO₂)", f"{base_total:.2f}")
    st.dataframe(base_emissions_df[['product_code','batch_num','total_emissions']].head(30))
    fig = px.bar(
        base_emissions_df.head(30),
        x='batch_num',
        y='total_emissions',
        color='product_code',
        title="Emissions per Batch (Base, first 30)"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Optimized Schedule")
    st.metric("Total Facility Emissions (kg CO₂)", f"{opt_total:.2f}")
    st.dataframe(best_emissions_df[['product_code','batch_num','total_emissions']].head(30))
    fig2 = px.bar(
        best_emissions_df.head(30),
        x='batch_num',
        y='total_emissions',
        color='product_code',
        title="Emissions per Batch (Optimized, first 30)"
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
    _Tip: The optimizer rearranges batches of all products to minimize total CO₂ emissions, including both process and switchover emissions, while keeping total schedule time within the allowed variation. The base schedule shown is a random shuffled sequence of all batches, not sequential by product._
    """
)
