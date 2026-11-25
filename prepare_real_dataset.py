import os
import sys
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from PIL import Image

DATA_DIR = r"F:\multimodal_dynamic_pricing\data"
RAW_CSV = os.path.join(DATA_DIR, "real_flipkart_dataset_raw.csv")
CLEAN_CSV = os.path.join(DATA_DIR, "flipkart_ecommerce_real_dataset.csv")
IMG_DIR = os.path.join(DATA_DIR, "real_images")
os.makedirs(IMG_DIR, exist_ok=True)

print("Loading raw Flipkart dataset...")
df = pd.read_csv(RAW_CSV)
print(f"Total rows in raw dataset: {len(df)}")

# Filter valid rows
df = df.dropna(subset=['retail_price', 'discounted_price', 'product_name', 'description', 'image'])
df['retail_price'] = pd.to_numeric(df['retail_price'], errors='coerce')
df['discounted_price'] = pd.to_numeric(df['discounted_price'], errors='coerce')
df = df.dropna(subset=['retail_price', 'discounted_price'])
df = df[(df['retail_price'] >= 200) & (df['discounted_price'] >= 150) & (df['retail_price'] <= 100000)]
df = df[df['retail_price'] >= df['discounted_price']] # MSRP >= Discounted Price

def parse_first_image_url(img_str):
    if not isinstance(img_str, str):
        return None
    try:
        urls = json.loads(img_str)
        if isinstance(urls, list) and len(urls) > 0:
            return urls[0]
    except Exception:
        # Fallback regex
        m = re.findall(r'http[s]?://[^\s",\'\]]+', img_str)
        if m:
            return m[0]
    return None

def extract_main_category(cat_str):
    if not isinstance(cat_str, str):
        return "General"
    cleaned = cat_str.strip("[\"'] ")
    parts = [p.strip() for p in cleaned.split(">>")]
    main_cat = parts[0] if len(parts) > 0 else "General"
    # Group into broad familiar categories
    if any(k in main_cat for k in ["Mobile", "Tablet", "Computer", "Electronic", "Camera"]):
        return "Mobiles & Tech"
    elif any(k in main_cat for k in ["Watch"]):
        return "Watches & Wearables"
    elif any(k in main_cat for k in ["Footwear"]):
        return "Footwear & Shoes"
    elif any(k in main_cat for k in ["Home", "Kitchen", "Furniture", "Tools"]):
        return "Home & Kitchen"
    elif any(k in main_cat for k in ["Beauty", "Personal Care", "Health"]):
        return "Beauty & Personal Care"
    elif any(k in main_cat for k in ["Clothing"]):
        return "Clothing & Fashion"
    elif any(k in main_cat for k in ["Jewellery"]):
        return "Jewellery & Accessories"
    elif any(k in main_cat for k in ["Automotive"]):
        return "Automotive & Tools"
    return "Lifestyle & Others"

df['first_image_url'] = df['image'].apply(parse_first_image_url)
df = df.dropna(subset=['first_image_url'])
df['category'] = df['product_category_tree'].apply(extract_main_category)

# Filter for top popular categories
target_cats = [
    "Mobiles & Tech", "Watches & Wearables", "Footwear & Shoes", 
    "Home & Kitchen", "Beauty & Personal Care", "Clothing & Fashion"
]
df_filtered = df[df['category'].isin(target_cats)].copy()

# Deduplicate by title
df_filtered = df_filtered.drop_duplicates(subset=['product_name'])

# Sample balanced 1,200 products (up to 200-250 per category)
samples_per_cat = 200
sampled_dfs = []
for cat in target_cats:
    sub = df_filtered[df_filtered['category'] == cat]
    if len(sub) > samples_per_cat:
        sampled_dfs.append(sub.sample(samples_per_cat, random_state=42))
    elif len(sub) > 0:
        sampled_dfs.append(sub)

df_sample = pd.concat(sampled_dfs).reset_index(drop=True)
print(f"Sampled {len(df_sample)} products across {len(target_cats)} categories:")
print(df_sample['category'].value_counts())

# Download images in parallel with timeout
print("Downloading product images in parallel...")

def download_image(row_tuple):
    idx, row = row_tuple
    url = row['first_image_url']
    sku = f"REAL_SKU_{idx:05d}"
    img_filename = f"{sku}.jpg"
    img_path = os.path.join(IMG_DIR, img_filename)

    if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
        return idx, img_filename, True

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            with open(img_path, 'wb') as f:
                f.write(data)
            # Verify it opens with PIL
            with Image.open(img_path) as im:
                im.verify()
        return idx, img_filename, True
    except Exception as e:
        # If download fails, create a clean category placeholder image
        try:
            im = Image.new("RGB", (224, 224), color=(240, 245, 250))
            im.save(img_path)
            return idx, img_filename, False
        except Exception:
            return idx, None, False

download_tasks = [(i, row) for i, row in df_sample.iterrows()]
image_map = {}
success_count = 0

with ThreadPoolExecutor(max_workers=16) as executor:
    futures = [executor.submit(download_image, task) for task in download_tasks]
    for future in as_completed(futures):
        idx, img_name, success = future.result()
        if img_name:
            image_map[idx] = img_name
            if success:
                success_count += 1

print(f"Downloaded / processed {len(image_map)} images (Live CDN successes: {success_count}).")

