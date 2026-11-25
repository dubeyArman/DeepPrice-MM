"""
data_generator.py
=================
Generates a realistic, publication-grade Multimodal E-Commerce Dynamic Pricing Dataset.

Each product record contains:
1. Product Image (.jpg): 224x224 RGB image with distinct category palettes, visual badge, styling,
   and visual quality/aesthetic score.
2. Rich Textual Metadata: Canonical Title, Brand Tier, Detailed Bulleted Description, and Specifications.
3. Tabular Econometric Attributes: Base Production Cost (₹), MSRP (₹), Competitor Minimum Price (₹),
   Competitor Average Price (₹), Current Inventory Count, Customer Rating (1-5), and Seasonal Surge Index.
4. Ground-Truth Microeconomic Demand (Units Sold) & Elasticity (PED):
   Simulated via a rigorous consumer discrete choice utility model:
     Utility = α_base + α_vis * VisualAesthetic + α_txt * TextQuality
               - β_price * (Price / CompetitorMinPrice) + γ_brand * BrandTier
               + δ_stock * ScarcityFactor + ε_noise
     Demand Q(P) = MarketCapacity * Sigmoid(Utility)
     Price Elasticity PED = (dQ / dP) * (P / Q)
"""

import os
import json
import random
import math
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from tqdm import tqdm

DATA_DIR = Path(__file__).resolve().parent / "data"
IMAGES_DIR = DATA_DIR / "images"
CSV_PATH = DATA_DIR / "ecommerce_multimodal_pricing_dataset.csv"

CATEGORIES = {
    "Smartphones": {
        "brands": [("Apple", 3.0, (230, 230, 235)), ("Samsung", 2.6, (200, 220, 245)), ("OnePlus", 2.3, (255, 215, 215)), ("Xiaomi", 1.8, (255, 235, 205)), ("Realme", 1.7, (255, 250, 205))],
        "base_cost_range": (8000, 60000),
        "markup_range": (1.25, 1.55),
        "price_sensitivity_beta": 1.95,
        "market_capacity": 600,
        "descriptors": [
            ("5G Flagship with 120Hz AMOLED Display, 50MP Sony OIS Camera, and 67W Turbo Flash Charging", "Ultra-thin aerospace aluminum body with Corning Gorilla Glass Victus protection."),
            ("Powerful Gaming Phone with Octa-Core Processor, 8GB LPDDR5 RAM, and 5000mAh Battery", "Vapor Chamber liquid cooling system engineered for intense multi-hour gaming sessions."),
            ("Cinematic Portrait Camera Phone with 4K Video Recording, 256GB Storage, and AI Photo Enhancer", "Dual stereo speakers certified by Dolby Atmos with pristine acoustic clarity."),
        ],
    },
    "Audio & Headphones": {
        "brands": [("Sony", 2.9, (220, 220, 225)), ("boAt", 1.9, (255, 210, 210)), ("Boult", 1.7, (235, 235, 240)), ("Noise", 1.8, (215, 240, 255)), ("JBL", 2.4, (255, 225, 205))],
        "base_cost_range": (600, 18000),
        "markup_range": (1.30, 1.80),
        "price_sensitivity_beta": 2.20,
        "market_capacity": 1200,
        "descriptors": [
            ("True Wireless In-Ear Earbuds with Hybrid Active Noise Cancellation and 60H Total Battery", "Low-latency gaming mode with 4-mic environmental noise reduction for crystal-clear calls."),
            ("Over-Ear Wireless Bluetooth Headphones with Deep Bass Drivers and Ergonomic Cushions", "Foldable lightweight headband with quick charge (10 mins gives 5 hours playtime)."),
            ("Waterproof Portable Bluetooth Speaker with Rugged Shockproof Bumper and 360 Soundstage", "IPX7 submersible rating with integrated carry cord and dual passive bass radiators."),
        ],
    },
    "Smartwatches & Wearables": {
        "brands": [("Apple", 3.0, (235, 235, 240)), ("Noise", 1.9, (210, 235, 255)), ("Fire-Boltt", 1.8, (255, 220, 220)), ("boAt", 1.8, (255, 230, 215)), ("Samsung", 2.7, (215, 225, 250))],
        "base_cost_range": (800, 25000),
        "markup_range": (1.35, 1.90),
        "price_sensitivity_beta": 2.10,
        "market_capacity": 900,
        "descriptors": [
            ("1.96-inch HD AMOLED Display Smartwatch with Bluetooth Calling and Continuous SpO2 Heart Monitor", "100+ professional sports tracking modes with customizable cloud-based watch faces."),
            ("Rugged Outdoor GPS Smartwatch with Military Standard Shock Resistance and 14-Day Battery", "Barometric altimeter, compass, and multi-GNSS satellite tracking for hiking and trekking."),
            ("Slim Fitness Tracker Band with Sleep Quality Analysis, Calorie Counter, and Water Resistance", "Ultra-lightweight skin-friendly silicone strap designed for 24/7 ergonomic wear."),
        ],
    },
    "Home & Kitchen Appliances": {
        "brands": [("Philips", 2.5, (220, 240, 255)), ("LG", 2.7, (245, 220, 230)), ("Bajaj", 1.9, (255, 235, 210)), ("Prestige", 2.1, (255, 220, 220)), ("Havells", 2.3, (225, 235, 245))],
        "base_cost_range": (1200, 35000),
        "markup_range": (1.20, 1.50),
        "price_sensitivity_beta": 1.75,
        "market_capacity": 450,
        "descriptors": [
            ("Rapid Air Technology Digital Air Fryer (4.2L) with Touch Panel and 8 One-Touch Presets", "Uses up to 90% less oil for crispy, healthy frying, baking, grilling, and roasting."),
            ("Inverter Direct Drive Front-Load Washing Machine with AI Steam Allergy Care Protection", "5-star energy efficiency rating with whisper-quiet brushless motor operation."),
            ("750W Heavy Duty Mixer Grinder with 3 Stainless Steel Jars and Overload Protection", "Pure copper high-torque motor engineered for tough Indian kitchen grinding tasks."),
        ],
    },
    "Personal Care & Cosmetics": {
        "brands": [("Wild Stone", 2.0, (220, 230, 240)), ("Dettol", 2.4, (220, 255, 220)), ("Nivea", 2.3, (210, 225, 255)), ("L'Oreal", 2.6, (255, 225, 235)), ("Mamaearth", 2.1, (230, 250, 230))],
        "base_cost_range": (120, 2500),
        "markup_range": (1.40, 2.20),
        "price_sensitivity_beta": 2.40,
        "market_capacity": 1500,
        "descriptors": [
            ("Long-Lasting Eau De Parfum for Men (100ml) with Exotic Amber and Citrus Cedarwood Notes", "Concentrated premium fragrance oils providing 12+ hours of lingering sillage."),
            ("Germ Protection Deep Clean Bathing Soap Bar Pack of 5 with Glycerin and Vitamin E", "Dermatologically tested formula that maintains natural skin moisture balance."),
            ("Hydrating Hyaluronic Acid & Vitamin C Face Serum for Radiant and Youthful Glowing Skin", "Lightweight, non-greasy, paraben-free daily anti-aging antioxidant booster."),
        ],
    },
}


