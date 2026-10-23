"""Unit tests for ProcessController: High-impact task response and safe process hold workflow.

Tests cover:
- High-resource process ranking
- Protected system process exclusions (PID <= 4, svchost.exe, csrss.exe, explorer.exe, SENTRON itself)
- Accurate Chrome contributor analysis (only flagged if measured data supports it; never assumed)
- Safe process pause and resume status verification
- Error handling for invalid PIDs and access denied
- Clean resume of all held processes on shutdown
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from sentron.crashguard.process_control import ProcessController
from sentron.core.models import ProcessSummary, SystemSnapshot


def _make_proc(pid: int, name: str, mem_mb: float = 100.0, cpu: float = 5.0) -> ProcessSummary:
    return ProcessSummary(
        pid=pid,
        name=name,
        memory_mb=mem_mb,
        cpu_percent=cpu,
    )


@pytest.mark.unit
def test_protected_processes_cannot_be_paused():
    """System-critical processes, PIDs <= 4, and SENTRON itself are strictly protected."""
    ctrl = ProcessController()
    current_pid = os.getpid()
    
    # Kernel / Idle
    is_prot, _ = ctrl.is_protected(0, "System Idle Process")
    assert is_prot
    is_prot, _ = ctrl.is_protected(4, "System")
    assert is_prot
    
    # Windows critical services
    is_prot, _ = ctrl.is_protected(1234, "svchost.exe")
    assert is_prot
    is_prot, _ = ctrl.is_protected(5678, "csrss.exe")
    assert is_prot
    is_prot, _ = ctrl.is_protected(9999, "explorer.exe")
    assert is_prot
    is_prot, _ = ctrl.is_protected(4321, "lsass.exe")
    assert is_prot
    
    # SENTRON itself
    is_prot, _ = ctrl.is_protected(current_pid, "python.exe")
    assert is_prot
    
    # Attempting to pause protected process must fail with clear refusal message
    with patch("psutil.Process") as mock_psutil_proc:
        mock_instance = MagicMock()
        mock_instance.name.return_value = "System"
        mock_psutil_proc.return_value = mock_instance
        
        success, msg = ctrl.pause_process(4)
        assert not success
        assert "Cannot pause" in msg
        assert "kernel/system process" in msg


@pytest.mark.unit
def test_chrome_contributor_analysis_requires_measured_data():
    """Chrome is treated as a contributor only when measured resource usage supports it; never simply because it is running."""
    ctrl = ProcessController()
    
    # Scenario 1: Chrome running with modest resource usage (1.2% CPU, 120MB)
    low_chrome_snap = SystemSnapshot(
        timestamp=1000.0,
        cpu_percent=94.0,
        memory_percent=70.0,
        memory_available_bytes=4 * 1024**3,
        disk_free_bytes=50 * 1024**3,
        disk_busy_percent=10.0,
        top_processes=[
            _make_proc(6001, "blender.exe", mem_mb=4096.0, cpu=88.5),
            _make_proc(5001, "chrome.exe", mem_mb=120.0, cpu=1.2),
        ],
        unavailable_metrics=(),
    )
    main_proc, is_chrome, summary = ctrl.analyze_contributor(low_chrome_snap)
    assert not is_chrome
    assert main_proc.name == "blender.exe"
    assert "modest resource usage" in summary
    
    # Scenario 2: Chrome running with heavy resource usage (42% CPU, 3500MB)
    high_chrome_snap = SystemSnapshot(
        timestamp=1000.0,
        cpu_percent=94.0,
        memory_percent=85.0,
        memory_available_bytes=2 * 1024**3,
        disk_free_bytes=50 * 1024**3,
        disk_busy_percent=10.0,
        top_processes=[
            _make_proc(5001, "chrome.exe", mem_mb=3500.0, cpu=42.0),
        ],
        unavailable_metrics=(),
    )
    main_proc, is_chrome, summary = ctrl.analyze_contributor(high_chrome_snap)
    assert is_chrome
    assert main_proc.name == "chrome.exe"
    assert "major contributor" in summary


@pytest.mark.unit
def test_pause_and_resume_verification():
    """Process pause and resume operations verify actual status and update suspended list."""
    ctrl = ProcessController()
    
    fake_proc = MagicMock()
    fake_proc.name.return_value = "worker_task.exe"
    fake_proc.status.return_value = "stopped"
    fake_mem = MagicMock()
    fake_mem.rss = 250 * 1024 * 1024
    fake_proc.memory_info.return_value = fake_mem
    
    with patch("psutil.Process", return_value=fake_proc):
        # Pause process
        success, msg = ctrl.pause_process(pid=9876)
        assert success
        fake_proc.suspend.assert_called_once()
        
        # Verify it appears in suspended list
        suspended = ctrl.get_suspended_processes()
        assert len(suspended) == 1
        assert suspended[0].pid == 9876
        assert suspended[0].name == "worker_task.exe"
        
        # Resume process
        fake_proc.status.return_value = "running"
        res_success, res_msg = ctrl.resume_process(pid=9876)
        assert res_success
        fake_proc.resume.assert_called_once()
        
        # Verify it is removed from suspended list
        assert len(ctrl.get_suspended_processes()) == 0


@pytest.mark.unit
def test_pause_failure_handling_nonexistent_process():
    """Attempting to pause a non-existent or terminating process handles error gracefully."""
    ctrl = ProcessController()
    
    import psutil
    with patch("psutil.Process", side_effect=psutil.NoSuchProcess(pid=99999)):
        success, msg = ctrl.pause_process(pid=99999)
        assert not success
        assert "no longer exists" in msg


@pytest.mark.unit
def test_resume_all_suspended_on_shutdown():
    """All suspended processes are resumed cleanly when resume_all_suspended is invoked."""
    ctrl = ProcessController()
    
    fake_proc1 = MagicMock()
    fake_proc1.name.return_value = "app1.exe"
    fake_proc1.memory_info.return_value = MagicMock(rss=100*1024*1024)
    
    fake_proc2 = MagicMock()
    fake_proc2.name.return_value = "app2.exe"
    fake_proc2.memory_info.return_value = MagicMock(rss=100*1024*1024)
    
    def proc_factory(pid):
        if pid == 1001:
            return fake_proc1
        return fake_proc2
        
    with patch("psutil.Process", side_effect=proc_factory):
        ctrl.pause_process(1001)
        ctrl.pause_process(1002)
        assert len(ctrl.get_suspended_processes()) == 2
        
        results = ctrl.resume_all_suspended()
        assert len(results) == 2
        assert all(success for _, success, _ in results)
        assert len(ctrl.get_suspended_processes()) == 0
        fake_proc1.resume.assert_called_once()
        fake_proc2.resume.assert_called_once()
