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
    elif provider == "17_wtf":
        test_url = "https://api.17.wtf/v1/models"
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
    # Birlashtirish (merge): mavjud .env dagi foydalanuvchi kalitlari va izohlar
    # saqlanadi; faqat sehrgar o'zgartirgan `managed` ro'yxatdagi o'zgaruvchilar
    # yangilanadi. To'liq ustiga yozish avval AGENT_* kabi maxsus sozlamalarni
    # yo'qotardi. SETUP_MODE / PRIMARY_PROVIDER ilova tomonidan IG'NOR qilinadi —
    # yozilmaydi va mavjud bo'lsa o'chirib tashlanadi (tozalik uchun).
    managed = [
        "ANT_HOST", "ANT_PORT", "ANT_RELOAD", "PROJECTS_BASE_DIR",
        "OPENROUTER_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY",
        "GITHUB_TOKEN", "WTF_API_KEY", "CUSTOM_API_KEY", "CUSTOM_BASE_URL",
    ]
    drop = {"SETUP_MODE", "PRIMARY_PROVIDER"}

    lines = []
    seen = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in drop:
                    continue  # eski/ignored o'zgaruvchini o'chirib tashlaymiz
                seen[k] = len(lines)
            lines.append(raw)

    for key in managed:
        val = config.get(key, "")
        if val == "":
            continue  # bo'sh qiymat — mavjud kalitni saqlaymiz (o'chirmaymiz)
        newline = f"{key}={val}"
        if key in seen:
            lines[seen[key]] = newline
        else:
            lines.append(newline)

    content = "\n".join(lines)
    if not ENV_FILE.exists():
        content = (
            "# Ant Colony AI Environment Configuration\n"
            f"# Yaratilgan vaqt: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            + content
        )
    ENV_FILE.write_text(content + "\n", encoding="utf-8")
    print_success("Sozlamalar `.env` fayliga saqlandi (mavjud kalitlar saqlanib qoldi).")

def create_start_script():
    start_sh = BASE_DIR / "start.sh"
    # `python run.py` ant_colony.server:app ni ishga tushiradi va ANT_HOST /
    # ANT_PORT / ANT_RELOAD o'zgaruvchilarini .env dan o'qiydi. Eski
    # `server:app` modul yo'li noto'g'ri edi (bunday modul mavjud emas).
    content = """#!/usr/bin/env bash
# Ant Colony AI — 1-klikda ishga tushirish skripti
set -e
cd "$(dirname "$0")"

echo ">>> Ant Colony AI serveri ishga tushmoqda..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python run.py
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
        "ANT_PORT": "8080",
        "ANT_HOST": "127.0.0.1",
        "ANT_RELOAD": "0",
        "PROJECTS_BASE_DIR": os.path.expanduser("~/Desktop/04_Loyihalar")
    }

    if choice == "1":
        env_config["SETUP_MODE"] = "single"
        print_step("1-REJIM: Yagona API Provayderni tanlang")
        print("  1. OpenRouter (DeepSeek V4, Nemotron, Claude, GPT, Llama bir joyda)")
        print("  2. Google Gemini (Gemini 2.5 Flash / Pro)")
        print("  3. OpenAI (GPT-4o, GPT-4o-mini)")
        print("  4. Groq (Juda tezkor Llama 3.3 / DeepSeek R1)")
        print("  5. 17.wtf (mutlaqo tekin modellar: posiden/*, elon/grok-4.5-free)")
        
        p_choice = input("Provayder raqami [1-5] (standart: 1): ").strip() or "1"
        
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
        elif p_choice == "5":
            env_config["PRIMARY_PROVIDER"] = "17_wtf"
            key = input("\n17.wtf API kalitini kiriting (sk-lm0-...): ").strip()
            if key:
                test_api_key("17_wtf", key)
                env_config["WTF_API_KEY"] = key

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

        wtf_key = input("5. 17.wtf API kaliti: ").strip()
        if wtf_key:
            test_api_key("17_wtf", wtf_key)
            env_config["WTF_API_KEY"] = wtf_key

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
    print("  yoki: \033[1;36mpython run.py\033[0m")
    print("  yoki: \033[1;36mpython3 -m uvicorn ant_colony.server:app --host 127.0.0.1 --port 8080\033[0m\n")
    print("Web interfeys: \033[1;34mhttp://localhost:8080\033[0m\n")

if __name__ == "__main__":
    main()
