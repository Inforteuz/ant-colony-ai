#!/usr/bin/env python3
"""
Ant Colony AI — Interactive Open-Source Installer & Setup Wizard
GitHub ochiq loyihasi uchun interaktiv o'rnatuvchi va API sozlagich.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"
SKILL_MATRIX_FILE = BASE_DIR / "model_skill_matrix.json"

BANNER = r"""
===================================================================
     _    _   _ _____    ____ ___  _     ___  _   ___   __
    / \  | \ | |_   _|  / ___/ _ \| |   / _ \| \ | \ \ / /
   / _ \ |  \| | | |   | |  | | | | |  | | | |  \| |\ V / 
  / ___ \| |\  | | |   | |__| |_| | |__| |_| | |\  | | |  
 /_/   \_\_| \_| |_|    \____\___/|_____\___/|_| \_| |_|  
                                                           
   ANT COLONY AI — AUTONOMOUS MULTI-AGENT PLATFORM (V2.0)
===================================================================
"""

def print_step(title: str):
    print(f"\n\033[1;36m>>> {title}\033[0m")

def print_success(msg: str):
    print(f"\033[1;32m[OK] {msg}\033[0m")

def print_warn(msg: str):
    print(f"\033[1;33m[OGOHLANTIRISH] {msg}\033[0m")

def print_err(msg: str):
    print(f"\033[1;31m[XATO] {msg}\033[0m")

def test_api_key(provider: str, key: str, base_url: str = None) -> bool:
    """API kalitini haqiqiy ping so'rovi bilan tekshiradi."""
    print(f"[*] `{provider}` provayderiga ulanish tekshirilmoqda...", end="", flush=True)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }

    test_url = "https://openrouter.ai/api/v1/models"
    if provider == "openrouter":
        test_url = "https://openrouter.ai/api/v1/models"
    elif provider == "gemini":
        test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        headers = {}
    elif provider == "openai":
        test_url = "https://api.openai.com/v1/models"
    elif provider == "groq":
        test_url = "https://api.groq.com/openai/v1/models"
    elif base_url:
        test_url = f"{base_url.rstrip('/')}/models"

    try:
        req = urllib.request.Request(test_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                print(" \033[1;32m[OK - Ulandi]\033[0m")
                return True
    except urllib.error.HTTPError as e:
        if e.code in (200, 400):  # ba'zi endpointlar get models bermaydi lekin kalit to'g'ri
            print(" \033[1;32m[OK]\033[0m")
            return True
        print(f" \033[1;31m[Rad etildi: HTTP {e.code}]\033[0m")
        return False
    except Exception as e:
        print(f" \033[1;33m[Ogohlantirish: {e}]\033[0m (Kiritilgan kalit saqlanadi)")
        return True
    return False

def save_env_config(config: dict):
    lines = [
        "# Ant Colony AI Environment Configuration",
        f"# Yaratilgan vaqt: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"PORT={config.get('PORT', '8088')}",
        f"HOST={config.get('HOST', '0.0.0.0')}",
        f"PROJECTS_BASE_DIR={config.get('PROJECTS_BASE_DIR', os.path.expanduser('~/Desktop/04_Loyihalar'))}",
        "",
        "# API Kalitlari",
        f"OPENROUTER_API_KEY={config.get('OPENROUTER_API_KEY', '')}",
        f"GEMINI_API_KEY={config.get('GEMINI_API_KEY', '')}",
        f"OPENAI_API_KEY={config.get('OPENAI_API_KEY', '')}",
        f"GROQ_API_KEY={config.get('GROQ_API_KEY', '')}",
        f"CUSTOM_API_KEY={config.get('CUSTOM_API_KEY', '')}",
        f"CUSTOM_BASE_URL={config.get('CUSTOM_BASE_URL', '')}",
        "",
        "# Default provider selection mode",
        f"SETUP_MODE={config.get('SETUP_MODE', 'single')}",
        f"PRIMARY_PROVIDER={config.get('PRIMARY_PROVIDER', 'openrouter')}",
    ]
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print_success(f"Sozlamalar `{ENV_FILE}` fayliga saqlandi.")

def create_start_script():
    start_sh = BASE_DIR / "start.sh"
    content = """#!/usr/bin/env bash
# Ant Colony AI — 1-klikda ishga tushirish skripti
set -e
cd "$(dirname "$0")"

echo ">>> Ant Colony AI serveri ishga tushmoqda..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python3 -m uvicorn server:app --host 0.0.0.0 --port 8088 --reload
"""
    start_sh.write_text(content, encoding="utf-8")
    start_sh.chmod(0o755)
    print_success("`start.sh` ishga tushirish skripti yaratildi.")

def main():
    print(BANNER)
    print("Xush kelibsiz! Ushbu sehrgar Ant Colony AI platformasini noldan sozlashga yordam beradi.\n")

    print("Qanday tartibda ishlatmoqchisiz?")
    print("  [1] Yagona API Provayder (Tavsiya etiladi - Faqat bitta OpenRouter/Gemini/OpenAI kaliti kifoya)")
    print("  [2] Gibrid / Ko'p Provayderli rejim (PM, Coder, QA uchun alohida kalitlar)")
    print("  [3] Lokal / Maxsus OpenAI-compatible endpoint (Ollama, LM Studio, vLLM)")
    
    choice = input("\nTanlovingizni kiriting [1-3] (standart: 1): ").strip() or "1"
    
    env_config = {
        "PORT": "8088",
        "HOST": "0.0.0.0",
        "PROJECTS_BASE_DIR": os.path.expanduser("~/Desktop/04_Loyihalar")
    }

    if choice == "1":
        env_config["SETUP_MODE"] = "single"
        print_step("1-REJIM: Yagona API Provayderni tanlang")
        print("  1. OpenRouter (DeepSeek V4, Nemotron, Claude, GPT, Llama bir joyda)")
        print("  2. Google Gemini (Gemini 2.5 Flash / Pro)")
        print("  3. OpenAI (GPT-4o, GPT-4o-mini)")
        print("  4. Groq (Juda tezkor Llama 3.3 / DeepSeek R1)")
        
        p_choice = input("Provayder raqami [1-4] (standart: 1): ").strip() or "1"
        
        if p_choice == "1":
            env_config["PRIMARY_PROVIDER"] = "openrouter"
            key = input("\nOpenRouter API kalitini kiriting (sk-or-v1-...): ").strip()
            if key:
                test_api_key("openrouter", key)
                env_config["OPENROUTER_API_KEY"] = key
        elif p_choice == "2":
            env_config["PRIMARY_PROVIDER"] = "gemini"
            key = input("\nGoogle Gemini API kalitini kiriting (AIzaSy...): ").strip()
            if key:
                test_api_key("gemini", key)
                env_config["GEMINI_API_KEY"] = key
        elif p_choice == "3":
            env_config["PRIMARY_PROVIDER"] = "openai"
            key = input("\nOpenAI API kalitini kiriting (sk-...): ").strip()
            if key:
                test_api_key("openai", key)
                env_config["OPENAI_API_KEY"] = key
        elif p_choice == "4":
            env_config["PRIMARY_PROVIDER"] = "groq"
            key = input("\nGroq API kalitini kiriting (gsk_...): ").strip()
            if key:
                test_api_key("groq", key)
                env_config["GROQ_API_KEY"] = key

    elif choice == "2":
        env_config["SETUP_MODE"] = "multi"
        print_step("2-REJIM: Gibrid / Ko'p Provayderli Sozlash")
        print("Mavjud kalitlaringizni kiriting (kerak bo'lmaganini Enter bilan bo'sh qoldiring):")
        
        or_key = input("1. OpenRouter API kaliti: ").strip()
        if or_key:
            test_api_key("openrouter", or_key)
            env_config["OPENROUTER_API_KEY"] = or_key
            
        gemini_key = input("2. Google Gemini API kaliti: ").strip()
        if gemini_key:
            test_api_key("gemini", gemini_key)
            env_config["GEMINI_API_KEY"] = gemini_key

        groq_key = input("3. Groq API kaliti: ").strip()
        if groq_key:
            test_api_key("groq", groq_key)
            env_config["GROQ_API_KEY"] = groq_key

        openai_key = input("4. OpenAI API kaliti: ").strip()
        if openai_key:
            test_api_key("openai", openai_key)
            env_config["OPENAI_API_KEY"] = openai_key

    elif choice == "3":
        env_config["SETUP_MODE"] = "custom"
        print_step("3-REJIM: Lokal yoki Maxsus Endpoint")
        base_url = input("Base URL (masalan, http://localhost:11434/v1): ").strip() or "http://localhost:11434/v1"
        cust_key = input("API kaliti (agar kerak bo'lmasa bo'sh qoldiring): ").strip() or "ollama"
        env_config["CUSTOM_BASE_URL"] = base_url
        env_config["CUSTOM_API_KEY"] = cust_key
        test_api_key("custom", cust_key, base_url)

    # Loyihalar papkasi
    print_step("Loyihalar saqlanadigan ishchi muhit papkasi")
    default_dir = os.path.expanduser("~/Desktop/04_Loyihalar")
    p_dir = input(f"Loyihalar katalogi [{default_dir}]: ").strip() or default_dir
    env_config["PROJECTS_BASE_DIR"] = p_dir
    Path(p_dir).mkdir(parents=True, exist_ok=True)

    # Saqlash
    save_env_config(env_config)
    create_start_script()

    print("\n" + "="*65)
    print_success("TABRIKLAYMIZ! ANT COLONY AI TO'LIQ SOZLANDI!")
    print("="*65)
    print("\nPlatformani ishga tushirish uchun:")
    print("  \033[1;32m./start.sh\033[0m")
    print("  yoki: \033[1;36mpython3 -m uvicorn server:app --host 0.0.0.0 --port 8088\033[0m\n")
    print("Web interfeys: \033[1;34mhttp://localhost:8088\033[0m\n")

if __name__ == "__main__":
    main()
