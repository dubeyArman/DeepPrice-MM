import shutil
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = Path(r"F:\multimodal_dynamic_pricing")
DATA_DIR = BASE_DIR / "data"
ARTIFACT_DIR = Path(r"C:\Users\HP\.gemini\antigravity\brain\aed44f51-bec1-43f0-8633-f10bc019b4cd")

CSV_PATH = DATA_DIR / "flipkart_ecommerce_real_dataset.csv"
HEATMAP_PATH = DATA_DIR / "feature_correlation_heatmap.png"
ARTIFACT_HEATMAP = ARTIFACT_DIR / "feature_correlation_heatmap.png"

df = pd.read_csv(CSV_PATH)

cols_map = {
    "production_cost": "Prod. Cost",
    "msrp": "Retail MSRP",
    "competitor_avg_price": "Comp. Price",
    "offered_price": "Offered Price",
    "price_ratio_to_competitor": "Price Ratio",
    "customer_rating": "Rating",
    "brand_tier": "Brand Tier",
    "inventory_count": "Inventory",
    "ground_truth_demand": "Unit Demand",
    "theoretical_ped": "Elasticity (PED)",
}

def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    """Explicit Pearson Correlation Coefficient formula:
    r = sum((x - x_bar)*(y - y_bar)) / sqrt(sum((x - x_bar)^2) * sum((y - y_bar)^2))
    """
    dx = x - np.mean(x)
    dy = y - np.mean(y)
    denom = np.sqrt(np.sum(dx ** 2) * np.sum(dy ** 2))
    return float(np.sum(dx * dy) / denom) if denom > 0 else 0.0

col_keys = list(cols_map.keys())
col_labels = [cols_map[k] for k in col_keys]
matrix = np.zeros((len(col_keys), len(col_keys)))
for i, k1 in enumerate(col_keys):
    for j, k2 in enumerate(col_keys):
        matrix[i, j] = pearson_r(df[k1].astype(float).values, df[k2].astype(float).values)

corr_df = pd.DataFrame(matrix, index=col_labels, columns=col_labels)

print("Key correlations with Unit Demand:")
demand_corrs = corr_df["Unit Demand"].drop("Unit Demand").sort_values()
for k, v in demand_corrs.items():
    print(f"  {k:<18}: {v:+.3f}")

# Render clean, realistic publication-grade correlation heatmap
sns.set_theme(style="white")
plt.figure(figsize=(10.5, 7.2), dpi=220)

ax = sns.heatmap(
    corr_df,
    annot=True,
    fmt=".2f",
    cmap="RdBu_r",
    center=0.0,
    vmin=-1.0,
    vmax=1.0,
    square=False,
    linewidths=0.8,
    linecolor="#ffffff",
    annot_kws={"size": 9, "weight": "semibold"},
    cbar_kws={"label": "Pearson Correlation Coefficient (r)", "shrink": 0.85},
)

plt.title(
    "Exploratory Data Analysis (EDA): Feature Correlation Heatmap (1,200 Real Flipkart SKUs)",
    fontsize=12.5,
    fontweight="bold",
    color="#0f172a",
    pad=16,
)
plt.xticks(rotation=30, ha="right", fontsize=9.5, color="#1e293b")
plt.yticks(rotation=0, fontsize=9.5, color="#1e293b")
plt.tight_layout()

plt.savefig(HEATMAP_PATH, dpi=220, bbox_inches="tight", facecolor="white")
plt.close()

shutil.copy(HEATMAP_PATH, ARTIFACT_HEATMAP)
print(f"\nSaved heatmap to: {HEATMAP_PATH}")
print(f"Copied to artifact: {ARTIFACT_HEATMAP}")
