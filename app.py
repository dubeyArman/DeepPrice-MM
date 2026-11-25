import sys
import json
import math
import base64
import io
from pathlib import Path
from PIL import Image
import numpy as np

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
METRICS_JSON_PATH = DATA_DIR / "ablation_evaluation_results.json"
CSV_PATH = DATA_DIR / "flipkart_ecommerce_real_dataset.csv"

sys.path.insert(0, str(BASE_DIR))
from optimizer import MultimodalPriceOptimizer

app = FastAPI(
    title="DeepPrice-MM | Real E-Commerce Dynamic Pricing",
    description="Multimodal Dynamic Pricing Engine trained on Real Flipkart Web Dataset (Vision + Text Transformers + Competitor Pricing)",
    version="2.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount data directory for real images & plots
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")

optimizer_instance = None

def get_optimizer():
    global optimizer_instance
    if optimizer_instance is None:
        logger.info("Initializing MultimodalPriceOptimizer...")
        optimizer_instance = MultimodalPriceOptimizer()
        logger.info("MultimodalPriceOptimizer ready!")
    return optimizer_instance


@app.get("/", response_class=FileResponse)
def serve_home():
    html_file = TEMPLATES_DIR / "index.html"
    return FileResponse(html_file)


@app.get("/api/sample-products")
def get_sample_products():
    """Returns 8 diverse real products from the Flipkart dataset for instant 1-click testing."""
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = pd.read_csv(CSV_PATH)
    
    # Select diverse representative products across categories
    samples = []
    categories = df["category"].unique()
    for cat in categories:
        sub = df[df["category"] == cat]
        if len(sub) > 0:
            row = sub.iloc[0]
            samples.append({
                "product_id": str(row["product_id"]),
                "category": str(row["category"]),
                "title": str(row["title"]),
                "description": str(row["description"]),
                "brand": str(row["brand"]) if pd.notna(row["brand"]) else "Flipkart Brand",
                "cost": float(row["production_cost"]),
                "msrp": float(row["msrp"]),
                "comp_min": float(row["competitor_min_price"]),
                "comp_avg": float(row["competitor_avg_price"]),
                "image_url": f"/{str(row['image_relative_path']).replace('\\', '/')}",
                "inventory": int(row["inventory_count"]),
                "rating": float(row["customer_rating"]),
            })
    
    # Also add 2 more popular high-ticket/distinct items if available
    if len(df) > 10:
        for extra_idx in [10, 25]:
            if extra_idx < len(df):
                row = df.iloc[extra_idx]
                samples.append({
                    "product_id": str(row["product_id"]),
                    "category": str(row["category"]),
                    "title": str(row["title"]),
                    "description": str(row["description"]),
                    "brand": str(row["brand"]) if pd.notna(row["brand"]) else "Flipkart Brand",
                    "cost": float(row["production_cost"]),
                    "msrp": float(row["msrp"]),
                    "comp_min": float(row["competitor_min_price"]),
                    "comp_avg": float(row["competitor_avg_price"]),
                    "image_url": f"/{str(row['image_relative_path']).replace('\\', '/')}",
                    "inventory": int(row["inventory_count"]),
                    "rating": float(row["customer_rating"]),
                })

    return samples


@app.get("/api/product/{product_id}")   #. When a user clicks "Test Price" on any of the 1,200 products in the dataset table, this endpoint retrieves the exact authentic specifications, image, and competitor prices for instant loading into the optimizer.
def get_product_by_id(product_id: str):
    """Returns the full record for any SKU in the dataset."""
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = pd.read_csv(CSV_PATH)
    matches = df[df["product_id"].astype(str) == product_id.strip()]
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail=f"Product ID '{product_id}' not found")
    row = matches.iloc[0]
    return {
        "product_id": str(row["product_id"]),
        "category": str(row["category"]),
        "title": str(row["title"]),
        "description": str(row["description"]),
        "brand": str(row["brand"]) if pd.notna(row["brand"]) else "Flipkart Brand",
        "cost": float(row["production_cost"]),
        "msrp": float(row["msrp"]),
        "comp_min": float(row["competitor_min_price"]),
        "comp_avg": float(row["competitor_avg_price"]),
        "image_url": f"/{str(row['image_relative_path']).replace('\\', '/')}",
        "inventory": int(row["inventory_count"]),
        "rating": float(row["customer_rating"]),
    }


@app.get("/api/dataset-records")
def get_dataset_records(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    query: str = Query("", max_length=100),
    category: str = Query("", max_length=50)
):
    """Searchable & filterable browse endpoint for the real Flipkart e-commerce dataset."""
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = pd.read_csv(CSV_PATH)
    
    if category and category.lower() != "all":
        df = df[df["category"].astype(str).str.lower() == category.lower()]

    if query:
        q_lower = query.lower()
        title_mask = df["title"].astype(str).str.lower().str.contains(q_lower, na=False)
        cat_mask = df["category"].astype(str).str.lower().str.contains(q_lower, na=False)
        brand_mask = df["brand"].astype(str).str.lower().str.contains(q_lower, na=False)
        df = df[title_mask | cat_mask | brand_mask]
    
    total = len(df)
    start = (page - 1) * limit
    end = start + limit
    page_df = df.iloc[start:end]
    
    items = []
    for _, r in page_df.iterrows():
        items.append({
            "product_id": str(r["product_id"]),
            "category": str(r["category"]),
            "brand": str(r["brand"]) if pd.notna(r["brand"]) else "Flipkart Brand",
            "title": str(r["title"])[:75] + ("..." if len(str(r["title"])) > 75 else ""),
            "full_title": str(r["title"]),
            "description": str(r["description"]),
            "cost": float(r["production_cost"]),
            "msrp": float(r["msrp"]),
            "competitor_price": float(r["competitor_avg_price"]),
            "customer_rating": float(r["customer_rating"]),
            "demand": int(r["ground_truth_demand"]),
            "image_url": f"/{str(r['image_relative_path']).replace('\\', '/')}",
        })
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items,
        "dataset_source": "Flipkart Real E-Commerce Dataset (GitHub/Kaggle)"
    }


