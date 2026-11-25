import time
import math
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "flipkart_ecommerce_real_dataset.csv"
TEXT_CACHE_PATH = DATA_DIR / "real_text_embeddings_cache.npy"
VISION_CACHE_PATH = DATA_DIR / "real_vision_embeddings_cache.npy"
DEMO_MODEL_PATH = BASE_DIR / "models" / "demo_live_trained_model.pth"


class ScaledDataset(Dataset):
    def __init__(self, vision, text, tab, y_scaled, raw_y, idxs):
        self.v = torch.tensor(vision[idxs], dtype=torch.float32)
        self.t = torch.tensor(text[idxs], dtype=torch.float32)
        self.tab = torch.tensor(tab[idxs], dtype=torch.float32)
        self.y = torch.tensor(y_scaled[idxs], dtype=torch.float32).unsqueeze(1)
        self.raw_y = raw_y[idxs]

    def __len__(self):
        return len(self.v)

    def __getitem__(self, i):
        return self.v[i], self.t[i], self.tab[i], self.y[i]


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


def main():
    t0 = time.time()
    torch.manual_seed(42)
    np.random.seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("=" * 78)
    print("   DEEPPRICE-MM : LIVE PYTORCH MULTIMODAL MODEL TRAINING DEMONSTRATION")
    print("=" * 78)
    print(f" Hardware Device      : {str(device).upper()}")
    print(f" Dataset File         : {CSV_PATH.name}")

    # 1. Load Data & Pre-extracted ResNet-18 + Sentence-BERT Embeddings
    df = pd.read_csv(CSV_PATH)
    text_embeddings = np.load(TEXT_CACHE_PATH)
    vision_embeddings = np.load(VISION_CACHE_PATH)

    print(f" Total Curated SKUs   : {len(df)} products across {df['category'].nunique()} categories")
    print(f" Vision Embeddings    : ResNet-18 shape {vision_embeddings.shape} (512-d per image)")
    print(f" Text Embeddings      : Sentence-BERT shape {text_embeddings.shape} (384-d per description)")

    # 2. Standardize Tabular Features & Demand Target
    tabular_cols = [
        "offered_price", "production_cost", "msrp", "competitor_min_price",
        "competitor_avg_price", "price_ratio_to_competitor", "inventory_count",
        "customer_rating"
    ]
    tab_scaler = StandardScaler()
    tabular_scaled = tab_scaler.fit_transform(df[tabular_cols].values)

    raw_demand = df["ground_truth_demand"].values
    demand_scaler = StandardScaler()
    demand_scaled = demand_scaler.fit_transform(raw_demand.reshape(-1, 1)).flatten()

    # 3. Stratified 70 / 15 / 15 Split
    train_idx, test_idx = train_test_split(
        np.arange(len(df)), test_size=0.15, random_state=42, stratify=df["category"]
    )
    train_idx, val_idx = train_test_split(train_idx, test_size=0.1765, random_state=42)
    print(f" Stratified Split     : Train={len(train_idx)} (70%) | Val={len(val_idx)} (15%) | Unseen Test={len(test_idx)} (15%)")

    train_loader = DataLoader(ScaledDataset(vision_embeddings, text_embeddings, tabular_scaled, demand_scaled, raw_demand, train_idx), batch_size=32, shuffle=True)
    val_loader = DataLoader(ScaledDataset(vision_embeddings, text_embeddings, tabular_scaled, demand_scaled, raw_demand, val_idx), batch_size=32, shuffle=False)
    test_ds = ScaledDataset(vision_embeddings, text_embeddings, tabular_scaled, demand_scaled, raw_demand, test_idx)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)

    # 4. Initialize PyTorch Cross-Attention Model
    model = FastMultimodalNet(tab_dim=len(tabular_cols)).to(device)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f" Neural Architecture  : FastMultimodalNet (4-Head Cross-Attention Fusion)")
    print(f" Trainable Parameters : {total_params:,} PyTorch weights")
    print(f" Optimizer & Loss     : AdamW (lr=0.001, weight_decay=1e-4) | MSELoss")
    print("-" * 78)
    print(f"{'Epoch':<10} | {'Train MSE Loss':<16} | {'Validation MSE':<16} | {'Checkpoint Status'}")
    print("-" * 78)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.MSELoss()

    epochs = 20
    best_val_loss = float("inf")
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss_sum = 0.0
        for v, t, tab, y in train_loader:
            v, t, tab, y = v.to(device), t.to(device), tab.to(device), y.to(device)
            optimizer.zero_grad()
            pred, _ = model(v, t, tab)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            train_loss_sum += loss.item()
        avg_train_loss = train_loss_sum / len(train_loader)

        model.eval()
        val_loss_sum = 0.0
        with torch.no_grad():
            for v, t, tab, y in val_loader:
                v, t, tab, y = v.to(device), t.to(device), tab.to(device), y.to(device)
                pred, _ = model(v, t, tab)
                val_loss_sum += criterion(pred, y).item()
        avg_val_loss = val_loss_sum / len(val_loader)

        status = ""
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), DEMO_MODEL_PATH)
            status = "★ Saved Best Checkpoint"

        print(f"Epoch {epoch:02d}/{epochs} | {avg_train_loss:<16.4f} | {avg_val_loss:<16.4f} | {status}")

    # 5. Live Evaluation on 180 Unseen Test Products
    model.load_state_dict(torch.load(DEMO_MODEL_PATH, weights_only=True, map_location=device))
    model.eval()
    preds_scaled = []
    with torch.no_grad():
        for v, t, tab, _ in test_loader:
            v, t, tab = v.to(device), t.to(device), tab.to(device)
            pred, _ = model(v, t, tab)
            preds_scaled.extend(pred.cpu().numpy().flatten())

    y_true = test_ds.raw_y
    y_pred = np.maximum(10.0, demand_scaler.inverse_transform(np.array(preds_scaled).reshape(-1, 1)).flatten())

    r2 = r2_score(y_true, y_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(1.0, y_true))) * 100)
    accuracy = 100.0 - mape

    elapsed = time.time() - t0
    print("=" * 78)
    print(f" LIVE TRAINING COMPLETE IN {elapsed:.2f} SECONDS!")
    print("-" * 78)
    print(f" Unseen Test Set (180 SKUs) Evaluation Results:")
    print(f"   * Prediction Accuracy (100% - MAPE) : {accuracy:.2f}%")
    print(f"   * MAPE Percentage Error             : {mape:.2f}%")
    print(f"   * MAE (Mean Absolute Error)         : {mae:.2f} units")
    print(f"   * R^2 Explanatory Score             : {r2:.4f}")
    print(f"   * RMSE                              : {rmse:.2f} units")
    print(f"   * Saved Demo Weights                : {DEMO_MODEL_PATH.name}")
    print("=" * 78)


if __name__ == "__main__":
    main()
