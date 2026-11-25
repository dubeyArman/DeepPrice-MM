"""
fast_evaluate.py
================
Ultra-fast evaluation & ablation runner:
1. Loads the already trained `best_multimodal_pricing_model.pth`.
2. Caches vision features across the 1200 images once in memory (takes ~20 seconds).
3. Trains the 3 ablation baselines (Tabular-only, Text+Tabular, Vision+Tabular) in ~10 seconds.
4. Performs full scientific evaluation on the 180 independent test SKUs.
5. Runs the dynamic pricing revenue lift simulation.
6. Outputs `ablation_evaluation_results.json` and renders publication-ready comparison charts.
"""

import os
import sys
import json
import math
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image

import torch
import torch.nn as nn
from torchvision import transforms, models
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "ecommerce_multimodal_pricing_dataset.csv"
MODEL_PATH = BASE_DIR / "models" / "best_multimodal_pricing_model.pth"
METRICS_JSON_PATH = DATA_DIR / "ablation_evaluation_results.json"

sys.path.insert(0, str(BASE_DIR))
from models.multimodal_pricing_net import (
    MultimodalPricingNet,
    TabularOnlyBaseline,
    TextTabularBaseline,
    VisionTabularBaseline,
)

image_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

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

def run_fast_eval():
    start_time = time.time()
    logger.info("=================================================================")
    logger.info("  Fast Evaluation & Dynamic Pricing Revenue Lift Benchmark       ")
    logger.info("=================================================================")

    df = pd.read_csv(CSV_PATH)
    logger.info("Loaded {} product records.", len(df))

    # Load text embeddings cache
    text_embeddings = np.load(DATA_DIR / "text_embeddings_cache.npy")

    # Tabular scaling
    tabular_cols = [
        "offered_price", "production_cost", "msrp", "competitor_min_price",
        "competitor_avg_price", "price_ratio_to_competitor", "inventory_count",
        "customer_rating"
    ]
    mean_scaler = np.load(DATA_DIR / "scaler_mean.npy")
    scale_scaler = np.load(DATA_DIR / "scaler_scale.npy")
    raw_tabs = df[tabular_cols].values
    tabular_scaled = (raw_tabs - mean_scaler) / scale_scaler

    # Splits
    train_idx, test_idx = train_test_split(np.arange(len(df)), test_size=0.15, random_state=42, stratify=df["category"])
    train_idx, val_idx = train_test_split(train_idx, test_size=0.1765, random_state=42)

    logger.info("Splits: Train={} | Validation={} | Test={}", len(train_idx), len(val_idx), len(test_idx))

    device = torch.device("cpu")

    # Load trained multimodal network
    logger.info("Loading pre-trained multimodal weights: {}", MODEL_PATH)
    model = MultimodalPricingNet(tabular_dim=len(tabular_cols), embed_dim=128, pretrained_vision=False)
    model.load_state_dict(torch.load(MODEL_PATH, weights_only=True, map_location=device))
    model.eval()

    # Pre-extract vision embeddings for all 1200 images using the trained vision branch
    vision_cache_path = DATA_DIR / "vision_embeddings_cache.npy"
    if vision_cache_path.exists():
        logger.info("Loading cached vision embeddings from: {}", vision_cache_path)
        vision_embeddings = np.load(vision_cache_path)
    else:
        logger.info("Extracting vision features across all 1200 images (takes ~25s) ...")
        v_list = []
        with torch.no_grad():
            for i in range(len(df)):
                img_path = BASE_DIR / df.iloc[i]["image_relative_path"]
                try:
                    img = Image.open(img_path).convert("RGB")
                except:
                    img = Image.new("RGB", (224, 224), color=(200, 200, 200))
                t_img = image_transform(img).unsqueeze(0)
                v_feat = model.vision_extractor(t_img).view(1, 512)
                v_list.append(v_feat.numpy().flatten())
        vision_embeddings = np.array(v_list)
        np.save(vision_cache_path, vision_embeddings)
        logger.info("Saved vision embeddings cache to: {}", vision_cache_path)

    # Convert to PyTorch tensors
    X_train_tab = torch.tensor(tabular_scaled[train_idx], dtype=torch.float32)
    X_train_txt = torch.tensor(text_embeddings[train_idx], dtype=torch.float32)
    X_train_vis = torch.tensor(vision_embeddings[train_idx], dtype=torch.float32)
    y_train = torch.tensor(df["ground_truth_demand"].values[train_idx], dtype=torch.float32).unsqueeze(1)

    X_test_tab = torch.tensor(tabular_scaled[test_idx], dtype=torch.float32)
    X_test_txt = torch.tensor(text_embeddings[test_idx], dtype=torch.float32)
    X_test_vis = torch.tensor(vision_embeddings[test_idx], dtype=torch.float32)
    y_test = df["ground_truth_demand"].values[test_idx]

    # ─────────────────────────────────────────────────────────────────────────
    # Fast Ablation Baselines
    # ─────────────────────────────────────────────────────────────────────────
    logger.info("--- Fast Fitting Ablation Baselines ---")

    # Baseline 1: Tabular Only
    b1_model = TabularOnlyBaseline(tabular_dim=len(tabular_cols))
    b1_opt = torch.optim.Adam(b1_model.parameters(), lr=0.01)
    for _ in range(80):
        b1_opt.zero_grad()
        loss = nn.MSELoss()(b1_model(X_train_tab), y_train)
        loss.backward()
        b1_opt.step()

    # Baseline 2: Text + Tabular
    b2_model = TextTabularBaseline(tabular_dim=len(tabular_cols))
    b2_opt = torch.optim.Adam(b2_model.parameters(), lr=0.005)
    for _ in range(80):
        b2_opt.zero_grad()
        loss = nn.MSELoss()(b2_model(X_train_txt, X_train_tab), y_train)
        loss.backward()
        b2_opt.step()

    # Baseline 3: Vision + Tabular (using extracted vision features)
    class FastVisionTabular(nn.Module):
        def __init__(self, tab_dim):
            super().__init__()
            self.v_proj = nn.Linear(512, 128)
            self.t_proj = nn.Linear(tab_dim, 128)
            self.fc = nn.Sequential(nn.Linear(256, 128), nn.ReLU(), nn.Linear(128, 1))
        def forward(self, v, tab):
            hv = torch.relu(self.v_proj(v))
            ht = torch.relu(self.t_proj(tab))
            return torch.relu(self.fc(torch.cat([hv, ht], dim=-1)))

    b3_model = FastVisionTabular(tab_dim=len(tabular_cols))
    b3_opt = torch.optim.Adam(b3_model.parameters(), lr=0.005)
    for _ in range(80):
        b3_opt.zero_grad()
        loss = nn.MSELoss()(b3_model(X_train_vis, X_train_tab), y_train)
        loss.backward()
        b3_opt.step()

    # Evaluate on Test Set
    b1_model.eval()
    b2_model.eval()
    b3_model.eval()

    with torch.no_grad():
        pred_b1 = b1_model(X_test_tab).numpy().flatten()
        pred_b2 = b2_model(X_test_txt, X_test_tab).numpy().flatten()
        pred_b3 = b3_model(X_test_vis, X_test_tab).numpy().flatten()

        # Proposed Multimodal Net inference
        # Modalities forward through projection + attention
        h_v = model.vision_proj(X_test_vis)
        h_t = model.text_proj(X_test_txt)
        h_tab = model.tabular_encoder(X_test_tab)
        modalities = torch.stack([h_v, h_t, h_tab], dim=1)
        attn_out, _ = model.modality_attention(modalities, modalities, modalities)
        fused = model.fusion_norm(modalities + attn_out).reshape(len(X_test_tab), -1)
        shared = model.shared_fc(fused)
        pred_proposed = torch.relu(model.demand_head(shared)).numpy().flatten()
        pred_peds = (-torch.nn.functional.softplus(model.elasticity_head(shared))).numpy().flatten()

    metrics_b1 = compute_metrics(y_test, pred_b1)
    metrics_b2 = compute_metrics(y_test, pred_b2)
    metrics_b3 = compute_metrics(y_test, pred_b3)
    metrics_proposed = compute_metrics(y_test, pred_proposed)

    logger.info("=================================================================")
    logger.info("  ABLATION STUDY RESULTS (Independent Test Set):                 ")
    logger.info("  1. Baseline (Tabular Only):      R²={:.4f} | RMSE={:.2f} | MAPE={:.2f}%", metrics_b1["R2_Score"], metrics_b1["RMSE"], metrics_b1["MAPE_pct"])
    logger.info("  2. NLP Text + Tabular:           R²={:.4f} | RMSE={:.2f} | MAPE={:.2f}%", metrics_b2["R2_Score"], metrics_b2["RMSE"], metrics_b2["MAPE_pct"])
    logger.info("  3. Vision ResNet + Tabular:      R²={:.4f} | RMSE={:.2f} | MAPE={:.2f}%", metrics_b3["R2_Score"], metrics_b3["RMSE"], metrics_b3["MAPE_pct"])
    logger.info("  4. Proposed Multimodal Attention:R²={:.4f} | RMSE={:.2f} | MAPE={:.2f}%", metrics_proposed["R2_Score"], metrics_proposed["RMSE"], metrics_proposed["MAPE_pct"])
    logger.info("=================================================================")

    # ─────────────────────────────────────────────────────────────────────────
    # Dynamic Pricing Revenue Lift Simulation
    # ─────────────────────────────────────────────────────────────────────────
    test_df = df.iloc[test_idx].reset_index(drop=True)
    static_revenues = []
    optimized_revenues = []
    optimal_prices = []

    candidate_multipliers = np.linspace(0.85, 1.25, 21)

    for i in range(len(test_df)):
        row = test_df.iloc[i]
        cost = row["production_cost"]
        msrp = row["msrp"]
        comp_min = row["competitor_min_price"]
        comp_avg = row["competitor_avg_price"]
        inv = row["inventory_count"]
        rat = row["customer_rating"]

        static_p = msrp
        static_q = y_test[i]
        static_revenues.append(static_p * static_q)

        # Evaluate candidate prices
        cand_tabs = []
        cand_prices = []
        for m in candidate_multipliers:
            cand_p = round(msrp * m, 2)
            p_ratio = round(cand_p / comp_min, 3)
            raw_tab = np.array([cand_p, cost, msrp, comp_min, comp_avg, p_ratio, inv, rat])
            scaled_tab = (raw_tab - mean_scaler) / scale_scaler
            cand_tabs.append(scaled_tab)
            cand_prices.append(cand_p)

        cand_tabs_tensor = torch.tensor(np.array(cand_tabs), dtype=torch.float32)
        v_rep = X_test_vis[i].repeat(len(candidate_multipliers), 1)
        t_rep = X_test_txt[i].repeat(len(candidate_multipliers), 1)

        with torch.no_grad():
            hv_rep = model.vision_proj(v_rep)
            ht_rep = model.text_proj(t_rep)
            htab_rep = model.tabular_encoder(cand_tabs_tensor)
            mods = torch.stack([hv_rep, ht_rep, htab_rep], dim=1)
            a_out, _ = model.modality_attention(mods, mods, mods)
            f_rep = model.fusion_norm(mods + a_out).reshape(len(cand_tabs), -1)
            sh_rep = model.shared_fc(f_rep)
            exp_demands = torch.relu(model.demand_head(sh_rep)).numpy().flatten()

        best_cand_p = msrp
        max_profit = -float("inf")
        for cp, eq in zip(cand_prices, exp_demands):
            prof = (cp - cost) * eq
            if prof > max_profit:
                max_profit = prof
                best_cand_p = cp

        optimal_prices.append(best_cand_p)
        price_ratio = best_cand_p / static_p
        ped = pred_peds[i]
        opt_demand = max(0, static_q * (1.0 + ped * (price_ratio - 1.0)))
        optimized_revenues.append(best_cand_p * opt_demand)

    total_static_rev = float(np.sum(static_revenues))
    total_opt_rev = float(np.sum(optimized_revenues))
    lift_pct = float(((total_opt_rev - total_static_rev) / total_static_rev) * 100)

    logger.success("=================================================================")
    logger.success("  DYNAMIC PRICING PERFORMANCE:                                   ")
    logger.success("  • Total Static Revenue:       ₹{:,.2f}", total_static_rev)
    logger.success("  • Total Multimodal Revenue:   ₹{:,.2f}", total_opt_rev)
    logger.success("  • NET REVENUE LIFT:           +{:.2f}%", lift_pct)
    logger.success("=================================================================")

    # Save metrics JSON
    results_payload = {
        "dataset_size": len(df),
        "test_size": len(test_df),
        "metrics": {
            "proposed_multimodal": metrics_proposed,
            "baseline_tabular_only": metrics_b1,
            "baseline_text_tabular": metrics_b2,
            "baseline_vision_tabular": metrics_b3,
        },
        "revenue_optimization": {
            "static_total_revenue_inr": round(total_static_rev, 2),
            "optimized_total_revenue_inr": round(total_opt_rev, 2),
            "revenue_lift_pct": round(lift_pct, 2),
            "average_recommended_price": round(float(np.mean(optimal_prices)), 2),
            "average_msrp": round(float(test_df["msrp"].mean()), 2),
        }
    }

    with open(METRICS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    # Publication-ready plots
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    models_labels = ["Tabular Only", "Text + Tab", "Vision + Tab", "Multimodal (Ours)"]
    r2_scores = [metrics_b1["R2_Score"], metrics_b2["R2_Score"], metrics_b3["R2_Score"], metrics_proposed["R2_Score"]]
    rmse_scores = [metrics_b1["RMSE"], metrics_b2["RMSE"], metrics_b3["RMSE"], metrics_proposed["RMSE"]]

    x = np.arange(len(models_labels))
    width = 0.35

    ax1 = axes[0]
    bars1 = ax1.bar(x - width/2, r2_scores, width, label='R² Score (Higher is better)', color='#3b82f6')
    ax1.set_ylabel('R² Score', color='#1e3a8a', fontweight='bold')
    ax1.set_title('Ablation Study: Demand Prediction R² Score', fontweight='bold', fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(models_labels, rotation=15)
    ax1.set_ylim(0, 1.0)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, yval + 0.02, f"{yval:.3f}", ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax2 = axes[1]
    bars2 = ax2.bar(x + width/2, rmse_scores, width, label='RMSE (Lower is better)', color='#ef4444')
    ax2.set_ylabel('Root Mean Squared Error (Units)', color='#991b1b', fontweight='bold')
    ax2.set_title('Ablation Study: Prediction Error (RMSE)', fontweight='bold', fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(models_labels, rotation=15)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, yval + 5, f"{int(yval)}", ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    chart_path = DATA_DIR / "ablation_comparison_plot.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()

    # Actual vs Predicted scatter
    plt.figure(figsize=(7, 6))
    plt.scatter(y_test, pred_proposed, alpha=0.65, color="#2563eb", s=35, label="Test SKU Observations")
    max_val = max(np.max(y_test), np.max(pred_proposed))
    plt.plot([0, max_val], [0, max_val], 'r--', lw=2, label=f"Fit (R² = {metrics_proposed['R2_Score']:.3f})")
    plt.xlabel("Actual Ground Truth Demand (Units Sold)", fontweight='bold')
    plt.ylabel("Multimodal Model Predicted Demand (Units)", fontweight='bold')
    plt.title("Multimodal Attention: Actual vs Predicted Demand", fontweight='bold', fontsize=12)
    plt.legend()
    plt.tight_layout()
    scatter_path = DATA_DIR / "actual_vs_predicted_scatter.png"
    plt.savefig(scatter_path, dpi=300)
    plt.close()

    elapsed = round(time.time() - start_time, 1)
    logger.success("Fast Evaluation finished in {} seconds! All charts and metrics exported.", elapsed)

if __name__ == "__main__":
    run_fast_eval()
