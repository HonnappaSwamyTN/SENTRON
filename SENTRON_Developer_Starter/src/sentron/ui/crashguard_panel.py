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
    QMessageBox,
)

from sentron.core.models import (
    RecoveryRecommendation,
    RiskAlert,
    SystemSnapshot,
    WindowsEvidence,
)
from sentron.crashguard.process_control import ProcessController
from sentron.crashguard.worker import MonitoringWorker
from sentron.ui.chart_widget import ResourceChartWidget
from sentron.ui.process_dialog import ProcessReviewDialog


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
        self._current_evidence: list[WindowsEvidence] = []
        self._evidence_warnings: list[str] = []
        self.resource_risk_threshold: float = 93.0
        self.temp_warning_threshold: float = 80.0
        self._theme: str = "light"

        self._init_ui()

    def set_theme(self, theme_name: str) -> None:
        """Propagate active theme to child chart and widgets."""
        self._theme = (theme_name or "light").lower()
        self.chart_widget.set_theme(self._theme)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header with live status badge and timestamp
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ CrashGuard System Health Guardian")
        title_label.setObjectName("headerTitle")
        title_label.setStyleSheet("font-size: 16px; font-weight: 800;")

        self.lbl_status = QLabel("MONITORING ACTIVE • 2s CADENCE")
        self.lbl_status.setObjectName("badgeActive")

        self.lbl_timestamp = QLabel("Last update: --:--:--")
        self.lbl_timestamp.setStyleSheet("color: #8b949e; font-size: 11px;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_timestamp)
        header_layout.addWidget(self.lbl_status)
        main_layout.addLayout(header_layout)

        # Stat cards row (CPU, RAM, Disk, CPU Temperature)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(8)

        self.card_cpu = self._create_stat_card("CPU UTILIZATION", "0.0%", "Warning threshold: >93% (sustained)")
        self.card_ram = self._create_stat_card("RAM UTILIZATION", "0.0%", "Available: -- MB")
        self.card_disk = self._create_stat_card("DISK STORAGE", "-- GB", "Primary Drive Free Space")
        self.card_temp = self._create_stat_card(
            "CPU TEMPERATURE",
            "Unavailable",
            "Your hardware or Windows configuration does not expose CPU temperature to SENTRON without elevated access. Other CrashGuard monitoring remains active.",
        )

        cards_layout.addWidget(self.card_cpu)
        cards_layout.addWidget(self.card_ram)
        cards_layout.addWidget(self.card_disk)
        cards_layout.addWidget(self.card_temp)
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
        btn_dismiss.setStyleSheet("background-color: #21262d; color: #f0f6fc; padding: 4px 10px; font-size: 11px;")
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

        # Rolling History Chart (Live psutil + Temperature Telemetry)
        chart_group = QGroupBox("Rolling Resource History (Live psutil & Temperature Telemetry)")
        chart_layout = QVBoxLayout(chart_group)
        self.chart_widget = ResourceChartWidget(max_samples=60, warning_threshold=self.resource_risk_threshold)
        chart_layout.addWidget(self.chart_widget)
        main_layout.addWidget(chart_group)

        # Windows Crash, Hang & Diagnostics Evidence (Extended Event Log Coverage)
        evidence_group = QGroupBox("Host Crash, Hang & System Diagnostics (Windows Event Log: IDs 1000, 1001, 1002, 6008, 41, 1074, 219)")
        evidence_layout = QVBoxLayout(evidence_group)
        evidence_layout.setSpacing(6)

        evidence_header = QHBoxLayout()
        self.lbl_evidence_status = QLabel(
            "Cadence: 60s & on sustained alerts • Coverage: Crash (1000), Hang (1002), WER (1001), Shutdown (6008), Power (41), Restart (1074), Driver (219) • Ready"
        )
        self.lbl_evidence_status.setStyleSheet("color: #4A453A; font-size: 11px; font-weight: 500;")

        self.btn_scan_evidence = QPushButton("Scan Evidence Now")
        self.btn_scan_evidence.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.btn_scan_evidence.clicked.connect(self._on_scan_evidence_clicked)

        evidence_header.addWidget(self.lbl_evidence_status)
        evidence_header.addStretch()
        evidence_header.addWidget(self.btn_scan_evidence)
        evidence_layout.addLayout(evidence_header)


        self.evidence_table = QTableWidget(0, 4)
        self.evidence_table.setHorizontalHeaderLabels(["Time", "Event ID", "Source", "Explanation"])
        self.evidence_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.evidence_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.evidence_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.evidence_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.evidence_table.setMinimumHeight(110)
        self.evidence_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        evidence_layout.addWidget(self.evidence_table)

        main_layout.addWidget(evidence_group)

        # Bottom section: Top Active Processes and Process Hold Controls
        proc_group = QGroupBox("Top Active Processes & Controlled Load Response")
        proc_layout = QVBoxLayout(proc_group)
        proc_layout.setSpacing(8)

        proc_header = QHBoxLayout()
        lbl_proc_desc = QLabel("Real host processes sorted by physical memory. Use Controlled Hold to relieve load safely.")
        lbl_proc_desc.setStyleSheet("font-size: 11px;")

        self.btn_review_processes = QPushButton("⚡ Review High-Impact Processes")
        self.btn_review_processes.setObjectName("btnWarning")
        self.btn_review_processes.setStyleSheet("font-weight: 700; font-size: 11px; padding: 4px 12px;")
        self.btn_review_processes.clicked.connect(self.open_process_review_dialog)

        proc_header.addWidget(lbl_proc_desc)
        proc_header.addStretch()
        proc_header.addWidget(self.btn_review_processes)
        proc_layout.addLayout(proc_header)

        self.proc_table = QTableWidget(0, 4)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "RAM (MB)"])
        self.proc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.proc_table.setMinimumHeight(110)
        self.proc_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        proc_layout.addWidget(self.proc_table)

        # Suspended Processes Drawer (visible when any processes are suspended)
        self.suspended_card = QFrame()
        self.suspended_card.setObjectName("statCard")
        self.suspended_card.setStyleSheet(
            "border: 1px dashed #E2B83B; border-radius: 6px; padding: 8px;"
        )
        susp_vbox = QVBoxLayout(self.suspended_card)
        susp_vbox.setSpacing(6)

        susp_header = QHBoxLayout()
        lbl_susp_title = QLabel("⏸️ Processes Currently Held on Pause by SENTRON")
        lbl_susp_title.setStyleSheet("font-weight: 700; color: #E2B83B; font-size: 11px;")
        susp_header.addWidget(lbl_susp_title)
        susp_header.addStretch()

        self.btn_resume_all = QPushButton("Resume All Held Processes")
        self.btn_resume_all.setStyleSheet("padding: 3px 8px; font-size: 10px;")
        self.btn_resume_all.clicked.connect(self._on_resume_all_clicked)
        susp_header.addWidget(self.btn_resume_all)
        susp_vbox.addLayout(susp_header)

        self.suspended_table = QTableWidget(0, 4)
        self.suspended_table.setHorizontalHeaderLabels(["PID", "Name", "Memory (MB)", "Action"])
        self.suspended_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.suspended_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.suspended_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.suspended_table.setMaximumHeight(90)
        susp_vbox.addWidget(self.suspended_table)

        self.suspended_card.setVisible(False)
        proc_layout.addWidget(self.suspended_card)

        main_layout.addWidget(proc_group)

    def _create_stat_card(self, title: str, value: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setObjectName("statTitle")
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        layout.addWidget(lbl_t)

        lbl_v = QLabel(value)
        lbl_v.setObjectName("valLabel")
        lbl_v.setStyleSheet("color: #E2B83B; font-size: 22px; font-weight: 800; margin: 2px 0;")
        layout.addWidget(lbl_v)

        lbl_s = QLabel(subtitle)
        lbl_s.setObjectName("subLabel")
        lbl_s.setStyleSheet("font-size: 11px;")
        lbl_s.setWordWrap(True)
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
            if snapshot.cpu_percent >= self.resource_risk_threshold:
                cpu_val_lbl.setStyleSheet("color: #E05252; font-size: 22px; font-weight: 800;")
            else:
                cpu_val_lbl.setStyleSheet("color: #E2B83B; font-size: 22px; font-weight: 800;")

        ram_val_lbl = self.card_ram.findChild(QLabel, "valLabel")
        ram_sub_lbl = self.card_ram.findChild(QLabel, "subLabel")
        if ram_val_lbl:
            ram_val_lbl.setText(f"{snapshot.memory_percent:.1f}%")
            if snapshot.memory_percent >= self.resource_risk_threshold:
                ram_val_lbl.setStyleSheet("color: #E05252; font-size: 22px; font-weight: 800;")
            else:
                ram_val_lbl.setStyleSheet("color: #F5F2E9; font-size: 22px; font-weight: 800;")
        if ram_sub_lbl:
            avail_mb = snapshot.memory_available_bytes / (1024 * 1024)
            ram_sub_lbl.setText(f"Available: {avail_mb:.0f} MB")

        disk_val_lbl = self.card_disk.findChild(QLabel, "valLabel")
        if disk_val_lbl:
            free_gb = snapshot.disk_free_bytes / (1024**3)
            disk_val_lbl.setText(f"{free_gb:.1f} GB")

        # Update CPU Temperature card
        temp_val_lbl = self.card_temp.findChild(QLabel, "valLabel")
        temp_sub_lbl = self.card_temp.findChild(QLabel, "subLabel")
        if temp_val_lbl and temp_sub_lbl:
            if snapshot.cpu_temperature_c is not None:
                temp_val_lbl.setText(f"{snapshot.cpu_temperature_c:.1f}°C")
                if snapshot.cpu_temperature_c >= self.temp_warning_threshold:
                    temp_val_lbl.setStyleSheet("color: #E05252; font-size: 22px; font-weight: 800;")
                    temp_sub_lbl.setText(f"Elevated (Advisory >{self.temp_warning_threshold:.0f}°C)")
                else:
                    temp_val_lbl.setStyleSheet("color: #E2B83B; font-size: 22px; font-weight: 800;")
                    temp_sub_lbl.setText(f"Normal • {snapshot.cpu_temperature_reason or 'Active Sensor'}")
            else:
                temp_val_lbl.setText("Unavailable")
                temp_val_lbl.setStyleSheet("color: #8C8578; font-size: 20px; font-weight: 700;")
                temp_sub_lbl.setText(
                    "Your hardware or Windows configuration does not expose CPU temperature to SENTRON "
                    "without elevated access. Other CrashGuard monitoring remains active."
                )

        # Update rolling chart
        self.chart_widget.update_metrics(snapshot.cpu_percent, snapshot.memory_percent, snapshot.cpu_temperature_c)

        # Update processes table (reusing existing items to minimize RAM and GC churn)
        if self.proc_table.rowCount() != len(snapshot.top_processes):
            self.proc_table.setRowCount(len(snapshot.top_processes))
        for r_idx, proc in enumerate(snapshot.top_processes):
            item_pid = self.proc_table.item(r_idx, 0)
            if item_pid is None:
                self.proc_table.setItem(r_idx, 0, QTableWidgetItem(str(proc.pid)))
                self.proc_table.setItem(r_idx, 1, QTableWidgetItem(proc.name))
                self.proc_table.setItem(r_idx, 2, QTableWidgetItem(f"{proc.cpu_percent:.1f}%"))
                self.proc_table.setItem(r_idx, 3, QTableWidgetItem(f"{proc.memory_mb:.1f} MB"))
            else:
                item_pid.setText(str(proc.pid))
                item_name = self.proc_table.item(r_idx, 1)
                if item_name:
                    item_name.setText(proc.name)
                item_cpu = self.proc_table.item(r_idx, 2)
                if item_cpu:
                    item_cpu.setText(f"{proc.cpu_percent:.1f}%")
                item_ram = self.proc_table.item(r_idx, 3)
                if item_ram:
                    item_ram.setText(f"{proc.memory_mb:.1f} MB")

        # Update suspended processes drawer
        self._refresh_suspended_processes_table()

        # Update status badge
        if "synthetic_demo_mode" in snapshot.unavailable_metrics:
            self.lbl_status.setText("DEMO MODE • SYNTHETIC TELEMETRY")
            self.lbl_status.setObjectName("badgeWarning")
            self.lbl_status.setStyleSheet("background-color: #9e6a0322; color: #d29922; border: 1px solid #bb8009;")
        else:
            self.lbl_status.setText("MONITORING ACTIVE • AUTHENTIC")
            self.lbl_status.setObjectName("badgeActive")
            self.lbl_status.setStyleSheet("background-color: #1f6feb22; color: #58a6ff; border: 1px solid #388bfd;")

    def _refresh_suspended_processes_table(self) -> None:
        controller = ProcessController.get_instance()
        suspended = controller.get_suspended_processes()
        if not suspended:
            self.suspended_card.setVisible(False)
            return

        self.suspended_card.setVisible(True)
        self.suspended_table.setRowCount(len(suspended))
        for r, sp in enumerate(suspended):
            item_pid = QTableWidgetItem(str(sp.pid))
            item_name = QTableWidgetItem(sp.name)
            item_mem = QTableWidgetItem(f"{sp.memory_mb:.1f} MB")

            btn_resume = QPushButton("Resume")
            btn_resume.setStyleSheet("padding: 2px 8px; font-size: 10px;")
            # Capture PID in lambda
            btn_resume.clicked.connect(lambda checked=False, p_pid=sp.pid: self._on_resume_single(p_pid))

            self.suspended_table.setItem(r, 0, item_pid)
            self.suspended_table.setItem(r, 1, item_name)
            self.suspended_table.setItem(r, 2, item_mem)
            self.suspended_table.setCellWidget(r, 3, btn_resume)

    def _on_resume_single(self, pid: int) -> None:
        controller = ProcessController.get_instance()
        success, msg = controller.resume_process(pid)
        if success:
            self._refresh_suspended_processes_table()
        else:
            QMessageBox.warning(self, "Resume Failed", msg)

    def _on_resume_all_clicked(self) -> None:
        controller = ProcessController.get_instance()
        controller.resume_all_suspended()
        self._refresh_suspended_processes_table()

    def open_process_review_dialog(self) -> None:
        """Open the controlled process review and safe-hold dialog."""
        dialog = ProcessReviewDialog(parent=self, theme=self._theme)
        dialog.exec()
        self._refresh_suspended_processes_table()

    @Slot(object, list)
    def handle_alert(self, alert: RiskAlert, recommendations: list[RecoveryRecommendation]) -> None:
        """Called when a sustained threshold breach alert occurs."""
        self._current_alert = alert
        unit = "%" if alert.metric_name in ("CPU", "Memory") else ("°C" if alert.metric_name == "CPUTemperature" else "GB")
        self.lbl_alert_title.setText(
            f"⚠️ SUSTAINED {alert.metric_name.upper()} PRESSURE ({alert.observed_value:.1f}{unit} for {alert.duration_seconds:.0f}s)"
        )
        self.lbl_alert_desc.setText(
            f"Observed value of {alert.observed_value:.1f}{unit} exceeded risk limit of {alert.threshold_value:.1f}{unit} continuously. "
            "Evidence indicates sustained system load."
        )

        # Build recovery bullet points
        advice_lines = ["Safe Recovery Guidance (Non-Destructive • No Auto-Kill):"]
        for idx, rec in enumerate(recommendations, 1):
            line = f"  • {rec.title}: {rec.suggested_action}"
            if rec.help_url:
                line += f" (Help: {rec.help_url})"
            advice_lines.append(line)
        self.lbl_recovery_advice.setText("\n".join(advice_lines))
        self.alert_banner.setVisible(True)

    def _dismiss_alert(self) -> None:
        self.alert_banner.setVisible(False)
        self._current_alert = None

    def _simulate_cpu_load(self) -> None:
        """Trigger synthetic 94% CPU load for demonstration testing (breaches 93% limit)."""
        self.worker.trigger_synthetic_demo_load(metric_name="CPU", value=94.0)

    def _simulate_ram_load(self) -> None:
        """Trigger synthetic 94% RAM load for demonstration testing (breaches 93% limit)."""
        self.worker.trigger_synthetic_demo_load(metric_name="Memory", value=94.0)

    def _simulate_temp_load(self) -> None:
        """Trigger synthetic 86°C CPU Temperature for demonstration testing (breaches 80°C advisory limit)."""
        self.worker.trigger_synthetic_demo_load(metric_name="CPUTemperature", value=86.0)

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

    @Slot(list, list)
    def update_evidence(self, evidence_records: list[WindowsEvidence], warnings: list[str] = ()) -> None:
        """Update the evidence table with captured diagnostic records and fallback warnings."""
        self._current_evidence = list(evidence_records)
        self._evidence_warnings = list(warnings)

        self.evidence_table.setRowCount(len(evidence_records))
        for r_idx, ev in enumerate(evidence_records):
            # Timestamp display
            try:
                t_part = ev.event_time.split("T")[1].split(".")[0] if "T" in ev.event_time else ev.event_time
            except Exception:
                t_part = ev.event_time

            item_time = QTableWidgetItem(t_part)
            item_time.setToolTip(ev.event_time)

            item_id = QTableWidgetItem(str(ev.event_id))
            item_id.setToolTip(f"Event ID: {ev.event_id} ({ev.log_channel} Channel)")

            item_source = QTableWidgetItem(ev.source)
            item_source.setToolTip(ev.source)

            # Separate confirmed observation from suspected cause (AC-11)
            confirmed, inferred = self.worker.evidence_collector.format_diagnostic_statement(ev)
            concise_explanation = f"{confirmed} — {inferred}"
            item_exp = QTableWidgetItem(concise_explanation)
            item_exp.setToolTip(
                f"{confirmed}\n\n{inferred}\n\nLog Channel: {ev.log_channel}\nRaw Details: {ev.description}"
            )
            item_exp.setData(Qt.UserRole, ev)

            self.evidence_table.setItem(r_idx, 0, item_time)
            self.evidence_table.setItem(r_idx, 1, item_id)
            self.evidence_table.setItem(r_idx, 2, item_source)
            self.evidence_table.setItem(r_idx, 3, item_exp)

        # Update evidence status label
        if warnings:
            warn_msg = ", ".join(warnings)
            self.lbl_evidence_status.setText(f"Status: Fallback active ({warn_msg})")
            self.lbl_evidence_status.setStyleSheet("color: #d29922; font-size: 11px;")
        elif not evidence_records:
            self.lbl_evidence_status.setText(
                "Status: No application errors, hangs, power cuts, or unexpected shutdown events recorded in Windows logs."
            )
            self.lbl_evidence_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        else:
            self.lbl_evidence_status.setText(
                f"Status: {len(evidence_records)} diagnostic record(s) captured across Application & System event logs"
            )
            self.lbl_evidence_status.setStyleSheet("color: #3fb950; font-size: 11px;")

    def _on_scan_evidence_clicked(self) -> None:
        """Trigger immediate non-blocking scan on user request."""
        self.worker.trigger_evidence_collection_async()

    def get_evidence_count(self) -> int:
        return len(self._current_evidence)

    def get_evidence_item(self, row: int) -> WindowsEvidence | None:
        if 0 <= row < len(self._current_evidence):
            return self._current_evidence[row]
        return None
