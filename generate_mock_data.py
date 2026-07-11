import pandas as pd
import numpy as np
import os

# Create workspace directory check
workspace_dir = r"d:\Code\Projects\Vendor's Performance Analysis"
os.makedirs(workspace_dir, exist_ok=True)

print("Generating mock data for Vendor Performance Analysis...")

# 1. Generate Vendor_Performance_Dashboard.xlsx [Data Sheet]
# Columns expected by Notebooks:
# VendorNumber, VendorName, Brand, Description, Volume, PurchasePrice, ActualPrice,
# TotalPurchaseQuantity, TotalPurchaseDollars, TotalSalesQuantity, TotalSalesDollars,
# TotalSalesPrice, TotalExciseTax, FreightCost, GrossProfit, ProfitMargin, StockTurnover, UnsoldCapital

np.random.seed(42)
num_rows = 8564

# Define key vendors that notebook 2 prints/references
key_vendors = [
    "DIAGEO NORTH AMERICA INC", "MARTIGNETTI COMPANIES", "PERNOD RICARD USA",
    "JIM BEAM BRANDS COMPANY", "BACARDI USA INC", "M S WALKER INC",
    "ULTRA BEVERAGE COMPANY LLP", "PERFECTA WINES", "E & J GALLO WINERY",
    "ADAMBA IMPORTS INTL INC", "ALISA CARR BEVERAGES", "ALTAMAR BRANDS LLC",
    "AMERICAN SPIRITS EXCHANGE", "AMERICAN VINTAGE BEVERAGE",
    "ATLANTIC IMPORTING COMPANY", "BANFI PRODUCTS CORP",
    "BLACK PRINCE DISTILLERY INC", "BLACK ROCK SPIRITS LLC",
    "IRA GOLDMAN AND WILLIAMS, LLP"
]

# We want 119 unique vendors in total
all_vendors = list(key_vendors)
while len(all_vendors) < 119:
    all_vendors.append(f"VENDOR_{len(all_vendors) + 1} INC")

# Generate vendor numbers map
vendor_numbers = {name: (i + 1) for i, name in enumerate(all_vendors)}

# Assign vendor names to rows (skewed distribution: Martignetti has 1084, Walker has 652, Ultra has 622, etc.)
vendor_choices = []
for v in all_vendors:
    if v == "MARTIGNETTI COMPANIES":
        count = 1084
    elif v == "M S WALKER INC":
        count = 652
    elif v == "ULTRA BEVERAGE COMPANY LLP":
        count = 622
    elif v == "PERFECTA WINES":
        count = 575
    elif v == "E & J GALLO WINERY":
        count = 437
    elif v in ["DIAGEO NORTH AMERICA INC", "PERNOD RICARD USA", "JIM BEAM BRANDS COMPANY", "BACARDI USA INC"]:
        count = 200
    else:
        count = 35 # average count for the remaining to sum to ~8564
    vendor_choices.extend([v] * count)

# Adjust vendor_choices length to exactly 8564
if len(vendor_choices) < num_rows:
    vendor_choices.extend(np.random.choice(all_vendors, num_rows - len(vendor_choices)))
else:
    vendor_choices = vendor_choices[:num_rows]
np.random.shuffle(vendor_choices)

# Brand ids: 8544 unique brands out of 8564 rows
brand_ids = list(range(1001, 1001 + 8544))
# Repeat 20 brands to make 8564 rows
brand_ids.extend(np.random.choice(brand_ids, 20))
np.random.shuffle(brand_ids)

# Let's generate base metrics
volumes = np.random.choice([375.0, 750.0, 1000.0, 1750.0], num_rows, p=[0.1, 0.6, 0.2, 0.1])
purchase_prices = np.random.uniform(5.0, 80.0, num_rows)
# Actual price usually has a markup over purchase price
actual_prices = purchase_prices * np.random.uniform(1.2, 1.6, num_rows)

purchase_quantities = np.random.randint(5, 500, num_rows)
# Add some very large vendors (Diageo, Martignetti, Pernod etc. are 100-1000x larger)
for i in range(num_rows):
    v = vendor_choices[i]
    if v in ["DIAGEO NORTH AMERICA INC", "MARTIGNETTI COMPANIES", "PERNOD RICARD USA", "JIM BEAM BRANDS COMPANY"]:
        purchase_quantities[i] *= np.random.randint(20, 100)

total_purchase_dollars = purchase_quantities * purchase_prices

# Sales quantity should be close to purchase quantity, with some unsold capital
sales_quantities = (purchase_quantities * np.random.uniform(0.7, 1.1, num_rows)).astype(int)
# Keep sales quantity >= 1 so filter_reliable doesn't drop them
sales_quantities = np.clip(sales_quantities, 1, None)

total_sales_dollars = sales_quantities * actual_prices
total_sales_price = total_sales_dollars / sales_quantities # avg sales price
total_excise_tax = sales_quantities * np.random.uniform(0.5, 3.0, num_rows)
freight_cost = total_purchase_dollars * np.random.uniform(0.02, 0.08, num_rows)

