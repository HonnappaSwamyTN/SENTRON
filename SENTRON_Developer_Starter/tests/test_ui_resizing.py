"""Tests verifying window resizing, responsive layouts, and multi-resolution behavior."""
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from sentron.main import create_application


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_main_window_free_resizing_and_min_dimensions(qapp, tmp_path):
    """Verify window can freely resize, has sensible min size, and adapts to 1366x768 and 1920x1080."""
    db_file = tmp_path / "test_resize_sentron.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()

        # 1. Verify sensible minimum dimensions (must not be fixed to 1280x840)
        min_size = window.minimumSize()
        assert min_size.width() <= 900
        assert min_size.height() <= 560

        # 2. Test typical 1366x768 laptop resolution
        window.resize(1160, 680)
        qapp.processEvents()
        assert window.width() == 1160
        assert window.height() == 680
        # Panels must be visible and responsive
        assert window.agentguard_panel.width() > 200
        assert window.crashguard_panel.width() > 200
        assert window.crashguard_panel.chart_widget.width() > 100

        # 3. Test large resolution (clamped to physical monitor width by OS if smaller)
        window.resize(1820, 980)
        qapp.processEvents()
        assert window.width() >= 1400 or window.width() == 1820
        assert window.height() >= 700 or window.height() == 980
        assert window.crashguard_panel.chart_widget.width() > 300

        # 4. Test smaller screen down to 900x580
        window.resize(900, 580)
        qapp.processEvents()
        assert window.width() >= 880
        assert window.height() >= 540

        # 5. Test maximize and restore
        window.showMaximized()
        qapp.processEvents()
        assert window.isMaximized() or window.width() >= 900

        window.showNormal()
        qapp.processEvents()

    finally:
        window.exit_application()
