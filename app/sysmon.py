# =============================================================================
# TubeArchive Pro  |  Version 1.0.12  |  File: app/sysmon.py
# Version history of this file:
#   1.0.12 - New: network speed, disk I/O and free space of the save directory (psutil)
# =============================================================================
"""Numbers for the gauges panel. Qt-free; `psutil` can be replaced in tests."""
import os
import time
from pathlib import Path

try:
    import psutil
except ImportError:          # the gauges then show 0
    psutil = None

NET_STEPS = (1, 5, 10, 25, 50, 100, 250, 500, 1000)         # MB/s: the gauge scale follows the value
DISK_STEPS = (10, 50, 100, 250, 500, 1000, 2000, 5000)
SIZE_STEPS = (1, 5, 10, 50, 100, 500, 1000, 5000)           # GB


def auto_max(value: float, steps) -> float:
    return next((s for s in steps if value <= s * 0.9), steps[-1])


def existing_parent(path) -> Path:
    p = Path(os.path.expanduser(str(path)))
    while not p.exists() and p != p.parent:
        p = p.parent
    return p


class SysMonitor:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._last = None                       # (time, net bytes received, disk bytes read + written)

    def _counters(self):
        if psutil is None:
            return 0, 0
        net = psutil.net_io_counters()
        try:
            dio = psutil.disk_io_counters()
            disk = (dio.read_bytes + dio.write_bytes) if dio else 0
        except Exception:                       # noqa: BLE001
            disk = 0
        return (net.bytes_recv if net else 0), disk

    def sample(self, folder) -> dict:
        """{'net': MB/s received by the computer, 'disk': MB/s read + written,
            'free': bytes free, 'total': bytes of the partition holding `folder`}"""
        now = self._clock()
        try:
            recv, disk = self._counters()
        except Exception:                       # noqa: BLE001
            recv, disk = 0, 0
        net_mbs = disk_mbs = 0.0
        if self._last:
            dt = max(now - self._last[0], 1e-3)
            net_mbs = max(0.0, (recv - self._last[1]) / dt / 1_000_000)
            disk_mbs = max(0.0, (disk - self._last[2]) / dt / 1_000_000)
        self._last = (now, recv, disk)
        free = total = 0
        try:
            if psutil is not None:
                u = psutil.disk_usage(str(existing_parent(folder)))
                free, total = u.free, u.total
        except Exception:                       # noqa: BLE001
            pass
        return {"net": net_mbs, "disk": disk_mbs, "free": free, "total": total}


def human_size(nbytes: float) -> tuple:
    """(number text, 'GB' or 'MB' key) for the gauges: MB below 1 GB."""
    gb = nbytes / 1e9
    if gb >= 1:
        return (f"{gb:.0f}" if gb >= 100 else f"{gb:.1f}"), "GB"
    return f"{nbytes / 1e6:.0f}", "MB"
