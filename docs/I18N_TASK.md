# i18n vazifasi — hardcoded rus matnlarini ko'p tilli qilish

> Bu brief boshqa model (Sonnet va h.k.) mustaqil bajarishi uchun yozilgan.
> Hech qanday qo'shimcha kontekst talab qilmaydi.

## Umumiy holat

Loyihada 4 til bor: `ru` (asl), `en`, `uz`, `uz_cyr`. Skanerlash natijasi
(2026-08-25, izohlar va `data-i18n` bor qatorlar hisobga olinmagan):

| Fayl | Tarjimasiz qator |
|---|---|
| `static/js/app.js` | 437 |
| `static/index.html` | 227 |
| `static/js/hive3d.js` | 73 |

**Nega ular ba'zan to'g'ri ko'rinadi:** `i18n.js` dagi sweeper token darajasida
taxminiy tarjima qiladi. Lug'atda yo'q so'z rus tilida qolib ketadi — foydalanuvchi
ko'rayotgan "qolib ketgan so'zlar" aynan shu.

## BOSQICH 1 (shu vazifa): toast + confirm/alert — 56 ta

Eng ko'p ko'rinadigan va eng kam kod talab qiladigan qism. Faqat
`static/js/app.js` ga tegiladi.

## Mexanizm

`static/js/i18n.js` da `EXTRA` bloki bor va uning ichida **uchta** lug'at:

```
2443:  var EXTRA = {
2444:      en: { ... },
2632:      uz: { ... },
2816:      ru: { ... },
```

- Yangi kalit **uchalasiga ham** qo'shiladi. Biriga qo'shib, boshqasiga
  unutish — eng ko'p uchraydigan xato.
- **`uz_cyr` ni QO'LDA yozmang** — u `uz` dan `uzToCyr()` bilan avtomatik
  hosil qilinadi.
- JS ichida chaqiruv: `I18N.t('kalit')`.
- Parametrli matn: `I18N.t('kalit', {n: MAX_MB})`, lug'atda `"Limit — {n} MB"`.
  `t(key, params)` `{...}` almashtirishni qo'llab-quvvatlaydi (i18n.js:3096).
  **Bu ro'yxatda 14 ta parametrli qator bor** — quyida `P` bilan belgilangan.

## Kalit nomlash

`toast_<mavzu>_<title|body>` ko'rinishida. Masalan:

```js
// oldin
this.toast('История очищена', 'Лента Project Manager пуста', 'ok');
// keyin
this.toast(I18N.t('toast_history_cleared_title'),
           I18N.t('toast_history_cleared_body'), 'ok');
```

`confirm`/`alert` uchun `confirm_<mavzu>` / `alert_<mavzu>`.

## Tuzoqlar (loyihada allaqachon boshdan kechirilgan)

1. **`I18N` mavjudligini tekshirmang** — u `app.js` dan oldin yuklanadi
   (`index.html` da tartib shunday). Ortiqcha `window.I18N ? ... : ...`
   yozmang, kod ifloslanadi.
2. **LLM javobiga TEGMANG.** Agent javobi turgan elementlar (`.pm-feed-item`,
   `.chat-thinking-card`, `.exec-summary-card`) hech qachon tarjima qilinmaydi.
   Bu ro'yxatdagi toastlar LLM javobi emas — xavfsiz. Lekin `e.message` yoki
   `event.error` kabi DINAMIK qiymatlarni tarjima qilishga urinmang, ular
   parametr sifatida uzatiladi.
3. **`static/` ni o'zgartirgandan keyin `index.html` dagi `?t=` cache-bust
   raqamini yangilang**, aks holda brauzer eski JS ni beradi va "ishlamadi"
   bo'lib ko'rinadi.
4. **Bash heredoc orqali Python skript yozayotganda teskari slesh yeyiladi**
   (`\'` -> `'`). Patch skriptini faylga yozib, keyin ishga tushiring.

