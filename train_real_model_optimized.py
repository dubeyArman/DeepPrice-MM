import os
import sys
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from loguru import logger

BASE_DIR = Path(r"F:\multimodal_dynamic_pricing")
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "flipkart_ecommerce_real_dataset.csv"
MODEL_SAVE_PATH = BASE_DIR / "models" / "best_multimodal_pricing_model.pth"
METRICS_JSON_PATH = DATA_DIR / "ablation_evaluation_results.json"
TEXT_CACHE_PATH = DATA_DIR / "real_text_embeddings_cache.npy"
VISION_CACHE_PATH = DATA_DIR / "real_vision_embeddings_cache.npy"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info("Using device: {}", device)

# Load Real Dataset & Precomputed Caches
df = pd.read_csv(CSV_PATH)
text_embeddings = np.load(TEXT_CACHE_PATH)
vision_embeddings = np.load(VISION_CACHE_PATH)

tabular_cols = [
    "offered_price", "production_cost", "msrp", "competitor_min_price",
    "competitor_avg_price", "price_ratio_to_competitor", "inventory_count",
    "customer_rating"
]
tab_scaler = StandardScaler()
tabular_scaled = tab_scaler.fit_transform(df[tabular_cols].values)
np.save(DATA_DIR / "scaler_mean.npy", tab_scaler.mean_)
np.save(DATA_DIR / "scaler_scale.npy", tab_scaler.scale_)

# Scale target for numerical stability
raw_demand = df["ground_truth_demand"].values.reshape(-1, 1)
demand_scaler = StandardScaler()
demand_scaled = demand_scaler.fit_transform(raw_demand).flatten()
np.save(DATA_DIR / "demand_scaler_mean.npy", demand_scaler.mean_)
np.save(DATA_DIR / "demand_scaler_scale.npy", demand_scaler.scale_)

train_idx, test_idx = train_test_split(np.arange(len(df)), test_size=0.15, random_state=42, stratify=df["category"])
train_idx, val_idx = train_test_split(train_idx, test_size=0.1765, random_state=42)

class ScaledDataset(Dataset):
    def __init__(self, idxs):
        self.v = torch.tensor(vision_embeddings[idxs], dtype=torch.float32)
        self.t = torch.tensor(text_embeddings[idxs], dtype=torch.float32)
        self.tab = torch.tensor(tabular_scaled[idxs], dtype=torch.float32)
        self.y = torch.tensor(demand_scaled[idxs], dtype=torch.float32).unsqueeze(1)
        self.raw_y = df["ground_truth_demand"].iloc[idxs].values

    def __len__(self):
        return len(self.v)

    def __getitem__(self, i):
        return self.v[i], self.t[i], self.tab[i], self.y[i]

train_ds = ScaledDataset(train_idx)
val_ds = ScaledDataset(val_idx)
test_ds = ScaledDataset(test_idx)

train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)
test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)

def compute_metrics(y_true, y_pred):
    r2 = r2_score(y_true, y_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(1.0, y_true))) * 100
    return {
        "R2_Score": round(float(r2), 4),
        "RMSE": round(float(rmse), 2),
        "MAE": round(float(mae), 2),
        "MAPE_pct": round(float(mape), 2),
    }

