# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, json, time
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# Local imports (no 'core.' package prefix)
from system.core.config import Config
from system.core.bus import EventBus
from system.core.services import ServiceRegistry, LatkaCoreService
from system.core.heartbeat import StoppableThread
from system.core.identity import load_identity
from system.core.emotions import EmotionEngine, reflect as emo_reflect
from system.core.memory import EpisodicMemory, MemoryEntry, default_episodic_store

def _now():
    # local timezone ISO string + human readable
    dt = datetime.now(timezone.utc).astimezone()  # local tz
    return dt.isoformat(), dt.strftime("%Y-%m-%d %H:%M:%S %Z")

def _identity_summary(identity_obj):
    """
    Unikamy bezpośrednich dot‑lookup, żeby zadowolić statyczne analizatory.
    """
    describe = getattr(identity_obj, "describe", None)
    if callable(describe):
        return describe()
    to_dict = getattr(identity_obj, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    # ostateczny fallback — bezpieczny string
    return str(identity_obj)

def scheduler_loop(services: ServiceRegistry):
    while True:
        services.tick_all()
        time.sleep(0.2)

def start_app():
    cfg = Config.load()
    bus = EventBus()
    services = ServiceRegistry()

    # lightweight app object (namespace)
    app = type("App", (), {})()
    app.cfg = cfg
    app.event_bus = bus
    app.metrics = {}
    app.identity = load_identity()
    app.emotions = EmotionEngine()
    app.memory = EpisodicMemory(default_episodic_store())

    core = LatkaCoreService(app, period_ms=1000)
    services.register("latka_core", core)
    services.start_all(bus)

    # startup memory entry
    iso, human = _now()
    app.memory.remember(MemoryEntry(
        timestamp = iso,
        typ = "startup",
        kategoria = "system",
        data = dict(
            opis = "Start Nowa Jaźń 2.0.2",
            tozsamosc = _identity_summary(app.identity),
            emotions = app.emotions.current_state(),
            ts_human = human
        )
    ))

    # background scheduler
    t = StoppableThread(target=lambda: scheduler_loop(services), daemon=True)
    t.start()
    return app, t, services

def cmd_reflect(app):
    txt = emo_reflect(app.emotions)
    print(txt)

def cmd_save(app, text):
    iso, human = _now()
    app.memory.remember(MemoryEntry(
        timestamp = iso,
        typ = "notatka",
        kategoria = "cli",
        data = dict(
            tresc = text,
            ts_human = human
        )
    ))
    print("OK zapisane.")

def cmd_state(app):
    out = {
        "identity": _identity_summary(app.identity),
        "emotions": app.emotions.current_state(),
        "metrics": app.metrics
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

def main(argv=None):
    argv = argv or sys.argv[1:]
    app, thread, services = start_app()

    try:
        if argv:
            # CLI one-shot commands
            if argv[0] == "reflect":
                cmd_reflect(app)
            elif argv[0] == "save":
                text = " ".join(argv[1:]).strip().strip('"').strip("'") if len(argv) > 1 else ""
                cmd_save(app, text or "(pusty wpis)")
            elif argv[0] == "state":
                cmd_state(app)
            else:
                print("Dostępne komendy: reflect | save \"tekst\" | state")
        else:
            # default: short demo run
            print("[Nowa Jaźń 2.0] Start OK — heartbeat działa.")  # demo ~3s
            time.sleep(3.0)
            cmd_state(app)
    finally:
        thread.stop()
        services.stop_all()

if __name__ == "__main__":
    main()
