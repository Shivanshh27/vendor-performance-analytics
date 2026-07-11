"""
E-Commerce Sales Performance Analysis — NLP Extension
Adds text-based product clustering (TF-IDF + KMeans) on top of the
original margin/discount analysis, to test whether product-name
semantics explain margin variation beyond Category/Sub-Category.

Original project: SQL/Pandas/Plotly margin analysis on Sample Superstore.
This extension: applies NLP to the Product Name field, which the
original analysis did not use.
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

# ---------------------------------------------------------------
# 1. Load + aggregate to product level
#    (product level, not transaction level -> avoids re-embedding
#    the same product name thousands of times)
# ---------------------------------------------------------------
df = pd.read_csv('Ecommerce Sales Analysis Data.csv', encoding='latin1')

prod = df.groupby('Product Name').agg(
    Sales=('Sales', 'sum'),
    Profit=('Profit', 'sum'),
    Discount=('Discount', 'mean'),
    Category=('Category', 'first'),
    Sub_Category=('Sub-Category', 'first')
).reset_index()

prod['Margin_Pct'] = (prod['Profit'] / prod['Sales']) * 100

# ---------------------------------------------------------------
# 2. Vectorize product names with TF-IDF
#    TF-IDF = weight each word by how distinctive it is to that
#    product name vs. the whole catalog (common words like "the"
#    get near-zero weight; brand/material words get high weight).
#    bigrams (ngram_range=(1,2)) capture 2-word terms like
#    "ring binder" as a single feature.
# ---------------------------------------------------------------
tfidf = TfidfVectorizer(max_features=300, stop_words='english', ngram_range=(1, 2))
X = tfidf.fit_transform(prod['Product Name'])

# ---------------------------------------------------------------
# 3. Cluster products by text similarity (unsupervised — no labels)
#    Reuses the same KMeans approach as the original Vendor project,
#    applied to a text feature space instead of numeric KPIs.
# ---------------------------------------------------------------
N_CLUSTERS = 8
kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
prod['text_cluster'] = kmeans.fit_predict(X)

# ---------------------------------------------------------------
# 4. Summarize: does semantic clustering explain margin variance?
# ---------------------------------------------------------------
summary = prod.groupby('text_cluster').agg(
    n_products=('Product Name', 'count'),
    avg_margin=('Margin_Pct', 'mean'),
    total_profit=('Profit', 'sum'),
    total_sales=('Sales', 'sum')
).sort_values('avg_margin')

print("=== Margin by text-based product cluster ===")
print(summary.round(1))

# Top TF-IDF terms per cluster = the "theme" of that cluster
terms = np.array(tfidf.get_feature_names_out())
order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]

print("\n=== What each cluster actually is ===")
for c in summary.index:
    top_terms = terms[order_centroids[c, :6]]
    print(f"Cluster {c}  |  avg margin {summary.loc[c, 'avg_margin']:.1f}%  "
          f"|  {summary.loc[c, 'n_products']} products  ->  {list(top_terms)}")

# ---------------------------------------------------------------
# OPTIONAL UPGRADE (run this locally / in Colab where huggingface.co
# is reachable — it's blocked in some sandboxed environments):
#
# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer('all-MiniLM-L6-v2')   # pretrained, no training
# embeddings = model.encode(prod['Product Name'].tolist())
# kmeans = KMeans(n_clusters=8, random_state=42, n_init=10).fit(embeddings)
# prod['text_cluster'] = kmeans.labels_
#
# This replaces TF-IDF (word-frequency based) with transformer
# embeddings (meaning-based) — e.g. "chair" and "seating" would be
# recognized as similar even with zero shared words. Same downstream
# analysis applies unchanged.
# ---------------------------------------------------------------
