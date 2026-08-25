"""
Dynamic Model Evaluation & Skill Matrix Engine.
Maintains persistent performance ratings across all models and automatically assigns
the highest-performing model to each specialized role.
"""
import json
import math
import time
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
from ant_colony.config import DATA_DIR, ROLES_DIR, MODELS_CATALOG, AGENT_CONFIG

MATRIX_FILE = DATA_DIR / "model_skill_matrix.json"
# ROLES_DIR endi config.py da markazlashtirilgan.

# UCB izlanish koeffitsienti: kam sinalgan modellarga imkon berish kuchi.
# 0 bo'lsa — sof greedy (bir marta yetakchi bo'lgan model abadiy yetakchi qoladi).
UCB_C = 6.0

# Bu holatdagi modellar tanlovdan chetlatiladi.
UNUSABLE_STATUSES = {"error", "rate_limited"}

DEFAULT_ROLE_DEFINITIONS = [
    {
        "id": "pm_orchestrator",
        "name": "Project Manager",
        "category": "planning_pm",
        "icon": "crown",
        "description": "Ведущий Project Manager и системный архитектор",
        "md_file": "pm_orchestrator.md",
        "initial_model": "gemini-2.5-flash"
    },
    {
        "id": "frontend_architect",
        "name": "Frontend Architect",
        "category": "frontend_ui",
        "icon": "code",
        "description": "Архитектор UI/UX и Frontend разработчик",
        "md_file": "frontend_architect.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "ui_designer",
        "name": "UI & Canvas Designer",
        "category": "frontend_ui",
        "icon": "ui",
        "description": "Эксперт по CSS анимациям, SVG и Canvas графике",
        "md_file": "ui_designer.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "backend_engineer",
        "name": "Backend Engineer",
        "category": "backend_api",
        "icon": "server",
        "description": "Инженер Backend и проектировщик API",
        "md_file": "backend_engineer.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "algorithm_solver",
        "name": "Algorithm Solver",
        "category": "algorithms",
        "icon": "math",
        "description": "Специалист по сложным алгоритмам и структурам данных",
        "md_file": "algorithm_solver.md",
        "initial_model": "gemini-2.5-flash"
    },
    {
        "id": "qa_test_automation",
        "name": "QA Specialist",
        "category": "qa_testing",
        "icon": "qa",
        "description": "Инженер автоматизации тестирования и QA контроля",
        "md_file": "qa_test_automation.md",
        "initial_model": "posiden/nemotron-3.5-lightning"
    },
    {
        "id": "devops_deployer",
        "name": "DevOps Deployer",
        "category": "devops",
        "icon": "deploy",
        "description": "Инженер DevOps, CI/CD автоматизации и деплоя",
        "md_file": "devops_deployer.md",
        "initial_model": "posiden/hy3"
    },
    {
        "id": "database_architect",
        "name": "Database Architect",
        "category": "backend_api",
        "icon": "db",
        "description": "Архитектор баз данных, SQL/NoSQL и схем данных",
        "md_file": "database_architect.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "security_auditor",
        "name": "Security Auditor",
        "category": "security",
        "icon": "shield",
        "description": "Аудитор информационной безопасности и чистоты кода",
        "md_file": "security_auditor.md",
        "initial_model": "posiden/nemotron-3.5-lightning"
    },
    {
        "id": "data_miner_researcher",
        "name": "Data Researcher",
        "category": "research",
        "icon": "data",
        "description": "Специалист по анализу данных, поиску и исследованиям",
        "md_file": "data_miner_researcher.md",
        "initial_model": "gemini-2.5-flash"
    },
    {
        "id": "performance_optimizer",
        "name": "Performance Optimizer",
        "category": "frontend_ui",
        "icon": "zap",
        "description": "Инженер по оптимизации производительности и профилированию",
        "md_file": "performance_optimizer.md",
        "initial_model": "posiden/nemotron-3.5-lightning"
    },
    {
        "id": "system_troubleshooter",
        "name": "System Troubleshooter",
        "category": "qa_testing",
        "icon": "bug",
        "description": "Специалист по глубокой отладке и устранению сбоев",
        "md_file": "system_troubleshooter.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "mobile_developer",
        "name": "Mobile Developer",
        "category": "frontend_ui",
        "icon": "smartphone",
        "description": "Разработка мобильных приложений на Flutter и React Native",
        "md_file": "mobile_developer.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "microservices_architect",
        "name": "Microservices Architect",
        "category": "backend_api",
        "icon": "network",
        "description": "Архитектор микросервисов, gRPC, message brokers и Kubernetes",
        "md_file": "microservices_architect.md",
        "initial_model": "gemini-2.5-flash"
    },
    {
        "id": "market_researcher",
        "name": "Market Researcher",
        "category": "research",
        "icon": "search",
        "description": "Аналитик рынка, конкурентная разведка, SWOT и ценовые стратегии",
        "md_file": "market_researcher.md",
        "initial_model": "gemini-3.7-flash"
    },
    {
        "id": "content_smm_specialist",
        "name": "Content & SMM Specialist",
        "category": "marketing",
        "icon": "edit",
        "description": "Копирайтер, контент-стратег, рекламные креативы и SMM-планы",
        "md_file": "content_smm_specialist.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "data_bi_analyst",
        "name": "Data & BI Analyst",
        "category": "analytics",
        "icon": "chart",
        "description": "Аналитик данных, Excel/SQL отчеты, визуализация и прогнозирование выручки",
        "md_file": "data_bi_analyst.md",
        "initial_model": "gemini-3.7-flash"
    },
    {
        "id": "legal_docs_specialist",
        "name": "Legal & Docs Specialist",
        "category": "legal",
        "icon": "shield",
        "description": "Юрист, аудит договоров, анализ рисков, PRD и нормативные регламенты",
        "md_file": "legal_docs_specialist.md",
        "initial_model": "posiden/nemotron-3.5-lightning"
    },
    {
        "id": "customer_support_sales",
        "name": "Customer Support & Sales",
        "category": "sales",
        "icon": "users",
        "description": "Скрипты продаж, отработка возражений, FAQ и регламенты поддержки",
        "md_file": "customer_support_sales.md",
        "initial_model": "posiden/deepseek-v4-flash"
    },
    {
        "id": "blockchain_dev",
        "name": "Blockchain Developer",
        "category": "backend_api",
        "icon": "chain",
        "description": "Смарт-контракты Solidity/Rust, DeFi, NFT и аудит безопасности",
        "md_file": "blockchain_dev.md",
        "initial_model": "gemini-2.5-flash"
    }
]

