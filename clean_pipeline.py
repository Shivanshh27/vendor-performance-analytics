"""
Vendor Performance Analytics — Data Cleaning & Feature Engineering Pipeline
Extracts, cleans, and engineers KPIs (ProfitMargin, StockTurnover, UnsoldCapital) 
from the vendor_sales_summary table.

Author: Shivansh Nigam
Email: s2704nigam@gmail.com
"""

import os
import sqlite3
import logging
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True
)

def load_summary(conn):
    """Load the vendor_sales_summary table produced by SQL from SQLite."""
    logging.info("Loading vendor_sales_summary from database")
    df = pd.read_sql_query("SELECT * FROM vendor_sales_summary", conn)
    logging.info(f"Loaded {len(df)} rows, {df.shape[1]} columns")
    return df

def clean_data(df):
    """
    Standard cleaning and KPI engineering routine:
      - Cast dtypes (Volume: object -> float64)
      - Handle nulls (fill with 0 - unsold purchased stock)
      - Strip whitespace from names/descriptions
      - Feature engineering: GrossProfit, ProfitMargin, StockTurnover, and UnsoldCapital
    """
    df = df.copy()
    df["Volume"] = df["Volume"].astype("float64")
    logging.info("Converted Volume to float64")

    before_na = df.isnull().sum().sum()
    df.fillna(0, inplace=True)
    logging.info(f"Filled {before_na} missing values with 0")

    df["VendorName"] = df["VendorName"].astype(str).str.strip()
    df["Description"] = df["Description"].astype(str).str.strip()
    logging.info("Stripped whitespace from VendorName and Description")

    df["GrossProfit"] = df["TotalSalesDollars"] - df["TotalPurchaseDollars"]
    df["ProfitMargin"] = (df["GrossProfit"] / df["TotalSalesDollars"].replace(0, pd.NA)) * 100
    df["StockTurnover"] = df["TotalSalesQuantity"] / df["TotalPurchaseQuantity"].replace(0, pd.NA)
    df["UnsoldCapital"] = (df["TotalPurchaseQuantity"] - df["TotalSalesQuantity"]) * df["PurchasePrice"]

    df["ProfitMargin"] = df["ProfitMargin"].fillna(0)
    df["StockTurnover"] = df["StockTurnover"].fillna(0)

    logging.info("Engineered GrossProfit, ProfitMargin, StockTurnover, UnsoldCapital")
    return df

def filter_reliable(df):
    """Remove records that would skew analysis: zero/negative profit or zero sales."""
    before = len(df)
    df_clean = df[
        (df["GrossProfit"] > 0)
        & (df["ProfitMargin"] > 0)
        & (df["TotalSalesQuantity"] > 0)
    ].copy()
    logging.info(f"Filtered inconsistent records: {before} -> {len(df_clean)} rows")
    return df_clean

def main():
    db_path = "vendor.db"
    excel_source = "Vendor_Performance_Dashboard.xlsx"

    # Fallback if SQLite database does not exist
    if not os.path.exists(db_path) and os.path.exists(excel_source):
        logging.info(f"Database '{db_path}' not found. Re-creating from dashboard '{excel_source}'...")
        try:
            raw = pd.read_excel(excel_source, sheet_name="Data")
            conn = sqlite3.connect(db_path)
            raw.to_sql("vendor_sales_summary", conn, if_exists="replace", index=False)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vss_vendor_brand ON vendor_sales_summary(VendorNumber, Brand);")
            conn.commit()
            logging.info("Database loaded and indexed successfully.")
        except Exception as e:
            logging.error(f"Failed to load data from dashboard Excel: {e}")
            return
    elif not os.path.exists(db_path):
        logging.error("No source data found (missing 'vendor.db' and 'Vendor_Performance_Dashboard.xlsx').")
        return

    # Execute cleaning pipeline
    try:
        conn = sqlite3.connect(db_path)
        df_raw = load_summary(conn)
        df_cleaned = clean_data(df_raw)
        df_filtered = filter_reliable(df_cleaned)

        # Write clean table back to SQLite
        df_filtered.to_sql("vendor_sales_summary_clean", conn, if_exists="replace", index=False)
        conn.close()
        logging.info("Saved cleaned summary back to database.")

        # Persist deliverables to CSV and Excel
        df_filtered.to_csv("vendor_sales_summary_clean.csv", index=False)
        df_filtered.to_excel("vendor_sales_summary_clean.xlsx", index=False)
        logging.info("Saved vendor_sales_summary_clean.csv and .xlsx to disk.")
        logging.info("Cleaning pipeline run completed successfully.")
        
    except Exception as e:
        logging.error(f"Error in running cleaning pipeline: {e}")

if __name__ == "__main__":
    main()
