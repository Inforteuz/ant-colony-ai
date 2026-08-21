# Mobile UI — implementation plan

_Ant Colony AI · reja 2026-08-21 da tuzildi. Bu hujjat ishni boshqa modelga (Sonnet, Hy3,
DeepSeek va h.k.) topshirish uchun yetarli darajada aniq yozilgan: har faza uchun tegiladigan
fayl, qo'shiladigan selektor/ID va qabul mezoni ko'rsatilgan._

> **Maqsad:** platformani telefonda (375–430px, touch) ishlaydigan qilish. Bu server'ga
> qo'yilganda kerak — hozir faqat desktopda ochiladi.

---

## 0. Boshlang'ich holat (o'lchangan, taxmin emas)

| Fayl | Qator |
|---|---|
| `static/index.html` | 1156 |
| `static/css/style.css` | 6798 |
| `static/js/app.js` | 5331 |
| `static/js/hive3d.js` | 3642 |

**Allaqachon bor:**
- `<meta name="viewport" content="width=device-width, initial-scale=1.0">` — bor, lekin
  `viewport-fit=cover` yo'q.
- `.colony-modal-card` ≤720px da `100vw/100vh`, `border-radius: 0`.
- `.pm-console-drawer`, `.live-workspace-drawer` ≤720px da `100vw`.
- 12 ta media query (1560 → 720px).
- **FPS asosidagi avtomatik sifat rejimi** — `hive3d.js` `_applyQualityMode()`:
  `high` (pixelRatio ≤2, soya bor) / `medium` (≤1.25) / `low` (1.0, soyasiz, `farSkipFrames=3`).
  Mobil GPU muammosining kattagina qismi shu bilan qoplangan.

**Yo'q:**
- 720px dan past breakpoint umuman yo'q — haqiqiy telefon (375–430px) qamralmagan.
- **Touch hodisalari yo'q:** `grep -c "touchstart|touchmove|touchend"` → `hive3d.js: 0`,
  `app.js: 0`. OrbitControls o'z ichida touch'ni qo'llaydi, lekin bosish/tanlash mantiqi
  faqat sichqoncha uchun sozlangan.
- Topbar: brand + 4 KPI pill + 7 tugma + til + tema — 375px ga sig'maydi.
- HUD'da 4 ta suzuvchi panel (`.hud-camera-bar` 14 tugma, `.hud-zoom-bar`,
  `.hud-workflow-bar`, `.hud-live-hud`) — kichik ekranda ustma-ust tushadi.
- 15 ta modal, shundan ~6 tasi ikki ustunli (roles, workspace, skill-editor, md-editor,
  BYOK, deploy) — telefonda stack + "orqaga" kerak.
- 3 ta jadval (usage / task-usage / leaderboard) — gorizontal scroll yoki karta ko'rinish kerak.

**Aniqlangan bug (Faza 0 da tuzatiladi):** `hive3d.js` `setupInteractions()` dagi drag-guard
chegarasi `5px`. Barmoq uchun juda tor — tap "sudrash" deb hisoblanadi va xonaga bosib o'tish
telefonda umuman ishlamaydi.

---

## 1. Breakpoint kelishuvi

Butun ish davomida faqat shu uchta chegara ishlatiladi. Yangi qiymat **o'ylab topilmasin** —
mavjud 12 ta media query allaqachon chalkash, yana qo'shilsa boshqarib bo'lmaydi.

| Nom | Shart | Kim uchun |
|---|---|---|
| `tablet` | `max-width: 900px` | planshet, kichik noutbuk (allaqachon qisman bor) |
| `mobile` | `max-width: 720px` | katta telefon, landshaft (allaqachon qisman bor) |
| `phone` | `max-width: 480px` | **yangi** — asosiy ish shu yerda |

Barcha yangi qoidalar `style.css` oxiriga, bitta izohli blok ostiga yoziladi:

```css
/* ==========================================================================
   MOBILE (≤480px) — docs/MOBILE_UI_PLAN.md
   Bu blok FAQAT telefon uchun. Desktop qoidalariga tegilmaydi — shuning uchun
   hammasi shu yerda, `@media (max-width: 480px)` ichida turadi.
   ========================================================================== */
```

**Qat'iy qoida:** mavjud desktop CSS o'chirilmaydi/o'zgartirilmaydi. Faqat media query
ichidan qayta yoziladi. Sabab — bu ish yarimta qolsa ham desktop buzilmasligi kerak.

---

## Faza 0 — Poydevor va touch (~80 CSS / 60 JS)

Mustaqil faza: desktopga umuman tegmaydi, yolg'iz o'zi ham to'liq qiymat beradi.

