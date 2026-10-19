"""Unified Timeline Panel for SENTRON (AC-16).

Aggregates AgentGuard and CrashGuard events into a single temporal feed.
Includes the authoritative causality disclaimer.
"""
from __future__ import annotations

import datetime
from PySide6.QtCore import Qt
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
        self._init_ui()
        self.refresh_timeline()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Causality Disclaimer Banner (AC-16)
        disclaimer_box = QFrame()
        disclaimer_box.setStyleSheet(
            "background-color: #1f242c; border-left: 4px solid #58a6ff; border-radius: 4px; padding: 10px;"
        )
        disc_layout = QVBoxLayout(disclaimer_box)
        lbl_disc_title = QLabel("ℹ️ Temporal Correlation Disclaimer (AC-16)")
        lbl_disc_title.setStyleSheet("font-weight: 700; color: #58a6ff; font-size: 12px;")
        lbl_disc_body = QLabel(
            "Temporal correlation between an AI-agent action and host resource pressure provides "
            "investigative context, NOT conclusive proof of causality. Other background processes, "
            "OS updates, or tasks may have caused or contributed to the observed system load."
        )
        lbl_disc_body.setStyleSheet("color: #8b949e; font-size: 11px;")
        lbl_disc_body.setWordWrap(True)
        disc_layout.addWidget(lbl_disc_title)
        disc_layout.addWidget(lbl_disc_body)
        layout.addWidget(disclaimer_box)

        # Search and filters row
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search events across all subsystems...")
        self.search_input.textChanged.connect(self.refresh_timeline)
        filter_row.addWidget(self.search_input, stretch=3)

        self.subsystem_filter = QComboBox()
        self.subsystem_filter.addItems(["All Subsystems", "AgentGuard", "CrashGuard", "Core"])
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

        self.table.setRowCount(len(events))
        for idx, ev in enumerate(events):
            time_str = datetime.datetime.fromtimestamp(ev.timestamp).strftime("%H:%M:%S")
            self.table.setItem(idx, 0, QTableWidgetItem(time_str))
            self.table.setItem(idx, 1, QTableWidgetItem(ev.subsystem))
            self.table.setItem(idx, 2, QTableWidgetItem(ev.event_type))

            sev_item = QTableWidgetItem(ev.severity.upper())
            if ev.severity == "critical":
                sev_item.setForeground(Qt.red)
            elif ev.severity == "warning":
                sev_item.setForeground(Qt.yellow)
            else:
                sev_item.setForeground(Qt.cyan)
            self.table.setItem(idx, 3, sev_item)

            self.table.setItem(idx, 4, QTableWidgetItem(ev.summary))
            red_str = "YES [Sanitized]" if ev.redacted else "No"
            self.table.setItem(idx, 5, QTableWidgetItem(red_str))
