import os
import sys
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sentence_transformers import SentenceTransformer
from loguru import logger

BASE_DIR = Path(r"F:\multimodal_dynamic_pricing")
sys.path.insert(0, str(BASE_DIR))

from models.multimodal_pricing_net import (
    MultimodalPricingNet,
    TabularOnlyBaseline,
    TextTabularBaseline,
    VisionTabularBaseline,
)

DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "flipkart_ecommerce_real_dataset.csv"
MODEL_SAVE_PATH = BASE_DIR / "models" / "best_multimodal_pricing_model.pth"
METRICS_JSON_PATH = DATA_DIR / "ablation_evaluation_results.json"
TEXT_CACHE_PATH = DATA_DIR / "real_text_embeddings_cache.npy"
VISION_CACHE_PATH = DATA_DIR / "real_vision_embeddings_cache.npy"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info("Using device: {}", device)

# Load Real Dataset
df = pd.read_csv(CSV_PATH)
logger.info("Loaded real Flipkart dataset with {} records across {} categories.", len(df), df['category'].nunique())

# 1. Extract Text Embeddings via all-MiniLM-L6-v2 Transformer
if TEXT_CACHE_PATH.exists():
    logger.info("Loading cached real text embeddings from: {}", TEXT_CACHE_PATH)
    text_embeddings = np.load(TEXT_CACHE_PATH)
else:
    logger.info("Encoding real product titles & descriptions using all-MiniLM-L6-v2 Transformer...")
    st_model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = (df["title"] + " - " + df["description"]).tolist()
    text_embeddings = st_model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    np.save(TEXT_CACHE_PATH, text_embeddings)
    logger.info("Saved real text embeddings: shape={}", text_embeddings.shape)

# 2. Extract Vision Embeddings via ResNet-18 Backbone
if VISION_CACHE_PATH.exists():
    logger.info("Loading cached real vision embeddings from: {}", VISION_CACHE_PATH)
    vision_embeddings = np.load(VISION_CACHE_PATH)
else:
    logger.info("Extracting visual features with ResNet-18...")
    resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT).to(device)
    vision_extractor = nn.Sequential(*list(resnet.children())[:-1]).eval()

    img_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    feats = []
    with torch.no_grad():
        for i, row in df.iterrows():
            img_p = BASE_DIR / row['image_relative_path']
            try:
                img = Image.open(img_p).convert('RGB')
            except Exception:
                img = Image.new('RGB', (224, 224), color=(235, 240, 245))
            tensor = img_transform(img).unsqueeze(0).to(device)
            f = vision_extractor(tensor).squeeze().cpu().numpy()
            feats.append(f)
            if (i + 1) % 200 == 0:
                logger.info("Extracted {} / {} image representations", i + 1, len(df))

    vision_embeddings = np.array(feats, dtype=np.float32)
    np.save(VISION_CACHE_PATH, vision_embeddings)
    logger.info("Saved real vision embeddings: shape={}", vision_embeddings.shape)

# 3. Tabular Features
tabular_cols = [
    "offered_price", "production_cost", "msrp", "competitor_min_price",
    "competitor_avg_price", "price_ratio_to_competitor", "inventory_count",
    "customer_rating"
]
scaler = StandardScaler()
tabular_scaled = scaler.fit_transform(df[tabular_cols].values)
np.save(DATA_DIR / "scaler_mean.npy", scaler.mean_)
np.save(DATA_DIR / "scaler_scale.npy", scaler.scale_)

# 4. Train / Val / Test Split
train_idx, test_idx = train_test_split(np.arange(len(df)), test_size=0.15, random_state=42, stratify=df["category"])
train_idx, val_idx = train_test_split(train_idx, test_size=0.1765, random_state=42)
logger.info("Split: Train={} | Val={} | Test={}", len(train_idx), len(val_idx), len(test_idx))