### 0.1 Viewport va safe-area
`static/index.html:5`:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

`style.css` — mobil blokka:
- `.fullscreen-viewport`, `.colony-hud-layer`, drawer'lar uchun `height: 100dvh`
  (`100vh` mobil brauzerda manzil paneli tufayli noto'g'ri — kontent pastdan kesiladi).
  `100vh` ni **o'chirmang**, `dvh` ni undan keyin qo'shing — eski brauzer fallback'siz qolmasin.
- Pastki elementlarga (`.hud-workflow-bar`, PM input qatori) `padding-bottom:
  calc(<mavjud> + env(safe-area-inset-bottom))`.
- Yuqoridagilarga (`.hud-topbar`) `padding-top: env(safe-area-inset-top)`.
- `body { overscroll-behavior: none; }` — sahifa "tortilib" ketmasin.

### 0.2 Canvas touch xatti-harakati
`style.css` mobil blokka:
```css
#hive-canvas {
  touch-action: none;              /* jestlarni OrbitControls o'zi boshqarsin */
  -webkit-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;     /* uzoq bosishda iOS menyusi chiqmasin */
}
```

### 0.3 Drag-guard chegarasi (bug tuzatish)
`hive3d.js` → `setupInteractions()` ichida `dragged` hisoblanadigan joy. Hozir qat'iy `5px`.
Bosish turiga qarab o'zgarsin:
```js
// Barmoq bosganda 5px juda tor — deyarli har tap "sudrash" deb hisoblanardi
// va xonaga bosib o'tish telefonda ishlamasdi.
const DRAG_SLOP_MOUSE = 5;
const DRAG_SLOP_TOUCH = 12;
```
`pointerdown` da `e.pointerType` ni saqlang, `pointermove` da mos chegarani ishlating.

### 0.4 Hover mantiqini touchda o'chirish
`setupInteractions()` dagi `mousemove` → kursor `pointer` qilish bloki telefonda keraksiz
(va har harakatda raycast qiladi). Boshiga:
```js
if (window.matchMedia('(hover: none)').matches) return;
```

### 0.5 `.is-phone` klassi (JS uchun yagona manba)
`app.js` konstruktorida yoki `init` da:
```js
// Mobil holatni bitta joydan aniqlaymiz — CSS va JS bir xil chegaradan
// foydalanishi uchun. `resize` da ham yangilanadi (planshet aylantirilishi).
const phoneMQ = window.matchMedia('(max-width: 480px)');
const applyPhoneClass = () => document.body.classList.toggle('is-phone', phoneMQ.matches);
applyPhoneClass();
phoneMQ.addEventListener('change', applyPhoneClass);
this.isPhone = () => phoneMQ.matches;
```

### 0.6 Touch target minimal o'lchami
Mobil blokda barcha bosiladigan elementlarga (`.topbar-btn-pill`, `.btn-cam-view`,
`.btn-drawer-action`, `.btn-hive-action`) `min-height: 44px; min-width: 44px`.

**Qabul mezoni (Faza 0):** telefonda 3D sahna aylanadi, pinch-zoom ishlaydi, xonaga tap
qilib o'tish ishlaydi, sahifa scroll bo'lib "sakramaydi", pastki panellar iPhone'ning
home-indicator chizig'i ostida qolmaydi. Desktopda hech narsa o'zgarmaydi.

---

## Faza 1 — Topbar (~180 CSS / 70 JS / 40 HTML)

375px da topbar'da o'ntadan ortiq element bor. Yechim: **KPI'lar bitta chipga yig'iladi,
amal tugmalari hamburger menyuga tushadi.**

### 1.1 KPI bar → bitta chip + sheet
- `.hud-kpi-bar` mobil blokda `display: none`.
- Uning o'rniga yangi element (`index.html`, `.hud-brand-box` dan keyin):
  ```html
  <button class="hud-kpi-chip" id="btn-kpi-sheet" type="button"
          data-i18n-title="kpi_sheet_title" title="Показатели">
    <span id="chip-kpi-models">21</span> · <span id="chip-kpi-tokens">0</span>
  </button>
  ```
  Faqat `body.is-phone` da ko'rinadi (`display: none` default, mobil blokda `flex`).
- Bosilganda pastdan chiquvchi sheet (`#sheet-kpi`) ochiladi — ichida 4 ta KPI to'liq
  ko'rinishda, har biri bosilsa mavjud modalni ochadi (`pill-models-kpi` va h.k. bilan
  bir xil handler'lar — **yangi handler yozmang, mavjudlarini qayta ishlating**).
