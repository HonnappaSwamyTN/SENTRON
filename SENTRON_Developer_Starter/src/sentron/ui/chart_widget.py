"""Real-time resource usage history chart widget for CrashGuard.

Draws authentic rolling CPU, RAM, and Temperature telemetry using anti-aliased QPainter.
Adapts dynamically to Light and Dark themes.
Includes 93% threshold guides, percentage labels, and legends.
Zero external charting dependencies.
"""
from __future__ import annotations

import collections

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget, QSizePolicy


class ResourceChartWidget(QWidget):
    """Custom painted rolling telemetry chart for CPU, RAM, and Temperature."""

    def __init__(
        self,
        max_samples: int = 60,
        warning_threshold: float = 93.0,
        theme: str = "light",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.max_samples = max_samples
        self.warning_threshold = warning_threshold
        self.theme = theme.lower()
        self.cpu_history: collections.deque[float] = collections.deque(maxlen=max_samples)
        self.ram_history: collections.deque[float] = collections.deque(maxlen=max_samples)
        self.temp_history: collections.deque[float | None] = collections.deque(maxlen=max_samples)
        self.setMinimumHeight(135)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_theme(self, theme_name: str) -> None:
        """Update active theme and repaint."""
        new_theme = (theme_name or "light").lower()
        if self.theme != new_theme:
            self.theme = new_theme
            if self.isVisible():
                self.update()

    def update_metrics(self, cpu: float, ram: float, temp: float | None = None) -> None:
        """Append fresh metrics sample and trigger repaint if visible."""
        self.cpu_history.append(cpu)
        self.ram_history.append(ram)
        self.temp_history.append(temp)
        if self.isVisible():
            self.update()

    def clear(self) -> None:
        self.cpu_history.clear()
        self.ram_history.clear()
        self.temp_history.clear()
        if self.isVisible():
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

        # Theme-aware colors
        is_dark = self.theme == "dark"
        bg_color = QColor("#171717") if is_dark else QColor("#FFFFFF")
        plot_bg = QColor("#212121") if is_dark else QColor("#FAF7F0")
        border_color = QColor("#333333") if is_dark else QColor("#D9D4C8")
        grid_color = QColor("#2B2B2B") if is_dark else QColor("#EAE6DB")
        text_color = QColor("#D9D4C8") if is_dark else QColor("#171717")
        ram_line_color = QColor("#F5F2E9") if is_dark else QColor("#4A453A")

        # Background fill
        painter.fillRect(0, 0, w, h, bg_color)
        painter.fillRect(pad_left, pad_top, plot_w, plot_h, plot_bg)
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(pad_left, pad_top, plot_w, plot_h)

        # Font setup
        font = QFont("Segoe UI", 9)
        painter.setFont(font)

        # Draw grid lines & Y labels (0%, 25%, 50%, 75%, 100%)
        grid_pen = QPen(grid_color, 1, Qt.DashLine)
        text_pen = QPen(text_color, 1)

        for pct in (0, 25, 50, 75, 100):
            y = pad_top + plot_h - (pct / 100.0) * plot_h
            painter.setPen(grid_pen)
            painter.drawLine(pad_left, int(y), pad_left + plot_w, int(y))
            painter.setPen(text_pen)
            painter.drawText(4, int(y + 4), f"{pct}%")

        # Draw Configurable 93% Warning threshold line
        thresh_y = pad_top + plot_h - (self.warning_threshold / 100.0) * plot_h
        warn_pen = QPen(QColor("#E05252"), 1, Qt.DotLine)
        painter.setPen(warn_pen)
        painter.drawLine(pad_left, int(thresh_y), pad_left + plot_w, int(thresh_y))

        # Legend at top (CPU: Golden yellow, RAM: Theme-aware, Temp: Coral, Threshold: 93%)
        legend_x = pad_left
        painter.setPen(QColor("#E2B83B"))
        cur_cpu = f"{self.cpu_history[-1]:.1f}%" if self.cpu_history else "0.0%"
        painter.drawText(legend_x, 18, f"■ CPU: {cur_cpu}")
        legend_x += 105

        painter.setPen(ram_line_color)
        cur_ram = f"{self.ram_history[-1]:.1f}%" if self.ram_history else "0.0%"
        painter.drawText(legend_x, 18, f"■ RAM: {cur_ram}")
        legend_x += 105

        # Temperature legend
        latest_temp = next((t for t in reversed(self.temp_history) if t is not None), None)
        if latest_temp is not None:
            painter.setPen(QColor("#E05252"))
            painter.drawText(legend_x, 18, f"◆ Temp: {latest_temp:.1f}°C")
        else:
            painter.setPen(QColor("#8C8578"))
            painter.drawText(legend_x, 18, "◆ Temp: Unavailable")
        legend_x += 135

        painter.setPen(QColor("#E05252"))
        painter.drawText(legend_x, 18, f"-- Risk Limit: {self.warning_threshold:.0f}%")

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

            cpu_pen = QPen(QColor("#E2B83B"), 2)
            painter.setPen(cpu_pen)
            for i in range(len(cpu_points) - 1):
                painter.drawLine(cpu_points[i], cpu_points[i + 1])

        # Plot RAM Line (Theme-aware)
        if len(self.ram_history) >= 2:
            ram_points: list[QPointF] = []
            dx = plot_w / float(self.max_samples - 1)
            start_x = pad_left + plot_w - (len(self.ram_history) - 1) * dx

            for i, val in enumerate(self.ram_history):
                px = start_x + i * dx
                clamped_val = min(100.0, max(0.0, val))
                py = pad_top + plot_h - (clamped_val / 100.0) * plot_h
                ram_points.append(QPointF(px, py))

            ram_pen = QPen(ram_line_color, 2)
            painter.setPen(ram_pen)
            for i in range(len(ram_points) - 1):
                painter.drawLine(ram_points[i], ram_points[i + 1])

        # Plot Temperature Trend Line (Coral dashed, normalized 0-100°C) if available
        valid_temps = [t for t in self.temp_history if t is not None]
        if len(valid_temps) >= 2 and len(self.temp_history) >= 2:
            temp_points: list[QPointF] = []
            dx = plot_w / float(self.max_samples - 1)
            start_x = pad_left + plot_w - (len(self.temp_history) - 1) * dx

            for i, val in enumerate(self.temp_history):
                if val is not None:
                    px = start_x + i * dx
                    clamped_val = min(100.0, max(0.0, val))
                    py = pad_top + plot_h - (clamped_val / 100.0) * plot_h
                    temp_points.append(QPointF(px, py))

            temp_pen = QPen(QColor("#E05252"), 1.8, Qt.DashLine)
            painter.setPen(temp_pen)
            for i in range(len(temp_points) - 1):
                painter.drawLine(temp_points[i], temp_points[i + 1])
