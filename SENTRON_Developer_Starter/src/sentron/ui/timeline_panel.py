"""Unified Timeline Panel for SENTRON (AC-16).

Aggregates AgentGuard and CrashGuard events into a single temporal feed.
Includes the authoritative causality disclaimer.
"""
from __future__ import annotations

import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QFrame,
)

from sentron.core.storage import EventStore


class UnifiedTimelinePanel(QWidget):
    """Temporal correlation search interface across AgentGuard and CrashGuard."""

    def __init__(self, event_store: EventStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.event_store = event_store
        self._theme = "light"
        self._init_ui()
        self.refresh_timeline()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Causality Disclaimer Banner (AC-16)
        self.disclaimer_box = QFrame()
        self.disclaimer_box.setStyleSheet(
            "background-color: #FAF6ED; border-left: 4px solid #E2B83B; border-radius: 4px; padding: 10px;"
        )
        disc_layout = QVBoxLayout(self.disclaimer_box)
        self.lbl_disc_title = QLabel("ℹ️ Temporal Correlation Disclaimer (AC-16)")
        self.lbl_disc_title.setStyleSheet("font-weight: 700; color: #171717; font-size: 12px;")
        self.lbl_disc_body = QLabel(
            "Temporal correlation between an AI-agent action and host resource pressure provides "
            "investigative context, NOT conclusive proof of causality. Other background processes, "
            "OS updates, or tasks may have caused or contributed to the observed system load."
        )
        self.lbl_disc_body.setStyleSheet("color: #4A453A; font-size: 11px;")
        self.lbl_disc_body.setWordWrap(True)
        disc_layout.addWidget(self.lbl_disc_title)
        disc_layout.addWidget(self.lbl_disc_body)
        layout.addWidget(self.disclaimer_box)

        # Search and filters row
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search events across all subsystems...")
        self.search_input.textChanged.connect(self.refresh_timeline)
        filter_row.addWidget(self.search_input, stretch=3)

        self.subsystem_filter = QComboBox()
        self.subsystem_filter.addItems(["All Subsystems", "AgentGuard", "CrashGuard", "Test", "Core"])
        self.subsystem_filter.currentTextChanged.connect(self.refresh_timeline)
        filter_row.addWidget(self.subsystem_filter, stretch=1)

        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All Severities", "info", "warning", "critical"])
        self.severity_filter.currentTextChanged.connect(self.refresh_timeline)
        filter_row.addWidget(self.severity_filter, stretch=1)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_timeline)
        filter_row.addWidget(btn_refresh)
        layout.addLayout(filter_row)

        # Timeline Events Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Time", "Subsystem", "Event Type", "Severity", "Summary", "Redacted"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def set_theme(self, theme_name: str) -> None:
        """Update disclaimer banner and table text colors to match the active theme."""
        self._theme = (theme_name or "light").lower()
        is_dark = self._theme == "dark"
        if is_dark:
            self.disclaimer_box.setStyleSheet(
                "background-color: #2D2200; border-left: 4px solid #E2B83B; border-radius: 4px; padding: 10px;"
            )
            self.lbl_disc_title.setStyleSheet("font-weight: 700; color: #F5F2E9; font-size: 12px;")
            self.lbl_disc_body.setStyleSheet("color: #D9D4C8; font-size: 11px;")
        else:
            self.disclaimer_box.setStyleSheet(
                "background-color: #FAF6ED; border-left: 4px solid #E2B83B; border-radius: 4px; padding: 10px;"
            )
            self.lbl_disc_title.setStyleSheet("font-weight: 700; color: #171717; font-size: 12px;")
            self.lbl_disc_body.setStyleSheet("color: #4A453A; font-size: 11px;")
        self.refresh_timeline()

    def refresh_timeline(self) -> None:
        """Query and populate the timeline table from SQLite storage."""
        query = self.search_input.text().strip()
        sub_sel = self.subsystem_filter.currentText()
        subsystem = None if sub_sel == "All Subsystems" else sub_sel
        sev_sel = self.severity_filter.currentText()
        severity = None if sev_sel == "All Severities" else sev_sel

        events = self.event_store.search_events(
            query=query,
            subsystem=subsystem,
            severity=severity,
            limit=100,
        )

        is_dark = getattr(self, "_theme", "light") == "dark"
        if is_dark:
            crit_color = QColor("#EF4444")
            warn_color = QColor("#F59E0B")
            info_color = QColor("#58A6FF")
            default_fg = QColor("#F5F2E9")
        else:
            crit_color = QColor("#CF222E")
            warn_color = QColor("#8A4500")
            info_color = QColor("#0969DA")
            default_fg = QColor("#171717")

        if self.table.rowCount() != len(events):
            self.table.setRowCount(len(events))
        for idx, ev in enumerate(events):
            time_str = datetime.datetime.fromtimestamp(ev.timestamp).strftime("%H:%M:%S")
            sev_color = crit_color if ev.severity == "critical" else (warn_color if ev.severity == "warning" else info_color)
            red_str = "YES [Sanitized]" if ev.redacted else "No"

            cells = [
                (0, time_str, default_fg),
                (1, ev.subsystem, default_fg),
                (2, ev.event_type, default_fg),
                (3, ev.severity.upper(), sev_color),
                (4, ev.summary, default_fg),
                (5, red_str, default_fg),
            ]

            for col_idx, text_val, fg in cells:
                item = self.table.item(idx, col_idx)
                if item is None:
                    item = QTableWidgetItem(text_val)
                    item.setForeground(fg)
                    self.table.setItem(idx, col_idx, item)
                else:
                    item.setText(text_val)
                    item.setForeground(fg)