def render_synthetic_product_image(
    image_path: Path,
    category_name: str,
    brand_name: str,
    product_title: str,
    base_color: tuple,
    visual_score: float,
):
    """
    Renders a clean, aesthetic 224x224 RGB e-commerce product mockup image
    with visual branding, category icon styling, and quality gradients.
    """
    W, H = 224, 224
    img = Image.new("RGB", (W, H), color=base_color)
    draw = ImageDraw.Draw(img)

    # 1. Subtle Radial / Circular background accent
    center_x, center_y = W // 2, H // 2 - 15
    radius = int(55 + visual_score * 25)
    accent_color = (
        min(255, base_color[0] + 25),
        min(255, base_color[1] + 25),
        min(255, base_color[2] + 25),
    )
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        fill=accent_color,
        outline=(180, 190, 205),
        width=2,
    )

    # 2. Category Iconic Geometric Representation
    if "Smartphone" in category_name:
        # Phone body
        draw.rounded_rectangle([75, 45, 149, 155], radius=12, fill=(30, 41, 59), outline=(71, 85, 105), width=3)
        # Screen
        draw.rounded_rectangle([80, 52, 144, 148], radius=8, fill=(15, 23, 42))
        # Camera punch hole
        draw.ellipse([110, 58, 114, 62], fill=(148, 163, 184))
    elif "Audio" in category_name:
        # Headband arc
        draw.arc([60, 40, 164, 130], start=180, end=0, fill=(30, 41, 59), width=8)
        # Ear cushions
        draw.rounded_rectangle([55, 90, 85, 145], radius=10, fill=(15, 23, 42), outline=(71, 85, 105), width=2)
        draw.rounded_rectangle([139, 90, 169, 145], radius=10, fill=(15, 23, 42), outline=(71, 85, 105), width=2)
    elif "Watch" in category_name:
        # Watch strap
        draw.rectangle([96, 30, 128, 170], fill=(71, 85, 105))
        # Watch dial
        draw.rounded_rectangle([74, 65, 150, 135], radius=16, fill=(15, 23, 42), outline=(203, 213, 225), width=3)
        draw.ellipse([92, 83, 132, 117], fill=(30, 41, 59))
    elif "Appliance" in category_name:
        # Boxy appliance
        draw.rounded_rectangle([65, 50, 159, 150], radius=14, fill=(241, 245, 249), outline=(51, 65, 85), width=3)
        draw.ellipse([85, 75, 139, 129], fill=(203, 213, 225), outline=(71, 85, 105), width=2)
    else: # Cosmetics / Bottles
        draw.rounded_rectangle([85, 70, 139, 160], radius=8, fill=(30, 41, 59), outline=(71, 85, 105), width=2)
        draw.rectangle([98, 42, 126, 70], fill=(203, 213, 225), outline=(71, 85, 105), width=2)

    # 3. Brand Pill Header
    draw.rounded_rectangle([15, 12, 15 + len(brand_name) * 9 + 18, 30], radius=6, fill=(15, 23, 42))
    draw.text((22, 14), brand_name.upper(), fill=(255, 255, 255))

    # 4. Product Title Label at Bottom
    draw.rectangle([0, 185, W, H], fill=(15, 23, 42))
    short_title = (product_title[:26] + "...") if len(product_title) > 28 else product_title
    draw.text((10, 192), short_title, fill=(241, 245, 249))

    # 5. Aesthetic Quality Badge in Top Right
    if visual_score >= 0.75:
        draw.rounded_rectangle([W - 48, 12, W - 12, 28], radius=4, fill=(16, 185, 129))
        draw.text((W - 42, 14), "★ HD", fill=(255, 255, 255))

    img.save(image_path, "JPEG", quality=90)


