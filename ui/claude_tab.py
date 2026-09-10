"""Claude Code configuration tab."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.claude_config import (
    model_alias_for,
    normalize_urls,
    read_settings,
    write_settings,
)
from services.app_prefs import get_pref, update_prefs
from services.env_manager import apply_claude_env, broadcast_env_change, read_claude_env
from services.profiles import KIND_CLAUDE
from services.gateway_client import fallback_models, fetch_models
from services.npm_installer import detect_installation, install_claude_code
from services.terminal_launcher import TerminalKind, launch_claude_interactive
from ui.log_hub import append as log_append
from ui.profile_bar import ProfileBar
from ui.scroll_area import create_app_scroll_area
from ui.widgets import ArrowComboBox, MaskedTokenEdit

DEFAULT_GATEWAY = "https://agentrouter.org/v1"
DEFAULT_VERSION = "2.1.195"
ROW_SPACING = 6
CUSTOM_MODEL_KEY = "__custom_model__"
CUSTOM_MODEL_LABEL = "مدل دلخواه..."


class ModelFetchWorker(QThread):
    finished = Signal(list, str)

    def __init__(self, base_url: str, token: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.token = token

    def run(self) -> None:
        models, error = fetch_models(self.base_url, self.token)
        if not models:
            models = fallback_models()
            if error:
                error = f"{error}\nاز لیست پیش‌فرض استفاده شد."
            else:
                error = ""
        self.finished.emit(models, error)


class InstallWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version

    def run(self) -> None:
        ok, message = install_claude_code(self.version)
        self.finished.emit(ok, message)


class ClaudeTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._model_worker: ModelFetchWorker | None = None
        self._install_worker: InstallWorker | None = None
        self._build_ui()
        self._load_ui_prefs()
        self._load_current_state()
        self._wire_pref_persistence()
        self.profile_bar.load_active_into_form()

    def _field_row(self, field: QWidget, *buttons: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(ROW_SPACING)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field, 1)
        for button in buttons:
            row.addWidget(button)
        return row

    @staticmethod
    def _hbox(*widgets) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(ROW_SPACING)
        row.setContentsMargins(0, 0, 0, 0)
        for widget in widgets:
            row.addWidget(widget)
        return row

    def _version_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(ROW_SPACING)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.version_input, 1)
        row.addWidget(self.install_btn)
        row.addWidget(self.detect_btn)
        return row

    def _browse_button(self) -> QPushButton:
        btn = QPushButton("انتخاب")
        btn.setObjectName("browseBtn")
        btn.setFixedWidth(48)
        return btn

    def _setup_form(self, group: QGroupBox) -> QFormLayout:
        group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        form = QFormLayout(group)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        form.setVerticalSpacing(6)
        form.setHorizontalSpacing(ROW_SPACING)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        return form

    def _build_ui(self) -> None:
        self.setObjectName("claudeTab")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll, content, root = create_app_scroll_area(
            content_object_name="claudeTabScroll",
        )
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.profile_bar = ProfileBar(
            KIND_CLAUDE,
            get_fields=self._profile_fields,
            set_fields=self._apply_profile_fields,
            apply_fields=lambda: self._save_settings(silent=True),
            default_name="Agent Router",
        )
        self.profile_bar.applied.connect(
            lambda: self._append_log("پروفایل Claude روی سیستم اعمال شد.")
        )
        root.addWidget(self.profile_bar)

        config_group = QGroupBox("اتصال Gateway")
        config_group.setAlignment(Qt.AlignmentFlag.AlignRight)
        form = self._setup_form(config_group)

        self.token_edit = MaskedTokenEdit()
        form.addRow("توکن API:", self.token_edit)

        self.gateway_url = QLineEdit(DEFAULT_GATEWAY)
        self.gateway_url.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.gateway_url.setPlaceholderText("https://agentrouter.org/v1")
        form.addRow("آدرس پایه (v1):", self.gateway_url)

        self.custom_model_input = QLineEdit()
        self.custom_model_input.setObjectName("customModelInput")
        self.custom_model_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.custom_model_input.setPlaceholderText("نام مدل — در ANTHROPIC_MODEL ذخیره می‌شود")
        self.custom_model_input.setToolTip(
            "مقدار این فیلد هنگام ذخیره در env ویندوز و settings.json اعمال می‌شود."
        )
        self.custom_model_input.setVisible(False)
        self.custom_model_input.setMinimumWidth(150)

        self.model_combo = ArrowComboBox()
        self.model_combo.setObjectName("modelCombo")
        self.model_combo.setEditable(False)
        self.model_combo.setMinimumWidth(180)
        self.model_combo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.model_combo.currentIndexChanged.connect(self._on_model_combo_changed)
        self._populate_model_combo()
        self.refresh_models_btn = QPushButton("بارگذاری مدل‌ها")
        self.refresh_models_btn.setToolTip(
            "gateway معمولاً این درخواست را رد می‌کند؛ "
            "لیست پیش‌فرض همان مدل‌های Claude Code است."
        )
        self.refresh_models_btn.clicked.connect(self._fetch_models)
        form.addRow("مدل:", self._model_row())

        self.model_alias = QLineEdit()
        self.model_alias.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.model_alias.setPlaceholderText("مثلاً opus[1m] — خالی = خودکار")
        form.addRow("نام مستعار (settings):", self.model_alias)

        self.working_dir = QLineEdit(str(Path.home()))
        self.working_dir.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        browse_wd_btn = self._browse_button()
        browse_wd_btn.clicked.connect(self._browse_working_dir)
        form.addRow("پوشه کاری:", self._field_row(self.working_dir, browse_wd_btn))

        root.addWidget(config_group)

        install_group = QGroupBox("نصب Claude Code")
        install_group.setAlignment(Qt.AlignmentFlag.AlignRight)
        install_form = self._setup_form(install_group)

        self.install_status = QLabel("در حال بررسی...")
        self.install_status.setWordWrap(False)
        self.install_status.setObjectName("hintLabel")
        self.install_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        install_form.addRow("وضعیت:", self.install_status)

        self.version_input = QLineEdit(DEFAULT_VERSION)
        self.version_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.version_input.setPlaceholderText("خالی = آخرین نسخه")
        self.install_btn = QPushButton("نصب / به‌روزرسانی")
        self.install_btn.clicked.connect(self._install_claude)
        self.detect_btn = QPushButton("بررسی مجدد")
        self.detect_btn.clicked.connect(self._refresh_install_status)
        install_form.addRow("نسخه:", self._version_row())

        root.addWidget(install_group)

        apply_group = QGroupBox("اعمال و اجرا")
        apply_group.setAlignment(Qt.AlignmentFlag.AlignRight)
        apply_form = self._setup_form(apply_group)

        self.terminal_combo = ArrowComboBox()
        self.terminal_combo.addItem("PowerShell", TerminalKind.POWERSHELL)
        self.terminal_combo.addItem("CMD", TerminalKind.CMD)
        self.terminal_combo.addItem("ترمینال اختصاصی", TerminalKind.CUSTOM)
        apply_form.addRow("محیط ترمینال:", self.terminal_combo)

        self.custom_terminal = QLineEdit()
        self.custom_terminal.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.custom_terminal.setPlaceholderText("مسیر exe ترمینال portable")
        self.custom_terminal.setToolTip(
            "پیشنهاد: Windows Terminal portable\n"
            "https://github.com/microsoft/terminal/releases"
        )
        browse_term_btn = self._browse_button()
        browse_term_btn.clicked.connect(self._browse_terminal)
        apply_form.addRow("مسیر ترمینال:", self._field_row(self.custom_terminal, browse_term_btn))

        root.addWidget(apply_group)

        self.apply_btn = QPushButton("اعمال و اجرای Claude")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.clicked.connect(self._launch_apply)

        self.load_btn = QPushButton("خواندن از ویندوز")
        self.load_btn.setToolTip(
            "توکن، آدرس و مدل را از env کاربر Windows و settings.json می‌خواند."
        )
        self.load_btn.clicked.connect(self._load_current_state)

        self.save_btn = QPushButton("ذخیره تنظیمات")
        self.save_btn.clicked.connect(self._save_settings)

        action_row = QHBoxLayout()
        action_row.setSpacing(ROW_SPACING)
        action_row.setContentsMargins(0, 6, 0, 0)
        action_row.addStretch()
        action_row.addWidget(self.apply_btn)
        action_row.addWidget(self.load_btn)
        action_row.addWidget(self.save_btn)
        action_row.addStretch()
        root.addLayout(action_row)

        self._refresh_install_status()
        default_idx = self.model_combo.findData("claude-opus-4-6")
        if default_idx >= 0:
            self.model_combo.setCurrentIndex(default_idx)

        outer.addWidget(scroll, 1)

    def _model_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(ROW_SPACING)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.model_combo, 1)
        row.addWidget(self.custom_model_input, 1)
        row.addWidget(self.refresh_models_btn)
        return row

    def _is_custom_model_selected(self) -> bool:
        return self.model_combo.currentData() == CUSTOM_MODEL_KEY

    def _sync_custom_model_field(self, visible: bool) -> None:
        self.custom_model_input.setVisible(visible)
        if visible:
            self.custom_model_input.setFocus()

    def _select_custom_model(self, text: str = "") -> None:
        idx = self.model_combo.findData(CUSTOM_MODEL_KEY)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        if text:
            self.custom_model_input.setText(text)
        self._sync_custom_model_field(True)

    def _on_model_combo_changed(self) -> None:
        self._sync_custom_model_field(self._is_custom_model_selected())

    def _append_custom_model_item(self) -> None:
        if self.model_combo.findData(CUSTOM_MODEL_KEY) < 0:
            self.model_combo.addItem(CUSTOM_MODEL_LABEL, CUSTOM_MODEL_KEY)

    def _populate_model_combo(self, *, keep_current: bool = False) -> None:
        was_custom = keep_current and self._is_custom_model_selected()
        custom_text = self.custom_model_input.text().strip() if was_custom else ""
        current = self._selected_model_id() if keep_current else ""

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for model in fallback_models():
            self.model_combo.addItem(model.display_name, model.model_id)
        self._append_custom_model_item()

        if keep_current:
            if was_custom:
                idx = self.model_combo.findData(CUSTOM_MODEL_KEY)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                self.custom_model_input.setText(custom_text or current)
                self._sync_custom_model_field(True)
            elif current:
                idx = self.model_combo.findData(current)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                    self._sync_custom_model_field(False)
                else:
                    idx = self.model_combo.findData(CUSTOM_MODEL_KEY)
                    if idx >= 0:
                        self.model_combo.setCurrentIndex(idx)
                    self.custom_model_input.setText(current)
                    self._sync_custom_model_field(True)
        else:
            self._sync_custom_model_field(False)

        self.model_combo.blockSignals(False)

    def _append_log(self, text: str) -> None:
        log_append(text)

    def _save_ui_prefs(self) -> None:
        kind = self.terminal_combo.currentData()
        if kind is None:
            return
        update_prefs(
            custom_terminal=self.custom_terminal.text().strip(),
            terminal_kind=kind.value,
            working_dir=self.working_dir.text().strip(),
        )

    def _load_ui_prefs(self) -> None:
        custom = get_pref("custom_terminal", "")
        if custom:
            self.custom_terminal.setText(str(custom))

        kind = get_pref("terminal_kind", TerminalKind.POWERSHELL.value)
        for i in range(self.terminal_combo.count()):
            if self.terminal_combo.itemData(i).value == kind:
                self.terminal_combo.setCurrentIndex(i)
                break

        workdir = get_pref("working_dir", "")
        if workdir:
            self.working_dir.setText(str(workdir))

    def _wire_pref_persistence(self) -> None:
        self.custom_terminal.editingFinished.connect(self._save_ui_prefs)
        self.working_dir.editingFinished.connect(self._save_ui_prefs)
        self.terminal_combo.currentIndexChanged.connect(self._save_ui_prefs)

    def _browse_working_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "انتخاب پوشه کاری", self.working_dir.text())
        if path:
            self.working_dir.setText(path)
            self._save_ui_prefs()

    def _browse_terminal(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب ترمینال",
            self.custom_terminal.text() or "",
            "Executable (*.exe);;All Files (*.*)",
        )
        if path:
            self.custom_terminal.setText(path)
            self._save_ui_prefs()

    def _load_current_state(self) -> None:
        env = read_claude_env()
        token = env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN") or ""
        if token:
            self.token_edit.setText(token)

        openai_base = env.get("OPENAI_BASE_URL") or ""
        if openai_base:
            self.gateway_url.setText(openai_base)
        else:
            settings = read_settings()
            if settings.get("baseUrl"):
                self.gateway_url.setText(str(settings["baseUrl"]))

        model_id = env.get("ANTHROPIC_MODEL") or ""
        if model_id:
            idx = self.model_combo.findData(model_id)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
                self._sync_custom_model_field(False)
            else:
                self._select_custom_model(model_id)

        settings = read_settings()
        if settings.get("model"):
            self.model_alias.setText(str(settings["model"]))

        self._append_log("تنظیمات فعلی سیستم بارگذاری شد.")

    def _profile_fields(self) -> dict:
        return {
            "token": self.token_edit.text(),
            "gateway_url": self.gateway_url.text().strip(),
            "model": self._selected_model_id(),
            "model_alias": self.model_alias.text().strip(),
            "working_dir": self.working_dir.text().strip(),
        }

    def _apply_profile_fields(self, fields: dict) -> None:
        token = str(fields.get("token") or "")
        if token:
            self.token_edit.setText(token)
        gateway = str(fields.get("gateway_url") or "")
        if gateway:
            self.gateway_url.setText(gateway)
        model = str(fields.get("model") or "")
        if model:
            idx = self.model_combo.findData(model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
                self._sync_custom_model_field(False)
            else:
                self._select_custom_model(model)
        alias = str(fields.get("model_alias") or "")
        if alias:
            self.model_alias.setText(alias)
        workdir = str(fields.get("working_dir") or "")
        if workdir:
            self.working_dir.setText(workdir)

    def _selected_model_id(self) -> str:
        data = self.model_combo.currentData()
        if data == CUSTOM_MODEL_KEY:
            return self.custom_model_input.text().strip()
        if data:
            return str(data)
        text = self.model_combo.currentText().strip()
        return text or "claude-opus-4-6"

    def _collect_env_values(self) -> dict[str, str]:
        token = self.token_edit.text()
        if not token:
            raise ValueError("توکن API الزامی است.")
        anthropic_base, openai_base = normalize_urls(self.gateway_url.text())
        model_id = self._selected_model_id()
        if self._is_custom_model_selected() and not model_id:
            raise ValueError("نام مدل دلخواه را وارد کنید.")
        if not model_id:
            model_id = "claude-opus-4-6"
        return {
            "ANTHROPIC_API_KEY": token,
            "ANTHROPIC_AUTH_TOKEN": token,
            "ANTHROPIC_BASE_URL": anthropic_base,
            "OPENAI_BASE_URL": openai_base,
            "ANTHROPIC_MODEL": model_id,
        }

    def _save_settings(self, silent: bool = False) -> bool:
        try:
            env_values = self._collect_env_values()
        except ValueError as exc:
            if not silent:
                QMessageBox.warning(self, "خطا", str(exc))
            return False

        token = env_values["ANTHROPIC_API_KEY"]
        _, openai_base = normalize_urls(self.gateway_url.text())
        model_id = env_values["ANTHROPIC_MODEL"]
        alias = model_alias_for(model_id, self.model_alias.text() or None)

        apply_claude_env(
            token=token,
            anthropic_base_url=env_values["ANTHROPIC_BASE_URL"],
            openai_base_url=openai_base,
            model_id=model_id,
        )
        settings_path = write_settings(token, openai_base, model_id, alias)
        broadcast_env_change()

        self.model_alias.setText(alias)
        self._save_ui_prefs()
        self.profile_bar.persist_or_create(self._profile_fields())
        model_note = " (مدل دلخواه)" if self._is_custom_model_selected() else ""
        self._append_log(
            f"ذخیره شد:\n"
            f"- env کاربر\n"
            f"- {settings_path}\n"
            f"- مدل: {model_id}{model_note}"
        )
        if not silent:
            QMessageBox.information(self, "موفق", "تنظیمات Claude Code ذخیره شد.")
        return True

    def _fetch_models(self) -> None:
        token = self.token_edit.text()
        if not token:
            QMessageBox.warning(self, "خطا", "برای بارگذاری مدل‌ها ابتدا توکن را وارد کنید.")
            return

        self.refresh_models_btn.setEnabled(False)
        self.refresh_models_btn.setText("در حال بارگذاری...")
        self._model_worker = ModelFetchWorker(self.gateway_url.text(), token)
        self._model_worker.finished.connect(self._on_models_fetched)
        self._model_worker.start()

    def _on_models_fetched(self, models: list, error: str) -> None:
        current = self._selected_model_id()
        was_custom = self._is_custom_model_selected()
        custom_text = self.custom_model_input.text().strip() if was_custom else ""

        if models:
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            for model in models:
                self.model_combo.addItem(model.display_name, model.model_id)
            self._append_custom_model_item()
            if was_custom:
                idx = self.model_combo.findData(CUSTOM_MODEL_KEY)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                self.custom_model_input.setText(custom_text or current)
                self._sync_custom_model_field(True)
            else:
                idx = self.model_combo.findData(current)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                self._sync_custom_model_field(False)
            self.model_combo.blockSignals(False)
        else:
            self._populate_model_combo(keep_current=True)
        self.refresh_models_btn.setEnabled(True)
        self.refresh_models_btn.setText("بارگذاری مدل‌ها")
        if error:
            self._append_log(f"بارگذاری مدل‌ها: {error}")
            if "unauthorized client" in error.lower() or "محدودیت کلاینت" in error:
                self._append_log("لیست پیش‌فرض همان مدل‌های Claude Code است.")
        else:
            self._append_log(f"{len(models)} مدل بارگذاری شد.")

    def _refresh_install_status(self) -> None:
        info = detect_installation()
        if info.installed:
            path = info.binary_path or info.shim_path or ""
            short = path if len(path) < 72 else f"...{path[-68:]}"
            self.install_status.setText(f"✓ {info.version}  |  {short}")
        else:
            self.install_status.setText("نصب نیست — npm global را بررسی کنید.")

    def _install_claude(self) -> None:
        self.install_btn.setEnabled(False)
        self.install_btn.setText("در حال نصب...")
        version = self.version_input.text().strip()
        self._install_worker = InstallWorker(version)
        self._install_worker.finished.connect(self._on_install_finished)
        self._install_worker.start()

    def _on_install_finished(self, ok: bool, message: str) -> None:
        self.install_btn.setEnabled(True)
        self.install_btn.setText("نصب / به‌روزرسانی")
        self._append_log(message)
        self._refresh_install_status()
        if ok:
            QMessageBox.information(self, "نصب", message)
        else:
            QMessageBox.warning(self, "خطای نصب", message)

    def _launch_apply(self) -> None:
        if self.apply_btn.isEnabled() is False:
            return
        self.apply_btn.setEnabled(False)
        try:
            if not self._save_settings(silent=True):
                return

            try:
                env_values = self._collect_env_values()
            except ValueError as exc:
                QMessageBox.warning(self, "خطا", str(exc))
                return

            terminal = self.terminal_combo.currentData()
            custom = self.custom_terminal.text().strip() or None
            working_dir = self.working_dir.text().strip() or None
            self._save_ui_prefs()

            ok, message = launch_claude_interactive(
                env=env_values,
                terminal=terminal,
                custom_terminal=custom,
                working_dir=working_dir,
            )
            self._append_log(message)
            if ok:
                QMessageBox.information(
                    self,
                    "اعمال و اجرا",
                    "ترمینال باز شد.\nClaude Code در همان پنجره اجرا می‌شود.",
                )
            else:
                QMessageBox.warning(self, "خطا", message)
        finally:
            self.apply_btn.setEnabled(True)
