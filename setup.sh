#!/usr/bin/env bash
# Ant Colony AI — Quick Automated Setup Wrapper
set -e

echo "==================================================================="
echo "   ANT COLONY AI — QUICK INSTALLER (PYTHON VIRTUALENV & SETUP)    "
echo "==================================================================="

# 1. Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[-] Python 3 topilmadi. Iltimos Python 3.10+ o'rnating."
    exit 1
fi

# 2. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "[*] Virtual muhit (venv) yaratilmoqda..."
    python3 -m venv venv
fi

echo "[*] Virtual muhit faollashtirilmoqda..."
source venv/bin/activate

# 3. Install Requirements
if [ -f "requirements.txt" ]; then
    echo "[*] Kerakli paketlar o'rnatilmoqda (pip install)..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
fi

# 4. Run Interactive Python Installer
python3 install.py
