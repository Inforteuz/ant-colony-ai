# i18n vazifasi — BOSQICH 2: Setup Wizard (`static/index.html`)

> Bu brief boshqa model/agent (loyihaning o'z PM orkestratori, Sonnet va h.k.)
> mustaqil bajarishi uchun yozilgan. Qo'shimcha kontekst talab qilmaydi.
> Yozilgan sana: 2026-08-26.

## Umumiy holat

`docs/HANDOFF.md` va `docs/I18N_TASK.md` (BOSQICH 1 — `app.js` dagi
toast/confirm/alert, 56 ta) bilan bir qatorda ishlaydigan ikkinchi bosqich.
Bu safar **faqat** `static/index.html` dagi Setup Wizard modaliga tegiladi
(`id="modal-setup-wizard"`, hozircha ~680–1046 qatorlar — aniq chegara
pastdagi Qadam 1 bilan tekshiriladi, chunki BOSQICH 1 ijrosi qator
raqamlarini siljitishi mumkin).

**MUHIM — bu BOSQICH 1 dan tubdan farq qiladi:** Tekshiruv shuni ko'rsatdiki,
88 ta tarjimasiz qatordan **84 tasi uchun kalit i18n.js da ALLAQACHON bor**
(en/uz/uz_cyr/ru to'rttalasida ham) — ular shunchaki HTML elementiga
`data-i18n*` atributi bilan **biriktirilmagan, xolos**. Faqat **4 ta** qator
uchun haqiqatan yangi kalit yozish kerak (b.ai/17.wtf provayderi shu
sessiyada qo'shilgani uchun — ular hali kalitga ega emas).

Demak bu vazifaning katta qismi — **tarjima yozish emas, balki mavjud
kalitlarni to'g'ri elementga ulash**. Yangi matn o'ylab topishga deyarli
ehtiyoj yo'q; xato ehtimoli ham past, chunki tarjima matni allaqachon
loyiha jamoasi tomonidan tasdiqlangan.

## Qadam 1 — chegarani tasdiqlang

```bash
grep -n 'id="modal-setup-wizard"' static/index.html
grep -n 'class="modal-backdrop' static/index.html   # keyingi modal shu yerda tugaydi
```

Ikkinchi qatordagi ro'yxatda `modal-setup-wizard`dan keyingi birinchi
`modal-backdrop` — bu modalning tugash chegarasi (hozircha
`modal-skill-editor`, qator ~1047).

## Mexanizm (uchta atribut, `static/js/i18n.js` boshqaradi)

```html
<span data-i18n="kalit_nomi">matn</span>                    → textContent
<input data-i18n-placeholder="kalit_nomi">                  → placeholder
<button data-i18n-title="kalit_nomi" title="...">           → title
```

`applyToElement()` (i18n.js, ~qator 3126) qoidasi — **muhim, xato qilishning
oldini oladi**:
- Agar elementda `data-i18n` bo'lsa va **bola-element yo'q bo'lsa**
  (masalan oddiy `<span>matn</span>`), butun `textContent` almashtiriladi.
- Agar elementda bola-element BOR bo'lsa (masalan ichida `<svg>` yoki
  dinamik qiymatli `<span id="...">`), sweeper faqat **birinchi bo'sh
  bo'lmagan TEXT node**ni topib, FAQAT o'shani almashtiradi — ichki
  element(lar)ga tegmaydi.
  → **Xulosa:** ikonka+matn tugmalarida (`<button><svg>...</svg>Matn</button>`)
    qo'shimcha `<span>` bilan o'rab o'tirish shart EMAS — `data-i18n`ni
    to'g'ridan-to'g'ri `<button>`ga qo'ying, ikonka avtomatik tegilmay
    qoladi. Loyihada bu pattern allaqachon ishlatilgan (`index.html:54`,
    `:69`, `:77` — `kpi-sub` misollariga qarang).
- **Bitta istisno (pastda "Maxsus holat" bo'limida batafsil):** agar bitta
  ota-elementda (masalan bitta `<p>`) BIR NECHTA mustaqil matn qatori
  `<br>` bilan ajratilgan bo'lsa, algoritm faqat BIRINCHISINI topadi —
  qolganlari o'zgarmay qoladi. Bunday holatda har bir qatorni alohida
  `<span data-i18n="...">` bilan o'rash SHART.

## Kalit qidirish tartibi (har bir qator uchun MAJBURIY)

Yangi kalit yozishdan OLDIN har doim mavjudligini tekshiring — deyarli
har doim allaqachon bor:

```bash
grep -n '"aniq_rus_matni"' static/js/i18n.js
```

Agar topilmasa, o'sha matnning bir qismini (5-6 so'z) qidiring — matn
`<code>`/`<br>` bilan bo'lingan bo'lishi mumkin.

## To'liq ro'yxat — 84 ta (mavjud kalit, faqat biriktiriladi)

`data-i18n` qaysi elementga qo'yilishini o'zingiz aniqlaysiz (yuqoridagi
mexanizmga qarab — ko'pincha shu qatordagi eng yaqin ota-element).

| Qator | Kalit | Joriy HTML (qisqartirilgan) |
|---|---|---|
| 683 | `setup_title` | `<h3>...">Ant Colony AI — Настройки API (Setup Wizard)</h3>` |
| 683 | `setup_subtitle` | `<small class="text-secondary-sub">Выберите единого провайдера или гибридный мульти-провайдерный режим...` |
| 693 | `setup_banner_title` | `<strong>Добавьте API-ключ, чтобы агенты заработали</strong>` |
| 694 | `setup_help_nokey` | `<p>Пока не задан ни один ключ, платформа не сможет обращаться к моделям.<br>` |
| 695 | `setup_help_one` + `setup_help_provider_save` | `Достаточно <b>одного</b> провайдера — ключ сохранится в файле <code>.env</code>.</p>` (ikkita alohida kalit — `<b>` oldi va keyingi qism) |
| 697 | `setup_link_gemini` | `<a href="...apikey" ...>Gemini — бесплатно</a>` |
| 698 | `setup_link_openrouter` | `<a href="...openrouter.ai/keys" ...>OpenRouter — free-модели</a>` |
| 699 | `setup_link_groq` | `<a href="...groq.com/keys" ...>Groq — бесплатно</a>` |
| 708 | `setup_ws_title` | `<div class="ws-setup-title">Рабочая папка (Workspace)</div>` |
| 709 | `setup_ws_desc` | `<div class="ws-setup-desc">Каталог, в котором AI агенты...</div>` |
| 714 | `setup_ws_browse` | `<button id="btn-ws-browse">Обзор…</button>` |
| 715 | `setup_ws_apply` | `<button id="btn-ws-apply">Применить</button>` |
| 718 | `setup_ws_current` | `<span id="ws-current-label">Текущая: <span id="ws-current-path">—</span></span>` — faqat "Текущая:" qismi, ichki `#ws-current-path` DINAMIK, tegmang |
| 724 | `up_one_level` (`data-i18n-title`) | `<button id="btn-ws-up" title="На уровень выше">↑</button>` |
| 736 | `setup_gen_title` | `<div class="ws-setup-title">Параметры генерации LLM</div>` |
| 737 | `setup_gen_desc` | `<div class="ws-setup-desc">Общие настройки для всех агентов...</div>` |
| 746 | `setup_gen_temp_hint` | `<div class="gen-hint">0 = детерминированно, 1 = креативно</div>` |
| 750 | `setup_gen_maxtokens_label` | `<span class="gen-label">Max tokens в ответе</span>` |
| 753 | `setup_gen_maxtokens_hint` | `<div class="gen-hint">Лимит длины ответа модели</div>` |
| 759 | `setup_gen_vision_label` | `<span class="gen-label">Vision (мультимодальность)</span>` |
| 760 | `setup_gen_vision_hint` | `<div class="gen-hint">Разрешить отправку изображений моделям</div>` |
| 768 | `setup_gen_free_label` | `<span class="gen-label">Только бесплатные модели</span>` |
| 769 | `skip_paid_fallback` | `<div class="gen-hint">Пропускать платные модели в фолбек-цепочке</div>` |
| 784 | `setup_gen_fetch_free` | `<button id="btn-fetch-free-openrouter">Загрузить бесплатные OpenRouter</button>` |
| 785 | `setup_gen_apply` | `<button id="btn-save-gen-settings">Применить параметры</button>` |
| 791 | `setup_tab_byok` | `<button data-mode="byok">Мои провайдеры (BYOK)</button>` |
| 792 | `setup_tab_single` | `<button data-mode="single">Быстрый старт (один ключ)</button>` |
| 793 | `setup_tab_multi` | `<button data-mode="multi">Гибридный / Мульти-провайдер</button>` |
| 794 | `setup_tab_custom` | `<button data-mode="custom">Локальный / Свой (Ollama, LM Studio)</button>` |
| 795 | `setup_tab_recreation` | `<button data-mode="recreation">Зоны отдыха и спорта</button>` |
| 801 | `byok_title` | `<h4>Подключите своего AI-провайдера</h4>` |
| 803 | `byok_desc1` | *(qarang: "Maxsus holat" bo'limi — 4 qatorli `<p>` bloki)* |
| 804 | `byok_desc2` | *(shu bilan birga)* |
| 805 | `byok_desc3` | *(shu bilan birga — `<code>` ichidagi matn ham kiradi)* |
| 806 | `byok_desc4` | *(shu bilan birga)* |
| 813 | `byok_provider_label` | `<div class="byok-section-label">Провайдер</div>` |
| 815 | `byok_catalog_loading` | `<div class="kpi-modal-loading">Загрузка каталога...</div>` |
| 822 | `byok_select_provider` | `<span class="byok-selected-name">Выберите провайдера слева</span>` |
| 833 | `byok_key_label` | `<label for="byok-api-key">API-ключ</label>` |
| 835 | `byok_key_placeholder` (`data-i18n-placeholder`) | `<input ... placeholder="Вставьте ключ провайдера">` |
| 837 | `byok_key_note` | *(bare text, `<label>` dan keyingi qator — "Maxsus holat"ga o'xshash, tekshiring)* |
| 842 | `byok_name_label` + `byok_name_optional` | `<label>Название подключения <span class="byok-optional">необязательно</span></label>` — ikkita alohida kalit |
| 844 | `byok_name_placeholder` (`data-i18n-placeholder`) | `<input ... placeholder="Например: OpenRouter (личный)">` |
| 848 | `byok_check` yoki `byok_test` | `<button id="btn-byok-test">Проверить</button>` (ikkalasi ham "Проверить" — birini tanlang, izchil bo'ling) |
| 850 | `byok_connect` | `<button id="btn-byok-connect" disabled>Подключить и загрузить модели</button>` — bitta text node, to'g'ridan-to'g'ri tugmaga `data-i18n` qo'ying |
| 860 | `byok_connected_title` | `<span>Подключённые провайдеры</span>` |
| 861 | `byok_refresh_tooltip` (`data-i18n-title`) | `<button id="btn-byok-refresh" title="Обновить список">` |
| 866 | `byok_loading` | `<div class="kpi-modal-loading">Загрузка...</div>` |
| 873 | `setup_single_title` | `<h4>Быстрый старт с единым провайдером</h4>` |
| 875 | `setup_single_provider_label` | `<label>Выберите провайдера:</label>` |
| 886 | `setup_single_key_label` | `<label>API ключ или GitHub Token:</label>` |
| 889, 904, 912, 920, 928, 936, 944 | `byok_check`/`byok_test` (bir xil kalit, 7 marta) | 7 ta `<button class="btn-key-test" data-test-provider="...">Проверить</button>` |
| 898 | `setup_multi_title` | `<h4>Гибридная мульти-провайдерная архитектура</h4>` |
| 909 | `setup_multi_or_label` | `<label>OpenRouter API ключ:</label>` |
| 917 | `setup_multi_gemini_label` | `<label>Google Gemini API ключ:</label>` |
| 925 | `setup_multi_openai_label` | `<label>OpenAI API ключ:</label>` |
| 953 | `setup_custom_title` | `<h4>Локальный Ollama / LM Studio / Свой API Endpoint</h4>` |
| 956 | `setup_custom_url_label` | `<label>Base URL (OpenAI-совместимый / Ollama):</label>` |
| 960 | `setup_custom_fetch` | *(bare text tugma ichida — 850 ga o'xshash, tekshiring)* |
| 965 | `setup_custom_key_label` | `<label>API ключ (при необходимости / опционально):</label>` |
| 970 | `byok_count_default` | `<span id="custom-models-count-label">Обнаружено моделей: 0</span>` |
| 971 | `byok_import` | `<button id="btn-import-all-custom-models">Импортировать в систему</button>` |
| 983 | `tg_title` | `<span>Управление Telegram ботом Ant Colony AI</span>` |
| 985 | `tg_status_none` | `<span id="tg-status-badge">Не настроен</span>` — DIQQAT: bu boshlang'ich holat, JS runtime'da qayta yozadi (pastga qarang) |
| 988 | `tg_desc` | *(bare text — 850 ga o'xshash, tekshiring)* |
| 992 | `tg_token_label` | `<label>Telegram Bot Token (от @BotFather):</label>` |
| 995 | `tg_save` | `<button id="btn-save-tg-bot">Сохранить и запустить</button>` |
| 1002 | `tg_active_desc` | `<div id="tg-bot-status-desc">Бот активен и принимает задачи</div>` — bu ham runtime holat |
| 1004 | `tg_stop` | `<button id="btn-toggle-tg-bot">Остановить</button>` |
| 1011 | `rec_title` | `<h4>Отображение зон отдыха (Футбол, Теннис, Фитнес)</h4>` |
| 1012 | `rec_desc` | `<p>Настройте, когда зоны спорта и отдыха...</p>` |
| 1017 | `rec_auto_label` | `<div>Авто: Показывать только когда нет задач (Рекомендуется)</div>` |
| 1018 | `setup_help_recreation` | `<div>При выполнении задачи зоны спорта скрываются...</div>` |
| 1024 | `rec_always_label` | `<div>Всегда показывать</div>` |
| 1025 | `rec_auto_desc` | `<div>Зоны футбола, тенниса и фитнеса всегда видны...</div>` |
| 1031 | `rec_disabled_label` | `<div>Отключить полностью (Строгий офис)</div>` |
| 1032 | `rec_disabled_desc` | `<div>Зоны отдыха полностью скрыты...</div>` |
| 1040 | `setup_save` | `<button id="btn-setup-save">Сохранить и применить</button>` |

## To'liq ro'yxat — 4 ta (YANGI kalit kerak)

Bular b.ai/17.wtf provayderi shu sessiyada qo'shilgani sababli hali
kalitga ega emas. `EXTRA` blokiga (yoki asosiy `STRINGS`ga — qaysi
qatorga yaqin bo'lsa o'shanga) uchala tilga ham qo'shing:

| Qator | Taklif etilgan kalit | Ruscha matn |
|---|---|---|
| 882 | `setup_single_bai_option` | `b.ai services (OpenAI-совместимый — Claude, GPT-5, Gemini, DeepSeek, Hy3)` |
| 883 | `setup_single_wtf_option` | `17.wtf (OpenAI-совместимый прокси — DeepSeek, GPT, Claude, Llama)` |
| 933 | `setup_multi_bai_label` | `b.ai services API ключ:` |
| 941 | `setup_multi_wtf_label` | `17.wtf API ключ:` |

**Eslatma:** 882/883 `<option>` elementlari ichida — provayder/model
nomlari (`b.ai`, `Claude`, `GPT-5`, `Gemini`, `DeepSeek`, `Hy3`, `17.wtf`,
`Llama`) proper noun, tarjima qilinmaydi, faqat "OpenAI-совместимый —"
kabi tavsif qismi tarjima qilinadi.

## Maxsus holat — `byok-intro` 4 qatorli blok (803–806)

```html
<p>
  Выберите провайдера, вставьте свой API-ключ и нажмите «Проверить».<br>
  Ключ шифруется (AES-256-GCM) и никогда не возвращается в браузер —<br>
  в интерфейсе виден только отпечаток вида <code>sk-...ABCD</code>.<br>
  Список моделей загружается прямо от провайдера, поэтому он всегда актуален.
</p>
```

To'rtta qator BITTA `<p>` ichida, `<br>` bilan ajratilgan xom matn
node'lari — `data-i18n`ni `<p>`ga qo'ysangiz, faqat BIRINCHI qator
tarjima bo'ladi. Har birini alohida `<span>`ga o'rang:

```html
<p>
  <span data-i18n="byok_desc1"></span><br>
  <span data-i18n="byok_desc2"></span><br>
  <span data-i18n="byok_desc3"></span><br>
  <span data-i18n="byok_desc4"></span>
</p>
```

**`byok_desc3` haqida:** mavjud kalit qiymati `"в интерфейсе виден только
отпечаток вида sk-...ABCD."` — ya'ni `sk-...ABCD` allaqachon **oddiy matn**
sifatida yozilgan, `<code>` teglarisiz. Shuning uchun `<code>` o'rashini
saqlashga urinmang (agar saqlasangiz, sweeper faqat oldingi matnni
almashtiradi va `sk-...ABCD` ikki marta chiqib qolishi mumkin — xato).
Kodli formatlashni yo'qotish qabul qilingan trade-off — monospace ko'rinish
kichik kosmetik yo'qotish, xavfsizroq yechim.

## Tuzoqlar (loyihada allaqachon boshdan kechirilgan + BOSQICH 1 dan meros)

1. **`I18N` mavjudligini tekshirmang** — `app.js`dan oldin yuklanadi.
2. **Runtime-holat matnlariga ehtiyot bo'ling** (985 `tg_status_none`,
   1002 `tg_active_desc`, 719 `запуск…`): bular boshlang'ich HTML qiymati,
   lekin `app.js` JS orqali ularni boshqa matn bilan qayta yozadi
   (masalan bot ishga tushganda "Активен" ga o'zgaradi). `data-i18n`
   qo'yish faqat SAHIFA YUKLANGANDAGI boshlang'ich holatni tarjima
   qiladi — bu yetarli (Phase 2 doirasi shu). Agar `app.js` ichida shu
   xabarlar uchun boshqa hardcoded rus matni topsangiz, ULARGA
   TEGMANG — bu alohida (keyingi bosqich) ish, `docs/HANDOFF.md`ga
   yozib qo'ying, o'zingiz kengaytirmang.
3. **`Janitor:` kabi proper noun'larni tarjima qilmang** — loyihada
   ataylab ingliz nomi sifatida qoldirilgan (asl ruscha matnda ham
   "Janitor" o'zgarmagan).
4. **`static/` ni o'zgartirgandan keyin `index.html` dagi `?t=`
   cache-bust raqamini albatta yangilang** (o'sha faylning o'zida,
   `<link rel="stylesheet" href="/static/css/style.css?t=...">` dan keyin
   yoki tegishli `<script src="...app.js?t=...">` qatorida — JS
   o'zgarmasa faqat CSS/HTML uchun ham cache-bust shart emas, lekin
   xatoga yo'l qo'ymaslik uchun index.html o'zi doim yangi so'rovda
   qayta yuklanadi, shu sabab bu qadam MAJBURIY emas — faqat `.js`
   fayllar o'zgarganda kerak).
5. **Yangi kalit qo'shsangiz — uchala lug'atga ham** (`en`, `uz`, `ru`;
   `uz_cyr` avtomatik). Joylashuvni tekshiring:
   ```bash
   grep -n "var EXTRA = {\|^      en: {\|^      uz: {\|^      ru: {" static/js/i18n.js
   ```
   (BOSQICH 1 avval bajarilgan bo'lsa, bu raqamlar siljigan bo'ladi —
   har doim yangidan grep qiling, eski raqamlarga ishonmang.)

## Tekshiruv (majburiy, hammasi o'tishi shart)

```bash
node --check static/js/i18n.js
PYTHONIOENCODING=utf-8 python tests/test_platform.py     # 115/115 bo'lishi shart
```

Va ish bajarilganini isbotlovchi hisob — Setup Wizard doirasida
**88 dan (yangi kalit kerak bo'lgan 4 tadan tashqari — ular yozilgach 0)
ga tushishi kerak**:

```bash
python - <<'EOF'
import re
from pathlib import Path
CYR = re.compile(r'[А-Яа-яЁё]')
start, end = 680, 1046   # zarur bo'lsa Qadam 1 dagi kabi qayta tekshiring
lines = Path("static/index.html").read_text(encoding="utf-8").split("\n")
n = 0
for i in range(start, end + 1):
    l = lines[i - 1]
    t = l.strip()
    if not CYR.search(l) or t.startswith(("<!--", "//")):
        continue
    if 'data-i18n' in l:
        continue
    n += 1
print("qolgan:", n)
EOF
```

Brauzerda qo'lda: tilni O'zbekchaga o'zgartirib, Setup Wizard modalini
oching — barcha yorliqlar, tugmalar, izohlar o'zbekcha chiqishi kerak;
`sk-...ABCD` namunasi va provayder nomlari (Gemini, OpenRouter, Groq,
b.ai, 17.wtf, Ollama) o'zgarmasligi kerak.

## Keyingi bosqichlar (shu briefdagi qoidalar o'zgarmaydi)

3. Topbar / HUD — `index.html`, ~50 ta
4. CEO Briefing + Token modallari — ~39 ta
5. Qolgan modallar
6. `hive3d.js` — ~73 ta (3D sahna yorliqlari; DOM emas, `I18N.t(key, lang)`
   to'g'ridan-to'g'ri chaqiriladi)
