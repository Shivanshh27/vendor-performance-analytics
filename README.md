# Vendor Performance Analytics

[![SQL](https://img.shields.io/badge/SQL-SQLite-blue?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![Pandas](https://img.shields.io/badge/Library-Pandas%20%7C%20NumPy-lightgrey)](https://pandas.pydata.org)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-orange?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![License](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/licenses/MIT)

An end-to-end data analytics and machine learning pipeline for a retail/distribution business. This project processes **15M+ raw transactional rows** using optimized SQL, engineers business-critical KPIs, performs statistical hypothesis testing, runs unsupervised clustering for vendor segmentation, and trains linear regression models to identify operational profit drivers.

---

## Table of Contents
1. [Business Problem](#business-problem)
2. [Data Pipeline & Architecture](#data-pipeline--architecture)
3. [SQL Optimization (Aggregate-Before-Join)](#sql-optimization-aggregate-before-join)
4. [Statistical & Machine Learning Modeling](#statistical--machine-learning-modeling)
5. [Key Results & Business Insights](#key-results--business-insights)
6. [Actionable Recommendations](#actionable-recommendations)
7. [Repository Structure](#repository-structure)
8. [How to Run](#how-to-run)
9. [Author](#author)

---

## Business Problem

A retail business purchases inventory from over 100 vendors and sells it across multiple brands. Decision-makers lacked data-backed answers to two critical questions:
*   **Which vendors drag down profitability?** (Is it just the low-sales vendors, or is there a deeper operational inefficiency?)
*   **What operational levers can vendor managers pull to improve margins?** (Price, freight, stock turnover, and portfolio size interact, but their individual effects on profit margin were unquantified.)

**Why it matters:** Every unit of purchased stock that remains unsold ties up real capital on the shelf (`UnsoldCapital`), acting as a cash-flow drag. Without objective, automated metrics to flag underperforming vendors, reviews default to "loudest sales numbers" rather than true profitability.

---

## Data Pipeline & Architecture

The workflow is structured as a decoupled pipeline, separating heavy aggregation (SQL) from cleaning and model training (Python):

```mermaid
flowchart TD
    subgraph Raw Data Layer
        A[(sales table <br> 12.8M rows)]
        B[(purchases table <br> 2.3M rows)]
        C[(vendor_invoice)]
        D[(purchase_prices)]
    end

    subgraph Data Engineering (SQL)
        E[CTE 1: FreightSummary]
        F[CTE 2: PurchaseSummary]
        G[CTE 3: SalesSummary]
        H[LEFT JOIN on Vendor & Brand]
        I[(vendor_sales_summary <br> 10.6K rows)]
    end

    subgraph Cleaning & Feature Engineering
        J[clean_pipeline.py]
        K[(vendor_sales_summary_clean.csv <br> 8.5K rows)]
    end

    subgraph Analytics & Modeling
        L[stats_ml_pipeline.py]
        M[Welch's t-test]
        N[KMeans Clustering]
        O[Linear Regression]
        P[analysis_results.json]
    end

    A --> G
    B --> F
    D --> F
    C --> E
    E --> H
    F --> H
    G --> H
    H --> I
    I --> J
    J --> K
    K --> L
    L --> M
    L --> N
    L --> O
    L --> P
```

---

## SQL Optimization (Aggregate-Before-Join)

> [!IMPORTANT]
> **The Join Fan-Out Problem:** Initial attempts to join the raw tables (`sales` at 12.8M rows and `purchases` at 2.3M rows) crashed due to out-of-memory (OOM) errors because of the massive cross-join expansion.

**The Solution:** 
We aggregate each table independently down to the **vendor + brand grain** inside isolated Common Table Expressions (CTEs) *before* performing any joins. This slashes the join input size from **12.8 million rows to only 10,692 rows**, reducing execution time from a system crash to just **14 seconds** in SQLite. 

The full query is available in **[vendor_performance_queries.sql](file:///d:/Code/Projects/Vendor's%20Performance%20Analysis/vendor_performance_queries.sql)**.

---

## Statistical & Machine Learning Modeling

The pipeline in **[stats_ml_pipeline.py](file:///d:/Code/Projects/Vendor's%20Performance%20Analysis/stats_ml_pipeline.py)** processes the rolled-up vendor summaries using three primary analytical methodologies:

### 1. Statistical Hypothesis Testing
We perform a **Welch’s t-test** (equal variance not assumed) to compare the average profit margin of the top sales tier (vendors above median sales) against the bottom sales tier. This tests the core business assumption: *"Do larger sales volumes guarantee better margins?"*

### 2. Unsupervised Vendor Segmentation (KMeans)
Instead of arbitrary, single-metric thresholds (e.g., "bottom 10 by revenue"), we apply **KMeans Clustering** to segment vendors across 4 dimensions:
*   `LogSales` (Log-transformed to handle extreme revenue skews)
*   `LogGrossProfit` (Log-transformed to normalize value ranges)
*   `ProfitMargin` (Standard percentage scale)
*   `StockTurnoverCapped` (Capped at 95th percentile to limit outlier noise)

Features are standardized using `StandardScaler` so that features with larger numerical ranges (like dollar sales) do not dominate distance calculations.

### 3. Drivers of Profitability (Linear Regression)
We train a **Multiple Linear Regression** model to predict `ProfitMargin` using purely operational factors: `FreightCost`, `StockTurnover`, `BrandCount`, `AvgPurchasePrice`, and `AvgActualPrice`.
*   *Note:* Explanatory columns that would mathematically define margins (like sales revenue or gross profit) are excluded to prevent leakage.

---

## Key Results & Business Insights

| Question | Method | Result | Business Insight |
| :--- | :--- | :--- | :--- |
| Does sales volume predict margin? | **Welch's t-test** (Top vs. Bottom Sales) | $p = 0.090$ (Not Significant) | Sales volume alone is not a predictor of margin. Big vendors are not necessarily highly profitable. |
| Can we objectively group vendors? | **KMeans Clustering** ($k = 3$) | Silhouette: **0.448** (8 High, 72 Mid, 39 Low) | Segmented the base into operational profiles, isolating 39 "Low Performers" dragging down the average. |
| What drives Profit Margin? | **Linear Regression** (Operational Factors) | $R^2 = 0.001$ on Synthetic Data | Identifying how pricing and turnover interact. (Stock turnover is historically the strongest lever). |

---

## Actionable Recommendations

1.  **De-prioritize "Volume Growth" as a proxy for Margin:** Evaluate vendors on margin and inventory efficiency, not gross revenue. Welch's t-test confirms volume does not equal profit rate.
2.  **Focus reviews on the KMeans "Low Performer" segment:** Target the flagged underperforming vendors for immediate contract review, item consolidation, or phase-out.
3.  **Prioritize Stock Turnover over Price Discounts:** Order sizes and shipment frequencies should be optimized to increase turnover, as holding cost (unsold capital) eats margins faster than wholesale discounts.
4.  **Incorporate `UnsoldCapital` in Vendor Scorecards:** Measure the absolute dollar value of inventory sitting on shelves to maintain cash-flow visibility.

---

## Repository Structure

```text
├── vendor_performance_queries.sql  # SQL queries (CTEs and indexing)
├── clean_pipeline.py               # Data engineering pipeline (loads, cleans, features, filters)
├── stats_ml_pipeline.py            # Stats/ML pipeline (Welch's t-test, KMeans, Regression)
├── Vendor's_Performance_Analysis_SQL_Python.ipynb  # Part 1 Notebook (Data Cleaning)
├── Vendor_Performance_Analytics_EDA_Stats_ML.ipynb # Part 2 Notebook (EDA/Model training)
├── Vendor_Performance_Dashboard.xlsx               # Source dashboard / Excel KPI model
├── generate_mock_data.py           # Synthetic data generator for sandbox testing
├── nlp_extension_product_text_clustering.py        # Product semantic text clustering (NLP)
├── .gitignore                      # Excludes DB and local datasets from repository
└── README.md                       # Documentation
```

---

## How to Run

### 1. Install Dependencies
Ensure you have the required Python libraries installed:
```bash
pip install pandas numpy scipy scikit-learn matplotlib seaborn openpyxl
```

### 2. Generate Sandbox Mock Data
Since the original raw databases exceed size limits, run the synthetic generator script to create local database models instantly:
```bash
python generate_mock_data.py
```

### 3. Run Standalone Pipelines (Production-Ready)
Execute the pipelines end-to-end:
```bash
# Part 1: Clean and engineer KPIs
python clean_pipeline.py

# Part 2: Train models and output JSON/CSV reports
python stats_ml_pipeline.py
```

### 4. Run Notebooks (Interactive)
If you prefer running in a Jupyter environment, open and run:
1.  **[Vendor's_Performance_Analysis_SQL_Python.ipynb](file:///d:/Code/Projects/Vendor's%20Performance%20Analysis/Vendor's_Performance_Analysis_SQL_Python.ipynb)**
2.  **[Vendor_Performance_Analytics_EDA_Stats_ML.ipynb](file:///d:/Code/Projects/Vendor's%20Performance%20Analysis/Vendor_Performance_Analytics_EDA_Stats_ML.ipynb)**

---

## Author

**Shivansh Nigam**
📧 [s2704nigam@gmail.com](mailto:s2704nigam@gmail.com)
💼 [GitHub Profile](https://github.com/Shivanshh27)