# AGENTS.md — ai-api-key-setter

## Corvexa Discovery

هویت پروژه در `.corvexa/project.yaml` است. Corvexa را از `CORVEXA_HOME` / `CORVEXA_ROOT` یا `~/.corvexa/install.yaml` پیدا کنید و `IDENTITY.corvexa_logical_id` را تطبیق دهید؛ سپس AGENTS و CONTINUE آن را بخوانید. Runtime، Work، State و Handoff در Corvexa می‌مانند. نبود Runtime به معنی امکان‌نداشتن Resume دقیق اجرای قبلی است.

راهنمای ایجنت برای ادامهٔ کار روی این پروژه بدون وابستگی به تاریخچهٔ چت.

## هدف پروژه

ابزار **Windows-only** (PySide6) برای اتصال **Claude Code**، **Codex CLI** و **Cursor** به gateway دلخواه (عمدتاً **Agent Router**: `https://agentrouter.org/v1`) بدون ویرایش دستی:

- env سطح کاربر Windows
- `~/.claude/settings.json`
- `~/.codex/config.toml` + `auth.json`
- `settings.json` در Cursor/VS Code (افزونه Codex)
- نصب npm global در صورت نیاز
- باز کردن ترمینال coach برای `claude` / `codex`

**نسخه:** `ui/app_meta.py` → `APP_VERSION` (فعلاً `1.7`). قبل از بیلد exe حتماً به‌روز شود.

**بیلد:** `.\build.ps1` → `dist\ai-api-key-setter.exe` (جزئیات در `README.md`).

---

## ساختار کد

| مسیر                              | نقش                                                      |
| --------------------------------- | -------------------------------------------------------- |
| `main.py`                         | ورود؛ `app.setLayoutDirection(RTL)`                      |
| `ui/main_window.py`               | تب‌ها: Claude \| Codex \| Cursor \| گزارش \| راهنما \| درباره |
| `ui/claude_tab.py`                | فرم Claude + ذخیره/اعمال                                 |
| `ui/codex_tab.py`                 | فرم Codex + relay status                                 |
| `ui/cursor_tab.py`                | فرم Cursor + ثبت مدل در picker                           |
| `ui/profile_bar.py`               | پروفایل اتصال (سوییچ/ایجاد/حذف)                          |
| `ui/log_tab.py`                   | گزارش عملیات (`log_hub`)                                 |
| `ui/help_tab.py`                  | راهنما — `GuidePage` + `guide_content.py`                |
| `ui/about_tab.py`                 | درباره — **`RtlContentPanel` + آیکن** (نه ساختار راهنما) |
| `ui/scroll_area.py`               | `create_app_scroll_area()` — اسکرول یکسان                |
| `ui/guide_widgets.py`             | ویجت‌های راهنما؛ متن فارسی با HTML `dir="rtl"`           |
| `ui/rtl_panel.py`                 | پنل درباره + `build_about_body()`                        |
| `ui/theme.py`                     | QSS + فونت IRANYekanX                                    |
| `services/codex_routing.py`       | انتخاب مسیر Codex هنگام ذخیره                            |
| `services/codex_gateway_probe.py` | probe `/v1/responses` و relay                            |
| `services/cursor_settings.py`     | OpenAI key / base URL / مدل در `state.vscdb`             |
| `services/profiles.py`            | پروفایل‌های ذخیره‌شدهٔ توکن/مدل                          |
| `services/npm_installer.py`       | npm در GUI (PATH اصلاح‌شده)                              |
| `services/terminal_launcher.py`   | coach script + باز کردن ترمینال                          |

---

## UI — قوانین مهم (اشتباهات رایج)

### اسکرول مشترک

- از `create_app_scroll_area()` استفاده شود؛ `objectName` اسکرول: `appScroll`.
- **هرگز** روی `content` دوباره `QVBoxLayout(content)` نسازید — layout از قبل در `create_app_scroll_area` ساخته شده. از layout برگشتی استفاده کنید (باگ «تب خالی»).

### راهنما vs درباره

| تب         | الگو                                                     | محتوا                                                            |
| ---------- | -------------------------------------------------------- | ---------------------------------------------------------------- |
| **راهنما** | `GuidePage` + `build_help_document()`                    | کارت/مرحله/FAQ در `guide_content.py`                             |
| **درباره** | `RtlContentPanel(show_icon=True)` + `build_about_body()` | متن کوتاه + آیکن؛ **عوض نشود** به ساختار راهنما مگر کاربر بخواهد |

### RTL فارسی

