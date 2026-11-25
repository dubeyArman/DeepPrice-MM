import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(r"F:\multimodal_dynamic_pricing")
OUTPUT_DIR = BASE_DIR / "docs_pdf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\HP\.gemini\antigravity\brain\aed44f51-bec1-43f0-8633-f10bc019b4cd")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fira+Code:wght@400;500;600&display=swap');

@page {
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
  @bottom-right {
    content: "Page " counter(page) " of " counter(pages);
    font-size: 9pt;
    color: #64748b;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }
}

* { box-sizing: border-box; }
body {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  color: #1e293b;
  line-height: 1.6;
  font-size: 10pt;
  background: #ffffff;
  margin: 0;
  padding: 0;
}

h1, h2, h3, h4 { color: #0f172a; font-weight: 800; margin-top: 1.4em; margin-bottom: 0.5em; page-break-after: avoid; }
h1 { font-size: 20pt; line-height: 1.2; border-bottom: 2px solid #2563eb; padding-bottom: 6px; }
h2 { font-size: 14pt; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; color: #1e3a8a; }
h3 { font-size: 11.5pt; color: #2563eb; }
h4 { font-size: 10.5pt; color: #334155; }

p { margin-top: 0; margin-bottom: 0.8em; }

.header-banner {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
  color: #ffffff;
  padding: 20px 24px;
  border-radius: 10px;
  margin-bottom: 22px;
}
.header-banner h1 { color: #ffffff; border: none; margin: 0 0 6px 0; padding: 0; font-size: 19pt; }
.header-banner p { color: #cbd5e1; margin: 0; font-size: 10pt; }
.header-banner .badge-row { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
.header-banner .badge {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #ffffff;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 8pt;
  font-weight: 700;
  text-transform: uppercase;
}

.table-custom {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0 18px 0;
  font-size: 9pt;
  page-break-inside: avoid;
}
.table-custom th, .table-custom td {
  border: 1px solid #cbd5e1;
  padding: 8px 10px;
  text-align: left;
}
.table-custom th {
  background-color: #f1f5f9;
  color: #0f172a;
  font-weight: 700;
}
.table-custom tr:nth-child(even) { background-color: #f8fafc; }

.callout {
  padding: 12px 16px;
  border-radius: 8px;
  margin: 14px 0;
  border-left: 4px solid;
  font-size: 9.5pt;
  page-break-inside: avoid;
}
.callout-info { background: #eff6ff; border-color: #2563eb; color: #1e3a8a; }
.callout-viva { background: #fefce8; border-color: #eab308; color: #713f12; }
.callout-success { background: #f0fdf4; border-color: #16a34a; color: #14532d; }
.callout-danger { background: #fef2f2; border-color: #dc2626; color: #991b1b; }

.callout-title {
  font-weight: 800;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  font-size: 8.5pt;
  letter-spacing: 0.5px;
}

pre, code {
  font-family: 'Fira Code', Consolas, monospace;
}
code {
  background: #f1f5f9;
  color: #0f172a;
  padding: 1.5px 5px;
  border-radius: 4px;
  font-size: 8.5pt;
  border: 1px solid #e2e8f0;
}
pre {
  background: #0f172a;
  color: #f8fafc;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 8.2pt;
  overflow-x: auto;
  line-height: 1.45;
  margin: 12px 0 16px 0;
  page-break-inside: avoid;
  border: 1px solid #334155;
}

.code-title {
  background: #1e293b;
  color: #94a3b8;
  font-family: 'Fira Code', monospace;
  font-size: 8pt;
  padding: 4px 12px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  margin-bottom: -12px;
  display: inline-block;
  font-weight: 600;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 12px 0;
}

.card {
  border: 1px solid #e2e8f0;
  background: #ffffff;
  border-radius: 8px;
  padding: 12px 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.viva-term {
  border: 1px solid #fed7aa;
  background: #fff7ed;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 10px;
  page-break-inside: avoid;
}
.viva-term strong {
  color: #9a3412;
  font-size: 9.5pt;
  display: block;
  margin-bottom: 3px;
}

.viva-qa {
  border-left: 3px solid #6366f1;
  background: #f8fafc;
  padding: 10px 14px;
  margin-bottom: 12px;
  border-radius: 0 6px 6px 0;
  page-break-inside: avoid;
}
.viva-qa .q { font-weight: 700; color: #1e1b4b; margin-bottom: 4px; }
.viva-qa .a { color: #334155; font-size: 9pt; }

.page-break { page-break-before: always; }
"""

print("Base setup ready.")