def generate_multimodal_dataset(num_samples: int = 1200):
    """
    Generates `num_samples` complete multimodal products with images, text, and ground-truth demand.
    """
    print("=================================================================")
    print(f"  Generating Multimodal Dynamic Pricing Dataset ({num_samples} SKUs)")
    print("=================================================================")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    np.random.seed(42)

    records = []
    category_names = list(CATEGORIES.keys())

    for i in tqdm(range(num_samples), desc="Synthesizing Multimodal Samples"):
        cat_name = category_names[i % len(category_names)]
        cat_info = CATEGORIES[cat_name]

        # 1. Brand selection
        brand_tuple = random.choice(cat_info["brands"])
        brand_name, brand_tier, base_rgb = brand_tuple

        # 2. Textual description
        desc_pair = random.choice(cat_info["descriptors"])
        feature_text, detail_text = desc_pair

        # Generate title
        variant = random.choice(["Pro", "Max", "Ultra", "Plus", "Standard Edition", "Gen-2", "Series 5"])
        color = random.choice(["Midnight Black", "Pastel Lime", "Moonstone Silver", "Deep Blue", "Pearl White"])
        product_title = f"{brand_name} {cat_name.split()[0]} {variant} ({color})"
        full_description = f"{feature_text}. {detail_text} Built by {brand_name} with premium industry-grade materials."

        # Text quality / richness score [0.4 to 1.0]
        text_quality_score = min(1.0, 0.45 + (len(full_description) / 300) + random.uniform(-0.05, 0.15))

        # 3. Visual Aesthetic Score [0.3 to 1.0]
        visual_aesthetic_score = round(random.uniform(0.35, 0.98), 3)

        # Render product image
        image_filename = f"prod_{i:05d}_{cat_name[:4].lower()}.jpg"
        image_path = IMAGES_DIR / image_filename
        render_synthetic_product_image(
            image_path=image_path,
            category_name=cat_name,
            brand_name=brand_name,
            product_title=product_title,
            base_color=base_rgb,
            visual_score=visual_aesthetic_score,
        )

        # 4. Tabular Econometric Attributes
        min_cost, max_cost = cat_info["base_cost_range"]
        cost = round(random.uniform(min_cost, max_cost), 2)

        # Recommended MSRP
        min_markup, max_markup = cat_info["markup_range"]
        msrp = round(cost * random.uniform(min_markup, max_markup), 2)

        # Competitor pricing landscape (18 Indian marketplaces)
        comp_min_price = round(msrp * random.uniform(0.85, 0.98), 2)
        comp_avg_price = round(comp_min_price * random.uniform(1.03, 1.15), 2)

        # Actual offered price (test candidate price)
        # We sample candidate prices varying from deep discount to premium markup
        price_factor = random.choice([0.88, 0.92, 0.96, 1.0, 1.04, 1.08, 1.15, 1.25])
        offered_price = round(msrp * price_factor, 2)

        inventory_count = random.randint(15, 500)
        customer_rating = round(random.uniform(3.2, 4.9), 1)
        seasonal_surge_index = round(random.uniform(1.0, 1.35), 2) # e.g. Diwali festive spike

        # 5. Microeconomic Ground Truth Simulation (Consumer Discrete Choice Utility)
        # Utility function:
        # High visual appeal (+), high text quality (+), strong brand (+), high competitor price (+),
        # but high offered price strongly decreases utility (-).
        beta_p = cat_info["price_sensitivity_beta"]
        price_ratio = offered_price / comp_min_price # > 1 means we are more expensive than competitors

        utility = (
            1.2
            + 1.4 * visual_aesthetic_score          # Visual impact
            + 0.9 * text_quality_score             # Text description clarity & specs
            + 0.5 * (brand_tier - 2.0)             # Brand equity premium
            + 0.3 * (customer_rating - 3.5)        # Rating trust
            - beta_p * (price_ratio - 1.0) * 3.5   # Strong economic downward price sensitivity
            + 0.25 * (seasonal_surge_index - 1.0)  # Festive demand lift
            + random.gauss(0, 0.12)                # Market stochastic noise
        )

        # Sigmoid choice probability P_buy in [0, 1]
        p_buy = 1.0 / (1.0 + math.exp(-utility))

        # Realized sales volume / demand Q
        market_cap = cat_info["market_capacity"] * seasonal_surge_index
        expected_demand = market_cap * p_buy
        realized_demand = max(0, int(round(expected_demand + random.gauss(0, math.sqrt(max(1.0, expected_demand * 0.15))))))

        # Calculate exact theoretical Price Elasticity of Demand (PED) at this point:
        # dQ/dP = market_cap * p_buy * (1 - p_buy) * (-beta_p * 3.5 / comp_min_price)
        dq_dp = market_cap * p_buy * (1.0 - p_buy) * (-beta_p * 3.5 / comp_min_price)
        ped = (dq_dp * offered_price / max(1.0, expected_demand)) if expected_demand > 0 else -1.5

        records.append({
            "product_id": f"SKU_{i:05d}",
            "category": cat_name,
            "brand": brand_name,
            "brand_tier": brand_tier,
            "title": product_title,
            "description": full_description,
            "image_filename": image_filename,
            "image_relative_path": f"data/images/{image_filename}",
            "visual_aesthetic_score": visual_aesthetic_score,
            "text_quality_score": round(text_quality_score, 3),
            "production_cost": cost,
            "msrp": msrp,
            "competitor_min_price": comp_min_price,
            "competitor_avg_price": comp_avg_price,
            "offered_price": offered_price,
            "price_ratio_to_competitor": round(price_ratio, 3),
            "inventory_count": inventory_count,
            "customer_rating": customer_rating,
            "seasonal_surge_index": seasonal_surge_index,
            "ground_truth_demand": realized_demand,
            "theoretical_ped": round(ped, 3),
            "realized_revenue": round(offered_price * realized_demand, 2),
            "realized_profit": round((offered_price - cost) * realized_demand, 2),
        })

    df = pd.DataFrame(records)
    df.to_csv(CSV_PATH, index=False)
    print(f"Dataset successfully created and saved to: {CSV_PATH}")
    print(f"  • Total Samples: {len(df)}")
    print(f"  • Total Images Rendered: {len(list(IMAGES_DIR.glob('*.jpg')))}")
    print(f"  • Categories: {df['category'].value_counts().to_dict()}")
    print(f"  • Mean Demand: {df['ground_truth_demand'].mean():.2f} units")
    print(f"  • Mean PED: {df['theoretical_ped'].mean():.2f}")
    return df


if __name__ == "__main__":
    generate_multimodal_dataset(1200)
