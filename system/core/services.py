# -*- coding: utf-8 -*-
from __future__ import annotations
import time, logging
from .heartbeat import HeartbeatMixin

log = logging.getLogger("jazn.services")

class IService(HeartbeatMixin):
    def __init__(self, app, period_ms: int = 1000):
        super().__init__(period_ms=period_ms)
        self.app = app
        self._running = False
    def start(self, bus): self._running = True
    def stop(self): self._running = False
    def tick(self, now: float | None = None): pass

class ServiceRegistry:
    """Rejestr usług z obsługą cyklu życia i metryk."""
    def __init__(self, logger: logging.Logger | None = None):
        self._services: dict[str, IService] = {}
        self._log = logger or logging.getLogger("jazn.services")
        self._metrics: dict[str, int] = {}
    def register(self, name: str, service: IService):
        if name in self._services:
            raise ValueError(f"Serwis {name} już istnieje")
        self._services[name] = service
    def start_all(self, bus=None):
        for name, svc in self._services.items():
            try:
                svc.start(bus)
            except Exception as e:
                self._log.warning("[ServiceRegistry] start %s failed: %s", name, e)
    def stop_all(self):
        for name, svc in self._services.items():
            try:
                svc.stop()
            except Exception as e:
                self._log.warning("[ServiceRegistry] stop %s failed: %s", name, e)
    def tick_all(self):
        now = time.time()
        for name, svc in self._services.items():
            try:
                if isinstance(svc, HeartbeatMixin) and svc._hb_due(now):
                    svc.tick(now); svc._hb_last_ts = now
            except Exception as e:
                self._log.warning("[ServiceRegistry] tick %s failed: %s", name, e)

class LatkaCoreService(IService):
    def __init__(self, app, period_ms: int = 1000):
        super().__init__(app, period_ms=period_ms)
        self._beats = 0
    def tick(self, now: float | None = None):
        self._beats += 1
        self.app.metrics['heartbeat'] = self._beats
