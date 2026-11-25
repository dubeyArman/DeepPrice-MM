import os
import sys
import time
import socket
import threading
import webbrowser
import urllib.request
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = r"F:\competitor_pricing_intel\.venv\Scripts\python.exe"
URL = "http://127.0.0.1:8501/"


def is_server_running(host="127.0.0.1", port=8501):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def open_browser_when_ready():
    """Polls the local server until it returns HTTP 200, then opens the default browser."""
    for _ in range(90):
        try:
            with urllib.request.urlopen(URL, timeout=2) as resp:
                if resp.status == 200:
                    print(f"\n[OK] Server is ready! Opening {URL} in your browser...\n")
                    webbrowser.open(URL)
                    return
        except Exception:
            pass
        time.sleep(0.5)
    print(f"\n[!] Server took longer than expected. Please open {URL} manually.")


def main():
    print("==========================================================================")
    print("   DeepPrice-MM : Multimodal Dynamic Pricing Engine")
    print("==========================================================================\n")

    if is_server_running():
        print(f"[OK] DeepPrice-MM server is already running at {URL}")
        print("Opening web browser now...")
        webbrowser.open(URL)
        time.sleep(2)
        return

    print("[1/2] Starting Deep Learning Server (PyTorch + ResNet-18 + Sentence-BERT)...")
    print("      Please wait ~5-10 seconds while AI models load into memory...")
    print("      Your browser will open automatically as soon as it is ready!\n")
    print("[2/2] Keep this window open during your presentation. Close it to stop.\n")

    # Launch background browser-opener thread
    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    # Launch Uvicorn server in foreground
    cmd = [
        PYTHON_EXE,
        "-m", "uvicorn",
        "app:app",
        "--app-dir", str(BASE_DIR),
        "--host", "127.0.0.1",
        "--port", "8501",
    ]
    try:
        subprocess.run(cmd, cwd=str(BASE_DIR), check=False)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"\n[ERROR] Failed to start server: {e}")
        input("\nPress Enter to close this window...")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}")
        input("\nPress Enter to close this window...")
