"""
Ant Colony AI — Proactive Project Manager (PM) Assistant & Memory Engine
Handles idle proactive proposals, CEO inquiries, persistent memory, and automated MD/Skill creation.
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from ant_colony.config import BASE_DIR, PROJECTS_BASE_DIR, WORKSPACE_DIR

MEMORY_FILE = BASE_DIR / "pm_memory.json"

class PMProactiveEngine:
    def __init__(self):
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        if MEMORY_FILE.exists():
            try:
                return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "ceo_preferences": {},
            "answered_inquiries": [],
            "generated_docs": [],
            "last_inquiry_time": 0,
            "proposals": []
        }

    def _save_memory(self):
        try:
            MEMORY_FILE.write_text(json.dumps(self.memory, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"Error saving PM memory: {e}")

    def get_proactive_insights(self) -> Dict[str, Any]:
        """Scans projects and roles to formulate intelligent proposals for the CEO."""
        proposals = []
        
        # 1. Check if core architectural MD documents exist
        doc_checks = [
            ("ARCHITECTURE.md", "Архитектурный обзор проекта", "Обзор архитектуры модулей, потоков данных и моделей"),
            ("API_SPEC.md", "Спецификация REST/WebSocket API", "Документация всех эндпоинтов, форматов запросов и ответов"),
            ("DEPLOYMENT.md", "Инструкция по деплою и CI/CD", "Гайд по развертыванию в Docker, на Netlify и VPS серверах"),
            ("SECURITY_CHECKLIST.md", "Чек-лист безопасности и чистоты", "Правила защиты от инъекций, утечек ключей и XSS")
        ]

        for fname, title, desc in doc_checks:
            file_path = BASE_DIR / fname
            if not file_path.exists():
                proposals.append({
                    "id": f"doc_create_{fname}",
                    "type": "missing_doc",
                    "target_file": fname,
                    "title": f"Создать документ: {fname}",
                    "description": f"В проекте отсутствует `{fname}`. {desc}.",
                    "action_label": f"Создать {fname}",
                    "category": "docs"
                })

        # 2. Check specialist roles
        roles_dir = BASE_DIR / "roles"
        if roles_dir.exists():
            role_files = [f.name for f in roles_dir.iterdir() if f.suffix == ".md"]
            if "system_architect.md" not in role_files:
                proposals.append({
                    "id": "skill_system_architect",
                    "type": "skill_proposal",
                    "target_file": "system_architect.md",
                    "title": "Добавить роль: System Architect (High-Load)",
                    "description": "Специализированная роль для проектирования масштабируемых микросервисов и кэширования.",
                    "action_label": "Создать роль",
                    "category": "skills"
                })

        # 3. Interactive questions to CEO
        questions = [
            {
                "id": "q_preferred_stack",
                "question": "Какому основному технологическому стеку отдать приоритет в новых проектах?",
                "options": ["FastAPI + Modern Web", "Next.js / TypeScript", "Go Microservices", "Python Full-Stack"],
                "category": "architecture"
            },
            {
                "id": "q_test_coverage",
                "question": "Какой уровень строгости QA тестов установить по умолчанию?",
                "options": ["Строгий (Unit + Integration тесты)", "Быстрый (Синтаксис + Smoke тесты)", "Полный аудит безопасности"],
                "category": "qa"
            },
            {
                "id": "q_caching_strategy",
                "question": "Использовать ли агрессивный Prompt Caching для экономии 70%+ токенов?",
                "options": ["Да, включить агрессивное кэширование (Рекомендуется)", "Стандартный режим"],
                "category": "performance"
            }
        ]

        # Filter out already answered questions
        answered_ids = {a["id"] for a in self.memory.get("answered_inquiries", [])}
        pending_questions = [q for q in questions if q["id"] not in answered_ids]

        return {
            "proposals": proposals,
            "pending_questions": pending_questions,
            "ceo_preferences": self.memory.get("ceo_preferences", {}),
            "answered_count": len(answered_ids),
            "last_check": time.time()
        }

    def record_ceo_feedback(self, question_id: str, question_text: str, answer_chosen: str):
        """Saves CEO's decision into persistent memory."""
        self.memory["ceo_preferences"][question_id] = answer_chosen
        self.memory["answered_inquiries"].append({
            "id": question_id,
            "question": question_text,
            "answer": answer_chosen,
            "timestamp": time.time()
        })
        self._save_memory()
        return {"success": True, "preference_saved": answer_chosen}

    def generate_recommended_doc(self, filename: str) -> Dict[str, Any]:
        """Generates professional Markdown documentation proposed by PM."""
        clean_name = os.path.basename(filename.strip())
        target_path = BASE_DIR / clean_name

        DOC_TEMPLATES = {
            "ARCHITECTURE.md": """# Архитектура Ant Colony AI Platform

## 1. Обзор системы
Ant Colony AI — это высокопроизводительная мульти-агентная платформа, объединяющая 7 специализированных AI ролей в единый рой (Swarm) с 3D изометрической визуализацией в реальном времени.

## 2. Ключевые компоненты
- **PM Orchestrator**: Анализирует требования пользователя, формирует спецификацию и координирует роли.
- **Continuous ELO Leaderboard**: Оценивает ответы моделей и назначает лучших исполнителей.
- **Prompt Caching Engine**: Кэширует префиксы и экономит до 75% стоимости токенов.
- **Virtual 3D Office (Three.js)**: Отображает физическое перемещение, набор текста на клавиатуре и зоны отдыха.

## 3. Поток выполнения задач (Pipeline)
`Требования` ➔ `Анализ` ➔ `Разработка` ➔ `QA и Тестирование (Параллельно)` ➔ `Аудит Безопасности` ➔ `Деплой`
""",
            "API_SPEC.md": """# Спецификация REST & WebSocket API

## Основные эндпоинты:
- `POST /api/orchestrator/stream` — Потоковый запуск мульти-агентной оркестрации (Server-Sent Events).
- `GET /api/hive/real-stats` — Реальная телеметрия: модели онлайн, использованные токены, кэш, размер рабочей среды.
- `GET /api/leaderboard` — ELO рейтинг моделей, задержка (Ping), статистика побед.
- `GET /api/roles` — Матрица ролей и назначенные AI модели.
- `GET /api/skills` — Список системных инструкций и навыков ролей.
- `GET /api/md` — Файловый браузер Markdown документов.
""",
            "DEPLOYMENT.md": """# Инструкция по деплою Ant Colony AI

## 1. Быстрый запуск (Локально)
```bash
python3 server.py
# Откройте браузер: http://localhost:8080
```

## 2. Переменные окружения (.env)
- `OPENROUTER_API_KEY` — Ключ для доступа к мульти-моделям (DeepSeek, Nemotron, Cohere).
- `GEMINI_API_KEY` — Ключ Google Gemini 2.5 Flash.
- `GITHUB_TOKEN` — Токен GitHub для выгрузки репозиториев.

## 3. Деплой на Netlify / GitHub
Используйте встроенную панель **«Деплой на Netlify/GitHub»** в меню Инструментов.
""",
            "SECURITY_CHECKLIST.md": """# Чек-лист безопасности и аудита кода

## 1. Защита данных
- [x] Никаких жестко закодированных API ключей в коде (использование `config.py` и переменных окружения).
- [x] Санитизация путей (Path Traversal Protection через `os.path.normpath` и запрет `..`).
- [x] Безопасное выполнение команд в каталоге проекта.

## 2. Аудит кода
- Параллельный запуск QA и Security Auditor для каждого сгенерированного файла.
- Автоматическая валидация синтаксиса Python и JavaScript перед сохранением.
"""
        }

        content = DOC_TEMPLATES.get(clean_name, f"# {clean_name[:-3] if clean_name.endswith('.md') else clean_name}\n\nСгенерировано PM Orchestrator.\n")
        target_path.write_text(content, encoding="utf-8")
        self.memory["generated_docs"].append({"filename": clean_name, "timestamp": time.time()})
        self._save_memory()

        return {"success": True, "filename": clean_name, "bytes": len(content.encode())}

pm_proactive_engine = PMProactiveEngine()