- Chip qiymatlari mavjud `val-total-models` / `val-tokens-used` yangilanadigan joyda
  birga yangilanadi (`app.js` da shu ID'lar yoziladigan funksiyani toping va yoniga qo'shing).

### 1.2 Amal tugmalari → hamburger
- `.hud-actions-group` ichidan mobil blokda faqat ikkitasi qoladi:
  `#btn-pm-console-toggle` (asosiy amal) va yangi `#btn-hud-menu` (hamburger).
  Qolganlari `display: none`.
- `#btn-hud-menu` bosilganda `#sheet-hud-menu` ochiladi: Рейтинг AI, CEO, Роли, Настройки,
  til tanlash, tema almashtirish.
- **Muhim:** menyudagi bandlar mavjud tugmalarning `click` handler'larini chaqirsin
  (`document.getElementById('btn-top-leaderboard').click()` uslubida) — logika
  dublikat qilinmasin, aks holda ikkita joyda tuzatish kerak bo'ladi.

### 1.3 Sheet komponenti (bir marta yoziladi, ikkalasi ishlatadi)
```css
.hud-sheet { position: fixed; left: 0; right: 0; bottom: 0; z-index: 60;
  transform: translateY(100%); transition: transform .22s ease;
  padding-bottom: env(safe-area-inset-bottom); }
.hud-sheet.open { transform: translateY(0); }
.hud-sheet-backdrop { position: fixed; inset: 0; z-index: 59; }
```
JS: `openSheet(id)` / `closeSheet(id)` — backdrop bosilsa va `Escape` da yopiladi.

### 1.4 Brand
Mobil blokda `.hud-brand-box` ichidagi matn (`ANT COLONY` / `AI SWARM`) `display: none`,
faqat SVG logo qoladi. `min-width: 135px` → `min-width: auto`.

### 1.5 i18n
Yangi kalitlar (uchala dictga — `i18n.js` `EXTRA` bloki): `kpi_sheet_title`, `hud_menu`,
`hud_menu_title`, `sheet_close`.

**Qabul mezoni (Faza 1):** 375px da topbar bitta qatorga sig'adi, gorizontal scroll yo'q,
barcha amallar ikki bosishda yetarli. Desktopda (>480px) topbar aynan avvalgidek.

---

## Faza 2 — HUD suzuvchi panellari (~200 CSS / 50 JS)

375px da 4 ta panel ekranning yarmini egallaydi. Har biri uchun qaror:

| Panel | Telefonda |
|---|---|
| `.hud-camera-bar` (14 tugma) | Pastda gorizontal scroll-strip; matnlar allaqachon ≤720px da yashiringan (`style.css:5464`), faqat ikonka qoladi. `scroll-snap-type: x mandatory`. |
| `.hud-zoom-bar` | `display: none` — pinch-zoom bor, tugma keraksiz. |
| `.hud-workflow-bar` | Ingichka gorizontal progress chizig'iga siqiladi (qadam nomlari o'rniga faqat rang + faol qadam nomi). |
| `.hud-live-hud` | Default yopiq; kichik "jonli" nishoni bosilganda ochiladi. Yoki PM drawer sarlavhasiga ko'chiriladi. |

`z-index` tartibi bir joyda hujjatlashtirilsin (hozir turli qiymatlar tarqoq).

**Qabul mezoni:** 3D sahnaning kamida 60% i bo'sh ko'rinadi; hech bir panel boshqasini
qoplamaydi; camera-strip barmoq bilan surилади.

---

## Faza 3 — PM console drawer (~150 CSS / 60 JS)

Eng ko'p ishlatiladigan ekran — sifat shu yerda hal bo'ladi.

- **Bottom-sheet:** telefonda yon panel emas, pastdan to'liq balandlikda chiqadi.
  `.pm-console-drawer` mobil blokda `inset: 0; width: 100vw; height: 100dvh`.
- **Klaviatura:** `visualViewport` API bilan input qatori klaviatura ustida qolsin:
  ```js
  // Mobil klaviatura ochilganda `100dvh` o'zgarmaydi va input klaviatura
  // ostida qolib ketadi. visualViewport balandligiga moslashtiramiz.
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => { /* drawer height */ });
  }
  ```
