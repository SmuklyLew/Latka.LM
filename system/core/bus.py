# -*- coding: utf-8 -*-
from __future__ import annotations
import time, uuid, threading, logging
from collections import deque, defaultdict
from typing import Callable, Any

log = logging.getLogger("jazn.bus")

class Event:
    __slots__ = ("topic", "payload", "id", "ts")
    def __init__(self, topic: str, payload: Any = None, id: str | None = None, ts: float | None = None):
        self.topic = topic
        self.payload = payload
        self.id = id or uuid.uuid4().hex
        self.ts = ts if ts is not None else time.time()

class EventBus:
    def __init__(self, max_queue: int = 2048, dedupe: bool = True, logger: logging.Logger | None = None):
        self._q = deque()
        self._max_queue = max_queue
        self._subs: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._seen: set[str] = set()
        self._lock = threading.RLock()
        self._dedupe = dedupe
        self._log = logger or log

    def subscribe(self, topic: str, handler: Callable[[Event], None]):
        with self._lock:
            self._subs[topic].append(handler)
            self._log.debug("[EventBus] sub: %s → %s", topic, getattr(handler, "__name__", str(handler)))
        return lambda: self.unsubscribe(topic, handler)

    def unsubscribe(self, topic: str, handler: Callable[[Event], None]):
        with self._lock:
            if topic in self._subs and handler in self._subs[topic]:
                self._subs[topic].remove(handler)

    def publish(self, topic: str, payload: Any = None, id: str | None = None) -> bool:
        ev = Event(topic, payload, id=id)
        with self._lock:
            if self._dedupe and ev.id in self._seen:
                return False
            if self._dedupe:
                self._seen.add(ev.id)
            if len(self._q) >= self._max_queue:
                self._q.popleft()
            self._q.append(ev)
        return True

    def pump(self, max_events: int = 256) -> int:
        dispatched = 0
        while dispatched < max_events:
            with self._lock:
                if not self._q:
                    break
                ev = self._q.popleft()
                handlers = list(self._subs.get(ev.topic, ()))
            for h in handlers:
                try:
                    h(ev)
                except Exception as e:
                    self._log.warning("[EventBus] handler error @%s: %s", ev.topic, e)
            dispatched += 1
        return dispatched
