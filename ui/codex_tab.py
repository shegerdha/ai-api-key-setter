"""OpenAI Codex configuration tab."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.app_prefs import get_pref, update_prefs
from services.codex_config import (
    DEFAULT_GATEWAY_V1,
    DEFAULT_MODEL,
    is_relay_base_url,
    normalize_gateway_v1,
    parse_config_base_url,
    parse_config_model,
    read_auth,
    read_config_text,
    write_codex_files,
)
from services.codex_env import apply_codex_env, read_codex_env
from services.codex_relay import (
    read_relay_state,
    relay_status_text,
)
from services.codex_config import DEFAULT_RELAY_PORT
from services.codex_routing import (
    LEGACY_CODEX_VERSION,
    CodexRoutingMode,
    resolve_codex_save_plan,
)
from services.gateway_client import fallback_models, fetch_models
from services.ide_codex_settings import apply_chatgpt_settings, restore_chatgpt_settings
from services.npm_installer import (
    codex_needs_legacy_pin,
    detect_codex_installation,
    install_codex,
)
from services.terminal_launcher import TerminalKind, launch_codex_interactive
from ui.log_hub import append as log_append
from ui.scroll_area import create_app_scroll_area
from ui.widgets import ArrowComboBox, MaskedTokenEdit

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


class CodexInstallWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version

    def run(self) -> None:
        ok, message = install_codex(self.version)
        self.finished.emit(ok, message)


class CodexTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._model_worker: ModelFetchWorker | None = None
        self._install_worker: CodexInstallWorker | None = None
        self._build_ui()
        self._load_ui_prefs()
        self._load_current_state()
        self._wire_pref_persistence()

    def _field_row_widget(self, field: QWidget, *buttons: QWidget) -> QWidget:
        row = QWidget()
        row.setObjectName("formRow")
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.setMinimumHeight(32)
        layout = QHBoxLayout(row)
        layout.setSpacing(ROW_SPACING)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(field, 1)
        for button in buttons:
            layout.addWidget(button)
        return row

    def _model_row_widget(self) -> QWidget:
        row = QWidget()
        row.setObjectName("formRow")
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.setMinimumHeight(32)
        layout = QHBoxLayout(row)
        layout.setSpacing(ROW_SPACING)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.model_combo, 1)
        layout.addWidget(self.custom_model_input, 1)
        layout.addWidget(self.refresh_models_btn)
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
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(ROW_SPACING)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        return form

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll, content, root = create_app_scroll_area(
            content_object_name="codexTab",
        )
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        config_group = QGroupBox("اتصال Gateway")
        config_group.setAlignment(Qt.AlignmentFlag.AlignRight)
        config_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        form = self._setup_form(config_group)

        self.token_edit = MaskedTokenEdit()
        self.token_edit.setPlaceholderText("AGENT_ROUTER_TOKEN / OPENAI_API_KEY")
        form.addRow("توکن API:", self.token_edit)

        self.gateway_url = QLineEdit(DEFAULT_GATEWAY_V1)
        self.gateway_url.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.gateway_url.setPlaceholderText("https://agentrouter.org/v1")
        form.addRow("آدرس پایه (v1):", self.gateway_url)

        self.custom_model_input = QLineEdit()
        self.custom_model_input.setObjectName("customModelInput")
        self.custom_model_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.custom_model_input.setPlaceholderText("نام مدل — در config.toml ذخیره می‌شود")
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
            "gateway معمولاً این درخواست را رد می‌کند؛ از لیست پیش‌فرض استفاده می‌شود."
        )
        self.refresh_models_btn.clicked.connect(self._fetch_models)
        form.addRow("مدل:", self._model_row_widget())

        self.working_dir = QLineEdit(str(Path.home()))
        self.working_dir.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        browse_wd_btn = self._browse_button()
        browse_wd_btn.clicked.connect(self._browse_working_dir)
        form.addRow("پوشه کاری:", self._field_row_widget(self.working_dir, browse_wd_btn))

        root.addWidget(config_group)

        install_group = QGroupBox("نصب Codex")
        install_group.setAlignment(Qt.AlignmentFlag.AlignRight)
        install_form = self._setup_form(install_group)

        self.install_status = QLabel("در حال بررسی...")
        self.install_status.setWordWrap(False)
        self.install_status.setObjectName("hintLabel")
        self.install_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        install_form.addRow("وضعیت:", self.install_status)

        self.relay_status = QLabel("codex-relay: ...")
        self.relay_status.setWordWrap(True)
        self.relay_status.setObjectName("ideHint")
        self.relay_status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        install_form.addRow(self.relay_status)

        self.version_input = QLineEdit()
        self.version_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.version_input.setPlaceholderText("خالی = آخرین نسخه")
        self.install_btn = QPushButton("نصب / به‌روزرسانی")
        self.install_btn.clicked.connect(self._install_codex)
        self.detect_btn = QPushButton("بررسی مجدد")
        self.detect_btn.clicked.connect(self._refresh_install_status)

        version_row = QWidget()
        version_row.setObjectName("formRow")
        version_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        version_row.setMinimumHeight(32)
        version_layout = QHBoxLayout(version_row)
        version_layout.setSpacing(ROW_SPACING)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.addWidget(self.version_input, 1)
        version_layout.addWidget(self.install_btn)
        version_layout.addWidget(self.detect_btn)
        install_form.addRow("نسخه:", version_row)

        root.addWidget(install_group)

        ide_group = QGroupBox("افزونه Codex در Cursor / VS Code")
        ide_group.setAlignment(Qt.AlignmentFlag.AlignRight)
        ide_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        ide_layout = QVBoxLayout(ide_group)
        ide_layout.setSpacing(8)
        ide_layout.setContentsMargins(10, 14, 10, 10)

        ide_row = QWidget()
        ide_row.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        ide_row_layout = QHBoxLayout(ide_row)
        ide_row_layout.setContentsMargins(0, 0, 0, 0)
        ide_row_layout.setSpacing(10)

        self.ide_hint = QLabel(
            "هنگام ذخیره، chatgpt.apiBase و chatgpt.config در Cursor و VS Code نوشته می‌شود. "
            "نسخهٔ قبلی settings.json به .bak.ai-api-key-setter منتقل می‌شود."
        )
        self.ide_hint.setWordWrap(True)
        self.ide_hint.setObjectName("ideHint")
        self.ide_hint.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.ide_hint.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self.restore_ide_btn = QPushButton("بازگردانی تنظیمات ادیتور")
        self.restore_ide_btn.clicked.connect(self._restore_ide_settings)
        self.restore_ide_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        ide_row_layout.addWidget(self.ide_hint, 1)
        ide_row_layout.addWidget(
            self.restore_ide_btn, 0, Qt.AlignmentFlag.AlignVCenter
        )
        ide_layout.addWidget(ide_row)

        root.addWidget(ide_group)

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
        browse_term_btn = self._browse_button()
        browse_term_btn.clicked.connect(self._browse_terminal)
        apply_form.addRow(
            "مسیر ترمینال:",
            self._field_row_widget(self.custom_terminal, browse_term_btn),
        )

        root.addWidget(apply_group)

        self.apply_btn = QPushButton("اعمال و اجرای Codex")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.clicked.connect(self._launch_apply)

        self.load_btn = QPushButton("خواندن از ویندوز")
        self.load_btn.setToolTip(
            "توکن را از env ویندوز و config.toml / auth.json می‌خواند."
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

        root.addStretch()
        outer.addWidget(scroll, 1)

        self._refresh_install_status()
        self._refresh_relay_status()
        default_idx = self.model_combo.findData(DEFAULT_MODEL)
        if default_idx >= 0:
            self.model_combo.setCurrentIndex(default_idx)

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
                    self._select_custom_model(current)
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
            codex_custom_terminal=self.custom_terminal.text().strip(),
            codex_terminal_kind=kind.value,
            codex_working_dir=self.working_dir.text().strip(),
        )

    def _load_ui_prefs(self) -> None:
        custom = get_pref("codex_custom_terminal", "")
        if custom:
            self.custom_terminal.setText(str(custom))

        kind = get_pref("codex_terminal_kind", TerminalKind.POWERSHELL.value)
        for i in range(self.terminal_combo.count()):
            if self.terminal_combo.itemData(i).value == kind:
                self.terminal_combo.setCurrentIndex(i)
                break

        workdir = get_pref("codex_working_dir", "")
        if workdir:
            self.working_dir.setText(str(workdir))

    def _wire_pref_persistence(self) -> None:
        self.custom_terminal.editingFinished.connect(self._save_ui_prefs)
        self.working_dir.editingFinished.connect(self._save_ui_prefs)
        self.terminal_combo.currentIndexChanged.connect(self._save_ui_prefs)

    def _refresh_relay_status(self) -> None:
        self.relay_status.setText(relay_status_text())

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
        env = read_codex_env()
        token = env.get("AGENT_ROUTER_TOKEN") or env.get("OPENAI_API_KEY") or ""
        if token:
            self.token_edit.setText(token)

        auth = read_auth()
        if not token and auth.get("OPENAI_API_KEY"):
            self.token_edit.setText(str(auth["OPENAI_API_KEY"]))
        elif not token and auth.get("AGENTROUTER_API_KEY"):
            self.token_edit.setText(str(auth["AGENTROUTER_API_KEY"]))

        config_text = read_config_text()
        relay_state = read_relay_state()
        base_url = parse_config_base_url(config_text)
        if relay_state:
            self.gateway_url.setText(relay_state.upstream)
        elif base_url and not is_relay_base_url(base_url):
            self.gateway_url.setText(base_url)

        model_id = parse_config_model(config_text)
        if model_id:
            idx = self.model_combo.findData(model_id)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
                self._sync_custom_model_field(False)
            else:
                self._select_custom_model(model_id)

        self._refresh_relay_status()
        self._append_log("تنظیمات Codex از سیستم بارگذاری شد.")

    def _selected_model_id(self) -> str:
        data = self.model_combo.currentData()
        if data == CUSTOM_MODEL_KEY:
            return self.custom_model_input.text().strip()
        if data:
            return str(data)
        text = self.model_combo.currentText().strip()
        return text or DEFAULT_MODEL

    def _collect_env_values(self) -> dict[str, str]:
        token = self.token_edit.text()
        if not token:
            raise ValueError("توکن API الزامی است.")
        model_id = self._selected_model_id()
        if self._is_custom_model_selected() and not model_id:
            raise ValueError("نام مدل دلخواه را وارد کنید.")
        if not model_id:
            model_id = DEFAULT_MODEL
        return {
            "AGENT_ROUTER_TOKEN": token,
            "AGENTROUTER_API_KEY": token,
            "OPENAI_API_KEY": token,
        }

    def _save_settings(self, silent: bool = False) -> bool:
        try:
            env_values = self._collect_env_values()
        except ValueError as exc:
            if not silent:
                QMessageBox.warning(self, "خطا", str(exc))
            return False

        token = env_values["AGENT_ROUTER_TOKEN"]
        base_url_v1 = normalize_gateway_v1(self.gateway_url.text())
        model_id = self._selected_model_id() or DEFAULT_MODEL

        save_plan, save_error = resolve_codex_save_plan(base_url_v1, token, relay_port=DEFAULT_RELAY_PORT)
        if save_plan is None:
            self._append_log(f"ذخیره Codex ناموفق: {save_error}")
            self._refresh_relay_status()
            if not silent:
                QMessageBox.warning(self, "خطای اتصال", save_error)
            return False

        routing_mode = save_plan.routing_mode
        route_note = save_plan.route_note
        relay_msg = save_plan.relay_msg
        legacy_msg = ""
        if save_plan.legacy_needed:
            info = detect_codex_installation()
            if codex_needs_legacy_pin(info.version):
                legacy_ok, legacy_msg = install_codex(LEGACY_CODEX_VERSION)
                if not legacy_ok:
                    manual = (
                        f"npm install -g @openai/codex@{LEGACY_CODEX_VERSION}"
                    )
                    legacy_msg = f"{legacy_msg}\nنصب دستی: {manual}"
                    self._append_log(f"نصب Codex {LEGACY_CODEX_VERSION}: {legacy_msg}")
                    if not silent:
                        QMessageBox.warning(
                            self,
                            "نصب خودکار ناموفق",
                            "تنظیمات legacy ذخیره می‌شود.\n\n"
                            f"{legacy_msg}",
                        )

        apply_codex_env(token)
        cfg_path, auth_file, mode_note = write_codex_files(
            token,
            base_url_v1,
            model_id,
            routing_mode=routing_mode,
            relay_port=DEFAULT_RELAY_PORT,
        )
        ide_logs = apply_chatgpt_settings(base_url_v1)

        self._save_ui_prefs()
        self._refresh_relay_status()
        model_note = " (مدل دلخواه)" if self._is_custom_model_selected() else ""
        relay_line = f"- relay: {relay_msg}\n" if relay_msg else ""
        legacy_line = f"- codex: {legacy_msg}\n" if legacy_msg else ""
        self._append_log(
            "ذخیره Codex:\n"
            f"- env: AGENT_ROUTER_TOKEN, OPENAI_API_KEY\n"
            f"- {cfg_path}\n"
            f"- {auth_file}\n"
            f"- مدل: {model_id}{model_note}\n"
            f"- مسیر: {mode_note} — {route_note}\n"
            f"{relay_line}"
            f"{legacy_line}"
            + "\n".join(f"- IDE: {line}" for line in ide_logs)
        )
        if not silent:
            extra_hint = ""
            if routing_mode == CodexRoutingMode.DIRECT_RESPONSES:
                extra_hint = (
                    "\n\nاتصال مستقیم با Codex جدید (responses) پیکربندی شد."
                )
            elif routing_mode == CodexRoutingMode.RELAY:
                extra_hint = (
                    "\n\ncodex-relay در پس‌زمینه فعال شد؛ "
                    "gateway فقط Chat داشت."
                )
            elif routing_mode == CodexRoutingMode.AGENTROUTER_LEGACY:
                extra_hint = (
                    f"\n\nrelay جواب نداد؛ fallback به Codex {LEGACY_CODEX_VERSION} (chat) فعال شد."
                )
            QMessageBox.information(
                self,
                "موفق",
                "تنظیمات Codex ذخیره شد.\n"
                "Cursor/VS Code را یک‌بار restart کنید تا افزونه تنظیمات جدید را ببیند."
                + extra_hint,
            )
        return True

    def _restore_ide_settings(self) -> None:
        logs = restore_chatgpt_settings()
        self._append_log("بازگردانی تنظیمات ادیتور:\n" + "\n".join(logs))
        if any("انجام شد" in line for line in logs):
            QMessageBox.information(self, "بازگردانی", "\n".join(logs))
        else:
            QMessageBox.warning(self, "بازگردانی", "\n".join(logs) or "عملیاتی انجام نشد.")

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
        else:
            self._append_log(f"{len(models)} مدل بارگذاری شد.")

    def _refresh_install_status(self) -> None:
        info = detect_codex_installation()
        if info.installed:
            path = info.binary_path or info.shim_path or ""
            short = path if len(path) < 72 else f"...{path[-68:]}"
            self.install_status.setText(f"✓ {info.version}  |  {short}")
        else:
            self.install_status.setText("نصب نیست — npm global را بررسی کنید.")

    def _install_codex(self) -> None:
        self.install_btn.setEnabled(False)
        self.install_btn.setText("در حال نصب...")
        version = self.version_input.text().strip()
        self._install_worker = CodexInstallWorker(version)
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
        if not self.apply_btn.isEnabled():
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

            ok, message = launch_codex_interactive(
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
                    "ترمینال باز شد.\nCodex در همان پنجره اجرا می‌شود.",
                )
            else:
                QMessageBox.warning(self, "خطا", message)
        finally:
            self.apply_btn.setEnabled(True)