- **Touch target:** send / stop / attach tugmalari ≥44px.
- **Attachment qatori** (`#pm-path-row`, drop hint) — `flex-wrap: wrap`.
- **Feed:** `.pm-feed-item` padding kamaytiriladi, `font-size: 13px`.
- **Auto-scroll:** klaviatura ochilganda oxirgi xabar ko'rinib tursin.
- **Drop hint** telefonda `display: none` (fayl tashlash yo'q) — o'rniga attach tugmasi.

**Qabul mezoni:** telefonda vazifa yozib yuborish, javobni o'qish, to'xtatish va tozalash
to'liq ishlaydi; klaviatura input'ni yopmaydi.

---

## Faza 4 — Modallar (~250 CSS / 40 JS / 40 HTML)

15 ta modal. `.colony-modal-card` allaqachon ≤720px da to'liq ekran — qolgan ish **ichki
layout**.

**4.1 Ikki ustunli modallar** (`#modal-roles-matrix`, `#modal-workspace`,
`#modal-skill-editor`, `#modal-md-editor`, BYOK paneli, `#modal-deploy`):
- Mobil blokda `grid-template-columns: 1fr` (14 ta `grid-template-columns` bor —
  har birini alohida tekshiring).
- Ikki panel bitta ekranga sig'magani uchun **"ro'yxat → tafsilot" navigatsiyasi**:
  ro'yxatdan element tanlanganda ro'yxat yashirinadi, tafsilot ochiladi, tepada
  "← Назад" tugmasi. Yagona umumiy mexanizm yozilsin (`data-mobile-pane="list|detail"`),
  har modal uchun alohida emas.

**4.2 Jadvallar** (`#modal-token-usage`, `#modal-task-usage`, `#modal-ai-leaderboard`):
- Eng sodda va ishonchli yechim: `overflow-x: auto` + `min-width` jadvalga.
- Vaqt bo'lsa: `usage-table` qatorlarini karta ko'rinishiga o'tkazish
  (`display: block` + `::before` bilan ustun nomi).

**4.3 Setup wizard** (`#modal-setup-wizard`, eng katta modal — ~360 qator HTML):
- `#setup-mode-tabs` (6 ta tab) → gorizontal scroll-strip.
- `.gen-grid` allaqachon ≤720px da `1fr` (`style.css:4759`) — tekshirib chiqilsin.
- Kalit inputlari + "Проверить" tugmasi (`.key-test-row`) → `flex-wrap: wrap`.

**Qabul mezoni:** har bir modal telefonda ochiladi, gorizontal scroll faqat jadvallarda
bo'ladi, har modaldan chiqish yo'li aniq.

---

## Faza 5 — Sinov va tuzatish

**Diqqat:** bu ishni bajaradigan agent brauzer ishga tushira olmaydi (loyiha qoidasi:
server ishga tushirilmaydi). Shuning uchun sinov **foydalanuvchi tomonidan** qilinadi.

Statik tekshiruv (agent qila oladi):
```bash
node --check static/js/app.js && node --check static/js/i18n.js && node --check static/js/hive3d.js
```
```bash
python tests/test_platform.py
```

Foydalanuvchi tekshiradigan ro'yxat:
1. iPhone Safari va Android Chrome — portret va landshaft.
2. 3D: aylantirish, pinch-zoom, xonaga tap.
3. Topbar: hamburger, KPI sheet.
4. PM: vazifa yuborish, klaviatura, stop, tozalash.
5. Har 15 modal ochiladi va yopiladi.
6. Tema almashtirish (yorug'/qorong'i) — ikkalasida ham.
7. Til almashtirish — uz / uz_cyr / ru / en.
8. **Desktop regressiya:** 1920px va 1280px da hech narsa o'zgarmaganini tasdiqlash.

---

## Bajarish tartibi va mustaqillik

```
Faza 0  ──►  Faza 1  ──►  Faza 2
   │
   └──────►  Faza 3  (0 dan keyin mustaqil)
   │
   └──────►  Faza 4  (0 dan keyin mustaqil)
```

Faza 0 — majburiy birinchi. 1, 3, 4 undan keyin **istalgan tartibda** va **alohida
sessiyalarda** bajarilishi mumkin. Faza 2 — Faza 1 dan keyin (sheet komponenti o'sha
yerda yoziladi va 2 da qayta ishlatiladi).

## Xavflar

| Xavf | Oldini olish |
|---|---|
| Yarim qo'llangan CSS desktopni buzadi | Barcha yangi qoidalar faqat `@media` ichida; mavjud qoidalar o'chirilmaydi |
| Handler dublikati (sheet + eski tugma) | Sheet bandlar mavjud tugmaning `.click()` ini chaqiradi |
| i18n sweeper yangi elementlarni buzadi | Dinamik/LLM matn bo'lsa `data-i18n-skip` yoki `.pm-feed-item` klassi (qarang `CLAUDE.md` i18n bo'limi) |
| Yangi breakpoint chalkashligi | Faqat 900 / 720 / 480 — yangi qiymat kiritilmaydi |
| 3D FPS pasayishi | Avtomatik sifat rejimi bor; qo'shimcha `low` majburlash **kerak emas** |
