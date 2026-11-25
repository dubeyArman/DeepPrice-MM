import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(r"F:\multimodal_dynamic_pricing")
OUTPUT_DIR = BASE_DIR / "docs_pdf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\HP\.gemini\antigravity\brain\aed44f51-bec1-43f0-8633-f10bc019b4cd")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

from build_docs_base import COMMON_CSS

html_platform_models = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DeepPrice-MM: Training Platform & AI Models Guide</title>
  <style>
    {COMMON_CSS}
  </style>
</head>
<body>

  <div class="header-banner">
    <h1>DeepPrice-MM: Training Platform & AI Models Guide</h1>
    <p>Comprehensive Viva Reference: Where the Model Was Trained, Platform Environment, and Exact AI Architectures</p>
    <div class="badge-row">
      <span class="badge">Hardware & Platform</span>
      <span class="badge">AI Model Backbones</span>
      <span class="badge">Step-by-Step Training</span>
      <span class="badge">Viva Defense Cheat Sheet</span>
    </div>
  </div>

  <h2>1. Platform & Environment Specifications (Where It Was Trained)</h2>
  <p>
    The model was developed, preprocessed, trained, and deployed locally on a dedicated Python machine learning workstation. Below are the exact platform specifications to tell your professor:
  </p>

  <table class="table-custom">
    <thead>
      <tr>
        <th>Component</th>
        <th>Specification / Platform Used</th>
        <th>Description & Purpose</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Operating System</strong></td>
        <td>Microsoft Windows 11 (x64)</td>
        <td>Host operating system for local development, data caching, and server hosting.</td>
      </tr>
      <tr>
        <td><strong>Programming Language</strong></td>
        <td>Python 3.14 (Virtual Environment: <code>.venv</code>)</td>
        <td>Modern runtime executing PyTorch, Scikit-learn, Sentence-Transformers, and FastAPI.</td>
      </tr>
      <tr>
        <td><strong>Deep Learning Framework</strong></td>
        <td>PyTorch 2.x (<code>torch</code> & <code>torch.nn</code>)</td>
        <td>Constructs dynamic computation graphs, handles automatic differentiation (autograd), and executes GPU/CPU tensor backpropagation.</td>
      </tr>
      <tr>
        <td><strong>Dataset Platform</strong></td>
        <td>Kaggle (PromptCloud Flipkart Products Dataset)</td>
        <td>Public benchmark repository sourcing 20,000 real Indian e-commerce listings with authentic prices and images.</td>
      </tr>
      <tr>
        <td><strong>Training Execution Environment</strong></td>
        <td>Local Python Script Pipeline (<code>train_real_model.py</code>)</td>
        <td>Executed in terminal using PyTorch DataLoader batches (batch size = 32, AdamW optimizer).</td>
      </tr>
      <tr>
        <td><strong>Deployment & Serving Server</strong></td>
        <td>FastAPI ASGI Web Server hosted via Uvicorn</td>
        <td>Runs locally at <code>http://127.0.0.1:8501/</code> providing real-time REST API pricing inference (&lt;15ms latency).</td>
      </tr>
      <tr>
        <td><strong>Browser Testing Platform</strong></td>
        <td>Microsoft Playwright (Headless Chromium)</td>
        <td>Automated end-to-end user flow verification across all 1,200 products.</td>
      </tr>
    </tbody>
  </table>

  <h2>2. Which AI Models We Have Used</h2>
  <p>
    Our system is not a single generic model; it is a <strong>composite Multimodal Deep Neural Network</strong> combining two pre-trained foundation models with custom neural projection and attention fusion layers:
  </p>

  <div class="card" style="margin-bottom: 14px;">
    <h3 style="margin-top: 0;">1. Vision Model: ResNet-18 (Residual Neural Network)</h3>
    <ul>
      <li><strong>Origin:</strong> Developed by Microsoft Research (He et al.), pre-trained on the 1.2-million-image <strong>ImageNet-1k</strong> dataset via <code>torchvision.models.resnet18</code>.</li>
      <li><strong>Architecture:</strong> 18-layer deep convolutional neural network with residual skip connections that eliminate the vanishing gradient problem.</li>
      <li><strong>Role in Our Project:</strong> Evaluates 224&times;224 RGB product photos. We stripped the final 1,000-class classification head and extracted the <strong>512-dimensional penultimate average-pooled feature vector</strong>. It quantifies packaging aesthetics, materials, build quality, and visual luxury cues.</li>
      <li><strong>Why ResNet-18:</strong> Lightweight (~45 MB), extremely fast inference (under 10ms per image), and proven capability to capture visual texture and finish without overfitting small datasets.</li>
    </ul>
  </div>

  <div class="card" style="margin-bottom: 14px;">
    <h3 style="margin-top: 0;">2. NLP / Text Model: Sentence-BERT (all-MiniLM-L6-v2)</h3>
    <ul>
      <li><strong>Origin:</strong> Transformer architecture developed by UKP Lab / Hugging Face, fine-tuned on over 1 billion sentence pairs for semantic similarity.</li>
      <li><strong>Architecture:</strong> 6-layer MiniLM Transformer with 12 self-attention heads and 384 hidden dimensions.</li>
      <li><strong>Role in Our Project:</strong> Tokenizes and encodes the concatenated <code>product_title + " - " + description</code> into a <strong>384-dimensional dense semantic embedding</strong>.</li>
      <li><strong>Why Sentence-BERT over TF-IDF:</strong> Standard keyword matching (TF-IDF) is blind to context. Sentence-BERT understands technical specifications, warranty guarantees, brand authority, and synonyms (e.g., recognizing that "genuine leather" and "premium hide" represent the same high-tier feature).</li>
    </ul>
  </div>

  <div class="card" style="margin-bottom: 14px;">
    <h3 style="margin-top: 0;">3. Tabular Econometric MLP (Multi-Layer Perceptron)</h3>
    <ul>
      <li><strong>Architecture:</strong> Custom 2-layer dense feedforward network: <code>Linear(8 &rarr; 64) &rarr; BatchNorm1d &rarr; ReLU &rarr; Dropout(0.15) &rarr; Linear(64 &rarr; 128) &rarr; BatchNorm1d &rarr; ReLU</code>.</li>
      <li><strong>Inputs:</strong> 8 numeric market indicators: manufacturing cost, catalog MSRP, competitor min price, competitor avg price, price ratio, stock count, and review rating.</li>
      <li><strong>Role:</strong> Encodes quantitative market boundaries and pricing benchmarks into the same 128-d latent space.</li>
    </ul>
  </div>

  <div class="page-break"></div>

  <div class="card" style="margin-bottom: 14px;">
    <h3 style="margin-top: 0;">4. Cross-Modal Fusion Model: Multi-Head Cross-Attention Layer</h3>
    <ul>
      <li><strong>Architecture:</strong> <code>nn.MultiheadAttention(embed_dim=128, num_heads=4)</code> followed by a residual connection (<code>modalities + attn_out</code>) and Layer Normalization (<code>nn.LayerNorm(128)</code>).</li>
      <li><strong>Role:</strong> Stacks the visual token, text token, and tabular token into a sequence <code>[Batch, 3, 128]</code>. The attention mechanism dynamically computes inter-modal correlation weights (e.g., determining whether high visual quality justifies pricing above the competitor average).</li>
    </ul>
  </div>

  <div class="card" style="margin-bottom: 14px;">
    <h3 style="margin-top: 0;">5. Dual Prediction Heads</h3>
    <ul>
      <li><strong>Demand Prediction Head:</strong> <code>Linear(128 &rarr; 64) &rarr; ReLU &rarr; Linear(64 &rarr; 1)</code>. Predicts expected customer order volume $Q(p)$ for any candidate price point.</li>
      <li><strong>Price Elasticity Head:</strong> <code>Linear(128 &rarr; 64) &rarr; ReLU &rarr; Linear(64 &rarr; 1) &rarr; -Softplus</code>. Predicts negative price elasticity $\\varepsilon(p) \\le 0$ enforcing downward-sloping demand curves.</li>
    </ul>
  </div>

  <h2>3. Step-by-Step Training Pipeline (How It Was Trained)</h2>
  
  <div class="callout callout-info">
    <div class="callout-title">Chronological 7-Step Training Lifecycle</div>
    <ol style="margin-top: 6px; padding-left: 20px;">
      <li><strong>Step 1: Download from Kaggle:</strong> Ingested <code>flipkart_com-ecommerce_sample.csv</code> (38 MB) containing raw web-scraped listings.</li>
      <li><strong>Step 2: Clean & Balance Data:</strong> Executed <code>prepare_real_dataset.py</code> to filter corrupt rows, extract image URLs, and sample 1,200 products equally balanced across 6 categories. Downloaded photos into <code>data/real_images/</code>.</li>
      <li><strong>Step 3: Extract & Cache Embeddings:</strong> Ran <code>train_real_model.py</code> to extract 512-d ResNet-18 vectors and 384-d Sentence-BERT vectors, saving them to <code>.npy</code> cache files for millisecond retrieval.</li>
      <li><strong>Step 4: Train Deep Neural Network:</strong> Trained <code>FastMultimodalNet</code> on 85% training data using PyTorch with AdamW optimizer (learning rate $2 \\times 10^{{-3}}$) and MSE Loss for 15 epochs. Checked validation loss each epoch and saved the best checkpoint to <code>best_multimodal_pricing_model.pth</code>.</li>
      <li><strong>Step 5: Run Comparative Ablation Study:</strong> Trained 3 baseline models (Tabular Only, Vision+Tabular, Text+Tabular) on the identical splits. Confirmed our proposed multimodal model achieved the lowest error (15.11% MAPE).</li>
      <li><strong>Step 6: Mathematical Profit Optimization:</strong> In <code>optimizer.py</code>, formulated the economic profit objective $\\Pi(p) = (p - \\text{{cost}}) \\times Q(p)$ and evaluated 50 candidate price points to identify the global profit peak $p^*$.</li>
      <li><strong>Step 7: Launch FastAPI Web Dashboard:</strong> Hosted <code>app.py</code> on local port 8501 via Uvicorn, serving the interactive frontend and real-time inference APIs.</li>
    </ol>
  </div>

  <h2>4. Quick Viva Cheat Sheet (Questions the Teacher Will Ask)</h2>
  <div class="viva-qa">
    <div class="q">Q1: On what platform did you train this model? Did you use AWS/GCP or a local machine?</div>
    <div class="a">A: We trained the model locally on our workstation in Python 3.14 using the PyTorch deep learning framework. The raw e-commerce dataset was sourced from Kaggle (Flipkart Products Dataset), and the production model is served locally via a high-performance FastAPI server running on Uvicorn.</div>
  </div>

  <div class="viva-qa">
    <div class="q">Q2: Exactly which AI models did you use?</div>
    <div class="a">A: We used a multimodal architecture combining two foundation models: <strong>ResNet-18</strong> (pre-trained on ImageNet) for visual packaging analysis, and <strong>Sentence-BERT (all-MiniLM-L6-v2)</strong> for natural language semantic understanding, fused together with a custom <strong>4-head PyTorch Cross-Attention layer</strong>.</div>
  </div>

  <div class="viva-qa">
    <div class="q">Q3: Why not train a Convolutional Neural Network from scratch?</div>
    <div class="a">A: Training a vision network from scratch requires millions of labeled images and days of GPU compute. By using <strong>Transfer Learning</strong> with pre-trained ResNet-18, we leverage low-level visual features (edges, textures, finishes) learned on ImageNet and adapt them to e-commerce pricing with high accuracy on our 1,200 curated products.</div>
  </div>

</body>
</html>
"""

html_path = OUTPUT_DIR / "DeepPrice_Platform_and_AI_Models_Guide.html"
pdf_path = OUTPUT_DIR / "DeepPrice_Platform_and_AI_Models_Guide.pdf"
artifact_pdf = ARTIFACT_DIR / "DeepPrice_Platform_and_AI_Models_Guide.pdf"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_platform_models)

print("Rendering Platform & AI Models Guide PDF with Playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file:///{str(html_path).replace(os.sep, '/')}")
    page.wait_for_timeout(1000)
    page.pdf(path=str(pdf_path), format="A4", print_background=True, margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"})
    page.pdf(path=str(artifact_pdf), format="A4", print_background=True, margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"})
    browser.close()

print(f"Platform and AI Models Guide PDF successfully created: {pdf_path}")
