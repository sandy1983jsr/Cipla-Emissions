import pandas as pd
import numpy as np

np.random.seed(42)

# 1. Generate Products
num_products = 10
products = [f"P{str(i+1).zfill(3)}" for i in range(num_products)]
product_names = [f"Product {chr(65+i)}" for i in range(num_products)]

details = pd.DataFrame({
    'product_code': products,
    'name': product_names,
    'running_hours': np.random.randint(6, 16, size=num_products),
    'total_electricity_consumed': np.random.randint(400, 1200, size=num_products),
    'total_steam_consumed': np.random.randint(50, 250, size=num_products),
    'batch_size': np.random.randint(200, 1000, size=num_products),
    'batch_unit': ['kg'] * num_products
})

# 2. Generate Switchover data
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

# 3. Generate Production Plan (random number of batches per product)
production = pd.DataFrame({
    'product_code': products,
    'number_of_batches': np.random.randint(4, 12, size=num_products)
})

# 4. Expand into batches and shuffle
batches = []
for i, row in production.iterrows():
    prod = row['product_code']
    for b in range(row['number_of_batches']):
        batches.append({'product_code': prod, 'batch_num': b+1})
batch_df = pd.DataFrame(batches)
shuffled_df = batch_df.sample(frac=1, random_state=42).reset_index(drop=True)

# SAVE FILES
details.to_csv("details.csv", index=False)
switchover.to_csv("switchover.csv", index=False)
production.to_csv("production.csv", index=False)
shuffled_df.to_csv("shuffled_batches.csv", index=False)

print("Generated details.csv, switchover.csv, production.csv, and shuffled_batches.csv")
