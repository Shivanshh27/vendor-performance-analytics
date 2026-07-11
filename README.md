# Vendor Performance Analytics

End-to-end vendor performance analysis for a retail/distribution business from raw SQL aggregation of 15M+ transactional rows, through Python data cleaning and feature engineering, to statistical hypothesis testing, KMeans clustering, and regression modeling delivered as a live Excel/Power BI style dashboard.

---

## Business Problem

A retail/distribution business purchases inventory from over a hundred vendors and sells it across many brands. Two questions kept coming up without a data-backed answer:

- **Which vendors are actually dragging down profitability**, and is that answer just "the ones with low sales" — or something more specific?
- **What can a vendor manager actually *do* about it?** Price, freight, inventory turnover, and portfolio size all interact, but nobody had isolated which of these actually moves profit margin.

**Why it matters:** vendor relationships tie up real capital. Every unit purchased but not sold is cash sitting on a shelf instead of earning revenue (`UnsoldCapital` in this dataset), and every low-margin vendor relationship that goes unreviewed is a quiet, ongoing drag on overall profitability. Without an objective, repeatable way to flag underperformance, vendor reviews default to gut feel or to whoever has the loudest sales numbers  which, as the analysis below shows, is not the same thing as whoever is hurting margin.

The raw data itself was also a practical blocker: the transactional tables (`sales`: 12,825,363 rows, `purchases`: 2,372,474 rows) were too large to join and analyze directly  a first attempt at a single large join crashed with a memory/disk-full error, which had to be solved before any analysis could happen at all.

---

## Approach

I treated this as a pipeline problem, not a single script, because each stage genuinely needed a different tool:

1. **SQL first**, because the data starts life too large for Python/pandas to touch efficiently. I restructured the query to aggregate each source table (freight, purchases, sales) independently inside CTEs *before* joining shrinking the join input from 12.8M rows to ~10K rows and turning a crash into a ~14-second query.
2. **Python second**, to clean the SQL output (dtype fixes, null handling from `LEFT JOIN` artifacts, whitespace stripping) and engineer the KPIs the rest of the analysis depends on: `GrossProfit`, `ProfitMargin`, `StockTurnover`, `UnsoldCapital`.
3. **EDA**, to sanity-check distributions and spot the skew (a handful of vendors are 100-1000x larger than the rest) before it silently broke any modeling downstream.
4. **Statistics**, to test the assumption everyone made by default that big vendors = profitable vendors before building anything on top of it.
5. **Machine Learning**, to replace a subjective "low performer" label with an objective one (KMeans across four performance dimensions at once) and to isolate which operational levers actually predict margin (Linear Regression, deliberately excluding variables that would trivially explain margin by definition).
6. **Dashboard**, to turn the analysis into something a non-technical stakeholder can actually use  live KPI cards and vendor/brand summaries that recalculate if the underlying data changes.

Every design decision along the way why CTEs, why `LEFT JOIN`, why log-transform before clustering, why exclude certain regression features is documented at the point it happens in the notebooks and in the dashboard's `Documentation` sheet, not just asserted here.

---

## Key Results

| Question | Method | Result |
|---|---|---|
| Does sales volume predict profit margin? | Welch's t-test (top vs. bottom sales tier) | **No**  p = 0.410 (not significant). Top tier mean margin 35.9% vs. bottom tier 38.0%. |
| Which vendors are objectively "low performing"? | KMeans clustering (sales, profit, margin, turnover) | **13 vendors** flagged as Low Performers, 51 Mid, 55 High. Silhouette score 0.44. |
| What drives Profit Margin? | Linear Regression (operational factors only) | **R² = 0.38.** Stock Turnover and list price are the strongest positive drivers; average purchase price is a negative driver. |

---

## Insights

**1. Growing sales volume alone will not improve profitability.**
The t-test found no significant difference in profit margin between high-sales and low-sales vendors (p = 0.41). Margin is driven by *how* a vendor operates, not how much they sell.

**2. 13 vendors are objectively Low Performers across multiple dimensions.**
KMeans clustering (sales scale, gross profit, margin, and turnover together) isolated 13 vendors as consistently weak on all four axes  not just low-volume, but genuinely inefficient.

**3. Stock Turnover is the strongest lever a manager can actually pull.**
Regression shows Stock Turnover has the largest positive coefficient on Profit Margin of any operational factor tested. Vendors whose inventory moves faster consistently retain more margin.

**4. Higher purchase price erodes margin, even after controlling for sales price.**
Average purchase price has a negative regression coefficient vendors bought at a higher unit cost retain a thinner margin, independent of what they sell for.

**5. A meaningful chunk of margin variation is still unexplained (R² = 0.38).**
Freight cost, turnover, brand count, and pricing together explain only ~38% of margin variance other factors (seasonality, product category, promotions, regional demand) likely matter too.