# Derived columns:
gross_profit = total_sales_dollars - total_purchase_dollars
# Make sure GrossProfit > 0 for all rows so filter_reliable doesn't filter them out
negative_gp = gross_profit <= 0
if np.any(negative_gp):
    # Adjust sales dollars to guarantee gross profit is positive
    total_sales_dollars[negative_gp] = total_purchase_dollars[negative_gp] * np.random.uniform(1.1, 1.4, sum(negative_gp))
    gross_profit = total_sales_dollars - total_purchase_dollars

profit_margin = (gross_profit / total_sales_dollars) * 100
stock_turnover = sales_quantities / purchase_quantities
unsold_capital = (purchase_quantities - sales_quantities) * purchase_prices

df_data = pd.DataFrame({
    "VendorNumber": [vendor_numbers[v] for v in vendor_choices],
    "VendorName": vendor_choices,
    "Brand": brand_ids,
    "Description": [f"Liquor Description {b}" for b in brand_ids],
    "Volume": volumes,
    "PurchasePrice": purchase_prices,
    "ActualPrice": actual_prices,
    "TotalPurchaseQuantity": purchase_quantities,
    "TotalPurchaseDollars": total_purchase_dollars,
    "TotalSalesQuantity": sales_quantities,
    "TotalSalesDollars": total_sales_dollars,
    "TotalSalesPrice": total_sales_price,
    "TotalExciseTax": total_excise_tax,
    "FreightCost": freight_cost,
    "GrossProfit": gross_profit,
    "ProfitMargin": profit_margin,
    "StockTurnover": stock_turnover,
    "UnsoldCapital": unsold_capital
})

# Save to Excel
excel_path = os.path.join(workspace_dir, "Vendor_Performance_Dashboard.xlsx")
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    df_data.to_excel(writer, sheet_name="Data", index=False)
print(f"Saved mock {excel_path} (Data sheet, {len(df_data)} rows)")


# 2. Generate vendor_performance_clusters_reference.csv
# This needs all 119 unique vendors with a PerformanceTier assignment.
# We will assign some realistic tiers so the notebook cross-check has reference records.
tiers = []
for name in all_vendors:
    if name in ["BACARDI USA INC", "BANFI PRODUCTS CORP", "DIAGEO NORTH AMERICA INC"]:
        tier = "High Performer"
    elif name in ["ALISA CARR BEVERAGES", "ATLANTIC IMPORTING COMPANY"]:
        tier = "Low Performer"
    else:
        tier = "Mid Performer"
    tiers.append(tier)

df_ref = pd.DataFrame({
    "VendorName": all_vendors,
    "PerformanceTier": tiers
})
ref_csv_path = os.path.join(workspace_dir, "vendor_performance_clusters_reference.csv")
df_ref.to_csv(ref_csv_path, index=False)
print(f"Saved mock {ref_csv_path} ({len(df_ref)} vendors)")


# 3. Generate Ecommerce Sales Analysis Data.csv
# Columns needed: Product Name, Sales, Profit, Discount, Category, Sub-Category
products = [
    "Classic Ring Binder", "Premium Copy Paper", "Heavy Duty Stapler", 
    "Ergonomic Office Chair", "Gel Ink Pens Pack", "Dry Erase Whiteboard",
    "Wireless Optical Mouse", "USB-C Charging Cable", "Bluetooth Keyboard",
    "Adjustable Desk Lamp"
]
categories = ["Office Supplies", "Office Supplies", "Office Supplies", "Furniture", "Office Supplies", "Furniture", "Technology", "Technology", "Technology", "Furniture"]
subcategories = ["Binders", "Paper", "Fasteners", "Chairs", "Pens", "Tables", "Accessories", "Cables", "Accessories", "Furnishings"]

np.random.seed(42)
num_products = 500
prod_names = []
prod_cats = []
prod_subcats = []

for _ in range(num_products):
    idx = np.random.randint(0, len(products))
    prod_names.append(products[idx] + f" V{np.random.randint(100, 999)}")
    prod_cats.append(categories[idx])
    prod_subcats.append(subcategories[idx])

sales = np.random.uniform(10.0, 2000.0, num_products)
discount = np.random.uniform(0.0, 0.4, num_products)
# Profit can be positive or negative
profit = sales * np.random.uniform(-0.2, 0.4, num_products)

df_ecommerce = pd.DataFrame({
    "Product Name": prod_names,
    "Sales": sales,
    "Profit": profit,
    "Discount": discount,
    "Category": prod_cats,
    "Sub-Category": prod_subcats
})

ecommerce_csv_path = os.path.join(workspace_dir, "Ecommerce Sales Analysis Data.csv")
df_ecommerce.to_csv(ecommerce_csv_path, index=False, encoding='latin1')
print(f"Saved mock {ecommerce_csv_path} ({len(df_ecommerce)} products)")

print("All mock datasets generated successfully!")