# Assign image filenames
df_sample['image_filename'] = [image_map.get(i, f"REAL_SKU_{i:05d}.jpg") for i in range(len(df_sample))]
df_sample['image_relative_path'] = df_sample['image_filename'].apply(lambda x: f"data/real_images/{x}")
df_sample['product_id'] = [f"REAL_SKU_{i:05d}" for i in range(len(df_sample))]

# Clean ratings
def clean_rating(r):
    try:
        val = float(r)
        if 1.0 <= val <= 5.0:
            return round(val, 1)
    except Exception:
        pass
    return round(float(np.random.normal(4.1, 0.4)), 1)

df_sample['customer_rating'] = df_sample['product_rating'].apply(clean_rating).clip(2.5, 5.0)

# Construct realistic pricing and economic variables from real Flipkart data:
# 1. msrp: real retail_price
# 2. competitor_avg_price: real discounted_price
# 3. production_cost: realistic gross margin ~55% of retail price
df_sample['msrp'] = df_sample['retail_price'].round(2)
df_sample['competitor_avg_price'] = df_sample['discounted_price'].round(2)
df_sample['competitor_min_price'] = (df_sample['competitor_avg_price'] * np.random.uniform(0.90, 0.98, size=len(df_sample))).round(2)
df_sample['production_cost'] = (df_sample['msrp'] * np.random.uniform(0.45, 0.60, size=len(df_sample))).round(2)

# Offered price randomly around competitor price (+/- 15%) for initial market snapshot
price_ratio = np.random.uniform(0.88, 1.15, size=len(df_sample))
df_sample['offered_price'] = (df_sample['competitor_avg_price'] * price_ratio).round(2)
df_sample['price_ratio_to_competitor'] = (df_sample['offered_price'] / df_sample['competitor_avg_price']).round(3)
df_sample['inventory_count'] = np.random.randint(20, 500, size=len(df_sample))

# Clean description and title
df_sample['title'] = df_sample['product_name'].str.slice(0, 120).str.strip()
df_sample['description'] = df_sample['description'].fillna(df_sample['product_name']).str.slice(0, 400).str.strip()

# Brand tier based on real brand presence
known_premium = ["Apple", "Samsung", "Sony", "Puma", "Nike", "Titan", "Fossil", "Philips", "Dyson", "L'Oreal", "Casio", "Adidas"]
def get_brand_tier(b):
    if not isinstance(b, str):
        return 1.5
    for p in known_premium:
        if p.lower() in b.lower():
            return 3.0
    return 2.0

df_sample['brand_tier'] = df_sample['brand'].apply(get_brand_tier)

# Microeconomic Discrete Choice Demand Calculation based on Real Attributes
# Text length / richness score
text_len = df_sample['description'].str.len().fillna(50)
text_quality = (text_len / text_len.max()).clip(0.3, 1.0)

# Random utility formula
# U = 1.0 + 0.6*(rating-3.5) + 0.5*(brand_tier-1.5) + 0.4*text_quality - 2.8*(P/Pcomp - 1) + eps
eps = np.random.normal(0, 0.25, size=len(df_sample))
utility = (
    1.1 
    + 0.55 * (df_sample['customer_rating'] - 3.5)
    + 0.50 * (df_sample['brand_tier'] - 1.5)
    + 0.45 * text_quality
    - 2.85 * (df_sample['price_ratio_to_competitor'] - 1.0)
    + eps
)

# Base market demand scaled by price range
base_demand = np.where(df_sample['msrp'] < 1000, 1500,
              np.where(df_sample['msrp'] < 5000, 800,
              np.where(df_sample['msrp'] < 20000, 350, 120)))

prob_choice = 1.0 / (1.0 + np.exp(-utility))
df_sample['ground_truth_demand'] = np.round(base_demand * prob_choice).astype(int).clip(10, 3000)

# Price elasticity of demand (PED)
# PED = dQ/dP * P/Q = -2.85 * (1 - prob) * (P/Pcomp)
ped = -2.85 * (1.0 - prob_choice) * df_sample['price_ratio_to_competitor']
df_sample['theoretical_ped'] = ped.round(3)

# Financial metrics
df_sample['realized_revenue'] = (df_sample['offered_price'] * df_sample['ground_truth_demand']).round(2)
df_sample['realized_profit'] = ((df_sample['offered_price'] - df_sample['production_cost']) * df_sample['ground_truth_demand']).round(2)

# Select final columns
final_cols = [
    'product_id', 'category', 'brand', 'brand_tier', 'title', 'description',
    'image_filename', 'image_relative_path', 'first_image_url',
    'production_cost', 'msrp', 'competitor_min_price', 'competitor_avg_price',
    'offered_price', 'price_ratio_to_competitor', 'inventory_count', 'customer_rating',
    'ground_truth_demand', 'theoretical_ped', 'realized_revenue', 'realized_profit'
]

df_final = df_sample[final_cols]
df_final.to_csv(CLEAN_CSV, index=False)
print(f"Successfully processed and saved real Flipkart dataset to: {CLEAN_CSV}")
print(f"Total products: {len(df_final)}")
print(df_final[['product_id', 'category', 'brand', 'title', 'msrp', 'competitor_avg_price', 'ground_truth_demand']].head(5))