**6. Unsold Capital is a real, quantifiable cash-flow drag.**
Several vendors carry sizable `UnsoldCapital` (purchased stock that hasn't sold), tying up cash on the shelf instead of converting it to revenue.

---

## Recommendations

**1. Retire "grow the biggest vendors" as a default profitability strategy.**
Since sales volume doesn't predict margin, evaluate vendors on margin and turnover, not just revenue contribution, when deciding where to invest relationship effort.

**2. Prioritize the 13 flagged Low Performers for a structured review.**
Renegotiate terms, reduce order volumes, or phase them out — rather than spreading limited review effort evenly across the full vendor base.

**3. Attack turnover before price.**
For Low/Mid Performers, focus first on reducing unsold inventory (smaller, more frequent orders; better demand forecasting) rather than renegotiating price — turnover moves margin more than any other controllable factor in this model.

**4. Target the highest-purchase-price, lowest-turnover vendors first for renegotiation.**
That combination compounds the two biggest negative drivers of margin at once, so it's the highest-leverage place to start.

**5. Treat the regression as a first-pass diagnostic, not a finished model.**
If it's worth deeper investment, extend it with product category and time-based features before relying on it for forecasting  38% of margin variance is still unexplained by operational factors alone.

**6. Add `UnsoldCapital` as a standing metric in vendor review meetings.**
It's the most direct dollar translation of "this vendor relationship is costing us cash right now," and shouldn't stay buried as a background KPI.

---

## Pipeline

```
Raw DB tables (purchases, sales, vendor_invoice, purchase_prices — 15M+ rows)
        │
        ▼
1. SQL  — aggregate-before-join CTEs → vendor_sales_summary (10,692 rows)
        │
        ▼
2. Python — dtype fixes, null handling, KPI feature engineering,
            outlier/artifact filtering → vendor_sales_summary_clean (8,564 rows)
        │
        ▼
3. EDA — distributions, top vendors, correlation checks
        │
        ▼
4. Statistics — Welch's t-test, correlation matrix
        │
        ▼
5. Machine Learning — KMeans (performance tiers), Linear Regression (margin drivers)
        │
        ▼
6. Dashboard — Excel workbook with live KPI cards, vendor/brand summaries, cluster labels
```

**Why SQL first:** the raw tables are too large to clean or model directly (`sales` alone is 12.8M rows). A single unoptimized join against it caused out-of-memory failures  fixed by aggregating each source table independently inside CTEs *before* joining, which cut the join input from 12.8M rows to ~10K and turned a crash into a 14-second query.

**Why Python second:** SQL hands off a wide summary table; Python is used for row-level cleaning (dtype casts, null handling, whitespace stripping) and derived KPI calculation (`GrossProfit`, `ProfitMargin`, `StockTurnover`, `UnsoldCapital`) that's easier to express and test in pandas than in SQL.

**Why clustering instead of a fixed threshold:** a hardcoded rule like "bottom 10 vendors by sales" ignores profit margin and turnover entirely. KMeans finds natural groupings across four dimensions at once, so the "Low Performer" label reflects overall performance shape, not one metric in isolation.

---

## Repository Structure

```
├── vendor_performance_queries.sql       # Full SQL: exploration, standalone queries, optimized CTE build
├── clean_pipeline.py                    # Python: load → clean → feature engineer → filter → export
├── stats_ml_pipeline.py                 # Python: t-test, correlation, KMeans clustering, linear regression
├── Part1_SQL_Python.ipynb               # Notebook 1 — SQL aggregation + Python cleaning, runnable end-to-end
├── Part2_EDA_Stats_ML.ipynb             # Notebook 2 — EDA, statistics, clustering, regression, runnable end-to-end
├── Vendor_Performance_Dashboard.xlsx    # Final deliverable: KPI dashboard + full methodology write-up
├── vendor_performance_clusters.csv      # Vendor-level output with cluster labels (ML result)
└── README.md
```

---

## Tech Stack

- **SQL** — SQLite (CTEs, window functions, aggregate-before-join optimization)
- **Python** — pandas, NumPy
- **Statistics** — SciPy (Welch's t-test), correlation analysis
- **Machine Learning** — scikit-learn (KMeans, StandardScaler, Linear Regression, silhouette score)
- **Visualization** — Matplotlib, Seaborn
- **Reporting** — Excel (live formulas, SUMIF/AVERAGEIF, conditional formatting)

---

## How to Run

1. Clone the repo and install dependencies:
   ```bash
   pip install pandas numpy scipy scikit-learn matplotlib seaborn openpyxl
   ```

### Option A: Run via Standalone Python Pipelines (Production Ready)
1. Run the cleaning and feature engineering pipeline:
   ```bash
   python clean_pipeline.py
   ```
2. Run the statistical analysis and machine learning pipeline:
   ```bash
   python stats_ml_pipeline.py
   ```

### Option B: Run via Interactive Jupyter Notebooks
1. Run **`Vendor's_Performance_Analysis_SQL_Python.ipynb`** (Part 1) — it builds the SQLite database, runs the SQL aggregation, cleans the data, and saves `vendor_sales_summary_clean.csv`.
2. Run **`Vendor_Performance_Analytics_EDA_Stats_ML.ipynb`** (Part 2) — it reads the output of Part 1 and runs EDA, statistical tests, clustering, and regression.

Open `Vendor_Performance_Dashboard.xlsx` to see the final KPI dashboard built on the same data.

> Note: the original raw tables (`purchases`, `sales`, `vendor_invoice`, `purchase_prices` — 15M+ rows) are not included in this repo due to size. Both notebooks and pipelines reproduce the exact SQL/Python logic that was run against the full database, executed here against the already-aggregated summary table, so they run end-to-end and produce verifiable output.

---

## Author

**Shivansh Nigam** — transitioning into Data Science & Analytics
📧 s2704nigam@gmail.com
#   v e n d o r - p e r f o r m a n c e - a n a l y t i c s  
 