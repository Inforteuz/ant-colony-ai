"""
Telegram Bot Integration for Ant Colony AI Platform.
Enables remote execution of AI Swarm tasks, status tracking, and file downloads directly via Telegram.
"""
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "telegram_config.json"

logger = logging.getLogger("telegram_bot")

class TelegramBotManager:
    def __init__(self):
        self.config: Dict[str, Any] = self.load_config()
        self.is_running: bool = False
        self.bot_info: Optional[Dict[str, Any]] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    def load_config(self) -> Dict[str, Any]:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading telegram config: {e}")
        
        return {
            "token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "enabled": bool(os.getenv("TELEGRAM_BOT_ENABLED", "false").lower() in ("1", "true", "yes")),
            "allowed_chat_ids": [],
            "notify_on_complete": True
        }

    def save_config(self, token: Optional[str] = None, enabled: Optional[bool] = None, allowed_chat_ids: Optional[List[int]] = None):
        if token is not None:
            self.config["token"] = token.strip()
        if enabled is not None:
            self.config["enabled"] = enabled
        if allowed_chat_ids is not None:
            self.config["allowed_chat_ids"] = allowed_chat_ids

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Checks if a bot token is valid via Telegram getMe API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"https://api.telegram.org/bot{token.strip()}/getMe")
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        return data.get("result")
        except Exception as e:
            logger.error(f"Telegram verify_token error: {e}")
        return None

    async def start(self) -> bool:
        """Starts long-polling loop in background."""
        token = self.config.get("token")
        if not token:
            logger.warning("Cannot start Telegram Bot: Token is empty")
            return False

        self.bot_info = await self.verify_token(token)
        if not self.bot_info:
            logger.error("Telegram Bot Token verification failed")
            return False

        if self.is_running:
            return True

        self.is_running = True
        self._http_client = httpx.AsyncClient(timeout=45.0)
        self._polling_task = asyncio.create_task(self._polling_loop())
        logger.info(f"Telegram Bot @{self.bot_info.get('username')} started successfully")
        return True

    async def stop(self):
        """Stops the polling loop."""
        self.is_running = False
        if self._polling_task:
            self._polling_task.cancel()
            self._polling_task = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("Telegram Bot stopped")

    async def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
        """Sends a message to a specific chat."""
        token = self.config.get("token")
        if not token or not self.is_running or not self._http_client:
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            res = await self._http_client.post(url, json=payload, timeout=15.0)
            if res.status_code != 200 and parse_mode:
                # Fallback to plain text if Markdown format error
                payload.pop("parse_mode", None)
                await self._http_client.post(url, json=payload, timeout=15.0)
            return True
        except Exception as e:
            logger.error(f"Failed to send telegram message: {e}")
            return False

    async def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> bool:
        """Uploads and sends a file to Telegram."""
        token = self.config.get("token")
        if not token or not file_path.exists():
            return False

        url = f"https://api.telegram.org/bot{token}/sendDocument"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(file_path, "rb") as f:
                    files = {"document": (file_path.name, f)}
                    data = {"chat_id": chat_id, "caption": caption[:1024]}
                    res = await client.post(url, data=data, files=files)
                    return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send telegram document: {e}")
            return False

    async def _polling_loop(self):
        offset = 0
        token = self.config.get("token")

        while self.is_running:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30"
                res = await self._http_client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            offset = update["update_id"] + 1
                            if "message" in update:
                                asyncio.create_task(self._handle_message(update["message"]))
                elif res.status_code == 401:
                    logger.error("Invalid bot token, stopping polling")
                    self.is_running = False
                    break
                else:
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(4)

    async def _handle_message(self, message: Dict[str, Any]):
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()
        from_user = message.get("from", {})
        username = from_user.get("username") or from_user.get("first_name", "Foydalanuvchi")

        if not chat_id or not text:
            return

        # Check allowed chats if configured
        allowed = self.config.get("allowed_chat_ids", [])
        if allowed and chat_id not in allowed:
            await self.send_message(
                chat_id,
                f"🚫 Kechirasiz @{username}, ushbu Ant Colony AI botiga faqat tasdiqlangan administratorlar kira oladi.\nSizning Chat ID: `{chat_id}`"
            )
            return

        # Commands handling
        if text.startswith("/start") or text.startswith("/help"):
            welcome = (
                f"👋 *Assalomu alaykum, {username}! Ant Colony AI botiga xush kelibsiz.*\n\n"
                "Bu bot orqali siz **17 ta mutaxassis AI agentdan** iborat jamoaga istalgan vazifani berishingiz mumkin:\n\n"
                "• 🚀 **Dasturlash:** Web ilova, REST API, botlar, skriptlar\n"
                "• 📊 **Marketing & SMM:** Bozor tahlili, 30 kunlik kontent-reja, sotuvchi matnlar\n"
                "• 📈 **BI & Tahlil:** Ma'lumotlarni tahlil qilish, daromad prognozi\n"
                "• ⚖️ **Hujjatlar:** Shartnomalarni tekshirish, PRD, nizomlar\n\n"
                "💡 *Shunchaki o'zingiz xohlagan vazifani matn ko'rinishida yuboring!*"
            )
            await self.send_message(chat_id, welcome)
            return

        if text.startswith("/status"):
            try:
                from models_hub import models_hub
                stats = models_hub.get_real_stats()
                status_text = (
                    f"📊 *Ant Colony AI Tizim Holati*\n\n"
                    f"• Modellar: `{stats.get('online_models', 11)}/{stats.get('total_models', 21)} onlayn`\n"
                    f"• Bajarilgan vazifalar: `{stats.get('total_tasks_run', 0)}`\n"
                    f"• Ishlatilgan tokenlar: `{stats.get('total_tokens_consumed', 0):,}`\n"
                    f"• Tejangan kesh: `{stats.get('prompt_cache', {}).get('tokens_saved', 0):,}`\n"
                )
                await self.send_message(chat_id, status_text)
            except Exception as e:
                await self.send_message(chat_id, f"Xatolik: {e}")
            return

        # Execute Task through Orchestrator
        await self.send_message(
            chat_id,
            f"⏳ *Vazifa qabul qilindi!*\n\n_«{text[:200]}»_\n\nProject Manager tahlil qilmoqda va mos mutaxassislar jamoasini ishga tushirmoqda..."
        )

        try:
            from agent_engine import agent_engine
            final_answer = ""
            assigned_role = ""
            created_files = []

            async for event in agent_engine.run_orchestrated_task_stream(text):
                ev_type = event.get("type")
                if ev_type == "pm_plan_ready":
                    plan_txt = event.get("plan_content", "")[:350]
                    role = event.get("assigned_role", "")
                    await self.send_message(
                        chat_id,
                        f"📋 *Project Manager Rejasi:*\n{plan_txt}...\n\n👨‍💻 *Yetakchi mutaxassis:* `{role}`"
                    )
                elif ev_type == "agent_message":
                    final_answer = event.get("content", "")
                elif ev_type == "orchestration_completed":
                    created_files = event.get("created_files", [])
                    if not final_answer:
                        summary = event.get("eval_summary", {})
                        final_answer = summary.get("summary", "Vazifa muvaffaqiyatli yakunlandi.")

            # Send final report
            if final_answer:
                # Telegram message size limit is 4096 characters
                if len(final_answer) > 4000:
                    chunks = [final_answer[i:i+4000] for i in range(0, len(final_answer), 4000)]
                    for idx, chunk in enumerate(chunks):
                        await self.send_message(chat_id, chunk)
                else:
                    await self.send_message(chat_id, f"✅ *Natija tayyor:*\n\n{final_answer}")

            # Send created files if any
            if created_files:
                from config import PROJECTS_BASE_DIR
                await self.send_message(chat_id, f"📁 *Yaratilgan fayllar ({len(created_files)} ta):*")
                for f_rel in created_files[:5]:
                    f_full = PROJECTS_BASE_DIR / f_rel
                    if f_full.exists() and f_full.is_file() and f_full.stat().st_size < 10 * 1024 * 1024:
                        await self.send_document(chat_id, f_full, caption=f"📄 {f_full.name}")

        except Exception as err:
            logger.error(f"Error executing telegram task: {err}")
            await self.send_message(chat_id, f"❌ Vazifani bajarishda xatolik yuz berdi:\n`{err}`")

telegram_bot_manager = TelegramBotManager()