class SkillMatrixEngine:
    def __init__(self):
        self.matrix: Dict[str, Any] = self.load_matrix()

    def load_matrix(self) -> Dict[str, Any]:
        if MATRIX_FILE.exists():
            try:
                with open(MATRIX_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Initial matrix baseline
        initial_scores = {}
        for m in MODELS_CATALOG:
            m_id = m["id"]
            initial_scores[m_id] = {
                "model_id": m_id,
                "model_name": m["name"],
                "provider": m["provider"],
                "total_evaluations": 0,
                "average_score": 88.0,
                "category_scores": {
                    "planning_pm": 96.0 if "deepseek" in m_id else (94.0 if "2.5-flash" in m_id else 85.0),
                    "frontend_ui": 97.0 if "deepseek" in m_id else (90.0 if "gemini" in m_id else 82.0),
                    "backend_api": 96.0 if "deepseek" in m_id else (92.0 if "gemini" in m_id else 84.0),
                    "algorithms": 95.0 if "deepseek" in m_id else (93.0 if "2.5-flash" in m_id else 85.0),
                    "qa_testing": 96.0 if "nemotron" in m_id else (90.0 if "deepseek" in m_id else 80.0),
                    "devops": 94.0 if "hy3" in m_id or "deepseek" in m_id else (88.0 if "gemini" in m_id else 80.0),
                    "security": 94.0 if "nemotron" in m_id else (90.0 if "deepseek" in m_id else 82.0),
                    "research": 95.0 if "2.5-flash" in m_id else (92.0 if "deepseek" in m_id else 83.0)
                },
                "history": []
            }

        return {
            "models": initial_scores,
            "role_assignments": {r["id"]: r["initial_model"] for r in DEFAULT_ROLE_DEFINITIONS},
            "last_updated": time.time()
        }

    def save_matrix(self):
        try:
            with open(MATRIX_FILE, "w", encoding="utf-8") as f:
                json.dump(self.matrix, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error saving skill matrix:", e)

    def get_role_md_content(self, md_filename: str) -> str:
        f_path = ROLES_DIR / md_filename
        base_content = ""
        if f_path.exists():
            base_content = f_path.read_text(encoding="utf-8")
        else:
            base_content = f"# Rol ko'rsatmasi ({md_filename})\nKo'nikmalar yuklanmoqda..."

        # Universal Multilingual Response Directive (Always reply in user's prompt language)
        lang_rule = (
            "\n\n## TIL QOIDASI / MULTILINGUAL RESPONSE DIRECTIVE:\n"
            "- Always detect and reply in the EXACT SAME LANGUAGE as the user's prompt.\n"
            "- If the user asks in Russian, write all reasoning, explanations, code comments, QA feedback, and summaries in Russian.\n"
            "- If the user asks in Uzbek, write all reasoning, explanations, code comments, QA feedback, and summaries in Uzbek.\n"
            "- If the user asks in English, write in English.\n"
            "- Never reply in a language different from what the user used in their task/query."
        )
        return base_content + lang_rule

    def get_all_roles(self) -> List[Dict[str, Any]]:
        roles = []
        for r in DEFAULT_ROLE_DEFINITIONS:
            pinned_model_id = (self.matrix.get("pinned_roles") or {}).get(r["id"])
            assigned_model_id = pinned_model_id or self.matrix.get("role_assignments", {}).get(r["id"], r["initial_model"])
            model_info = self.matrix.get("models", {}).get(assigned_model_id, {})
            category = r["category"]
            cat_score = model_info.get("category_scores", {}).get(category, 90.0)

            roles.append({
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "icon": r["icon"],
                "description": r["description"],
                "md_file": r["md_file"],
                "assigned_model": assigned_model_id,
                "pinned": bool(pinned_model_id),
                "pinned_model": pinned_model_id,
                "model_name": model_info.get("model_name", assigned_model_id),
                "model_provider": model_info.get("provider", ""),
                "skill_score": round(cat_score, 1),
                "total_evaluations": model_info.get("total_evaluations", 0)
            })
        return roles

    def set_role_model(self, role_id: str, model_id: str) -> Dict[str, Any]:
        """
        Rolga modelni QO'LDA biriktiradi (pin). Shundan keyin ELO/UCB tanlovi
        bu rolga tegmaydi. `model_id` bo'sh bo'lsa — pin olib tashlanadi.
        """
        pinned = self.matrix.setdefault("pinned_roles", {})
        if model_id:
            pinned[role_id] = model_id
            self.matrix.setdefault("role_assignments", {})[role_id] = model_id
        else:
            pinned.pop(role_id, None)
        self.matrix["last_updated"] = time.time()
        self.save_matrix()
        return {"role_id": role_id, "pinned": bool(model_id), "model_id": model_id or None}

    def clear_role_model(self, role_id: str) -> Dict[str, Any]:
        """Rolni avtomatik (ELO) tanlovga qaytaradi."""
        return self.set_role_model(role_id, "")

    def _category_evals(self, m_data: Dict[str, Any], category: str) -> int:
        """Shu modelning aynan shu kategoriyada necha marta baholanganini sanaydi."""
        return sum(1 for h in m_data.get("history", []) if h.get("category") == category)

    def get_best_model_for_role(self, role_id: str, *, explore: bool = True) -> str:
        """
        Rol uchun modelni tanlaydi.

        Ilgari bu sof `argmax` edi va ikki jiddiy nuqsoni bor edi:
          1. Bir marta yetakchi bo'lgan model abadiy tanlanardi — boshqa modellar
             hech qachon sinalmasdi, ya'ni "continuous learning" amalda to'xtab qolardi.
          2. Model onlaynmi-yo'qmi umuman hisobga olinmasdi — o'lik modelga
             topshiriq berilib, har safar zaxira zanjirida vaqt yo'qotilardi.

        Endi UCB1 uslubidagi izlanish bonusi qo'shiladi va ishlamayotgan
        modellar chetlatiladi.
        """
        # Foydalanuvchi rol uchun modelni QO'LDA biriktirgan bo'lsa, ELO/UCB
        # tanlovi umuman ishlamaydi — aks holda avtomatik qayta biriktirish
        # foydalanuvchi tanlovini keyingi vazifada bekor qilib qo'yardi.
        # Baholash (record_evaluation) baribir davom etadi, shunchaki tanlovga
        # ta'sir qilmaydi.
        pinned = (self.matrix.get("pinned_roles") or {}).get(role_id)
        if pinned:
            assignments = self.matrix.setdefault("role_assignments", {})
            if assignments.get(role_id) != pinned:
                assignments[role_id] = pinned
                self.matrix["last_updated"] = time.time()
                self.save_matrix()
            return pinned

        role_def = next((r for r in DEFAULT_ROLE_DEFINITIONS if r["id"] == role_id), None)
        if not role_def:
            return "gemini-3.7-flash"

        category = role_def["category"]
        models = self.matrix.get("models", {})

        # Sog'liq holatini models_hub'dan olamiz (import shu yerda — aylanma importni oldini olish uchun).
        health: Dict[str, str] = {}
        try:
            from ant_colony.llm.models_hub import models_hub
            health = {k: v.get("status", "unknown") for k, v in models_hub.stats.items()}
        except Exception:
            pass

        # Sog'liq holatidan tashqari, provayderning O'ZI ishlatsa bo'ladiganmi
        # ham tekshiriladi: kaliti yo'q yoki xizmat sifatida yopilgan
        # provayderning modeli ELO bo'yicha yuqori tursa ham, unga topshiriq
        # berish har safar zaxira zanjiriga tushish demakdir.
        def _provider_usable(m_id: str) -> bool:
            meta = next((m for m in MODELS_CATALOG if m["id"] == m_id), None)
            if not meta:
                # Katalogda yo'q. Ikki holat farqlanadi:
                #  * models_hub biladi -> tirik BYOK modeli, to'smaymiz;
                #  * hech kim bilmaydi -> katalogdan OLIB TASHLANGAN model,
                #    lekin `data/model_skill_matrix.json` da ELO yozuvi
                #    qolib ketgan. Bunday "arvoh" yozuv tanlansa, agent
                #    mavjud bo'lmagan modelga topshiriq berardi.
                try:
                    from ant_colony.llm.models_hub import models_hub
                    return m_id in models_hub.stats
                except Exception:
                    return True
            if AGENT_CONFIG.get("free_models_only") and not meta.get("is_free"):
                return False
            try:
                from ant_colony.llm.models_hub import models_hub
                return models_hub.is_provider_configured(meta["provider"])
            except Exception:
                return True

        usable = {
            m_id: m_data for m_id, m_data in models.items()
            if health.get(m_id, "unknown") not in UNUSABLE_STATUSES
            and _provider_usable(m_id)
        }
        if not usable:
            usable = models  # hammasi tushib qolgan — hech bo'lmasa urinib ko'ramiz

        total_cat_evals = sum(self._category_evals(m, category) for m in usable.values())
        exploring = explore and random.random() < AGENT_CONFIG["exploration_rate"]

        scored: List[tuple] = []
        for m_id, m_data in usable.items():
            base = m_data.get("category_scores", {}).get(category, 85.0)
            n = self._category_evals(m_data, category)
            # Kam sinalgan modelga bonus; ko'p sinalganida bonus nolga intiladi.
            bonus = UCB_C * math.sqrt(math.log(total_cat_evals + 2) / (n + 1))
            degraded_penalty = 4.0 if health.get(m_id) in ("degraded", "timeout") else 0.0
            scored.append((base + bonus - degraded_penalty, base, m_id))

        if not scored:
            return role_def["initial_model"]

        scored.sort(reverse=True)
        if exploring and len(scored) > 1:
            # Izlanish raundi: eng yaxshi 3 taning ichidan tasodifiy tanlaymiz.
            best_model_id = random.choice(scored[:3])[2]
        else:
            best_model_id = scored[0][2]

        previous = self.matrix.get("role_assignments", {}).get(role_id)
        self.matrix.setdefault("role_assignments", {})[role_id] = best_model_id
        if previous != best_model_id:
            # Tanlov o'zgargani diskda ham qolishi kerak — ilgari saqlanmasdi.
            self.matrix["last_updated"] = time.time()
            self.save_matrix()
        return best_model_id

    def record_evaluation(
        self,
        role_id: str,
        model_id: str,
        score: float,
        feedback: str = ""
    ) -> Dict[str, Any]:
        """Record evaluation, update model score, and adjust role leader."""
        role_def = next((r for r in DEFAULT_ROLE_DEFINITIONS if r["id"] == role_id), None)
        category = role_def["category"] if role_def else "general"

        if model_id not in self.matrix["models"]:
            meta = next((m for m in MODELS_CATALOG if m["id"] == model_id), None)
            self.matrix["models"][model_id] = {
                "model_id": model_id,
                "model_name": meta["name"] if meta else model_id,
                "provider": meta["provider"] if meta else "openrouter",
                "total_evaluations": 0,
                "average_score": score,
                "category_scores": {category: score},
                "history": []
            }

        m_data = self.matrix["models"][model_id]
        total_evals = m_data.get("total_evaluations", 0) + 1
        m_data["total_evaluations"] = total_evals

        # Moslashuvchan o'rganish tezligi: dastlabki baholashlar reytingni tezroq
        # to'g'rilaydi (boshlang'ich qiymatlar taxminiy edi), keyin barqarorlashadi.
        # Fiksirlangan 0.3 koeffitsienti bilan qo'lda qo'yilgan boshlang'ich ball
        # o'nlab baholashdan keyin ham ta'sirini saqlab qolardi.
        cat_evals = self._category_evals(m_data, category)
        alpha = max(0.15, 1.0 / (cat_evals + 2))
        prev_cat_score = m_data.get("category_scores", {}).get(category, 85.0)
        new_cat_score = round(prev_cat_score * (1 - alpha) + score * alpha, 1)
        m_data["category_scores"][category] = new_cat_score

        # Update overall average
        all_cat_scores = list(m_data["category_scores"].values())
        m_data["average_score"] = round(sum(all_cat_scores) / len(all_cat_scores), 1)

        eval_entry = {
            "timestamp": time.time(),
            "role_id": role_id,
            "category": category,
            "score": score,
            "feedback": feedback[:200]
        }
        m_data["history"] = (m_data.get("history", []) + [eval_entry])[-20:]

        # Yetakchini qayta hisoblaymiz — bu yerda izlanishsiz (sof eng yaxshi),
        # chunki bu ko'rsatiladigan "yetakchi", ishga tayinlash emas.
        self.get_best_model_for_role(role_id, explore=False)
        self.matrix["last_updated"] = time.time()
        self.save_matrix()

        return {
            "role_id": role_id,
            "model_id": model_id,
            "score": score,
            "new_category_score": new_cat_score,
            "assigned_leader": self.matrix["role_assignments"].get(role_id)
        }

    def score_from_signals(
        self,
        *,
        qa_score: Optional[float] = None,
        files_written: int = 0,
        tool_calls: int = 0,
        tool_failures: int = 0,
        hit_step_limit: bool = False,
        had_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Bahoni HAQIQIY signallardan hisoblaydi, taxmindan emas.

        Ilgari QA agentiga har safar qat'iy 95.0 ball berilardi — ya'ni QA modeli
        o'z ishini o'zi maqtardi va reyting hech qachon haqiqatni ko'rsatmasdi.
        Endi ball uchta o'lchanadigan manbadan yig'iladi:
          * QA hisobotidagi ball (agar bo'lsa) — 60% ulush;
          * haqiqiy natija: fayllar yozildimi — 25%;
          * bajarilish sifati: asboblar xatosi, sikl, limitga urilish — 15%.
        """
        breakdown: Dict[str, Any] = {}

        # 1. QA komponenti
        if qa_score is not None and qa_score > 0:
            qa_part = max(0.0, min(100.0, qa_score))
            breakdown["qa"] = qa_part
        elif files_written >= 2:
            qa_part = 88.0
            breakdown["qa"] = 88.0
        elif files_written == 1:
            qa_part = 80.0
            breakdown["qa"] = 80.0
        else:
            qa_part = 50.0
            breakdown["qa"] = None

        # 2. Natija komponenti — fayl yozilmasa bu jiddiy muvaffaqiyatsizlik.
        if files_written >= 2:
            artifact_part = 100.0
        elif files_written == 1:
            artifact_part = 85.0
        else:
            artifact_part = 25.0
        breakdown["artifacts"] = artifact_part

        # 3. Bajarilish sifati
        exec_part = 100.0
        if tool_calls > 0:
            failure_rate = tool_failures / tool_calls
            exec_part -= failure_rate * 55.0
        else:
            exec_part = 40.0  # birorta ham asbob chaqirmagan agent ish qilmagan
        if hit_step_limit:
            exec_part -= 15.0
        if had_error:
            exec_part -= 30.0
        exec_part = max(0.0, min(100.0, exec_part))
        breakdown["execution"] = round(exec_part, 1)

        final = qa_part * 0.60 + artifact_part * 0.25 + exec_part * 0.15
        final = round(max(30.0, min(100.0, final)), 1)
        return {"score": final, "breakdown": breakdown}

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        sorted_models = sorted(
            self.matrix.get("models", {}).values(),
            key=lambda x: x.get("average_score", 0),
            reverse=True
        )
        return sorted_models

    def get_leaderboard_payload(self) -> Dict[str, Any]:
        sorted_models = sorted(
            self.matrix.get("models", {}).values(),
            key=lambda x: x.get("average_score", 0),
            reverse=True
        )

        from ant_colony.llm.models_hub import models_hub
        ranked = []
        for idx, m in enumerate(sorted_models):
            rank = idx + 1
            m_copy = dict(m)
            m_copy["rank"] = rank
            if rank == 1:
                m_copy["medal"] = "gold"
                m_copy["badge"] = "#1 Золото"
            elif rank == 2:
                m_copy["medal"] = "silver"
                m_copy["badge"] = "#2 Серебро"
            elif rank == 3:
                m_copy["medal"] = "bronze"
                m_copy["badge"] = "#3 Бронза"
            else:
                m_copy["medal"] = None
                m_copy["badge"] = f"#{rank}"

            CATEGORY_NAMES = {
                "planning_pm": "Project Management",
                "frontend_ui": "Frontend и UI",
                "backend_api": "Backend и API",
                "qa_testing": "QA и тестирование",
                "devops": "DevOps и деплой",
                "security": "Аудит безопасности",
                "research": "Анализ данных",
                "algorithms": "Алгоритмы и логика",
                "general": "Общая разработка"
            }

            cat_scores = m.get("category_scores", {})
            if cat_scores:
                best_cat = max(cat_scores.items(), key=lambda x: x[1])
                m_copy["best_category"] = CATEGORY_NAMES.get(best_cat[0], best_cat[0])
                m_copy["best_category_key"] = best_cat[0]
                m_copy["best_category_score"] = best_cat[1]
            else:
                m_copy["best_category"] = "Общая разработка"
                m_copy["best_category_key"] = "general"
                m_copy["best_category_score"] = m.get("average_score", 85.0)

            # Haqiqiy ping va status. MUHIM: ilgari o'lchanmagan model uchun
            # model nomiga qarab "taxminiy" latency to'qib chiqarilardi (190/280/340...)
            # va u UI'da real o'lchov sifatida ko'rsatilardi. Bu foydalanuvchini
            # chalg'itadi — endi o'lchanmagan qiymat 0 bo'lib qoladi, UI "—" chizadi.
            st = models_hub.stats.get(m["model_id"], {})
            m_copy["latency_ms"] = st.get("latency_ms", 0)
            m_copy["status"] = st.get("status", "unknown")
            m_copy["tokens_total"] = st.get("tokens_total", 0)
            # Model hali hech baholanmagan bo'lsa, ELO — bu boshlang'ich baza qiymati,
            # o'lchov emas. UI shu bayroqqa qarab "базовая оценка" deb belgilaydi.
            m_copy["is_baseline"] = (m.get("total_evaluations", 0) or 0) == 0
            ranked.append(m_copy)

        # Eng tez model faqat haqiqatan o'lchangan modellar orasidan tanlanadi.
        measured = [r for r in ranked if (r.get("latency_ms") or 0) > 0]
        fastest_m = min(measured, key=lambda x: x["latency_ms"]) if measured else None

        categories = [
            ("frontend_ui", "Frontend и UI"),
            ("backend_api", "Backend и API"),
            ("planning_pm", "Project Management"),
            ("qa_testing", "QA и тестирование"),
            ("devops", "DevOps и деплой"),
            ("security", "Аудит безопасности"),
            ("research", "Анализ данных"),
            ("algorithms", "Алгоритмы и логика")
        ]
        category_leaders = {}
        for cat_key, cat_label in categories:
            best_m = max(
                self.matrix.get("models", {}).values(),
                key=lambda x: x.get("category_scores", {}).get(cat_key, 0),
                default=None
            )
            if best_m:
                category_leaders[cat_key] = {
                    "label": cat_label,
                    "model_id": best_m["model_id"],
                    "model_name": best_m["model_name"],
                    "score": best_m.get("category_scores", {}).get(cat_key, 0)
                }

        return {
            "total_models": len(ranked),
            "top_podium": ranked[:3],
            "rankings": ranked,
            "fastest_model": fastest_m,
            "category_leaders": category_leaders,
            "last_updated": self.matrix.get("last_updated", time.time())
        }


    def register_custom_role(self, role_dict: Dict[str, Any]):
        """Dynamically registers a new specialized role and creates initial ELO entries."""
        role_id = role_dict["id"]
        # Check if already exists in default
        existing = next((r for r in DEFAULT_ROLE_DEFINITIONS if r["id"] == role_id), None)
        if not existing:
            DEFAULT_ROLE_DEFINITIONS.append(role_dict)
        if "assigned_roles" not in self.matrix:
            self.matrix["assigned_roles"] = {}
        self.matrix["assigned_roles"][role_id] = role_dict.get("initial_model", "posiden/deepseek-v4-flash")
        self.save_matrix()

skill_matrix = SkillMatrixEngine()