# 1. Proposed Multimodal Cross-Attention Network
class FastMultimodalNet(nn.Module):
    def __init__(self, tab_dim=8, embed_dim=128, num_heads=4):
        super().__init__()
        self.vision_proj = nn.Sequential(
            nn.Linear(512, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
        )
        self.text_proj = nn.Sequential(
            nn.Linear(384, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
        )
        self.tabular_encoder = nn.Sequential(
            nn.Linear(tab_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
        )
        self.modality_attention = nn.MultiheadAttention(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dropout=0.1,
            batch_first=True,
        )
        self.fusion_norm = nn.LayerNorm(embed_dim)
        self.shared_fc = nn.Sequential(
            nn.Linear(embed_dim * 3, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

    def forward(self, v_feats, t_embeds, tab_feats):
        B = v_feats.size(0)
        h_v = self.vision_proj(v_feats)
        h_t = self.text_proj(t_embeds)
        h_tab = self.tabular_encoder(tab_feats)
        modalities = torch.stack([h_v, h_t, h_tab], dim=1)
        attn_out, attn_w = self.modality_attention(modalities, modalities, modalities)
        fused = self.fusion_norm(modalities + attn_out)
        fused_flat = fused.reshape(B, -1)
        out = self.shared_fc(fused_flat)
        return out, attn_w

logger.info("Training Proposed Multimodal Cross-Attention Network...")
model = FastMultimodalNet(tab_dim=len(tabular_cols)).to(device)
opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
criterion = nn.MSELoss()

best_loss = float('inf')
for epoch in range(30):
    model.train()
    for v, t, tab, y in train_loader:
        v, t, tab, y = v.to(device), t.to(device), tab.to(device), y.to(device)
        opt.zero_grad()
        pred, _ = model(v, t, tab)
        loss = criterion(pred, y)
        loss.backward()
        opt.step()

    model.eval()
    val_loss = 0.0
    with torch.no_grad():
        for v, t, tab, y in val_loader:
            v, t, tab, y = v.to(device), t.to(device), tab.to(device), y.to(device)
            pred, _ = model(v, t, tab)
            val_loss += criterion(pred, y).item()
    if val_loss < best_loss:
        best_loss = val_loss
        torch.save(model.state_dict(), MODEL_SAVE_PATH)

# Test Proposed Model
model.eval()
preds_scaled = []
with torch.no_grad():
    for v, t, tab, _ in test_loader:
        v, t, tab = v.to(device), t.to(device), tab.to(device)
        pred, _ = model(v, t, tab)
        preds_scaled.extend(pred.cpu().numpy().flatten())

y_true_real = test_ds.raw_y
y_pred_real = np.maximum(10.0, demand_scaler.inverse_transform(np.array(preds_scaled).reshape(-1, 1)).flatten())
prop_metrics = compute_metrics(y_true_real, y_pred_real)
logger.info("Proposed Multimodal Test Metrics: {}", prop_metrics)

# 2. Baseline 1: Tabular Only
tab_model = nn.Sequential(
    nn.Linear(len(tabular_cols), 64),
    nn.BatchNorm1d(64),
    nn.ReLU(),
    nn.Linear(64, 32),
    nn.ReLU(),
    nn.Linear(32, 1),
).to(device)
opt_tab = torch.optim.Adam(tab_model.parameters(), lr=1e-3)
for _ in range(30):
    tab_model.train()
    for _, _, tab, y in train_loader:
        tab, y = tab.to(device), y.to(device)
        opt_tab.zero_grad()
        loss = criterion(tab_model(tab), y)
        loss.backward()
        opt_tab.step()

tab_model.eval()
t_preds = []
with torch.no_grad():
    for _, _, tab, _ in test_loader:
        tab = tab.to(device)
        t_preds.extend(tab_model(tab).cpu().numpy().flatten())
b1_y_pred = np.maximum(10.0, demand_scaler.inverse_transform(np.array(t_preds).reshape(-1, 1)).flatten())
b1_metrics = compute_metrics(y_true_real, b1_y_pred)
logger.info("Baseline 1 (Tabular Only): {}", b1_metrics)

# 3. Baseline 2: Text + Tabular
class TextTab(nn.Module):
    def __init__(self, tab_dim=8):
        super().__init__()
        self.t_proj = nn.Sequential(nn.Linear(384, 128), nn.BatchNorm1d(128), nn.ReLU())
        self.tab_proj = nn.Sequential(nn.Linear(tab_dim, 64), nn.BatchNorm1d(64), nn.ReLU())
        self.fc = nn.Sequential(nn.Linear(128 + 64, 64), nn.ReLU(), nn.Linear(64, 1))
    def forward(self, t, tab):
        h_t = self.t_proj(t)
        h_tab = self.tab_proj(tab)
        return self.fc(torch.cat([h_t, h_tab], dim=-1))

tt_model = TextTab().to(device)
opt_tt = torch.optim.Adam(tt_model.parameters(), lr=1e-3)
for _ in range(30):
    tt_model.train()
    for _, t, tab, y in train_loader:
        t, tab, y = t.to(device), tab.to(device), y.to(device)
        opt_tt.zero_grad()
        loss = criterion(tt_model(t, tab), y)
        loss.backward()
        opt_tt.step()

tt_model.eval()
tt_preds = []
with torch.no_grad():
    for _, t, tab, _ in test_loader:
        t, tab = t.to(device), tab.to(device)
        tt_preds.extend(tt_model(t, tab).cpu().numpy().flatten())
b2_y_pred = np.maximum(10.0, demand_scaler.inverse_transform(np.array(tt_preds).reshape(-1, 1)).flatten())
b2_metrics = compute_metrics(y_true_real, b2_y_pred)
logger.info("Baseline 2 (Text + Tabular): {}", b2_metrics)

# 4. Baseline 3: Vision + Tabular
class VisTab(nn.Module):
    def __init__(self, tab_dim=8):
        super().__init__()
        self.v_proj = nn.Sequential(nn.Linear(512, 128), nn.BatchNorm1d(128), nn.ReLU())
        self.tab_proj = nn.Sequential(nn.Linear(tab_dim, 64), nn.BatchNorm1d(64), nn.ReLU())
        self.fc = nn.Sequential(nn.Linear(128 + 64, 64), nn.ReLU(), nn.Linear(64, 1))
    def forward(self, v, tab):
        h_v = self.v_proj(v)
        h_tab = self.tab_proj(tab)
        return self.fc(torch.cat([h_v, h_tab], dim=-1))

vt_model = VisTab().to(device)
opt_vt = torch.optim.Adam(vt_model.parameters(), lr=1e-3)
for _ in range(30):
    vt_model.train()
    for v, _, tab, y in train_loader:
        v, tab, y = v.to(device), tab.to(device), y.to(device)
        opt_vt.zero_grad()
        loss = criterion(vt_model(v, tab), y)
        loss.backward()
        opt_vt.step()

vt_model.eval()
vt_preds = []
with torch.no_grad():
    for v, _, tab, _ in test_loader:
        v, tab = v.to(device), tab.to(device)
        vt_preds.extend(vt_model(v, tab).cpu().numpy().flatten())
b3_y_pred = np.maximum(10.0, demand_scaler.inverse_transform(np.array(vt_preds).reshape(-1, 1)).flatten())
b3_metrics = compute_metrics(y_true_real, b3_y_pred)
logger.info("Baseline 3 (Vision + Tabular): {}", b3_metrics)

# Dynamic Pricing Simulation
test_df = df.iloc[test_idx].copy().reset_index(drop=True)
static_revenues = []
opt_revenues = []
opt_prices = []

sweep_factors = np.linspace(0.85, 1.25, 40)
for idx_in_test in range(len(test_df)):
    row = test_df.iloc[idx_in_test]
    cost = row["production_cost"]
    msrp = row["msrp"]
    comp_p = row["competitor_avg_price"]

    static_rev = row["offered_price"] * y_true_real[idx_in_test]
    static_revenues.append(static_rev)

    best_p = comp_p
    best_profit = -1e9
    best_rev = static_rev

    v_t = torch.tensor(vision_embeddings[test_idx[idx_in_test]], dtype=torch.float32).unsqueeze(0).to(device)
    t_t = torch.tensor(text_embeddings[test_idx[idx_in_test]], dtype=torch.float32).unsqueeze(0).to(device)

    for factor in sweep_factors:
        cand_p = round(float(comp_p * factor), 2)
        ratio = cand_p / comp_p
        raw_tab = [cand_p, cost, msrp, row["competitor_min_price"], comp_p, ratio, row["inventory_count"], row["customer_rating"]]
        scaled_tab = (np.array(raw_tab) - tab_scaler.mean_) / tab_scaler.scale_
        tab_t = torch.tensor(scaled_tab, dtype=torch.float32).unsqueeze(0).to(device)

        with torch.no_grad():
            q_scaled = model(v_t, t_t, tab_t)[0].item()
            q_est = max(10.0, float(demand_scaler.inverse_transform([[q_scaled]])[0][0]))

        profit = (cand_p - cost) * q_est
        if profit > best_profit:
            best_profit = profit
            best_p = cand_p
            best_rev = cand_p * q_est

    opt_revenues.append(best_rev)
    opt_prices.append(best_p)

total_static_rev = float(sum(static_revenues))
total_opt_rev = float(sum(opt_revenues))
revenue_lift_pct = round(((total_opt_rev - total_static_rev) / total_static_rev) * 100, 2)
avg_opt_price = round(float(np.mean(opt_prices)), 2)
avg_msrp = round(float(test_df["msrp"].mean()), 2)

logger.info("Total Static Revenue: INR {:,.2f}", total_static_rev)
logger.info("Total Optimized Revenue: INR {:,.2f}", total_opt_rev)
logger.info("Dynamic Revenue Lift: +{}%", revenue_lift_pct)

# Save Metrics JSON
eval_results = {
    "dataset_source": "Flipkart Real E-Commerce Product Catalog (Web Data)",
    "dataset_size": len(df),
    "test_size": len(test_idx),
    "metrics": {
        "proposed_multimodal": prop_metrics,
        "baseline_tabular_only": b1_metrics,
        "baseline_text_tabular": b2_metrics,
        "baseline_vision_tabular": b3_metrics,
    },
    "revenue_optimization": {
        "static_total_revenue_inr": round(total_static_rev, 2),
        "optimized_total_revenue_inr": round(total_opt_rev, 2),
        "revenue_lift_pct": revenue_lift_pct,
        "average_recommended_price": avg_opt_price,
        "average_msrp": avg_msrp,
    }
}

with open(METRICS_JSON_PATH, "w") as f:
    json.dump(eval_results, f, indent=2)

# Generate Visual Plots
sns.set_theme(style="whitegrid", palette="deep")

models_labels = ["Tabular Only", "Vision + Tab", "Text + Tab", "Proposed Multimodal"]
r2_vals = [b1_metrics["R2_Score"], b3_metrics["R2_Score"], b2_metrics["R2_Score"], prop_metrics["R2_Score"]]
mape_vals = [b1_metrics["MAPE_pct"], b3_metrics["MAPE_pct"], b2_metrics["MAPE_pct"], prop_metrics["MAPE_pct"]]
colors = ["#94a3b8", "#38bdf8", "#818cf8", "#10b981"]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
bars1 = axes[0].bar(models_labels, r2_vals, color=colors, edgecolor="black", linewidth=0.8)
axes[0].set_title("Explanatory Accuracy (R² Score) on Real Flipkart Test Set", fontsize=11, fontweight="bold")
axes[0].set_ylabel("R² Score (Higher is Better)", fontsize=10)
axes[0].set_ylim(0, 1.05)
for bar in bars1:
    y = bar.get_height()
    axes[0].text(bar.get_x() + bar.get_width()/2, y + 0.02, f"{y:.4f}", ha='center', va='bottom', fontweight='bold', fontsize=9.5)

bars2 = axes[1].bar(models_labels, mape_vals, color=colors, edgecolor="black", linewidth=0.8)
axes[1].set_title("Prediction Error (MAPE %)", fontsize=11, fontweight="bold")
axes[1].set_ylabel("MAPE % (Lower is Better)", fontsize=10)
for bar in bars2:
    y = bar.get_height()
    axes[1].text(bar.get_x() + bar.get_width()/2, y + 0.4, f"{y:.2f}%", ha='center', va='bottom', fontweight='bold', fontsize=9.5)

plt.tight_layout()
ablation_plot_path = DATA_DIR / "ablation_comparison_plot.png"
fig.savefig(ablation_plot_path, dpi=200)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 5.5))
ax.scatter(y_true_real, y_pred_real, alpha=0.6, color="#2563eb", edgecolors="w", s=40, label="Real Flipkart Test SKUs")
max_v = max(max(y_true_real), max(y_pred_real))
ax.plot([0, max_v], [0, max_v], "r--", linewidth=2, label="1:1 Perfect Parity Line")
ax.set_title("Actual vs. Predicted Unit Demand on Real Flipkart Test Set", fontsize=11, fontweight="bold")
ax.set_xlabel("Actual Demand Volume (Units)", fontsize=10)
ax.set_ylabel("Deep Learning Predicted Demand (Units)", fontsize=10)
ax.legend(loc="upper left")
plt.tight_layout()
scatter_plot_path = DATA_DIR / "actual_vs_predicted_scatter.png"
fig.savefig(scatter_plot_path, dpi=200)
plt.close(fig)

# Copy to brain artifact directory as well
ARTIFACT_DIR = Path(r"C:\Users\HP\.gemini\antigravity\brain\aed44f51-bec1-43f0-8633-f10bc019b4cd")
fig.savefig(ARTIFACT_DIR / "actual_vs_predicted_scatter.png", dpi=200)
plt.close()

import shutil
shutil.copyfile(ablation_plot_path, ARTIFACT_DIR / "ablation_comparison_plot.png")

logger.info("All model training on Real Flipkart Web Dataset completed successfully!")
