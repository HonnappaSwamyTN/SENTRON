"""Real-time resource usage history chart widget for CrashGuard.

Draws authentic rolling CPU & RAM telemetry using anti-aliased QPainter.
Includes threshold guides, percentage labels, and legends.
Zero external charting dependencies.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QLinearGradient
from PySide6.QtWidgets import QWidget, QSizePolicy


class ResourceChartWidget(QWidget):
    """Custom painted rolling telemetry chart for CPU and RAM."""

    def __init__(
        self,
        max_samples: int = 60,
        warning_threshold: float = 85.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.max_samples = max_samples
        self.warning_threshold = warning_threshold
        self.cpu_history: list[float] = []
        self.ram_history: list[float] = []
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_metrics(self, cpu: float, ram: float) -> None:
        """Append fresh metrics sample and trigger repaint."""
        self.cpu_history.append(cpu)
        if len(self.cpu_history) > self.max_samples:
            self.cpu_history.pop(0)

        self.ram_history.append(ram)
        if len(self.ram_history) > self.max_samples:
            self.ram_history.pop(0)

        self.update()

    def clear(self) -> None:
        self.cpu_history.clear()
        self.ram_history.clear()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Canvas bounds with margin for axes
        pad_left = 40
        pad_right = 16
        pad_top = 28
        pad_bottom = 24

        plot_w = max(10, w - pad_left - pad_right)
        plot_h = max(10, h - pad_top - pad_bottom)

        # Background fill
        painter.fillRect(0, 0, w, h, QColor("#171717"))
        painter.fillRect(pad_left, pad_top, plot_w, plot_h, QColor("#212121"))
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawRect(pad_left, pad_top, plot_w, plot_h)

        # Font setup
        font = QFont("Segoe UI", 9)
        painter.setFont(font)

        # Draw grid lines & Y labels (0%, 25%, 50%, 75%, 100%)
        grid_pen = QPen(QColor("#2B2B2B"), 1, Qt.DashLine)
        text_pen = QPen(QColor("#D9D4C8"), 1)

        for pct in (0, 25, 50, 75, 100):
            y = pad_top + plot_h - (pct / 100.0) * plot_h
            painter.setPen(grid_pen)
            painter.drawLine(pad_left, int(y), pad_left + plot_w, int(y))
            painter.setPen(text_pen)
            painter.drawText(4, int(y + 4), f"{pct}%")

        # Draw 85% Warning threshold line
        thresh_y = pad_top + plot_h - (self.warning_threshold / 100.0) * plot_h
        warn_pen = QPen(QColor("#E2B83B"), 1, Qt.DotLine)
        painter.setPen(warn_pen)
        painter.drawLine(pad_left, int(thresh_y), pad_left + plot_w, int(thresh_y))

        # Legend at top (CPU: Golden yellow, RAM: Muted warm grey)
        painter.setPen(QColor("#E2B83B"))
        cur_cpu = f"{self.cpu_history[-1]:.1f}%" if self.cpu_history else "0.0%"
        painter.drawText(pad_left, 18, f"■ CPU: {cur_cpu}")

        painter.setPen(QColor("#F5F2E9"))
        cur_ram = f"{self.ram_history[-1]:.1f}%" if self.ram_history else "0.0%"
        painter.drawText(pad_left + 110, 18, f"■ RAM: {cur_ram}")

        painter.setPen(QColor("#E2B83B"))
        painter.drawText(pad_left + 220, 18, f"-- Threshold: {self.warning_threshold:.0f}%")

        # Time axis label
        painter.setPen(text_pen)
        painter.drawText(pad_left, h - 6, f"-{self.max_samples * 2}s")
        painter.drawText(pad_left + plot_w - 30, h - 6, "Now")

        # Plot CPU Line (Golden yellow)
        if len(self.cpu_history) >= 2:
            cpu_points: list[QPointF] = []
            dx = plot_w / float(self.max_samples - 1)
            start_x = pad_left + plot_w - (len(self.cpu_history) - 1) * dx

            for i, val in enumerate(self.cpu_history):
                px = start_x + i * dx
                clamped_val = min(100.0, max(0.0, val))
                py = pad_top + plot_h - (clamped_val / 100.0) * plot_h
                cpu_points.append(QPointF(px, py))

            # Draw CPU Line
            cpu_pen = QPen(QColor("#E2B83B"), 2)
            painter.setPen(cpu_pen)
            for i in range(len(cpu_points) - 1):
                painter.drawLine(cpu_points[i], cpu_points[i + 1])

        # Plot RAM Line (Warm white / grey)
        if len(self.ram_history) >= 2:
            ram_points: list[QPointF] = []
            dx = plot_w / float(self.max_samples - 1)
            start_x = pad_left + plot_w - (len(self.ram_history) - 1) * dx

            for i, val in enumerate(self.ram_history):
                px = start_x + i * dx
                clamped_val = min(100.0, max(0.0, val))
                py = pad_top + plot_h - (clamped_val / 100.0) * plot_h
                ram_points.append(QPointF(px, py))

            # Draw RAM Line
            ram_pen = QPen(QColor("#F5F2E9"), 2)
            painter.setPen(ram_pen)
            for i in range(len(ram_points) - 1):
                painter.drawLine(ram_points[i], ram_points[i + 1])
