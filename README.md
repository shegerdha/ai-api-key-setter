# ai-api-key-setter

ابزار ویندوزی (PySide6) برای تنظیم Claude Code و Codex روی gateway دلخواه (مثل Agent Router).

**نسخه فعلی:** 1.5  
**مجوز:** MIT — [`LICENSE`](LICENSE)

---

## پیش‌نیاز

- **Windows 10/11**
- **Python 3.10+** در PATH (`python --version`)

فونت و آیکون داخل [`assets/`](assets/) هستند؛ برای بیلد نیازی به دانلود از اینترنت نیست.

---

## بیلد exe (روش پیشنهادی)

از **PowerShell** داخل پوشهٔ پروژه:

```powershell
.\build.ps1
```

اسکریپت `build.ps1` این کارها را انجام می‌دهد:

1. نصب وابستگی‌ها از `requirements.txt`
2. بررسی وجود فایل‌های `assets/` (جزئیات در `assets/ASSETS.md`)
3. ساخت `app-icon.ico` از PNG در صورت نبودن
4. اجرای PyInstaller با `ai-api-key-setter.spec`

**خروجی:**

```text
dist\ai-api-key-setter.exe
```

همین فایل را اجرا کن — نصب جدا لازم نیست.

---

## اجرای بدون بیلد (توسعه)

```powershell
python -m pip install -r requirements.txt
python main.py
```

---

## اگر بیلد خطا داد

| مشکل                | راه‌حل                                                  |
| ------------------- | ------------------------------------------------------- |
| `Python not found`  | Python را نصب کن و تیک **Add to PATH** را بزن           |
| خطای `PyInstaller`  | `python -m pip install -U pyinstaller`                  |
| خطای `PIL` / Pillow | `python -m pip install -U Pillow`                       |
| فایل asset گم شده   | `assets/` را از repo کامل clone کن — `assets/ASSETS.md` |

بیلد دستی (بدون اسکریپت):

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm ai-api-key-setter.spec
```

---

## پوشه‌های مهم

| مسیر                     | توضیح                                |
| ------------------------ | ------------------------------------ |
| `main.py`                | نقطهٔ ورود برنامه                    |
| `build.ps1`              | اسکریپت بیلد یک‌مرحله‌ای             |
| `ai-api-key-setter.spec` | تنظیمات PyInstaller                  |
| `assets/`                | فونت و آیکون (commit شده)            |
| `dist\`                  | exe نهایی (بعد از بیلد)              |
| `build\`                 | فایل‌های موقت PyInstaller (قابل حذف) |

---

## نکته

قبل از بیلد نسخهٔ جدید، در `ui\app_meta.py` مقدار `APP_VERSION` را به‌روز کن.

---

## برای ایجنت / توسعهٔ بعدی

جزئیات معماری، Agent Router، الگوهای UI و اشتباهات رایج در **`AGENTS.md`** همین پوشه است.
