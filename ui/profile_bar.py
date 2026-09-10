"""Reusable profile switcher for Claude / Codex / Cursor tabs."""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.app_prefs import get_pref
from services.profiles import (
    active_id,
    create_profile,
    delete_profile,
    list_profiles,
    rename_profile,
    save_fields_to_active,
    set_active,
)
from ui.widgets import ArrowComboBox

ROW_SPACING = 6


class ProfileBar(QGroupBox):
    applied = Signal()

    def __init__(
        self,
        kind: str,
        *,
        get_fields: Callable[[], Dict],
        set_fields: Callable[[Dict], None],
        apply_fields: Optional[Callable[[], bool]] = None,
        auto_apply: bool = True,
        default_name: str = "پیش‌فرض",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__("پروفایل اتصال", parent)
        self.kind = kind
        self._get_fields = get_fields
        self._set_fields = set_fields
        self._apply_fields = apply_fields
        self._auto_apply = auto_apply
        self._default_name = default_name
        self._refreshing = False
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        hint = QLabel(
            "توکن هر پروفایل جدا ذخیره می‌شود. با سوییچ، لازم نیست کلید را دوباره وارد کنید."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)

        self.combo = ArrowComboBox()
        self.combo.setMinimumWidth(180)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)

        self.new_btn = QPushButton("جدید")
        self.rename_btn = QPushButton("تغییر نام")
        self.delete_btn = QPushButton("حذف")
        self.new_btn.clicked.connect(self._create)
        self.rename_btn.clicked.connect(self._rename)
        self.delete_btn.clicked.connect(self._delete)

        row = QHBoxLayout()
        row.setSpacing(ROW_SPACING)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.combo, 1)
        row.addWidget(self.new_btn)
        row.addWidget(self.rename_btn)
        row.addWidget(self.delete_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(hint)
        layout.addLayout(row)

        self.refresh()

    def _auto_apply_key(self) -> str:
        return f"profiles_auto_apply_{self.kind}"

    def auto_apply_enabled(self) -> bool:
        return self._auto_apply and bool(get_pref(self._auto_apply_key(), True))

    def snapshot_current(self) -> None:
        pid = active_id(self.kind)
        if not pid:
            return
        try:
            fields = self._get_fields()
        except Exception:
            return
        token = str(fields.get("token") or "").strip()
        if not token:
            return
        save_fields_to_active(self.kind, fields)

    def refresh(self) -> None:
        self._refreshing = True
        self.combo.blockSignals(True)
        self.combo.clear()
        items = list_profiles(self.kind)
        current = active_id(self.kind)
        if not items:
            self.combo.addItem("پروفایلی نیست — با ذخیره ساخته می‌شود", "")
            self.rename_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
        else:
            self.rename_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            selected = 0
            for index, item in enumerate(items):
                self.combo.addItem(str(item.get("name") or "بدون نام"), item.get("id"))
                if item.get("id") == current:
                    selected = index
            self.combo.setCurrentIndex(selected)
        self.combo.blockSignals(False)
        self._refreshing = False

    def persist_or_create(self, fields: Dict) -> None:
        if active_id(self.kind):
            save_fields_to_active(self.kind, fields)
        else:
            create_profile(self.kind, self._default_name, fields)
        self.refresh()

    def load_active_into_form(self) -> None:
        items = list_profiles(self.kind)
        if not items:
            return
        current = None
        pid = active_id(self.kind)
        for item in items:
            if item.get("id") == pid:
                current = item
                break
        if current is None:
            current = items[0]
            set_active(self.kind, str(current["id"]))
        fields = current.get("fields")
        if isinstance(fields, dict):
            self._set_fields(fields)
        self.refresh()

    def _on_combo_changed(self) -> None:
        if self._refreshing:
            return
        new_id = self.combo.currentData()
        if not new_id:
            return
        if new_id == active_id(self.kind):
            return
        self.snapshot_current()
        set_active(self.kind, str(new_id))
        self.load_active_into_form()
        if self.auto_apply_enabled() and self._apply_fields is not None:
            try:
                fields = self._get_fields()
            except Exception:
                return
            if str(fields.get("token") or "").strip():
                if self._apply_fields():
                    self.applied.emit()

    def _create(self) -> None:
        name, ok = QInputDialog.getText(self, "پروفایل جدید", "نام پروفایل:")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام پروفایل خالی است.")
            return
        self.snapshot_current()
        try:
            fields = self._get_fields()
        except Exception:
            fields = {}
        created = create_profile(self.kind, name, fields)
        set_active(self.kind, str(created["id"]))
        self.refresh()

    def _rename(self) -> None:
        pid = active_id(self.kind)
        if not pid:
            return
        current_name = self.combo.currentText()
        name, ok = QInputDialog.getText(
            self, "تغییر نام", "نام جدید:", text=current_name
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام پروفایل خالی است.")
            return
        rename_profile(self.kind, pid, name)
        self.refresh()

    def _delete(self) -> None:
        pid = active_id(self.kind)
        if not pid:
            return
        answer = QMessageBox.question(
            self,
            "حذف پروفایل",
            f"پروفایل «{self.combo.currentText()}» حذف شود؟",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        delete_profile(self.kind, pid)
        self.refresh()
        self.load_active_into_form()