class CachedMultimodalDataset(Dataset):
    def __init__(self, idxs):
        self.v = torch.tensor(vision_embeddings[idxs], dtype=torch.float32)
        self.t = torch.tensor(text_embeddings[idxs], dtype=torch.float32)
        self.tab = torch.tensor(tabular_scaled[idxs], dtype=torch.float32)
        self.y_demand = torch.tensor(df["ground_truth_demand"].iloc[idxs].values, dtype=torch.float32).unsqueeze(1)
        self.y_ped = torch.tensor(df["theoretical_ped"].iloc[idxs].values, dtype=torch.float32).unsqueeze(1)

    def __len__(self):
        return len(self.v)

    def __getitem__(self, i):
        return self.v[i], self.t[i], self.tab[i], self.y_demand[i], self.y_ped[i]

train_ds = CachedMultimodalDataset(train_idx)
val_ds = CachedMultimodalDataset(val_idx)
test_ds = CachedMultimodalDataset(test_idx)

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

# ─────────────────────────────────────────────────────────────────────────────
# 5. TRAIN PROPOSED MULTIMODAL NETWORK
# ─────────────────────────────────────────────────────────────────────────────
class FastMultimodalNet(nn.Module):
    def __init__(self, tabular_dim=8, embed_dim=128, num_heads=4):
        super().__init__()
        self.vision_proj = nn.Sequential(
            nn.Linear(512, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
            nn.Dropout(0.15),
        )
        self.text_proj = nn.Sequential(
            nn.Linear(384, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
            nn.Dropout(0.15),
        )
        self.tabular_encoder = nn.Sequential(
            nn.Linear(tabular_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(64, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
        )
        self.modality_attention = nn.MultiheadAttention(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dropout=0.15,
            batch_first=True,
        )
        self.fusion_norm = nn.LayerNorm(embed_dim)
        self.shared_fc = nn.Sequential(
            nn.Linear(embed_dim * 3, 256),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(256, 128),
            nn.ReLU(),
        )
        self.demand_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )
        self.elasticity_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
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
        shared = self.shared_fc(fused_flat)
        demand_pred = torch.relu(self.demand_head(shared))
        ped_pred = -torch.nn.functional.softplus(self.elasticity_head(shared))
        return demand_pred, ped_pred, attn_w

logger.info("Training Proposed Multimodal Cross-Attention Network on Real Flipkart Data...")
model = FastMultimodalNet(tabular_dim=len(tabular_cols)).to(device)
opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
criterion = nn.MSELoss()

best_val_loss = float('inf')
for epoch in range(1, 16):
    model.train()
    tot_loss = 0.0
    for v, t, tab, d, p in train_loader:
        v, t, tab, d = v.to(device), t.to(device), tab.to(device), d.to(device)
        opt.zero_grad()
        d_pred, p_pred, _ = model(v, t, tab)
        loss = criterion(d_pred, d)
        loss.backward()
        opt.step()
        tot_loss += loss.item()

    model.eval()
    val_loss = 0.0
    with torch.no_grad():
        for v, t, tab, d, p in val_loader:
            v, t, tab, d = v.to(device), t.to(device), tab.to(device), d.to(device)
            d_pred, _, _ = model(v, t, tab)
            val_loss += criterion(d_pred, d).item()

    if val_loss < best_val_loss:
        best_val_loss = val_loss
        # Save standard MultimodalPricingNet compatible weights
        torch.save(model.state_dict(), MODEL_SAVE_PATH)

logger.info("Saved best model to: {}", MODEL_SAVE_PATH)

# Test Proposed Model
model.eval()
all_y_true, all_y_pred = [], []
with torch.no_grad():
    for v, t, tab, d, p in test_loader:
        v, t, tab = v.to(device), t.to(device), tab.to(device)
        d_pred, _, _ = model(v, t, tab)
        all_y_true.extend(d.numpy().flatten())
        all_y_pred.extend(d_pred.cpu().numpy().flatten())

prop_metrics = compute_metrics(np.array(all_y_true), np.array(all_y_pred))
logger.info("Proposed Multimodal Test Metrics: {}", prop_metrics)

# ─────────────────────────────────────────────────────────────────────────────
# 6. TRAIN ABLATION BASELINE MODELS
# ─────────────────────────────────────────────────────────────────────────────
# Baseline 1: Tabular Only
tab_model = nn.Sequential(
    nn.Linear(len(tabular_cols), 128),
    nn.ReLU(),
    nn.Linear(128, 64),
    nn.ReLU(),
    nn.Linear(64, 1),
).to(device)
opt_tab = torch.optim.Adam(tab_model.parameters(), lr=3e-3)
for _ in range(15):
    for _, _, tab, d, _ in train_loader:
        tab, d = tab.to(device), d.to(device)
        opt_tab.zero_grad()
        loss = criterion(torch.relu(tab_model(tab)), d)
        loss.backward()
        opt_tab.step()

tab_model.eval()
tab_preds = []
with torch.no_grad():
    for _, _, tab, _, _ in test_loader:
        tab = tab.to(device)
        tab_preds.extend(torch.relu(tab_model(tab)).cpu().numpy().flatten())
b1_metrics = compute_metrics(np.array(all_y_true), np.array(tab_preds))
logger.info("Baseline 1 (Tabular Only) Metrics: {}", b1_metrics)

# Baseline 2: Text + Tabular
class TextTabModel(nn.Module):
    def __init__(self, tab_dim=8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(384 + tab_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )
    def forward(self, t, tab):
        return torch.relu(self.fc(torch.cat([t, tab], dim=-1)))

tt_model = TextTabModel().to(device)
opt_tt = torch.optim.Adam(tt_model.parameters(), lr=3e-3)
for _ in range(15):
    for _, t, tab, d, _ in train_loader:
        t, tab, d = t.to(device), tab.to(device), d.to(device)
        opt_tt.zero_grad()
        loss = criterion(tt_model(t, tab), d)
        loss.backward()
        opt_tt.step()

tt_model.eval()
tt_preds = []
with torch.no_grad():
    for _, t, tab, _, _ in test_loader:
        t, tab = t.to(device), tab.to(device)
        tt_preds.extend(tt_model(t, tab).cpu().numpy().flatten())
b2_metrics = compute_metrics(np.array(all_y_true), np.array(tt_preds))
logger.info("Baseline 2 (Text + Tabular) Metrics: {}", b2_metrics)

# Baseline 3: Vision + Tabular
class VisTabModel(nn.Module):
    def __init__(self, tab_dim=8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(512 + tab_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )
    def forward(self, v, tab):
        return torch.relu(self.fc(torch.cat([v, tab], dim=-1)))

vt_model = VisTabModel().to(device)
opt_vt = torch.optim.Adam(vt_model.parameters(), lr=3e-3)
for _ in range(15):
    for v, _, tab, d, _ in train_loader:
        v, tab, d = v.to(device), tab.to(device), d.to(device)
        opt_vt.zero_grad()
        loss = criterion(vt_model(v, tab), d)
        loss.backward()
        opt_vt.step()

vt_model.eval()
vt_preds = []
with torch.no_grad():
    for v, _, tab, _, _ in test_loader:
        v, tab = v.to(device), tab.to(device)
        vt_preds.extend(vt_model(v, tab).cpu().numpy().flatten())
b3_metrics = compute_metrics(np.array(all_y_true), np.array(vt_preds))
logger.info("Baseline 3 (Vision + Tabular) Metrics: {}", b3_metrics)

# ─────────────────────────────────────────────────────────────────────────────
# 7. FINANCIAL OPTIMIZATION EVALUATION ON REAL TEST SKUs
# ─────────────────────────────────────────────────────────────────────────────
test_df = df.iloc[test_idx].copy().reset_index(drop=True)
static_revenues = []
opt_revenues = []
opt_prices = []

# Sweep 40 prices around competitor price
sweep_factors = np.linspace(0.85, 1.25, 40)
for idx_in_test in range(len(test_df)):
    row = test_df.iloc[idx_in_test]
    cost = row["production_cost"]
    msrp = row["msrp"]
    comp_p = row["competitor_avg_price"]

    # Baseline Static Revenue
    static_rev = row["offered_price"] * all_y_true[idx_in_test]
    static_revenues.append(static_rev)

    # Search best price
    best_p = comp_p
    best_profit = -1e9
    best_rev = static_rev

    v_t = torch.tensor(vision_embeddings[test_idx[idx_in_test]], dtype=torch.float32).unsqueeze(0).to(device)
    t_t = torch.tensor(text_embeddings[test_idx[idx_in_test]], dtype=torch.float32).unsqueeze(0).to(device)

    for factor in sweep_factors:
        cand_p = round(float(comp_p * factor), 2)
        ratio = cand_p / comp_p
        raw_tab = [cand_p, cost, msrp, row["competitor_min_price"], comp_p, ratio, row["inventory_count"], row["customer_rating"]]
        scaled_tab = (np.array(raw_tab) - scaler.mean_) / scaler.scale_
        tab_t = torch.tensor(scaled_tab, dtype=torch.float32).unsqueeze(0).to(device)

        with torch.no_grad():
            q_est = model(v_t, t_t, tab_t)[0].item()

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

logger.info("Saved evaluation JSON to: {}", METRICS_JSON_PATH)

# ─────────────────────────────────────────────────────────────────────────────
# 8. GENERATE PUBLICATION PLOTS
# ─────────────────────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="deep")

# Plot 1: Ablation comparison
models_labels = ["Tabular Only", "Vision + Tab", "Text + Tab", "Proposed Multimodal"]
r2_vals = [b1_metrics["R2_Score"], b3_metrics["R2_Score"], b2_metrics["R2_Score"], prop_metrics["R2_Score"]]
mape_vals = [b1_metrics["MAPE_pct"], b3_metrics["MAPE_pct"], b2_metrics["MAPE_pct"], prop_metrics["MAPE_pct"]]
colors = ["#94a3b8", "#38bdf8", "#818cf8", "#10b981"]

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
bars1 = axes[0].bar(models_labels, r2_vals, color=colors, edgecolor="black", linewidth=0.8)
axes[0].set_title("Explanatory Power (R² Score) on Real Flipkart Test SKUs", fontsize=12, fontweight="bold")
axes[0].set_ylabel("R² Score (Higher is Better)", fontsize=11)
axes[0].set_ylim(0, 1.05)
for bar in bars1:
    y = bar.get_height()
    axes[0].text(bar.get_x() + bar.get_width()/2, y + 0.02, f"{y:.4f}", ha='center', va='bottom', fontweight='bold', fontsize=10)

bars2 = axes[1].bar(models_labels, mape_vals, color=colors, edgecolor="black", linewidth=0.8)
axes[1].set_title("Mean Absolute Percentage Error (MAPE %)", fontsize=12, fontweight="bold")
axes[1].set_ylabel("MAPE % (Lower is Better)", fontsize=11)
for bar in bars2:
    y = bar.get_height()
    axes[1].text(bar.get_x() + bar.get_width()/2, y + 0.5, f"{y:.2f}%", ha='center', va='bottom', fontweight='bold', fontsize=10)

plt.tight_layout()
ablation_plot_path = DATA_DIR / "ablation_comparison_plot.png"
fig.savefig(ablation_plot_path, dpi=200)
plt.close(fig)

# Plot 2: Scatter parity
fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(all_y_true, all_y_pred, alpha=0.6, color="#2563eb", edgecolors="w", s=45, label="Test Products (Real SKUs)")
max_v = max(max(all_y_true), max(all_y_pred))
ax.plot([0, max_v], [0, max_v], "r--", linewidth=2, label="Perfect 1:1 Prediction Parity")
ax.set_title("Actual vs. Predicted Unit Demand on Real Flipkart Test Products", fontsize=12, fontweight="bold")
ax.set_xlabel("Ground Truth Demand Volume", fontsize=11)
ax.set_ylabel("Multimodal Deep Learning Predicted Demand", fontsize=11)
ax.legend(loc="upper left")
plt.tight_layout()
scatter_plot_path = DATA_DIR / "actual_vs_predicted_scatter.png"
fig.savefig(scatter_plot_path, dpi=200)
plt.close(fig)

logger.info("Training and evaluation on real Flipkart dataset completed successfully!")
