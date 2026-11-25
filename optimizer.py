import sys
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from PIL import Image
from torchvision import transforms, models
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_PATH = BASE_DIR / "models" / "best_multimodal_pricing_model.pth"

image_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


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


class MultimodalPriceOptimizer:
    def __init__(self):
        self.device = torch.device("cpu")
        print("Loading Sentence-BERT all-MiniLM-L6-v2...")
        self.st_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Load ResNet-18 extractor
        print("Loading ResNet-18 vision extractor...")
        resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.vision_extractor = nn.Sequential(*list(resnet.children())[:-1]).eval()

        # Load tabular and demand scalers
        self.mean_scaler = np.load(DATA_DIR / "scaler_mean.npy")
        self.scale_scaler = np.load(DATA_DIR / "scaler_scale.npy")
        self.demand_mean = float(np.load(DATA_DIR / "demand_scaler_mean.npy")[0])
        self.demand_scale = float(np.load(DATA_DIR / "demand_scaler_scale.npy")[0])

        # Load trained Multimodal Net
        print("Loading trained MultimodalPricingNet checkpoint...")
        self.model = FastMultimodalNet(tab_dim=8, embed_dim=128)
        self.model.load_state_dict(torch.load(MODEL_PATH, weights_only=True, map_location=self.device))
        self.model.eval()
        print("MultimodalPriceOptimizer initialized successfully!")

    def optimize(
        self,
        image: Image.Image,
        title: str,
        description: str,
        cost: float,
        msrp: float,
        comp_min: float,
        comp_avg: float,
        inventory: int = 150,
        rating: float = 4.3,
        num_candidates: int = 35,
    ) -> dict:
        # 1. Process Image
        img_tensor = image_transform(image.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            v_feat = self.vision_extractor(img_tensor).view(1, 512)

        # 2. Process Text
        text_full = f"{title} - {description}"
        txt_emb = self.st_model.encode([text_full], normalize_embeddings=True)
        txt_tensor = torch.tensor(txt_emb, dtype=torch.float32)

        # 3. Anchor Multimodal Neural Inference at Reference Market Price
        # Evaluate the trained PyTorch Multimodal Cross-Attention Network within its
        # calibrated distribution to extract base demand Q_NN and modality attention weights.
        p_ref = max(comp_avg, cost * 1.15, 1.0)
        ref_ratio = p_ref / max(1.0, comp_avg)
        raw_ref_tab = np.array([p_ref, cost, msrp, comp_min, comp_avg, ref_ratio, inventory, rating])
        scaled_ref_tab = (raw_ref_tab - self.mean_scaler) / self.scale_scaler
        ref_tab_tensor = torch.tensor(scaled_ref_tab, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            pred_scaled_ref, attn_weights = self.model(v_feat, txt_tensor, ref_tab_tensor)
            q_base = float(max(50.0, pred_scaled_ref.item() * self.demand_scale + self.demand_mean))

        # Modality attention weights [Visual, Text, Tabular]
        avg_attn = attn_weights.mean(dim=0).mean(dim=0).numpy()
        total_attn = float(np.sum(avg_attn))
        vis_w = float(avg_attn[0] / total_attn)
        txt_w = float(avg_attn[1] / total_attn)
        tab_w = float(avg_attn[2] / total_attn)
        attn_pcts = {
            "visual_aesthetic_weight": round(vis_w * 100, 1),
            "text_specifications_weight": round(txt_w * 100, 1),
            "pricing_tabular_weight": round(tab_w * 100, 1),
        }

        # 4. Economics-Constrained Monotonic Elasticity Layer (Guarantees Law of Demand: dQ/dp < 0)
        # Combines market base elasticity (2.85) with customer rating and multimodal quality share
        # so higher-rated / visually-strong products command higher pricing power.
        vis_txt_share = vis_w + txt_w
        beta = float(np.clip(2.85 - 0.45 * (rating - 4.0) - 0.50 * (vis_txt_share - 0.50), 1.80, 4.20))

        # Analytical sweet spot p* = cost + p_ref / beta; frame candidate grid around it
        est_opt_p = cost + (p_ref / beta)
        min_p = max(cost * 1.05, min(comp_avg * 0.75, est_opt_p * 0.70))
        max_p = max(msrp * 1.25, comp_avg * 1.35, est_opt_p * 1.45, min_p * 1.60)
        candidate_prices = np.linspace(min_p, max_p, num_candidates)

        # Strictly monotonic exponential demand curve anchored to the neural network's base demand
        pred_demands = np.maximum(
            10.0,
            q_base * np.exp(-beta * ((candidate_prices - p_ref) / p_ref)),
        )

        # Pricing curve and optimal search
        curve_data = []
        best_profit = -1e9
        best_p_profit = comp_avg
        best_q_profit = 100.0
        best_rev = 0.0
        best_p_rev = comp_avg

        for i, (cp, q) in enumerate(zip(candidate_prices, pred_demands)):
            rev = cp * q
            prof = (cp - cost) * q
            
            # Estimate local PED elasticity
            if i > 0:
                dq = q - pred_demands[i - 1]
                dp = cp - candidate_prices[i - 1]
                ped = (dq / max(1.0, q)) / (dp / cp)
            else:
                ped = -1.25

            if prof > best_profit:
                best_profit = prof
                best_p_profit = cp
                best_q_profit = q

            if rev > best_rev:
                best_rev = rev
                best_p_rev = cp

            curve_data.append({
                "candidate_price": round(float(cp), 2),
                "expected_demand": round(float(q), 1),
                "expected_revenue": round(float(rev), 2),
                "expected_profit": round(float(prof), 2),
                "elasticity_ped": round(float(np.clip(ped, -4.0, -0.1)), 2),
            })

        # Baseline: selling at competitor price
        comp_q = float(max(10.0, q_base * np.exp(-beta * ((comp_avg - p_ref) / p_ref))))
        static_rev = comp_avg * comp_q
        static_profit = (comp_avg - cost) * comp_q

        rev_lift = ((best_rev - static_rev) / static_rev * 100) if static_rev > 0 else 0.0
        profit_lift = ((best_profit - static_profit) / static_profit * 100) if static_profit > 0 else 0.0

        return {
            "recommended_optimal_price": round(float(best_p_profit), 2),
            "revenue_maximizing_price": round(float(best_p_rev), 2),
            "current_msrp": round(float(msrp), 2),
            "production_cost": round(float(cost), 2),
            "competitor_min_price": round(float(comp_min), 2),
            "competitor_avg_price": round(float(comp_avg), 2),
            "expected_demand_at_optimal": round(float(best_q_profit), 1),
            "static_revenue": round(float(static_rev), 2),
            "optimized_revenue": round(float(best_rev), 2),
            "revenue_lift_pct": round(float(rev_lift), 2),
            "profit_lift_pct": round(float(profit_lift), 2),
            "multimodal_attention_weights": attn_pcts,
            "pricing_curve": curve_data,
        }
