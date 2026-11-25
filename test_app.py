import requests
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8501"

print("1. Testing GET / (Home page)...")
r = requests.get(f"{BASE_URL}/")
assert r.status_code == 200, f"Home page failed: {r.status_code}"
assert "DeepPrice-MM" in r.text
print("   Passed! Status:", r.status_code)

print("2. Testing GET /api/sample-products (Real Flipkart presets)...")
r = requests.get(f"{BASE_URL}/api/sample-products")
assert r.status_code == 200, f"Sample products failed: {r.status_code}"
samples = r.json()
assert len(samples) >= 5, f"Expected at least 5 categories, got {len(samples)}"
print(f"   Passed! Received {len(samples)} real category samples:")
for s in samples:
    print(f"   - {s['category']}: {s['title'][:40]}... (₹{s['comp_avg']})")

print("3. Testing GET /api/dataset-records (Real dataset table browse)...")
r = requests.get(f"{BASE_URL}/api/dataset-records?page=1&limit=5")
assert r.status_code == 200, f"Dataset records failed: {r.status_code}"
data = r.json()
assert data["total"] == 1200
print(f"   Passed! Total real dataset SKUs: {data['total']}")

print("4. Testing GET /api/evaluation-metrics...")
r = requests.get(f"{BASE_URL}/api/evaluation-metrics")
assert r.status_code == 200, f"Metrics failed: {r.status_code}"
metrics = r.json()
print("   Passed! Dataset Source:", metrics.get("dataset_source"))
print("   Dynamic Revenue Lift:", metrics["revenue_optimization"]["revenue_lift_pct"], "%")

print("5. Testing POST /api/optimize (Live multimodal inference)...")
test_payload = {
    "title": samples[0]["title"],
    "description": samples[0]["description"],
    "cost": samples[0]["cost"],
    "msrp": samples[0]["msrp"],
    "comp_min": samples[0]["comp_min"],
    "comp_avg": samples[0]["comp_avg"],
    "image_url": samples[0]["image_url"],
    "inventory": 150,
    "rating": 4.2
}
r = requests.post(f"{BASE_URL}/api/optimize", data=test_payload)
assert r.status_code == 200, f"Optimize endpoint failed: {r.status_code} {r.text}"
res = r.json()
print("   Passed! Optimization Output:")
print("   - Recommended Price: ₹", res["recommended_optimal_price"])
print("   - Expected Demand: ", res["expected_demand_at_optimal"], "units")
print("   - Profit Lift: ", res["profit_lift_pct"], "%")
print("   - Attention Weights: ", res["multimodal_attention_weights"])

print("\nALL ENDPOINTS 100% OPERATIONAL & VERIFIED!")
