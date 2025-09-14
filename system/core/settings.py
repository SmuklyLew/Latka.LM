# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Central runtime settings for the Jaźń system.

One source of truth for intervals, queue sizes, and feature flags.
Settings can be overridden via environment variables or runtime_config.json.
"""
import os, json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

RUNTIME_CONFIG_FILE = os.environ.get("JAZN_RUNTIME_CONFIG", "runtime_config.json")

@dataclass
class Intervals:
    heartbeat_sec: float = float(os.environ.get("JAZN_HEARTBEAT_SEC", 2.0))
    watchdog_kick_sec: float = float(os.environ.get("JAZN_WD_KICK_SEC", 5.0))
    bus_poll_ms: int = int(os.environ.get("JAZN_BUS_POLL_MS", 50))

@dataclass
class Queues:
    eventbus_max: int = int(os.environ.get("JAZN_EVENTBUS_MAX", 1024))
    emotions_max: int = int(os.environ.get("JAZN_EMOTIONS_MAX", 256))

@dataclass
class Flags:
    debug: bool = os.environ.get("JAZN_DEBUG", "0") == "1"
    strict_errors: bool = os.environ.get("JAZN_STRICT_ERRORS", "0") == "1"
    service_mode: str = os.environ.get("JAZN_SERVICE_MODE", "offline")  # 'mock'|'offline'|'online'

@dataclass
class Settings:
    intervals: Intervals = field(default_factory=Intervals)
    queues: Queues = field(default_factory=Queues)
    flags: Flags = field(default_factory=Flags)
    raw: Dict[str, Any] = field(default_factory=dict)

def _merge_env_over_json(cfg: dict) -> dict:
    # Environment already reflected in dataclasses; keep json as overrides if present.
    return cfg

def load_settings() -> Settings:
    cfg = {}
    if os.path.exists(RUNTIME_CONFIG_FILE):
        try:
            with open(RUNTIME_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except json.JSONDecodeError:
            # Fallback to empty; upstream logging should record details
            cfg = {}
    s = Settings()
    # Apply json overrides, if any
    if "intervals" in cfg:
        for k, v in cfg["intervals"].items():
            if hasattr(s.intervals, k):
                setattr(s.intervals, k, v)
    if "queues" in cfg:
        for k, v in cfg["queues"].items():
            if hasattr(s.queues, k):
                setattr(s.queues, k, v)
    if "flags" in cfg:
        for k, v in cfg["flags"].items():
            if hasattr(s.flags, k):
                setattr(s.flags, k, v)
    s.raw = cfg
    return s

# Singleton-ish accessor
_CACHED: Optional[Settings] = None
def get_settings() -> Settings:
    global _CACHED
    if _CACHED is None:
        _CACHED = load_settings()
    return _CACHED