## Tekshiruv (majburiy, hammasi o'tishi shart)

```bash
node --check static/js/app.js
PYTHONIOENCODING=utf-8 python tests/test_platform.py     # 115/115 bo'lishi shart
```

Va ish haqiqatan bajarilganini isbotlovchi hisob — **56 dan 0 ga tushishi kerak**:

```bash
python - <<'EOF'
import re
from pathlib import Path
CYR = re.compile(r'[А-Яа-яЁё]')
n = 0
for l in Path("static/js/app.js").read_text(encoding="utf-8").split("\n"):
    t = l.strip()
    if not CYR.search(l) or t.startswith(("//", "*", "/*")):
        continue
    if any(k in t for k in (".toast(", "showToast(", "confirm(", "alert(")):
        n += 1
print("qolgan:", n)
EOF
```

## To'liq ro'yxat (56 ta) — `static/js/app.js`

`P` = parametrli (`${...}` bor, `I18N.t(key, {...})` ishlating).

| Qator | P | Kod |
|---|---|---|
| 1250 |  | `if (hasContent && !window.confirm('Очистить всю историю Project Manager? Это действие необратимо.')) {` |
| 1308 |  | `this.toast('История очищена', 'Лента Project Manager пуста', 'ok');` |
| 1372 | **P** | `this.toast('Файл слишком большой', `Лимит — ${MAX_MB} МБ. Укажите путь к папке.`, 'error');` |
| 1386 |  | `this.toast('Материал прикреплён',` |
| 1391 |  | `this.toast('Не удалось прикрепить', e.message, 'error');` |
| 1413 |  | `this.toast('Папка прикреплена',` |
| 1418 |  | `this.toast('Путь недоступен', e.message, 'error');` |
| 2098 |  | `this.toast('Остановка', 'Задача отменена', 'warn');` |
| 2100 |  | `this.toast('Остановка', 'Нет активной задачи для отмены', 'warn');` |
| 2103 |  | `this.toast('Не удалось остановить', e.message, 'error');` |
| 2117 |  | `this.toast('Задача уже выполняется', 'Дождитесь завершения или нажмите «Стоп»', 'warn');` |
| 2158 |  | `this.toast('Запомнено в памяти PM', remembered.slice(0, 80), 'ok');` |
| 2210 |  | `this.toast('Ошибка оркестратора', err.message.slice(0, 120), 'error');` |
| 2658 |  | `this.toast('Оркестрация остановлена', event.error \|\| '', 'error', 6000);` |
| 2716 |  | `this.toast('Оркестрация отменена', 'Задача остановлена по запросу пользователя', 'warn', 4000);` |
| 2724 |  | `this.toast('Файл записан', event.filename \|\| '', 'info', 2000);` |
| 3456 |  | `this.toast('Не удалось назначить модель', e.message, 'error');` |
| 3567 | **P** | `alert(`Роль «${roleName.trim()}» успешно создана!`);` |
| 3570 |  | `alert('Ошибка при создании роли: ' + JSON.stringify(data));` |
| 3573 |  | `alert('Ошибка: ' + e.message);` |
| 3779 | **P** | `this.toast('Провайдер подключён', `${c.display_name}: ${c.models_count} моделей`, 'ok');` |
| 3875 |  | `this.toast('Не удалось выполнить', data.error.safe_message \|\| data.error.code, 'error');` |
| 3877 | **P** | `this.toast('Модели обновлены', `${(data.models \|\| []).length} моделей`, 'ok');` |
| 3879 |  | `this.toast('Соединение в порядке', 'Провайдер отвечает', 'ok');` |
| 3881 |  | `this.toast('Подключение удалено', data.note \|\| '', 'warn');` |
| 3886 |  | `this.toast('Ошибка сети', e.message, 'error');` |
| 4300 |  | `if (!confirm('Сбросить всю статистику расхода токенов и начать новый учётный период?')) return;` |
| 4592 |  | `this.toast('Сеть', 'Не удалось сохранить режим кэша: ' + e.message, 'error');` |
| 4604 | **P** | `this.toast('Параметры сохранены', `temp=${t}, max_tokens=${m}, vision=${v ? 'вкл' : 'выкл'}, free=${f ? 'да' : 'нет'}${c` |
| 4606 |  | `this.toast('Ошибка', data.error \|\| '—', 'error');` |
| 4609 |  | `this.toast('Сеть', e.message, 'error');` |
| 4639 | **P** | `this.toast('Бесплатные модели', `Загружено ${data.count} моделей от OpenRouter`, 'ok');` |
| 4782 | **P** | `if (resultEl) { resultEl.className = 'key-test-result ok'; resultEl.textContent = '✓ ' + (data.message \|\| 'OK'); } windo` |
| 4784 | **P** | `if (resultEl) { resultEl.className = 'key-test-result err'; resultEl.textContent = '✗ ' + (data.error \|\| `HTTP ${data.st` |
| 4854 |  | `window.showToast('Настройки сохранены', 'Конфигурация API и режим зон успешно применены', 'success');` |
| 4858 |  | `window.showToast('Ошибка сохранения', data.message \|\| 'Проверьте API ключ', 'error');` |
| 4971 |  | `alert('Ошибка создания файла: ' + JSON.stringify(data));` |
| 4974 |  | `alert('Ошибка: ' + e.message);` |
| 5079 |  | `alert('Ошибка создания файла: ' + JSON.stringify(data));` |
| 5082 |  | `alert('Ошибка: ' + e.message);` |
| 5103 |  | `alert('Пожалуйста, укажите Base URL провайдера (например, http://localhost:11434/v1 или https://openrouter.ai/api/v1)');` |
| 5131 | **P** | `alert(`Не удалось загрузить модели с ${baseUrl}: ${data.error \|\| 'Список моделей пуст'}`);` |
| 5134 |  | `alert('Ошибка запроса: ' + e.message);` |
| 5143 |  | `alert('Сначала загрузите список моделей!');` |
| 5163 | **P** | `alert(`Успешно импортировано ${data.count} моделей в систему Ant Colony AI!`);` |
| 5169 |  | `alert('Ошибка импорта: ' + e.message);` |
| 5176 |  | `window.showToast('Файл не выбран', 'Выберите файл для удаления', 'warning');` |
| 5179 | **P** | `if (!confirm(`Вы действительно хотите удалить файл ${_activeSkillFile}?`)) return;` |
| 5185 | **P** | `window.showToast('Файл удален', `Файл ${_activeSkillFile} успешно удален`, 'info');` |
| 5191 |  | `window.showToast('Ошибка удаления', data.detail \|\| data.error, 'error');` |
| 5194 |  | `window.showToast('Ошибка сети', e.message, 'error');` |
| 5200 |  | `window.showToast('Документ не выбран', 'Выберите документ для удаления', 'warning');` |
| 5203 | **P** | `if (!confirm(`Вы действительно хотите удалить документ ${_activeMdFile}?`)) return;` |
| 5209 | **P** | `window.showToast('Документ удален', `Файл ${_activeMdFile} успешно удален`, 'info');` |
| 5215 |  | `window.showToast('Ошибка удаления', data.detail \|\| data.error, 'error');` |
| 5218 |  | `window.showToast('Ошибка сети', e.message, 'error');` |

## Keyingi bosqichlar (shu briefdagi qoidalar o'zgarmaydi)

2. Setup Wizard — `index.html`, 88 ta
3. Topbar / HUD — `index.html`, 50 ta
4. CEO Briefing + Token modallari — 39 ta
5. Qolgan modallar
6. `hive3d.js` — 73 ta (3D sahna yorliqlari; DOM emas, `I18N.t(key, lang)`
   to'g'ridan-to'g'ri chaqiriladi — `CLAUDE.md` dagi "3D canvas labels" ga qarang)
