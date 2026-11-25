import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path(r"C:\Users\HP\.gemini\antigravity\brain\aed44f51-bec1-43f0-8633-f10bc019b4cd")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 900})

    print("Navigating to http://127.0.0.1:8501/ ...")
    page.goto("http://127.0.0.1:8501/")
    page.wait_for_timeout(2500)

    # Capture Tab 1: Live Optimizer
    p1 = ARTIFACT_DIR / "real_web_tab1_optimizer.png"
    page.screenshot(path=str(p1), full_page=False)
    print(f"Captured: {p1}")

    # Switch to Tab 2: Real Dataset
    page.click("#tab-btn-dataset")
    page.wait_for_timeout(1500)
    p2 = ARTIFACT_DIR / "real_web_tab2_dataset.png"
    page.screenshot(path=str(p2), full_page=False)
    print(f"Captured: {p2}")

    # Switch to Tab 3: Model Accuracy
    page.click("#tab-btn-evaluation")
    page.wait_for_timeout(1000)
    p3 = ARTIFACT_DIR / "real_web_tab3_evaluation.png"
    page.screenshot(path=str(p3), full_page=False)
    print(f"Captured: {p3}")

    # Switch to Tab 4: Architecture
    page.click("#tab-btn-architecture")
    page.wait_for_timeout(1000)
    p4 = ARTIFACT_DIR / "real_web_tab4_architecture.png"
    page.screenshot(path=str(p4), full_page=False)
    print(f"Captured: {p4}")

    browser.close()

print("All screenshots successfully captured!")
