"""Controlled Process Review and Safe Hold Dialog for CrashGuard (Requirement 6).

Allows the user to safely inspect high-resource processes, assess Chrome's contribution,
confirm a safe process pause, and resume held processes.
"""
from __future__ import annotations

import time
from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QMessageBox,
    QWidget,
)

from sentron.crashguard.process_control import ProcessController


class ProcessReviewDialog(QDialog):
    """Controlled process-response dialog for safe system load relief."""

    def __init__(
        self,
        parent: QWidget | None = None,
        controller: ProcessController | None = None,
        theme: str = "light",
    ) -> None:
        super().__init__(parent)
        self.controller = controller or ProcessController.get_instance()
        self.theme = (theme or "light").lower()

        self.setWindowTitle("SENTRON — High-Resource Process Response")
        self.setMinimumSize(680, 520)
        self.resize(760, 560)

        self._init_ui()
        self.refresh_processes()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header Title and Explanation
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(3)

        title_lbl = QLabel("⚡ High-Resource Process Review & Controlled Hold")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800;")
        header_vbox.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Review active processes consuming system resources. You may selectively pause non-critical "
            "tasks to reduce system load without terminating applications or losing unsaved progress."
        )
        desc_lbl.setStyleSheet("font-size: 11px;")
        desc_lbl.setWordWrap(True)
        header_vbox.addWidget(desc_lbl)
        layout.addLayout(header_vbox)

        # Chrome Advisory Banner (Visible if Chrome is detected)
        self.chrome_card = QFrame()
        self.chrome_card.setObjectName("statCard")
        self.chrome_card.setStyleSheet(
            "border: 1px solid #E2B83B; border-radius: 6px; padding: 10px;"
        )
        chrome_vbox = QVBoxLayout(self.chrome_card)
        chrome_vbox.setSpacing(4)

        self.lbl_chrome_title = QLabel("🌐 Google Chrome Analysis")
        self.lbl_chrome_title.setStyleSheet("font-weight: 700; color: #E2B83B; font-size: 12px;")
        chrome_vbox.addWidget(self.lbl_chrome_title)

        self.lbl_chrome_desc = QLabel("Scanning running Chrome processes...")
        self.lbl_chrome_desc.setStyleSheet("font-size: 11px;")
        self.lbl_chrome_desc.setWordWrap(True)
        chrome_vbox.addWidget(self.lbl_chrome_desc)

        self.lbl_chrome_warn = QLabel(
            "⚠️ Notice: Suspending Chrome pauses thread execution. Active file downloads, media playback, "
            "and web apps will pause until resumed. Always save your web forms and open work first."
        )
        self.lbl_chrome_warn.setStyleSheet("color: #E05252; font-size: 10px; font-weight: 600;")
        self.lbl_chrome_warn.setWordWrap(True)
        chrome_vbox.addWidget(self.lbl_chrome_warn)

        layout.addWidget(self.chrome_card)

        # Top Running Processes Table
        table_header_row = QHBoxLayout()
        tbl_title = QLabel("Active Host Processes (Sorted by RAM)")
        tbl_title.setStyleSheet("font-weight: 700; font-size: 12px;")
        table_header_row.addWidget(tbl_title)
        table_header_row.addStretch()

        btn_refresh = QPushButton("🔄 Refresh List")
        btn_refresh.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_refresh.clicked.connect(self.refresh_processes)
        table_header_row.addWidget(btn_refresh)
        layout.addLayout(table_header_row)

        self.proc_table = QTableWidget(0, 5)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "Memory (MB)", "Status", "Protection"])
        self.proc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.proc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.proc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.proc_table.setSelectionMode(QTableWidget.SingleSelection)
        self.proc_table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.proc_table)

        # Action Buttons row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.btn_pause = QPushButton("⏸️ Pause Selected Process")
        self.btn_pause.setObjectName("btnWarning")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        action_layout.addWidget(self.btn_pause)

        self.btn_resume = QPushButton("▶️ Resume Selected Process")
        self.btn_resume.setObjectName("btnPrimary")
        self.btn_resume.setEnabled(False)
        self.btn_resume.clicked.connect(self._on_resume_clicked)
        action_layout.addWidget(self.btn_resume)

        action_layout.addStretch()

        self.btn_close = QPushButton("Done / Close")
        self.btn_close.clicked.connect(self.accept)
        action_layout.addWidget(self.btn_close)

        layout.addLayout(action_layout)

    def refresh_processes(self) -> None:
        """Populate processes and check Chrome status."""
        procs = self.controller.get_detailed_process_list(limit=25)
        self.proc_table.setRowCount(len(procs))

        chrome_count = 0
        chrome_total_mb = 0.0

        for r, p in enumerate(procs):
            pid = p["pid"]
            name = p["name"]
            mem_mb = p["memory_mb"]
            is_chrome = p["is_chrome"]
            protected = p["protected"]
            prot_reason = p["protection_reason"]
            is_suspended = p["is_suspended"]

            if is_chrome:
                chrome_count += 1
                chrome_total_mb += mem_mb

            # Status label
            if is_suspended:
                status_str = "PAUSED (HELD)"
            elif protected:
                status_str = "SYSTEM CRITICAL"
            else:
                status_str = "RUNNING"

            prot_str = prot_reason if protected else "None (Safe to Hold)"

            item_pid = QTableWidgetItem(str(pid))
            item_name = QTableWidgetItem(name)
            item_mem = QTableWidgetItem(f"{mem_mb:.1f} MB")
            item_stat = QTableWidgetItem(status_str)
            item_prot = QTableWidgetItem(prot_str)

            # Store process dict in row
            item_pid.setData(Qt.UserRole, p)

            self.proc_table.setItem(r, 0, item_pid)
            self.proc_table.setItem(r, 1, item_name)
            self.proc_table.setItem(r, 2, item_mem)
            self.proc_table.setItem(r, 3, item_stat)
            self.proc_table.setItem(r, 4, item_prot)

        # Update Chrome analysis card
        if chrome_count > 0:
            self.chrome_card.setVisible(True)
            if chrome_total_mb >= 300.0:
                self.lbl_chrome_desc.setText(
                    f"Chrome has {chrome_count} active processes consuming {chrome_total_mb:.1f} MB RAM. "
                    "Measured telemetry confirms Chrome is a primary system resource contributor. "
                    "Recommendation: Save work in your open web tabs, then close unnecessary tabs or pause non-critical Chrome processes."
                )
            else:
                self.lbl_chrome_desc.setText(
                    f"Chrome is running with modest memory consumption ({chrome_total_mb:.1f} MB RAM). "
                    "Measured telemetry indicates Chrome is NOT the primary cause of current system pressure."
                )
        else:
            self.chrome_card.setVisible(False)

        self._on_row_selected()

    def _on_row_selected(self) -> None:
        selected_rows = self.proc_table.selectedItems()
        if not selected_rows:
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(False)
            return

        row = self.proc_table.currentRow()
        item = self.proc_table.item(row, 0)
        if not item:
            return

        p = item.data(Qt.UserRole)
        if not p:
            return

        is_suspended = p["is_suspended"]
        is_protected = p["protected"]

        self.btn_pause.setEnabled(not is_suspended and not is_protected)
        self.btn_resume.setEnabled(is_suspended)

    def _on_pause_clicked(self) -> None:
        row = self.proc_table.currentRow()
        item = self.proc_table.item(row, 0)
        if not item:
            return
        p = item.data(Qt.UserRole)
        pid = p["pid"]
        name = p["name"]
        is_chrome = p["is_chrome"]

        # Confirmation Dialog
        warn_text = f"Are you sure you want to pause process '{name}' (PID {pid})?"
        if is_chrome:
            warn_text += (
                "\n\n⚠️ IMPORTANT FOR CHROME:\n"
                "Suspending Chrome will freeze its tabs, active media, and running web applications. "
                "Active downloads will pause. Please ensure you have saved any form inputs or document edits."
            )
        else:
            warn_text += "\n\nThis will temporarily halt process compute to reduce system pressure until resumed."

        confirm = QMessageBox.question(
            self,
            "Confirm Process Hold",
            warn_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if confirm == QMessageBox.Yes:
            success, msg = self.controller.pause_process(pid)
            if success:
                QMessageBox.information(self, "Process Paused", msg)
            else:
                QMessageBox.warning(self, "Pause Failed", msg)
            self.refresh_processes()

    def _on_resume_clicked(self) -> None:
        row = self.proc_table.currentRow()
        item = self.proc_table.item(row, 0)
        if not item:
            return
        p = item.data(Qt.UserRole)
        pid = p["pid"]

        success, msg = self.controller.resume_process(pid)
        if success:
            QMessageBox.information(self, "Process Resumed", msg)
        else:
            QMessageBox.warning(self, "Resume Failed", msg)
        self.refresh_processes()
