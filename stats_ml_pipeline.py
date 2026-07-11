"""
Vendor Performance Analytics — Statistical & Machine Learning Pipeline
Runs Welch's t-test, correlation matrix, KMeans clustering (vendor performance tiers),
and Linear Regression to identify profit margin drivers.

Author: Shivansh Nigam
Email: s2704nigam@gmail.com
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, silhouette_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True
)

RESULTS = {}

def vendor_level_aggregate(df):
    """Roll brand-level rows up to one row per vendor for clustering/stats."""
    logging.info("Aggregating brand-level rows to vendor-level...")
    agg = df.groupby("VendorName").agg(
        TotalPurchaseDollars=("TotalPurchaseDollars", "sum"),
        TotalSalesDollars=("TotalSalesDollars", "sum"),
        GrossProfit=("GrossProfit", "sum"),
        FreightCost=("FreightCost", "sum"),
        StockTurnover=("StockTurnover", "mean"),
        ProfitMargin=("ProfitMargin", "mean"),
        UnsoldCapital=("UnsoldCapital", "sum"),
        BrandCount=("Brand", "nunique"),
        AvgPurchasePrice=("PurchasePrice", "mean"),
        AvgActualPrice=("ActualPrice", "mean"),
    ).reset_index()
    logging.info(f"Aggregated data into {len(agg)} vendor records.")
    return agg

def run_statistics(vendor_df):
    """Run Welch's t-test and calculate the KPI correlation matrix."""
    logging.info("Running statistical analysis (Welch's t-test & correlation)...")
    median_sales = vendor_df["TotalSalesDollars"].median()
    top = vendor_df[vendor_df["TotalSalesDollars"] >= median_sales]["ProfitMargin"]
    bottom = vendor_df[vendor_df["TotalSalesDollars"] < median_sales]["ProfitMargin"]

    t_stat, p_val = stats.ttest_ind(top, bottom, equal_var=False)

    corr_matrix = vendor_df[
        ["TotalSalesDollars", "GrossProfit", "ProfitMargin", "StockTurnover", "UnsoldCapital"]
    ].corr(numeric_only=True)

    RESULTS["statistics"] = {
        "ttest_top_vs_bottom_sales_tier": {
            "top_n": int(len(top)),
            "bottom_n": int(len(bottom)),
            "top_mean_margin": round(float(top.mean()), 2),
            "bottom_mean_margin": round(float(bottom.mean()), 2),
            "t_statistic": round(float(t_stat), 3),
            "p_value": round(float(p_val), 5),
            "significant_at_0.05": bool(p_val < 0.05),
        },
        "correlation_matrix": corr_matrix.round(3).to_dict(),
    }
    return corr_matrix

def run_clustering(vendor_df, k=3):
    """Run KMeans clustering to segment vendors into High, Mid, and Low Performers."""
    logging.info("Running KMeans vendor clustering...")
    cluster_df = vendor_df.copy()
    cluster_df["LogSales"] = np.log1p(cluster_df["TotalSalesDollars"].clip(lower=0))
    cluster_df["LogGrossProfit"] = np.log1p(cluster_df["GrossProfit"].clip(lower=0))
    cap = cluster_df["StockTurnover"].quantile(0.95)
    cluster_df["StockTurnoverCapped"] = cluster_df["StockTurnover"].clip(upper=cap)

    features = ["LogSales", "LogGrossProfit", "ProfitMargin", "StockTurnoverCapped"]
    X = cluster_df[features].copy()
    X_scaled = StandardScaler().fit_transform(X)

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    vendor_df["Cluster"] = km.fit_predict(X_scaled)

    sil = silhouette_score(X_scaled, vendor_df["Cluster"])

    # Rank clusters based on average gross profit to assign logical labels
    cluster_rank = (
        vendor_df.groupby("Cluster")["GrossProfit"].mean().sort_values().index.tolist()
    )
    label_map = {cluster_rank[0]: "Low Performer", cluster_rank[-1]: "High Performer"}
    for c in cluster_rank[1:-1]:
        label_map[c] = "Mid Performer"
    vendor_df["PerformanceTier"] = vendor_df["Cluster"].map(label_map)

    summary_features = ["TotalSalesDollars", "GrossProfit", "ProfitMargin", "StockTurnover"]
    cluster_summary = (
        vendor_df.groupby("PerformanceTier")[summary_features]
        .mean()
        .round(2)
        .to_dict(orient="index")
    )
    RESULTS["clustering"] = {
        "algorithm": "KMeans (k=3, standardized, log-scaled dollar features)",
        "features_used": features,
        "silhouette_score": round(float(sil), 3),
        "cluster_profile_means": cluster_summary,
        "vendor_counts": vendor_df["PerformanceTier"].value_counts().to_dict(),
    }
    logging.info(f"Clustering silhouette score: {sil:.3f}")
    return vendor_df

def run_regression(vendor_df):
    """Run multiple linear regression to determine drivers of ProfitMargin."""
    logging.info("Training Profit Margin linear regression model...")
    features = ["FreightCost", "StockTurnover", "BrandCount", "AvgPurchasePrice", "AvgActualPrice"]
    X = vendor_df[features].fillna(0)
    y = vendor_df["ProfitMargin"]

    model = LinearRegression().fit(X, y)
    preds = model.predict(X)
    r2 = r2_score(y, preds)

    coefs = dict(zip(features, model.coef_.round(4)))
    RESULTS["regression"] = {
        "target": "ProfitMargin (%)",
        "features": features,
        "r2_score": round(float(r2), 3),
        "intercept": round(float(model.intercept_), 2),
        "coefficients": {k: float(v) for k, v in coefs.items()},
    }
    logging.info(f"Regression model trained. R^2: {r2:.3f}")
    return model

def cross_check(vendor_df):
    """Cross-check clustering results against the production reference file."""
    ref_path = "vendor_performance_clusters_reference.csv"
    if os.path.exists(ref_path):
        logging.info("Cross-checking clusters with reference file...")
        reference = pd.read_csv(ref_path)
        check = vendor_df[["VendorName", "PerformanceTier"]].merge(
            reference[["VendorName", "PerformanceTier"]],
            on="VendorName", suffixes=("_pipeline", "_reference")
        )
        match_rate = (check["PerformanceTier_pipeline"] == check["PerformanceTier_reference"]).mean()
        logging.info(f"Performance tier agreement with reference: {match_rate:.1%}")
    else:
        logging.warning("Reference file not found. Skipping cross-check.")

def main():
    cleaned_data_path = "vendor_sales_summary_clean.csv"

    if not os.path.exists(cleaned_data_path):
        logging.error(f"Cleaned summary file '{cleaned_data_path}' not found. Please run 'clean_pipeline.py' first.")
        return

    try:
        # Load and process data
        df = pd.read_csv(cleaned_data_path)
        vendor_df = vendor_level_aggregate(df)

        # Run pipeline
        run_statistics(vendor_df)
        vendor_df = run_clustering(vendor_df)
        run_regression(vendor_df)

        # Save output deliverables
        vendor_df.to_csv("vendor_performance_clusters.csv", index=False)
        logging.info("Saved vendor_performance_clusters.csv to disk.")

        with open("analysis_results.json", "w") as f:
            json.dump(RESULTS, f, indent=2)
        logging.info("Saved metrics and analysis details to analysis_results.json.")

        # Cross-check outputs
        cross_check(vendor_df)
        logging.info("Statistical and Machine Learning pipeline completed successfully.")

    except Exception as e:
        logging.error(f"Error executing stats and ML pipeline: {e}")

if __name__ == "__main__":
    main()
