import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from torchvision import transforms


class MultimodalPricingNet(nn.Module):
    def __init__(
        self,
        tabular_dim: int = 8,
        embed_dim: int = 128,
        num_heads: int = 4,
        dropout_p: float = 0.15,
        pretrained_vision: bool = True,
    ):
        super().__init__()
        self.embed_dim = embed_dim

        # ── (ResNet-18) ──    ####
        # Using ResNet-18 as vision feature extractor
        resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained_vision else None)
        # Remove final FC classification layer
        self.vision_extractor = nn.Sequential(*list(resnet.children())[:-1]) # Output: (B, 512, 1, 1)
        self.vision_proj = nn.Sequential(
            nn.Linear(512, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
            nn.Dropout(dropout_p),
        )

       
        # Input: 384-dimensional dense sentence embeddings from all-MiniLM-L6-v2
        self.text_proj = nn.Sequential(
            nn.Linear(384, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
            nn.Dropout(dropout_p),
        )

        # ── 3. TABULAR ECONOMETRIC MLP ──
        self.tabular_encoder = nn.Sequential(
            nn.Linear(tabular_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(dropout_p),
            nn.Linear(64, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.ReLU(),
        )

        # ── 4. CROSS-MODAL ATTENTION FUSION ──
        # Modalities form a sequence of length 3: [Vision, Text, Tabular]
        self.modality_attention = nn.MultiheadAttention(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dropout=dropout_p,
            batch_first=True,
        )
        self.fusion_norm = nn.LayerNorm(embed_dim)

        # ── 5. PREDICTION HEADS ──
        # Fused vector is pooled across the 3 modalities (size: embed_dim)
        self.shared_fc = nn.Sequential(
            nn.Linear(embed_dim * 3, 256),
            nn.ReLU(),
            nn.Dropout(dropout_p),
            nn.Linear(256, 128),
            nn.ReLU(),
        )

        # Head A: Demand Prediction Head Q_hat >= 0
        self.demand_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

        # Head B: Theoretical Price Elasticity of Demand (PED) Head
        self.elasticity_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, images, text_embeddings, tabular_features):
        """
        Args:
            images: Tensor (Batch, 3, 224, 224)
            text_embeddings: Tensor (Batch, 384)
            tabular_features: Tensor (Batch, tabular_dim)
        Returns:
            demand_pred: Tensor (Batch, 1)
            elasticity_pred: Tensor (Batch, 1)
            attention_weights: Tensor (Batch, 3, 3)
        """
        B = images.size(0)

        # 1. Vision Forward
        v_feats = self.vision_extractor(images) # (B, 512, 1, 1)
        v_feats = v_feats.view(B, 512)
        h_v = self.vision_proj(v_feats) # (B, embed_dim)

        # 2. Text Forward
        h_t = self.text_proj(text_embeddings) # (B, embed_dim)

        # 3. Tabular Forward
        h_tab = self.tabular_encoder(tabular_features) # (B, embed_dim)

        # 4. Modality Sequence: shape (B, 3, embed_dim)
        modalities = torch.stack([h_v, h_t, h_tab], dim=1)

        # Multi-Head Self-Attention across modalities
        attn_out, attn_weights = self.modality_attention(modalities, modalities, modalities)
        fused = self.fusion_norm(modalities + attn_out) # Residual add & norm

        # Flatten all modality representations
        fused_flat = fused.reshape(B, -1) # (B, embed_dim * 3)

        # Shared representation
        shared = self.shared_fc(fused_flat)

        # Predictions
        demand_pred = F.relu(self.demand_head(shared)) # Demand cannot be negative
        elasticity_pred = -F.softplus(self.elasticity_head(shared)) # Elasticity is typically negative (downward sloping)

        return demand_pred, elasticity_pred, attn_weights


# ─────────────────────────────────────────────────────────────────────────────
# ABLATION BASELINE MODELS

class TabularOnlyBaseline(nn.Module):
    """Baseline 1: Standard Tabular ML (Price, Cost, Competitor, Inventory)"""
    def __init__(self, tabular_dim: int = 8):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(tabular_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, tabular_features):
        return F.relu(self.net(tabular_features))


class TextTabularBaseline(nn.Module):
    """Baseline 2: NLP Text Transformer + Tabular (No Vision)"""
    def __init__(self, tabular_dim: int = 8, embed_dim: int = 128):
        super().__init__()
        self.text_proj = nn.Linear(384, embed_dim)
        self.tab_proj = nn.Linear(tabular_dim, embed_dim)
        self.fc = nn.Sequential(
            nn.Linear(embed_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

    def forward(self, text_embeddings, tabular_features):
        h_t = F.relu(self.text_proj(text_embeddings))
        h_tab = F.relu(self.tab_proj(tabular_features))
        fused = torch.cat([h_t, h_tab], dim=-1)
        return F.relu(self.fc(fused))


class VisionTabularBaseline(nn.Module):  #####
    """Baseline 3: Vision Transformer/ResNet + Tabular (No Text)"""
    def __init__(self, tabular_dim: int = 8, embed_dim: int = 128):
        super().__init__()
        resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.vision_extractor = nn.Sequential(*list(resnet.children())[:-1])
        self.vision_proj = nn.Linear(512, embed_dim)
        self.tab_proj = nn.Linear(tabular_dim, embed_dim)
        self.fc = nn.Sequential(
            nn.Linear(embed_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

    def forward(self, images, tabular_features):
        B = images.size(0)
        v = self.vision_extractor(images).view(B, 512)
        h_v = F.relu(self.vision_proj(v))
        h_tab = F.relu(self.tab_proj(tabular_features))
        fused = torch.cat([h_v, h_tab], dim=-1)
        return F.relu(self.fc(fused))
