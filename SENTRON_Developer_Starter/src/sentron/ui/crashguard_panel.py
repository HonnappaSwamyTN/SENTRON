"""CrashGuard Desktop Panel: Real-time Host Telemetry, Sustained-Risk & Recovery Guidance."""
from __future__ import annotations

import datetime
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QSizePolicy,
)

from sentron.core.models import RecoveryRecommendation, RiskAlert, SystemSnapshot
from sentron.crashguard.worker import MonitoringWorker
from sentron.ui.chart_widget import ResourceChartWidget


class CrashGuardPanel(QWidget):
    """Real-time Windows system monitoring and safe recovery guidance panel."""

    alert_recorded = Signal(object, list)

    def __init__(
        self,
        worker: MonitoringWorker,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.worker = worker
        self._current_alert: RiskAlert | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header with live status badge and timestamp
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ CrashGuard System Health Guardian")
        title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #58a6ff;")

        self.lbl_status = QLabel("MONITORING ACTIVE • 2s CADENCE")
        self.lbl_status.setObjectName("badgeActive")

        self.lbl_timestamp = QLabel("Last update: --:--:--")
        self.lbl_timestamp.setStyleSheet("color: #8b949e; font-size: 11px;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_timestamp)
        header_layout.addWidget(self.lbl_status)
        main_layout.addLayout(header_layout)

        # Stat cards row (CPU, RAM, Disk)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(8)

        self.card_cpu = self._create_stat_card("CPU UTILIZATION", "0.0%", "Warning threshold: >85% (sustained)")
        self.card_ram = self._create_stat_card("RAM UTILIZATION", "0.0%", "Available: -- MB")
        self.card_disk = self._create_stat_card("DISK STORAGE", "-- GB", "Primary Drive Free Space")

        cards_layout.addWidget(self.card_cpu)
        cards_layout.addWidget(self.card_ram)
        cards_layout.addWidget(self.card_disk)
        main_layout.addLayout(cards_layout)

        # Sustained-Risk Alert Banner (Hidden by default, shown upon alert)
        self.alert_banner = QFrame()
        self.alert_banner.setStyleSheet(
            "background-color: #2e1a1a; border: 1px solid #da3633; border-radius: 8px; padding: 12px;"
        )
        alert_vbox = QVBoxLayout(self.alert_banner)
        alert_header = QHBoxLayout()

        self.lbl_alert_title = QLabel("⚠️ SUSTAINED RESOURCE PRESSURE DETECTED")
        self.lbl_alert_title.setStyleSheet("font-weight: 800; color: #f85149; font-size: 13px;")

        btn_dismiss = QPushButton("Dismiss Alert")
        btn_dismiss.setStyleSheet("background-color: #21262d; padding: 4px 10px; font-size: 11px;")
        btn_dismiss.clicked.connect(self._dismiss_alert)

        alert_header.addWidget(self.lbl_alert_title)
        alert_header.addStretch()
        alert_header.addWidget(btn_dismiss)
        alert_vbox.addLayout(alert_header)

        self.lbl_alert_desc = QLabel("Observed sustained pressure.")
        self.lbl_alert_desc.setStyleSheet("color: #e6edf3; font-size: 12px; margin-top: 4px;")
        self.lbl_alert_desc.setWordWrap(True)
        alert_vbox.addWidget(self.lbl_alert_desc)

        self.lbl_recovery_advice = QLabel("Safe Recovery Steps:")
        self.lbl_recovery_advice.setStyleSheet("color: #3fb950; font-size: 12px; font-weight: 600; margin-top: 6px;")
        self.lbl_recovery_advice.setWordWrap(True)
        alert_vbox.addWidget(self.lbl_recovery_advice)

        self.alert_banner.setVisible(False)
        main_layout.addWidget(self.alert_banner)

        # Rolling History Chart
        chart_group = QGroupBox("Rolling Resource History (Live psutil Telemetry)")
        chart_layout = QVBoxLayout(chart_group)
        self.chart_widget = ResourceChartWidget(max_samples=60, warning_threshold=85.0)
        chart_layout.addWidget(self.chart_widget)
        main_layout.addWidget(chart_group)

        # Bottom section: Top Processes Table & Synthetic Demo Controls
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        # Top processes table
        proc_group = QGroupBox("Top Active Processes (Safe Ordinary Permissions)")
        proc_layout = QVBoxLayout(proc_group)
        self.proc_table = QTableWidget(0, 4)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "RAM (MB)"])
        self.proc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.proc_table.setMinimumHeight(100)
        self.proc_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        proc_layout.addWidget(self.proc_table)
        bottom_row.addWidget(proc_group, stretch=3)

        # Synthetic Demonstration Box
        demo_group = QGroupBox("Synthetic Demo Controls (Safe Test)")
        demo_layout = QVBoxLayout(demo_group)
        demo_info = QLabel(
            "Test sustained-risk alerts & safe recovery recommendations without overloading your PC:"
        )
        demo_info.setStyleSheet("color: #8b949e; font-size: 11px;")
        demo_info.setWordWrap(True)
        demo_layout.addWidget(demo_info)

        self.btn_sim_cpu = QPushButton("Simulate Sustained CPU (92%)")
        self.btn_sim_cpu.setObjectName("btnWarning")
        self.btn_sim_cpu.clicked.connect(self._simulate_cpu_load)
        demo_layout.addWidget(self.btn_sim_cpu)

        self.btn_sim_ram = QPushButton("Simulate Sustained RAM (94%)")
        self.btn_sim_ram.setObjectName("btnWarning")
        self.btn_sim_ram.clicked.connect(self._simulate_ram_load)
        demo_layout.addWidget(self.btn_sim_ram)

        self.btn_reset_live = QPushButton("Reset to Authentic Live")
        self.btn_reset_live.clicked.connect(self._reset_to_authentic)
        demo_layout.addWidget(self.btn_reset_live)

        demo_note = QLabel("[DEMO] Never mixed with authentic telemetry.")
        demo_note.setStyleSheet("color: #6e7681; font-size: 10px; font-style: italic;")
        demo_layout.addWidget(demo_note)
        demo_layout.addStretch()

        bottom_row.addWidget(demo_group, stretch=2)
        main_layout.addLayout(bottom_row)

    def _create_stat_card(self, title: str, value: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setStyleSheet(
            "background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px;"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        layout.addWidget(lbl_t)

        lbl_v = QLabel(value)
        lbl_v.setObjectName("valLabel")
        lbl_v.setStyleSheet("color: #f0f6fc; font-size: 22px; font-weight: 800; margin: 2px 0;")
        layout.addWidget(lbl_v)

        lbl_s = QLabel(subtitle)
        lbl_s.setObjectName("subLabel")
        lbl_s.setStyleSheet("color: #6e7681; font-size: 11px;")
        layout.addWidget(lbl_s)

        return card

    @Slot(object)
    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Called on main thread when a new SystemSnapshot arrives."""
        time_str = datetime.datetime.fromtimestamp(snapshot.timestamp).strftime("%H:%M:%S")
        self.lbl_timestamp.setText(f"Last update: {time_str}")

        # Update card labels
        cpu_val_lbl = self.card_cpu.findChild(QLabel, "valLabel")
        if cpu_val_lbl:
            cpu_val_lbl.setText(f"{snapshot.cpu_percent:.1f}%")
            if snapshot.cpu_percent >= 85.0:
                cpu_val_lbl.setStyleSheet("color: #f85149; font-size: 22px; font-weight: 800;")
            else:
                cpu_val_lbl.setStyleSheet("color: #58a6ff; font-size: 22px; font-weight: 800;")

        ram_val_lbl = self.card_ram.findChild(QLabel, "valLabel")
        ram_sub_lbl = self.card_ram.findChild(QLabel, "subLabel")
        if ram_val_lbl:
            ram_val_lbl.setText(f"{snapshot.memory_percent:.1f}%")
            if snapshot.memory_percent >= 85.0:
                ram_val_lbl.setStyleSheet("color: #d29922; font-size: 22px; font-weight: 800;")
            else:
                ram_val_lbl.setStyleSheet("color: #3fb950; font-size: 22px; font-weight: 800;")
        if ram_sub_lbl:
            avail_mb = snapshot.memory_available_bytes / (1024 * 1024)
            ram_sub_lbl.setText(f"Available: {avail_mb:.0f} MB")

        disk_val_lbl = self.card_disk.findChild(QLabel, "valLabel")
        if disk_val_lbl:
            free_gb = snapshot.disk_free_bytes / (1024**3)
            disk_val_lbl.setText(f"{free_gb:.1f} GB")

        # Update rolling chart
        self.chart_widget.update_metrics(snapshot.cpu_percent, snapshot.memory_percent)

        # Update processes table
        self.proc_table.setRowCount(len(snapshot.top_processes))
        for r_idx, proc in enumerate(snapshot.top_processes):
            self.proc_table.setItem(r_idx, 0, QTableWidgetItem(str(proc.pid)))
            self.proc_table.setItem(r_idx, 1, QTableWidgetItem(proc.name))
            self.proc_table.setItem(r_idx, 2, QTableWidgetItem(f"{proc.cpu_percent:.1f}%"))
            self.proc_table.setItem(r_idx, 3, QTableWidgetItem(f"{proc.memory_mb:.1f} MB"))

        # Update status badge
        if "synthetic_demo_mode" in snapshot.unavailable_metrics:
            self.lbl_status.setText("DEMO MODE • SYNTHETIC TELEMETRY")
            self.lbl_status.setObjectName("badgeWarning")
            self.lbl_status.setStyleSheet("background-color: #9e6a0322; color: #d29922; border: 1px solid #bb8009;")
        else:
            self.lbl_status.setText("MONITORING ACTIVE • AUTHENTIC")
            self.lbl_status.setObjectName("badgeActive")
            self.lbl_status.setStyleSheet("background-color: #1f6feb22; color: #58a6ff; border: 1px solid #388bfd;")

    @Slot(object, list)
    def handle_alert(self, alert: RiskAlert, recommendations: list[RecoveryRecommendation]) -> None:
        """Called when a sustained threshold breach alert occurs."""
        self._current_alert = alert
        self.lbl_alert_title.setText(
            f"⚠️ SUSTAINED {alert.metric_name.upper()} PRESSURE ({alert.observed_value:.1f}% for {alert.duration_seconds:.0f}s)"
        )
        self.lbl_alert_desc.setText(
            f"Observed value of {alert.observed_value:.1f}% exceeded threshold of {alert.threshold_value:.1f}% continuously. "
            "Evidence indicates sustained system load."
        )

        # Build recovery bullet points
        advice_lines = ["Safe Recovery Guidance (Non-Destructive • No Auto-Kill):"]
        for idx, rec in enumerate(recommendations, 1):
            advice_lines.append(f"  • {rec.title}: {rec.suggested_action}")
        self.lbl_recovery_advice.setText("\n".join(advice_lines))
        self.alert_banner.setVisible(True)

    def _dismiss_alert(self) -> None:
        self.alert_banner.setVisible(False)
        self._current_alert = None

    def _simulate_cpu_load(self) -> None:
        """Trigger synthetic 92% CPU load for demonstration testing."""
        self.worker.trigger_synthetic_demo_load(metric_name="CPU", value=92.0)

    def _simulate_ram_load(self) -> None:
        """Trigger synthetic 94% RAM load for demonstration testing."""
        self.worker.trigger_synthetic_demo_load(metric_name="Memory", value=94.0)

    def _reset_to_authentic(self) -> None:
        """Clear synthetic simulation and resume authentic measurements."""
        self.worker.clear_synthetic_demo_load()
        self.alert_banner.setVisible(False)
        self._current_alert = None
        win = self.window()
        if win and hasattr(win, "dismiss_simulated_alerts"):
            try:
                win.dismiss_simulated_alerts()
            except Exception:
                pass