- اپ سراسری RTL است (`main.py`).
- برای متن راهنما: `QLabel` با **RichText** و `<p dir="rtl" align="right">` در `guide_widgets._rtl_paragraph`.
- `AlignRight` تنها روی `QLabel` در RTL کافی نیست.
- ردیف مراحل: `QHBoxLayout` با `LeftToRight` — متن چپ، badge شماره راست.

### دکمه‌ها

- **«ذخیره تنظیمات»:** فقط env + فایل‌ها؛ ترمینال باز **نمی‌کند**.
- **«اعمال و اجرا»:** ذخیره + **یک‌بار** باز کردن ترمینال با coach.
- برای اجرای بعدی کاربر باید خودش ترمینال تازه باز کند (`claude` / `codex`).

---

## Agent Router + Codex (دانش حیاتی)

مستندات Agent Router برای Codex جدید **کهنه** است. رفتار واقعی:

| لایه                         | واقعیت                                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------------------- |
| Codex 0.130+                 | فقط `wire_api = "responses"`                                                                       |
| Agent Router `/v1/responses` | اغلب **404**                                                                                       |
| `/v1/chat/completions`       | **401** برای کلاینت عمومی                                                                          |
| codex-relay محلی             | upstream ممکن است **401 unauthorized client** بدهد                                                 |
| **مسیر کار برای کاربر**      | **Codex 0.92.0** + `wire_api=chat` + `base_url` مستقیم Agent Router — اتصال اول کند (Reconnecting) |

**اولویت ذخیره** (`resolve_codex_save_plan`):

1. `DIRECT_RESPONSES` اگر `/v1/responses` قابل استفاده باشد
2. `RELAY` روی localhost:4444
3. `AGENTROUTER_LEGACY` → توقف relay، chat مستقیم، نصب 0.92 در صورت نیاز

Claude Code با همان توکن روی Agent Router معمولاً کار می‌کند.

---

## Claude Code — مدل

- در **این برنامه** مدل را روی **`claude-opus-4-6`** بگذارید؛ مدل دیگر در gateway ممکن است درست کار نکند.
- بعد از ورود به CLI: `/models` — فقط مدل‌های موجود در پنل واسط (مثلاً Haiku اگر در Agent Router نباشد، در دسترس نیست).
- «بارگذاری مدل‌ها» در UI ممکن است 401 بدهد — طبیعی است؛ لیست پیش‌فرض استفاده می‌شود.

---

## مقادیر اولیه UI (سیستم تازه)

| فیلد     | Claude / Codex                               |
| -------- | -------------------------------------------- |
| توکن     | خالی (مگر env قبلی از ابزار دیگر)            |
| Base URL | **پیش‌فرض پر:** `https://agentrouter.org/v1` |
| مدل      | پیش‌فرض combo (مثلاً opus 4.6 / gpt-5.5)     |

نصب نبودن CLI روی خالی بودن توکن اثر ندارد؛ env ویندوز مهم است.

---

## فایل‌هایی که برنامه می‌نویسد

- `HKCU\Environment` — کلیدهای Claude/Codex
- `~/.claude/settings.json`
- `~/.codex/config.toml`, `auth.json`
- `~/.codex/ai-api-key-setter-coach.ps1` (ممکن است توکن plain-text داشته باشد)
- Cursor/VS Code `settings.json` (با `.bak.ai-api-key-setter`)
- `%APPDATA%\Cursor\User\globalStorage\state.vscdb` — کلید OpenAI، base URL، مدل‌های picker
- `~/.claude/ai-api-key-setter-prefs.json` — prefs UI + پروفایل‌های اتصال (توکن)

---

## ویرایش متن راهنما

- فقط `ui/guide_content.py` — تب درباره در `ui/rtl_panel.py` → `build_about_body()`.
- لحن راهنما: فارسی ساده، تفکیک ذخیره/اعمال، گام ترمینال اجباری.
- در تب Cursor، Cursor باید کاملاً بسته باشد؛ ذخیرهٔ کلید در worker انجام می‌شود و تا پایان Overlay رابط را قفل می‌کند.

---

## محدودیت‌های توسعه

- **Windows only** — از registry و PowerShell coach استفاده می‌شود.
- ویرایش فایل: `apply_patch` (نه PowerShell روی UTF-8).
- تست/بیلد/اجرا فقط وقتی کاربر بخواهد.
- commit/push فقط با درخواست صریح کاربر.
- پاسخ به کاربر فارسی؛ پیام commit انگلیسی.

---

## دستورات سریع

```powershell
python main.py
.\build.ps1
python -c "from ui.main_window import MainWindow"
```