@app.get("/api/evaluation-metrics")
def get_evaluation_metrics():
    """Returns the scientific ablation study results and revenue lift benchmarks."""
    if not METRICS_JSON_PATH.exists():
        raise HTTPException(status_code=404, detail="Metrics file not found.")
    with open(METRICS_JSON_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    return metrics


ALLOWED_PEARSON_COLS = {
    "production_cost": "Production Cost (₹)",
    "msrp": "Retail MSRP (₹)",
    "competitor_avg_price": "Competitor Avg Price (₹)",
    "offered_price": "Offered Price (₹)",
    "price_ratio_to_competitor": "Price Ratio to Competitor",
    "customer_rating": "Customer Rating (Stars)",
    "brand_tier": "Brand Tier",
    "inventory_count": "Inventory Stock",
    "ground_truth_demand": "Unit Demand",
    "theoretical_ped": "Price Elasticity (PED)",
}


def compute_pearson_formula(x_vals: np.ndarray, y_vals: np.ndarray) -> dict:
    """
    Explicit implementation of the Pearson Product-Moment Correlation Coefficient (r):
      r = sum((x_i - x_mean) * (y_i - y_mean)) / sqrt(sum((x_i - x_mean)^2) * sum((y_i - y_mean)^2))
    """
    n = len(x_vals)
    x_mean = float(np.mean(x_vals))
    y_mean = float(np.mean(y_vals))
    dx = x_vals - x_mean
    dy = y_vals - y_mean

    numerator = float(np.sum(dx * dy))
    sum_sq_x = float(np.sum(dx ** 2))
    sum_sq_y = float(np.sum(dy ** 2))
    denominator = math.sqrt(sum_sq_x * sum_sq_y)

    r = (numerator / denominator) if denominator > 0 else 0.0
    r_squared = r ** 2

    abs_r = abs(r)
    if abs_r >= 0.70:
        strength = "Strong"
    elif abs_r >= 0.35:
        strength = "Moderate"
    elif abs_r >= 0.10:
        strength = "Weak"
    else:
        strength = "Negligible"

    direction = "Positive" if r > 0.02 else ("Negative" if r < -0.02 else "Neutral")
    label = f"{strength} {direction} Correlation" if strength != "Negligible" else "No Significant Linear Correlation"

    return {
        "n": n,
        "x_mean": round(x_mean, 4),
        "y_mean": round(y_mean, 4),
        "numerator": round(numerator, 2),
        "denominator": round(denominator, 2),
        "pearson_r": round(r, 4),
        "r_squared": round(r_squared, 4),
        "variance_explained_pct": round(r_squared * 100, 2),
        "strength": strength,
        "direction": direction,
        "interpretation": label,
    }


@app.get("/api/pearson-correlation")
def get_pearson_correlation(
    x_col: str = Query("msrp"),
    y_col: str = Query("ground_truth_demand"),
    category: str = Query("all"),
):
    """Computes live Pearson Correlation Coefficient (r) between any two dataset features."""
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    if x_col not in ALLOWED_PEARSON_COLS or y_col not in ALLOWED_PEARSON_COLS:
        raise HTTPException(status_code=400, detail="Invalid column selected for Pearson correlation.")

    df = pd.read_csv(CSV_PATH)
    if category and category.lower() != "all":
        df = df[df["category"].astype(str).str.lower() == category.lower()]

    x_vals = df[x_col].astype(float).values
    y_vals = df[y_col].astype(float).values

    result = compute_pearson_formula(x_vals, y_vals)
    result["x_col"] = x_col
    result["y_col"] = y_col
    result["x_label"] = ALLOWED_PEARSON_COLS[x_col]
    result["y_label"] = ALLOWED_PEARSON_COLS[y_col]
    result["category"] = category
    return result


@app.post("/api/optimize")   # It accepts both standard form fields and multipart image uploads
async def optimize_price(
    title: str = Form(...),
    description: str = Form(...),
    cost: float = Form(...),
    msrp: float = Form(...),
    comp_min: float = Form(...),
    comp_avg: float = Form(...),
    inventory: int = Form(150),
    rating: float = Form(4.3),
    image_file: UploadFile = File(None),
    image_url: str = Form(None),
):
    """
    Multimodal Optimization Endpoint:
    Processes product image (ResNet-18), text description (Sentence-BERT),
    and competitor prices through the trained Multimodal Cross-Attention Network.
    """
    opt = get_optimizer()

    # Load image
    if image_file and image_file.filename:
        content = await image_file.read()
        pil_img = Image.open(io.BytesIO(content)).convert("RGB")
    elif image_url:
        clean_path = image_url.lstrip("/")
        full_path = BASE_DIR / clean_path
        if full_path.exists():
            pil_img = Image.open(full_path).convert("RGB")
        else:
            pil_img = Image.new("RGB", (224, 224), color=(220, 225, 235))
    else:
        pil_img = Image.new("RGB", (224, 224), color=(220, 225, 235))

    result = opt.optimize(
        image=pil_img,
        title=title,
        description=description,
        cost=cost,
        msrp=msrp,
        comp_min=comp_min,
        comp_avg=comp_avg,
        inventory=inventory,
        rating=rating,
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8501, reload=True)
