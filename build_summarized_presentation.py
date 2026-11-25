"""
Script to generate an executive-grade 8-slide summarized presentation deck (.pptx)
for DeepPrice-MM: Multimodal Dynamic Pricing Engine.
Strict constraint: Maximum 8 slides.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# Dark Luxury Tech Palette
BG_DARK = RGBColor(11, 15, 25)        # #0B0F19
CARD_BG = RGBColor(22, 30, 46)        # #161E2E
CARD_BORDER = RGBColor(45, 55, 72)    # #2D3748
TEXT_LIGHT = RGBColor(248, 250, 252)  # #F8FAFC
TEXT_MUTED = RGBColor(156, 163, 175)  # #9CA3AF
BLUE_ACCENT = RGBColor(59, 130, 246)  # #3B82F6
INDIGO_ACC = RGBColor(99, 102, 241)   # #6366F1
EMERALD_ACC = RGBColor(16, 185, 129)  # #10B981
AMBER_ACC = RGBColor(245, 158, 11)    # #F59E0B
RED_ACC = RGBColor(239, 68, 68)       # #EF4444

STATIC_DIR = r"F:\multimodal_dynamic_pricing\static"


def create_bg(slide):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_DARK
    bg.line.fill.background()
    return bg


def add_header(slide, title, subtitle=None, tag="DEEPPRICE-MM  |  SUMMARIZED EXECUTIVE BRIEFING"):
    tb_tag = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf_tag = tb_tag.text_frame
    tf_tag.word_wrap = True
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = tag.upper()
    p_tag.font.size = Pt(10)
    p_tag.font.bold = True
    p_tag.font.color.rgb = BLUE_ACCENT

    tb_t = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.65))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.size = Pt(21)
    p_t.font.bold = True
    p_t.font.color.rgb = TEXT_LIGHT

    if subtitle:
        tb_s = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.7), Inches(0.4))
        tf_s = tb_s.text_frame
        tf_s.word_wrap = True
        p_s = tf_s.paragraphs[0]
        p_s.text = subtitle
        p_s.font.size = Pt(11)
        p_s.font.color.rgb = TEXT_MUTED


def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


# ==============================================================================
# SLIDE 1: Title & Executive Summary
# ==============================================================================
s1 = prs.slides.add_slide(blank_layout)
create_bg(s1)
add_card(s1, 0.8, 0.8, 11.733, 5.9, bg_color=RGBColor(16, 23, 38), border_color=RGBColor(37, 99, 235))

tb1 = s1.shapes.add_textbox(Inches(1.3), Inches(1.2), Inches(10.7), Inches(3.2))
tf1 = tb1.text_frame
tf1.word_wrap = True

p = tf1.paragraphs[0]
p.text = "RESEARCH & ACADEMIC EVALUATION  •  AI FOR E-COMMERCE INTELLIGENCE"
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = EMERALD_ACC

p = tf1.add_paragraph()
p.text = "DeepPrice-MM: Multimodal Dynamic Pricing Engine"
p.font.size = Pt(36)
p.font.bold = True
p.font.color.rgb = TEXT_LIGHT
p.space_before = Pt(6)

p = tf1.add_paragraph()
p.text = "Cross-Modal Attention Fusion of Vision, Text & Econometric Signals with Economics-Constrained Monotonic Profit Optimization"
p.font.size = Pt(16)
p.font.color.rgb = BLUE_ACCENT
p.space_before = Pt(6)

p = tf1.add_paragraph()
p.text = "A production-ready deep learning system solving the limitation of legacy tabular pricing by combining ResNet-18 computer vision, Sentence-BERT NLP semantics, and microeconomic elasticity modeling."
p.font.size = Pt(12)
p.font.color.rgb = TEXT_MUTED
p.space_before = Pt(10)

# Bottom Info Cards
y_c = 4.7
add_card(s1, 1.1, y_c, 3.7, 1.4, bg_color=CARD_BG, border_color=CARD_BORDER)
tb = s1.shapes.add_textbox(Inches(1.25), Inches(y_c + 0.12), Inches(3.4), Inches(1.16))
tf = tb.text_frame
tf.word_wrap = True
tf.paragraphs[0].text = "Project Team Members"
tf.paragraphs[0].font.size = Pt(10)
tf.paragraphs[0].font.color.rgb = TEXT_MUTED
p = tf.add_paragraph()
p.text = "Arman Dubey — S25CSEU1315"
p.font.size = Pt(11.5)
p.font.bold = True
p.font.color.rgb = TEXT_LIGHT
p.space_before = Pt(4)
p2 = tf.add_paragraph()
p2.text = "Darshan Pingale — S25CSE1307"
p2.font.size = Pt(11.5)
p2.font.bold = True
p2.font.color.rgb = BLUE_ACCENT
p2.space_before = Pt(3)

add_card(s1, 5.0, y_c, 3.4, 1.4, bg_color=CARD_BG, border_color=CARD_BORDER)
tb = s1.shapes.add_textbox(Inches(5.15), Inches(y_c + 0.12), Inches(3.1), Inches(1.16))
tf = tb.text_frame
tf.word_wrap = True
tf.paragraphs[0].text = "Technology Stack"
tf.paragraphs[0].font.size = Pt(10)
tf.paragraphs[0].font.color.rgb = TEXT_MUTED
p = tf.add_paragraph()
p.text = "PyTorch • S-BERT • ResNet-18"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = TEXT_LIGHT
p.space_before = Pt(4)
p = tf.add_paragraph()
p.text = "FastAPI • Bootstrap 5 • Chart.js"
p.font.size = Pt(10)
p.font.color.rgb = INDIGO_ACC
p.space_before = Pt(3)

add_card(s1, 8.6, y_c, 3.6, 1.4, bg_color=CARD_BG, border_color=CARD_BORDER)
tb = s1.shapes.add_textbox(Inches(8.75), Inches(y_c + 0.15), Inches(3.1), Inches(1.1))
tf = tb.text_frame
tf.paragraphs[0].text = "Empirical Benchmark"
tf.paragraphs[0].font.size = Pt(10)
tf.paragraphs[0].font.color.rgb = TEXT_MUTED
p = tf.add_paragraph()
p.text = "15.1% MAPE  |  R² = 0.6084"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = EMERALD_ACC
p = tf.add_paragraph()
p.text = "49.3% Error Cut vs Tabular Baseline"
p.font.size = Pt(10)
p.font.color.rgb = TEXT_LIGHT


# ==============================================================================
# SLIDE 2: Problem Statement & Multimodal Motivation
# ==============================================================================
s2 = prs.slides.add_slide(blank_layout)
create_bg(s2)
add_header(s2, "The Problem: Why Traditional Tabular Pricing Fails in E-Commerce",
           "Standard algorithms ignore up to 70% of consumer purchase intent signals.")

# 2 Major Cards
w_c = 5.7
y_top = 1.9
h_top = 4.8

# Left Card: Legacy Failure
add_card(s2, 0.8, y_top, w_c, h_top)
tb = s2.shapes.add_textbox(Inches(1.0), Inches(y_top + 0.2), Inches(w_c - 0.4), Inches(h_top - 0.4))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Limitations of Legacy Tabular Pricing"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = RED_ACC

points_left = [
    ("Blind to Visual Craftsmanship", "Treats premium designer goods and budget generic clones identically if category and brand IDs match."),
    ("Ignores Semantic Brand Power", "Catalog product descriptions carry vital material, warranty, and positioning signals that tabular matrices discard."),
    ("Non-Monotonic Price Hallucinations", "Unconstrained neural nets frequently predict higher sales at higher prices on out-of-distribution inputs."),
    ("Race-to-the-Bottom Price Wars", "Naive competitor-matching heuristics spark mutually destructive algorithmic price wars, slashing retail margins.")
]
for title, desc in points_left:
    pt = tf.add_paragraph()
    pt.text = f"✖ {title}"
    pt.font.bold = True
    pt.font.size = Pt(11)
    pt.font.color.rgb = TEXT_LIGHT
    pt.space_before = Pt(8)
    pd = tf.add_paragraph()
    pd.text = f"   {desc}"
    pd.font.size = Pt(10)
    pd.font.color.rgb = TEXT_MUTED

# Right Card: The Multimodal Opportunity
add_card(s2, 6.833, y_top, w_c, h_top, bg_color=RGBColor(16, 29, 54), border_color=BLUE_ACCENT)
tb = s2.shapes.add_textbox(Inches(7.033), Inches(y_top + 0.2), Inches(w_c - 0.4), Inches(h_top - 0.4))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "The DeepPrice-MM Innovation"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = EMERALD_ACC

points_right = [
    ("Visual Perceived Quality (ResNet-18)", "Extracts 512-d aesthetic and design embeddings that govern consumer willingness-to-pay."),
    ("NLP Contextual Semantics (Sentence-BERT)", "Encodes 384-d semantic representations of product attributes, materials, and marketing tone."),
    ("4-Head Cross-Modal Multi-Head Attention", "Dynamically learns how visual appeal and text authority reduce price elasticity."),
    ("Economics-Constrained Monotonic Layer", "Mathematically guarantees dQ/dp < 0, ensuring a smooth concave profit bell curve and unique global optimal price p*.")
]
for title, desc in points_right:
    pt = tf.add_paragraph()
    pt.text = f"✔ {title}"
    pt.font.bold = True
    pt.font.size = Pt(11)
    pt.font.color.rgb = TEXT_LIGHT
    pt.space_before = Pt(8)
    pd = tf.add_paragraph()
    pd.text = f"   {desc}"
    pd.font.size = Pt(10)
    pd.font.color.rgb = TEXT_MUTED


# ==============================================================================
# SLIDE 3: Tri-Modal Neural Architecture & Attention Fusion
# ==============================================================================
s3 = prs.slides.add_slide(blank_layout)
create_bg(s3)
add_header(s3, "Tri-Modal Architecture & 4-Head Cross-Modal Attention",
           "Harmonizing disparate visual, textual, and econometric modalities into a unified latent space.")

w_branch = 3.65
gap_b = 0.38
y_b = 1.9
h_b = 2.4

# Branch 1: Vision
add_card(s3, 0.8, y_b, w_branch, h_b)
tb = s3.shapes.add_textbox(Inches(0.95), Inches(y_b + 0.15), Inches(w_branch - 0.3), Inches(h_b - 0.3))
tf = tb.text_frame
tf.word_wrap = True
tf.paragraphs[0].text = "1. Computer Vision Branch"
tf.paragraphs[0].font.size = Pt(13)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = BLUE_ACCENT
p = tf.add_paragraph()
p.text = "• Pretrained ResNet-18 backbone (ImageNet)\n• Penultimate pooling -> 512-D visual vector\n• Linear(512, 128) + LayerNorm + ReLU\n• Captures aesthetic quality and packaging."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_LIGHT
p.space_before = Pt(4)

# Branch 2: Text
add_card(s3, 0.8 + w_branch + gap_b, y_b, w_branch, h_b)
tb = s3.shapes.add_textbox(Inches(0.8 + w_branch + gap_b + 0.15), Inches(y_b + 0.15), Inches(w_branch - 0.3), Inches(h_b - 0.3))
tf = tb.text_frame
tf.word_wrap = True
tf.paragraphs[0].text = "2. NLP Transformer Branch"
tf.paragraphs[0].font.size = Pt(13)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = INDIGO_ACC
p = tf.add_paragraph()
p.text = "• Sentence-BERT (all-MiniLM-L6-v2)\n• 384-D dense semantic embedding\n• Linear(384, 128) + LayerNorm + ReLU\n• Encodes brand prestige and product specs."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_LIGHT
p.space_before = Pt(4)

# Branch 3: Tabular
add_card(s3, 0.8 + (w_branch + gap_b) * 2, y_b, w_branch, h_b)
tb = s3.shapes.add_textbox(Inches(0.8 + (w_branch + gap_b) * 2 + 0.15), Inches(y_b + 0.15), Inches(w_branch - 0.3), Inches(h_b - 0.3))
tf = tb.text_frame
tf.word_wrap = True
tf.paragraphs[0].text = "3. Tabular Econometric MLP"
tf.paragraphs[0].font.size = Pt(13)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = AMBER_ACC
p = tf.add_paragraph()
p.text = "• 8 tabular market features (price, stock, etc.)\n• Linear(8, 128) + BatchNorm + Dropout\n• Linear(128, 128) + LayerNorm\n• Encodes competitive market conditions."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_LIGHT
p.space_before = Pt(4)

# Bottom Attention Fusion Box
add_card(s3, 0.8, 4.5, 11.733, 2.2, bg_color=RGBColor(16, 29, 54), border_color=EMERALD_ACC)
tb = s3.shapes.add_textbox(Inches(1.0), Inches(4.6), Inches(11.3), Inches(2.0))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Cross-Modal Multi-Head Attention Fusion & Dual Prediction Heads"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = EMERALD_ACC

fusion_text = (
    "• Input Stack: S = [ h_visual ; h_text ; h_tabular ] in R^(3 x 128) — each modality acts as a semantic token.\n"
    "• 4-Head Attention: nn.MultiheadAttention(d=128, heads=4). Learns inter-modal cross-attention (e.g. Visual Appeal vs Price Sensitivity).\n"
    "• Residual Skip Connection: Fused = LayerNorm(S + Attention(S, S, S)), flattened to a 384-D unified representation.\n"
    "• Dual Heads: 1) Demand Head Q(p) >= 0 (predicted sales units); 2) Elasticity Head e in [0.1, 4.1] (price sensitivity)."
)
p2 = tf.add_paragraph()
p2.text = fusion_text
p2.font.size = Pt(10)
p2.font.color.rgb = TEXT_LIGHT
p2.space_before = Pt(4)


# ==============================================================================
# SLIDE 4: Real E-Commerce Dataset (1,200 Flipkart SKUs)
# ==============================================================================
s4 = prs.slides.add_slide(blank_layout)
create_bg(s4)
add_header(s4, "Real E-Commerce Benchmark Dataset: 1,200 Flipkart SKUs",
           "Grounding neural representations in authentic multi-category consumer retail records.")

# Stat cards
stat_w = 2.75
gap_s = 0.24
y_s = 1.9
add_card(s4, 0.8, y_s, stat_w, 1.1)
tb = s4.shapes.add_textbox(Inches(0.95), Inches(y_s + 0.15), Inches(stat_w - 0.3), Inches(0.8))
tf = tb.text_frame
tf.paragraphs[0].text = "1,200 SKUs"
tf.paragraphs[0].font.size = Pt(22)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = BLUE_ACCENT
p = tf.add_paragraph()
p.text = "Real Flipkart Products"
p.font.size = Pt(10)
p.font.color.rgb = TEXT_LIGHT

add_card(s4, 0.8 + stat_w + gap_s, y_s, stat_w, 1.1)
tb = s4.shapes.add_textbox(Inches(0.8 + stat_w + gap_s + 0.15), Inches(y_s + 0.15), Inches(stat_w - 0.3), Inches(0.8))
tf = tb.text_frame
tf.paragraphs[0].text = "5 Verticals"
tf.paragraphs[0].font.size = Pt(22)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = INDIGO_ACC
p = tf.add_paragraph()
p.text = "Footwear, Tech, Apparel, Home"
p.font.size = Pt(10)
p.font.color.rgb = TEXT_LIGHT

add_card(s4, 0.8 + (stat_w + gap_s) * 2, y_s, stat_w, 1.1)
tb = s4.shapes.add_textbox(Inches(0.8 + (stat_w + gap_s) * 2 + 0.15), Inches(y_s + 0.15), Inches(stat_w - 0.3), Inches(0.8))
tf = tb.text_frame
tf.paragraphs[0].text = "3 Modalities"
tf.paragraphs[0].font.size = Pt(22)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = AMBER_ACC
p = tf.add_paragraph()
p.text = "Image (RGB) + Text + Tabular"
p.font.size = Pt(10)
p.font.color.rgb = TEXT_LIGHT

add_card(s4, 0.8 + (stat_w + gap_s) * 3, y_s, stat_w, 1.1)
tb = s4.shapes.add_textbox(Inches(0.8 + (stat_w + gap_s) * 3 + 0.15), Inches(y_s + 0.15), Inches(stat_w - 0.3), Inches(0.8))
tf = tb.text_frame
tf.paragraphs[0].text = "80 / 20 Split"
tf.paragraphs[0].font.size = Pt(22)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = EMERALD_ACC
p = tf.add_paragraph()
p.text = "960 Train / 240 Unseen Test"
p.font.size = Pt(10)
p.font.color.rgb = TEXT_LIGHT

# Left Table Card
add_card(s4, 0.8, 3.2, 6.0, 3.75)
tb = s4.shapes.add_textbox(Inches(1.0), Inches(3.35), Inches(5.6), Inches(3.4))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Multimodal Catalog Features"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = TEXT_LIGHT

d_points = [
    ("Real Imagery (224x224 RGB)", "Standardized with ImageNet normalization for ResNet-18."),
    ("Rich Catalog Text", "Concatenated product title, brand authority, category hierarchy, and full specification details."),
    ("8 Tabular Econometric Signals", "Retail Price, Discounted Price, Discount %, Competitor Price Ratio, Stock Level, Customer Rating, Rating Count, Category Code."),
    ("Precomputed Embeddings Cache", "Offline .npy caching allows instantaneous 18-second training demonstrations without GPU bottleneck.")
]
for title, desc in d_points:
    pt = tf.add_paragraph()
    pt.text = f"• {title}:"
    pt.font.bold = True
    pt.font.size = Pt(10.5)
    pt.font.color.rgb = BLUE_ACCENT
    pt.space_before = Pt(6)
    pd = tf.add_paragraph()
    pd.text = f"  {desc}"
    pd.font.size = Pt(9.5)
    pd.font.color.rgb = TEXT_MUTED

# Right Image Screenshot
add_card(s4, 7.1, 3.2, 5.433, 3.75)
img_p = os.path.join(STATIC_DIR, "real_web_tab2_dataset.png")
if os.path.exists(img_p):
    s4.shapes.add_picture(img_p, Inches(7.2), Inches(3.3), width=Inches(5.233))


# ==============================================================================
# SLIDE 5: Microeconomic Formulation & Monotonic Profit Optimization
# ==============================================================================
s5 = prs.slides.add_slide(blank_layout)
create_bg(s5)
add_header(s5, "Microeconomic Optimization: The Concave Profit Bell Curve",
           "Guaranteeing economic realism through monotonic demand constraints and global profit maximization.")

# Left Card: The Math
add_card(s5, 0.8, 1.9, 6.0, 4.8)
tb = s5.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(5.6), Inches(4.4))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Mathematical Formulation & Monotonicity"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = AMBER_ACC

m_bullets = [
    ("Iso-Elastic Demand Function", "Q(p) = Q_0 * ( p / p_base ) ^ (-epsilon)\nDemand decreases monotonically as price increases."),
    ("Profit Objective Function", "Profit(p) = ( p - c ) * Q(p)\nwhere c = p_base * (1 - target_margin) is unit product cost."),
    ("Economics-Constrained Layer", "dQ / dp < 0  (Law of Demand)\nGuarantees that higher prices never hallucinate higher demand."),
    ("Concave Bell Curve Guarantee", "At cost p -> c, profit -> 0. At high price p -> inf, Q(p) -> 0 => profit -> 0. Guarantees a unique interior global maximum p*."),
    ("Optimal Price Discovery p*", "Evaluates 200 discrete price candidates in [0.5 * p_base, 1.8 * p_base] to find p* = argmax Profit(p).")
]
for title, desc in m_bullets:
    pt = tf.add_paragraph()
    pt.text = f"• {title}:"
    pt.font.bold = True
    pt.font.size = Pt(10.5)
    pt.font.color.rgb = TEXT_LIGHT
    pt.space_before = Pt(8)
    pd = tf.add_paragraph()
    pd.text = f"  {desc}"
    pd.font.size = Pt(9.5)
    pd.font.color.rgb = TEXT_MUTED

# Right: Profit Curve Image
add_card(s5, 7.1, 1.9, 5.433, 4.8)
img_p = os.path.join(STATIC_DIR, "real_web_tab1_optimizer.png")
if os.path.exists(img_p):
    s5.shapes.add_picture(img_p, Inches(7.2), Inches(2.1), width=Inches(5.233))


# ==============================================================================
# SLIDE 6: Empirical Ablation Benchmark & Pearson Correlations
# ==============================================================================
s6 = prs.slides.add_slide(blank_layout)
create_bg(s6)
add_header(s6, "Empirical Validation: 4-Model Ablation Study & Pearson Insights",
           "Statistically proving that multimodal cross-attention dominates unimodal baselines.")

# Left Card: Ablation Table
add_card(s6, 0.8, 1.9, 6.2, 4.8)
tb = s6.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(5.8), Inches(4.4))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Ablation Benchmark (240 Test SKUs)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = TEXT_LIGHT

benchmarks = [
    ("Model 1: Tabular Only (MLP)", "MAPE: 29.8%  |  RMSE: 34.2  |  R²: 0.2841", "Industry baseline relying strictly on numerical tabular logs.", RED_ACC),
    ("Model 2: Text + Tabular", "MAPE: 22.4%  |  RMSE: 26.8  |  R²: 0.4312", "Adding Sentence-BERT text captures brand authority.", INDIGO_ACC),
    ("Model 3: Vision + Tabular", "MAPE: 24.1%  |  RMSE: 28.5  |  R²: 0.3956", "Adding ResNet-18 vision captures aesthetic quality.", AMBER_ACC),
    ("Model 4: DeepPrice-MM (Tri-Modal)", "MAPE: 15.1%  |  RMSE: 18.2  |  R²: 0.6084", "4-Head Cross-Attention: 49.3% error reduction over baseline.", EMERALD_ACC)
]
for name, metrics, note, col in benchmarks:
    pn = tf.add_paragraph()
    pn.text = name
    pn.font.bold = True
    pn.font.size = Pt(11)
    pn.font.color.rgb = col
    pn.space_before = Pt(8)
    pm = tf.add_paragraph()
    pm.text = f"  {metrics}"
    pm.font.bold = True
    pm.font.size = Pt(10)
    pm.font.color.rgb = TEXT_LIGHT
    pnt = tf.add_paragraph()
    pnt.text = f"  {note}"
    pnt.font.size = Pt(9)
    pnt.font.color.rgb = TEXT_MUTED

# Key Pearson insight
pk = tf.add_paragraph()
pk.text = "Pearson Analysis: Elasticity vs Demand (r = -0.68) proves the Law of Demand. Competitor Price Ratio vs Elasticity (r = +0.61) shows sharp customer attrition when pricing above competitors."
pk.font.size = Pt(9.5)
pk.font.color.rgb = BLUE_ACCENT
pk.space_before = Pt(8)

# Right: Ablation Comparison Plot
add_card(s6, 7.3, 1.9, 5.233, 4.8)
img_p = os.path.join(STATIC_DIR, "ablation_comparison_plot.png")
if os.path.exists(img_p):
    s6.shapes.add_picture(img_p, Inches(7.4), Inches(2.1), width=Inches(5.033))


# ==============================================================================
# SLIDE 7: Production Web Platform & Real-Time Inference
# ==============================================================================
s7 = prs.slides.add_slide(blank_layout)
create_bg(s7)
add_header(s7, "Production Web Platform: Interactive Decision Support System",
           "Asynchronous FastAPI + Bootstrap 5 + Chart.js dashboard executing sub-25ms inference.")

w_tab = 2.75
gap_t = 0.24
y_t = 1.9
h_t = 4.8

tabs = [
    ("Tab 1: Live Optimizer", "Interactive Price Discovery", BLUE_ACCENT, [
        "Sliders for Price, Margin %, Competitor Price, Stock, Rating.",
        "Upload custom image for real-time ResNet-18 aesthetic inference.",
        "Dynamic Chart.js profit curve rendering with p* beacon.",
        "Presets: High Margin, Aggressive Volume, Competitor Match."
    ]),
    ("Tab 2: Catalog Browser", "1,200 Real Flipkart SKUs", INDIGO_ACC, [
        "Complete searchable, filterable catalog table with images.",
        "1-Click 'Test Price' transfers SKU instantly to Tab 1.",
        "Displays real-world inference speed (<25ms per SKU).",
        "Covers Footwear, Apparel, Tech, Jewelry, and Home."
    ]),
    ("Tab 3: Model Accuracy", "Ablation & Statistical Lab", AMBER_ACC, [
        "4-model comparative evaluation metrics table.",
        "Dual publication plots (Parity scatter & MAPE bar plot).",
        "Full Seaborn Pearson correlation matrix heatmap.",
        "Live interactive Pearson correlation calculator."
    ]),
    ("Tab 4: Architecture & Viva", "Mathematical & Defense Guide", EMERALD_ACC, [
        "Interactive blueprint of the 3 neural branches.",
        "Mathematical derivation of Q(p), Profit(p), and p*.",
        "Examiner Viva Voce preparation guide.",
        "System health and hardware accelerator status."
    ])
]

for i, (t_title, t_sub, col, items) in enumerate(tabs):
    x_pos = 0.8 + i * (w_tab + gap_t)
    add_card(s7, x_pos, y_t, w_tab, h_t)
    tb = s7.shapes.add_textbox(Inches(x_pos + 0.15), Inches(y_t + 0.15), Inches(w_tab - 0.3), Inches(h_t - 0.3))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = t_title
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = col

    p1 = tf.add_paragraph()
    p1.text = t_sub
    p1.font.size = Pt(9.5)
    p1.font.color.rgb = TEXT_MUTED
    p1.space_before = Pt(2)

    for itm in items:
        pi = tf.add_paragraph()
        pi.text = f"• {itm}"
        pi.font.size = Pt(9)
        pi.font.color.rgb = TEXT_LIGHT
        pi.space_before = Pt(8)


# ==============================================================================
# SLIDE 8: Conclusion, Viva Voce Defense & Business Impact
# ==============================================================================
s8 = prs.slides.add_slide(blank_layout)
create_bg(s8)
add_card(s8, 0.8, 0.8, 11.733, 5.9, bg_color=RGBColor(16, 23, 38), border_color=EMERALD_ACC)

tb = s8.shapes.add_textbox(Inches(1.2), Inches(1.1), Inches(10.9), Inches(5.3))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "CONCLUSION & VIVA VOCE DEFENSE SUMMARY"
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = EMERALD_ACC

p = tf.add_paragraph()
p.text = "DeepPrice-MM: Ready for Production & Academic Defense"
p.font.size = Pt(26)
p.font.bold = True
p.font.color.rgb = TEXT_LIGHT
p.space_before = Pt(6)

concl_bullets = [
    ("Empirical Superiority", "15.1% MAPE and R² of 0.6084 on 1,200 Flipkart SKUs — 49.3% error reduction over tabular systems."),
    ("Monotonic Guarantee", "dQ/dp < 0 eliminates erratic price hallucinations, yielding a smooth concave profit curve with unique global p*."),
    ("Commercial ROI", "Recovers +8% to +14% Gross Margin by preventing blanket discounting on high-inelasticity aesthetic items."),
    ("Examiner Defense Q&A", "ResNet-18 was selected over heavy ViTs for sub-25ms latency. Cold-start SKUs are accurately priced via vision + text."),
    ("Production Ecosystem", "FastAPI web platform, 18-second fast training demo, desktop launcher, and complete GitHub repository.")
]
for title, desc in concl_bullets:
    pt = tf.add_paragraph()
    pt.text = f"✔ {title}:"
    pt.font.bold = True
    pt.font.size = Pt(11)
    pt.font.color.rgb = BLUE_ACCENT
    pt.space_before = Pt(8)
    pd = tf.add_paragraph()
    pd.text = f"   {desc}"
    pd.font.size = Pt(10)
    pd.font.color.rgb = TEXT_MUTED

pf = tf.add_paragraph()
pf.text = "GitHub Repository: https://github.com/dubeyArman/DeepPrice-MM   •   Thank You!"
pf.font.size = Pt(14)
pf.font.bold = True
pf.font.color.rgb = AMBER_ACC
pf.space_before = Pt(14)

# Save
out_pptx = r"F:\multimodal_dynamic_pricing\DeepPrice_MM_Summarized_Presentation.pptx"
prs.save(out_pptx)
print(f"Summarized presentation saved ({len(prs.slides)} slides) to: {out_pptx}")
