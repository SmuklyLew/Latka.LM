# -*- coding: utf-8 -*-
from __future__ import annotations
import time, threading

class HeartbeatMixin:
    def __init__(self, period_ms: int = 1000):
        self._hb_period_ms = max(50, int(period_ms))
        self._hb_last_ts = 0.0
    def _hb_due(self, now: float | None = None) -> bool:
        now = now or time.time()
        return (now - self._hb_last_ts) * 1000.0 >= self._hb_period_ms
    def heartbeat(self, now: float | None = None):
        self._hb_last_ts = now or time.time()

class StoppableThread(threading.Thread):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._stop_evt = threading.Event()
    def stop(self): self._stop_evt.set()
    def stopped(self): return self._stop_evt.is_set()
