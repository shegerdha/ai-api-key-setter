"""Cursor IDE OpenAI-compatible gateway tab."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.codex_config import DEFAULT_GATEWAY_V1, normalize_gateway_v1
from services.cursor_settings import (
    apply_cursor_gateway,
    current_cursor_summary,
    cursor_appears_running,
    read_openai_key,
    state_db_path,
)
from services.gateway_client import fallback_models, fetch_models
from services.profiles import KIND_CURSOR
from ui.log_hub import append as log_append
from ui.profile_bar import ProfileBar
from ui.scroll_area import create_app_scroll_area
from ui.widgets import ArrowComboBox, MaskedTokenEdit

ROW_SPACING = 6
CUSTOM_MODEL_KEY = "__custom_model__"
CUSTOM_MODEL_LABEL = "مدل دلخواه..."
DEFAULT_CURSOR_MODEL = "claude-opus-4-6"


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


class ApplyWorker(QThread):
    finished = Signal(list, str)

    def __init__(self, token: str, base_url: str, model_id: str, extra: list[str]) -> None:
        super().__init__()
        self.args = (token, base_url, model_id, extra)

    def run(self) -> None:
        try:
            logs = apply_cursor_gateway(
                token=self.args[0], base_url_v1=self.args[1],
                model_id=self.args[2], extra_models=self.args[3]
            )
            self.finished.emit(logs, "")
        except Exception as exc:
            self.finished.emit([], str(exc))


class CursorTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._model_worker: ModelFetchWorker | None = None
        self._apply_worker: ApplyWorker | None = None
        self._build_ui()
        self._load_current_state()
        self.profile_bar.load_active_into_form()

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
        self.setObjectName("cursorTab")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll, _content, root = create_app_scroll_area(
            content_object_name="cursorTabScroll",
        )
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.profile_bar = ProfileBar(
            KIND_CURSOR,
            get_fields=self._profile_fields,
            set_fields=self._apply_profile_fields,
            apply_fields=lambda: self._save_settings(silent=True),
            auto_apply=False,
            default_name="Agent Router",
        )
        self.profile_bar.applied.connect(
            lambda: self._append_log("پروفایل Cursor روی سیستم اعمال شد.")
        )
        root.addWidget(self.profile_bar)

        config_group = QGroupBox("اتصال Gateway در Cursor")
        config_group.setAlignment(Qt.AlignmentFlag.AlignRight)
        form = self._setup_form(config_group)

        self.token_edit = MaskedTokenEdit()
        self.token_edit.setPlaceholderText("توکن gateway / OpenAI-compatible")
        form.addRow("توکن API:", self.token_edit)

        self.gateway_url = QLineEdit(DEFAULT_GATEWAY_V1)
        self.gateway_url.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.gateway_url.setPlaceholderText("https://agentrouter.org/v1")
        form.addRow("آدرس پایه (v1):", self.gateway_url)

        self.custom_model_input = QLineEdit()
        self.custom_model_input.setObjectName("customModelInput")
        self.custom_model_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.custom_model_input.setPlaceholderText("شناسه مدل — همان که gateway انتظار دارد")
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
        self.refresh_models_btn.clicked.connect(self._fetch_models)
        form.addRow("مدل:", self._model_row())

        self.register_defaults = QCheckBox(
            "مدل‌های پیش‌فرض gateway را هم در لیست مدل Cursor ثبت کن"
        )
        self.register_defaults.setChecked(True)
        form.addRow("", self.register_defaults)

        root.addWidget(config_group)

        info = QLabel(
            "ذخیره، OpenAI API Key و Override Base URL را در Cursor می‌نویسد "
            "و مدل را به picker اضافه می‌کند. پیش از ذخیره Cursor را کاملاً ببندید؛ سپس دوباره باز کنید."
        )
        info.setObjectName("hintLabel")
        info.setWordWrap(True)
        root.addWidget(info)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hintLabel")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        root.addWidget(self.status_label)

        self.load_btn = QPushButton("خواندن از Cursor")
        self.load_btn.clicked.connect(self._load_current_state)
        self.save_btn = QPushButton("ذخیره در Cursor")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self._save_settings)

        action_row = QHBoxLayout()
        action_row.setSpacing(ROW_SPACING)
        action_row.setContentsMargins(0, 6, 0, 0)
        action_row.addStretch()
        action_row.addWidget(self.save_btn)
        action_row.addWidget(self.load_btn)
        action_row.addStretch()
        root.addLayout(action_row)
        root.addStretch()
        outer.addWidget(scroll, 1)

        self._save_overlay = QFrame(self)
        self._save_overlay.setStyleSheet("QFrame { background: rgba(20, 24, 35, 210); }")
        overlay_layout = QVBoxLayout(self._save_overlay)
        overlay_layout.addStretch()
        self._save_overlay_label = QLabel("در حال ذخیرهٔ تنظیمات Cursor…")
        self._save_overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._save_overlay_label.setStyleSheet("QLabel { color: white; font-size: 16px; font-weight: 600; }")
        overlay_layout.addWidget(self._save_overlay_label)
        overlay_layout.addStretch()
        self._save_overlay.hide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_save_overlay"):
            self._save_overlay.setGeometry(self.rect())
        self._refresh_status()

        default_idx = self.model_combo.findData(DEFAULT_CURSOR_MODEL)
        if default_idx >= 0:
            self.model_combo.setCurrentIndex(default_idx)

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
                self._select_custom_model(custom_text or current)
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

    def _selected_model_id(self) -> str:
        data = self.model_combo.currentData()
        if data == CUSTOM_MODEL_KEY:
            return self.custom_model_input.text().strip()
        if data:
            return str(data)
        text = self.model_combo.currentText().strip()
        return text or DEFAULT_CURSOR_MODEL

    def _extra_models(self) -> list[str]:
        if not self.register_defaults.isChecked():
            return []
        selected = self._selected_model_id()
        return [
            model.model_id
            for model in fallback_models()
            if model.model_id != selected
        ]

    def _set_model(self, model_id: str) -> None:
        if not model_id:
            return
        idx = self.model_combo.findData(model_id)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
            self._sync_custom_model_field(False)
        else:
            self._select_custom_model(model_id)

    def _profile_fields(self) -> dict:
        return {
            "token": self.token_edit.text(),
            "gateway_url": self.gateway_url.text().strip(),
            "model": self._selected_model_id(),
            "register_defaults": self.register_defaults.isChecked(),
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
            self._set_model(model)
        if "register_defaults" in fields:
            self.register_defaults.setChecked(bool(fields.get("register_defaults")))

    def _refresh_status(self) -> None:
        db = state_db_path()
        running = "باز است" if cursor_appears_running() else "باز نیست"
        if not db.exists():
            self.status_label.setText(f"فایل Cursor پیدا نشد. وضعیت برنامه: {running}")
            return
        base, model_id, models = current_cursor_summary()
        extra = f" — مدل فعلی: {model_id}" if model_id else ""
        listed = f" — در picker: {', '.join(models)}" if models else ""
        self.status_label.setText(
            f"Cursor {running}. Base URL ذخیره‌شده: {base or '—'}{extra}{listed}"
        )

    def _load_current_state(self) -> None:
        token = read_openai_key()
        if token:
            self.token_edit.setText(token)
        base, model_id, _models = current_cursor_summary()
        if base:
            self.gateway_url.setText(base)
        if model_id:
            self._set_model(model_id)
        self._refresh_status()
        self._append_log("تنظیمات فعلی Cursor خوانده شد.")

    def _collect(self) -> tuple[str, str, str]:
        token = self.token_edit.text()
        if not token:
            raise ValueError("توکن API الزامی است.")
        model_id = self._selected_model_id()
        if self._is_custom_model_selected() and not model_id:
            raise ValueError("نام مدل دلخواه را وارد کنید.")
        if not model_id:
            model_id = DEFAULT_CURSOR_MODEL
        return token, normalize_gateway_v1(self.gateway_url.text()), model_id

    def _save_settings(self, silent: bool = False) -> bool:
        if self._apply_worker and self._apply_worker.isRunning():
            return False
        try:
            token, base_url, model_id = self._collect()
        except ValueError as exc:
            if not silent:
                QMessageBox.warning(self, "خطا", str(exc))
            return False

        extra = self._extra_models()
        self.save_btn.setEnabled(False)
        self.token_edit.setEnabled(False)
        self._save_overlay.setGeometry(self.rect())
        self._save_overlay.show()
        self._save_overlay.raise_()
        self.status_label.setText("در حال ذخیرهٔ تنظیمات Cursor…")
        self._append_log("ذخیرهٔ Cursor شروع شد؛ لطفاً چند لحظه صبر کنید.")
        self._apply_worker = ApplyWorker(token, base_url, model_id, extra)
        self._apply_worker.finished.connect(
            lambda logs, error: self._on_apply_finished(logs, error, silent)
        )
        self._apply_worker.start()
        return True

    def _on_apply_finished(self, logs: list, error: str, silent: bool) -> None:
        self.save_btn.setEnabled(True)
        self.token_edit.setEnabled(True)
        self._save_overlay.hide()
        self._apply_worker = None
        if error:
            message = error or "ذخیره در Cursor ناموفق بود."
            self.status_label.setText("ذخیرهٔ Cursor ناموفق بود.")
            self._append_log(message)
            if not silent:
                QMessageBox.warning(self, "ذخیره انجام نشد", message)
            return
        self.profile_bar.persist_or_create(self._profile_fields())
        self._refresh_status()
        self._append_log("ذخیره Cursor:\n" + "\n".join(f"- {line}" for line in logs))
        if not silent:
            QMessageBox.information(self, "موفق", "تنظیمات Cursor ذخیره شد. Cursor را دوباره باز کنید.")

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
                self._select_custom_model(custom_text or current)
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
