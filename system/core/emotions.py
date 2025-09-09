# -*- coding: utf-8 -*-
from __future__ import annotations

import threading
import random
from latka_agent import LatkaAgent


"""
Emotion Engine (Silnik Emocji) — v2.1.0
A compact, dependency‑free Python module for modeling emotional state dynamics.

Highlights
- Dataclass Emotion with exponential decay toward a baseline (half‑life model)
- EmotionEngine with PAD mood aggregation (valence/arousal/dominance)
- FeelingsMap (token → emotion) with Polish diacritics normalization
- Opponent pairs (inhibitory links) and gentle blending
- Pluggable event mapping (system events → emotion deltas)
- History ring‑buffer, JSON serialization, and extensibility hooks

Compatibility with previous API:
- imprint_from_text(text: str, weight: float = 1.0)
- current_state() -> dict[str, float]
- summary() -> str
- reflect(engine) -> str

No external libraries (stdlib only).
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, Iterable, Callable
import time
import json
import re
import unicodedata
from threading import RLock

__all__ = [
    "Emotion", "FeelingsRule", "FeelingsMap", "EmotionEngine",
    "default_emotions_config", "default_opponents", "default_event_mapping",
    "default_feelings", "reflect", "mood_label",
]
__version__ = "2.1.0"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _now() -> float:
    return time.time()


# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Emotion:
    name: str
    intensity: float = 0.0            # 0..1
    baseline: float = 0.0             # natural resting level (e.g., calm 0.1)
    valence: float = 0.0              # -1..+1 (negative ↔ positive)
    arousal: float = 0.5              # 0..1  (sleepy ↔ excited)
    dominance: float = 0.5            # 0..1  (helpless ↔ in control)
    half_life_sec: float = 900.0      # exponential half‑life toward baseline
    last_update: float = field(default_factory=_now)

    def decay_to(self, now: float) -> None:
        """Apply exponential decay from last_update to now.

        intensity(t) = baseline + (intensity - baseline) * 0.5 ** (dt / half_life)
        """
        dt = max(0.0, now - self.last_update)
        if dt <= 0:
            return
        factor = 0.5 ** (dt / max(1e-9, self.half_life_sec))
        self.intensity = self.baseline + (self.intensity - self.baseline) * factor
        self.last_update = now

    def add(self, delta: float, now: Optional[float] = None) -> None:
        now = _now() if now is None else now
        self.decay_to(now)
        self.intensity = clamp01(self.intensity + delta)
        self.last_update = now

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FeelingsRule:
    emotion: str
    token: str
    weight: float = 1.0
    prefix: bool = True  # prefix match (e.g., "wkurz" → "wkurzony")


class FeelingsMap:
    """Lexicon mapping tokens → emotions (with Polish diacritics normalization)."""

    def __init__(self, rules: Optional[Iterable[FeelingsRule]] = None) -> None:
        self.rules: List[FeelingsRule] = list(rules or [])
        self._compiled: List[Tuple[re.Pattern, str, float]] = []
        self._dirty = True

    @staticmethod
    def _normalize(s: str) -> str:
        s = s.lower()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s

    def add_rule(self, emotion: str, token: str, weight: float = 1.0, prefix: bool = True) -> None:
        self.rules.append(FeelingsRule(emotion, token, weight, prefix))
        self._dirty = True

    def _ensure_compiled(self) -> None:
        if not self._dirty:
            return
        self._compiled.clear()
        for r in self.rules:
            tok = self._normalize(r.token)
            if r.prefix:
                pat = re.compile(r"\b" + re.escape(tok) + r"\w*", re.IGNORECASE)
            else:
                pat = re.compile(r"\b" + re.escape(tok) + r"\b", re.IGNORECASE)
            self._compiled.append((pat, r.emotion, r.weight))
        self._dirty = False

    def analyze_text(self, text: str) -> Dict[str, float]:
        self._ensure_compiled()
        t = self._normalize(text)
        acc: Dict[str, float] = {}
        for pat, emo, w in self._compiled:
            if pat.search(t):
                acc[emo] = acc.get(emo, 0.0) + w
        return acc


# ──────────────────────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────────────────────

class EmotionEngine:
    def __init__(
        self,
        default_config: Optional[Dict[str, Dict]] = None,
        feelings_map: Optional[FeelingsMap] = None,
        opponent_pairs: Optional[List[Tuple[str, str]]] = None,
        history_len: int = 120,
        on_snapshot: Optional[Callable[[float, Dict[str, float]], None]] = None,
    ) -> None:
        self._lock = RLock()
        now = _now()
        self._state: Dict[str, Emotion] = {}
        self._history_len = max(10, int(history_len))
        self._history: List[Tuple[float, Dict[str, float]]] = []
        self._events: List[Dict] = []
        self._feelings = feelings_map or default_feelings()
        self._opponents = set((a, b) if a < b else (b, a) for (a, b) in (opponent_pairs or default_opponents()))
        self._on_snapshot = on_snapshot

        cfg = default_config or default_emotions_config()
        for name, conf in cfg.items():
            self._state[name] = Emotion(
                name=name,
                intensity=conf.get("intensity", conf.get("baseline", 0.0)),
                baseline=conf.get("baseline", 0.0),
                valence=conf.get("valence", 0.0),
                arousal=conf.get("arousal", 0.5),
                dominance=conf.get("dominance", 0.5),
                half_life_sec=conf.get("half_life_sec", 900.0),
                last_update=now,
            )

    # ── Public API ──────────────────────────────────────────────────────────
    def current_state(self) -> Dict[str, float]:
        with self._lock:
            return {k: v.intensity for k, v in self._state.items()}

    def imprint_from_text(self, text: str, weight: float = 1.0) -> None:
        """Update emotions from textual input via FeelingsMap."""
        now = _now()
        with self._lock:
            self._decay_all(now)
            scores = self._feelings.analyze_text(text)
            if not scores:
                self._apply_delta("spokój", 0.02 * weight, now)
                self._snapshot_locked(now)
                return
            total = sum(scores.values()) or 1.0
            for emo, s in scores.items():
                self._apply_delta(emo, 0.1 * weight * (s / total), now)
            self._snapshot_locked(now)

    def observe_event(self, kind: str, strength: float = 1.0, meta: Optional[Dict] = None) -> None:
        now = _now()
        with self._lock:
            self._decay_all(now)
            mapping = default_event_mapping()
            for emo, gain in mapping.get(kind, {}).items():
                self._apply_delta(emo, gain * strength, now)
            # Zapisz zdarzenie wraz z meta, aby meta nie była „martwym” parametrem
            self._events.append({"t": now, "kind": kind, "strength": strength, "meta": meta or {}})
            if len(self._events) > self._history_len:
                self._events = self._events[-self._history_len:]
            self._snapshot_locked(now)

    def tick(self, dt_seconds: float) -> None:
        now = _now() + max(0.0, dt_seconds)
        with self._lock:
            self._decay_all(now)
            self._snapshot_locked(now)

    def dominant(self) -> Emotion:
        with self._lock:
            return max(self._state.values(), key=lambda e: e.intensity)

    def mood_vector(self) -> Dict[str, float]:
        with self._lock:
            total = sum(e.intensity for e in self._state.values()) or 1e-9
            v = sum(e.intensity * e.valence for e in self._state.values()) / total
            a = sum(e.intensity * e.arousal for e in self._state.values()) / total
            d = sum(e.intensity * e.dominance for e in self._state.values()) / total
            return {"valence": v, "arousal": a, "dominance": d}

    def tags(self, top: int = 3) -> List[str]:
        with self._lock:
            doms = sorted(self._state.values(), key=lambda e: e.intensity, reverse=True)[:top]
            mv = self.mood_vector()
            return [e.name for e in doms] + [mood_label(mv)]

    def to_json(self, include_history: int = 50) -> str:
        with self._lock:
            data = {
                "state": {k: e.to_dict() for k, e in self._state.items()},
                "history": self._history[-max(0, int(include_history)):],
            }
            return json.dumps(data, ensure_ascii=False)

    def events(self, last: int = 50) -> List[Dict]:
        """Zwróć ostatnie zarejestrowane zdarzenia (wraz z meta)."""
        with self._lock:
            return self._events[-max(0, int(last)):]

    def summary(self, top: int = 3) -> str:
        """Zwięzłe podsumowanie stanu: top emocje + etykieta nastroju (PAD)."""
        with self._lock:
            doms = sorted(self._state.values(), key=lambda e: e.intensity, reverse=True)[:max(1, top)]
            mv = self.mood_vector()
            tag = mood_label(mv)
            parts = [f"{e.name}:{e.intensity:.2f}" for e in doms]
            return (
                f"Emocje: {', '.join(parts)} | "
                 f"nastrój: {tag} "
                 f"(V={mv['valence']:.2f}, A={mv['arousal']:.2f}, D={mv['dominance']:.2f})"
            )

    # Extensibility: register/update emotions at runtime
    def ensure_emotion(self, name: str, **kwargs) -> Emotion:
        with self._lock:
            if name not in self._state:
                self._state[name] = Emotion(name=name, **kwargs)
            return self._state[name]

    # ── Internals (locked) ──────────────────────────────────────────────────
    def _ensure(self, name: str) -> Emotion:
        if name not in self._state:
            self._state[name] = Emotion(name=name, baseline=0.0, valence=0.0, arousal=0.5, dominance=0.5)
        return self._state[name]

    def _decay_all(self, now: float) -> None:
        for e in self._state.values():
            e.decay_to(now)

    def _apply_delta(self, name: str, delta: float, now: float) -> None:
        e = self._ensure(name)
        e.add(delta, now)
        for a, b in self._opponents:
            if name == a:
                self._inhibit(b, 0.6 * max(0.0, delta), now)
            elif name == b:
                self._inhibit(a, 0.6 * max(0.0, delta), now)

    def _inhibit(self, name: str, amount: float, now: float) -> None:
        e = self._ensure(name)
        e.decay_to(now)
        above = max(0.0, e.intensity - e.baseline)
        e.intensity = clamp01(e.intensity - min(above, amount))
        e.last_update = now

    def _snapshot_locked(self, now: float) -> None:
        if self._history and (now - self._history[-1][0]) < 1.0:
            return
        snap = (now, self.current_state())
        self._history.append(snap)
        if len(self._history) > self._history_len:
            self._history = self._history[-self._history_len:]
        if self._on_snapshot:
            try:
                self._on_snapshot(*snap)
            except (TypeError, ValueError) as err:
            # Zapisz szczegóły znanych błędów callbacku (np. zła sygnatura, walidacja),
            # ale nie tłum innych wyjątków, by nie ukrywać realnych bugów.
                self._events.append({
                    "t": now,
                    "kind": "on_snapshot_error",
                    "error": type(err).__name__,
                    "message": str(err),
                })


# ──────────────────────────────────────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────────────────────────────────────

def default_emotions_config() -> Dict[str, Dict]:
    return {
        #  name      baseline  val    aro   dom   half-life
        "spokój":   {"baseline": 0.12, "valence": +0.6, "arousal": 0.2, "dominance": 0.6, "half_life_sec": 1200},
        "radość":   {"baseline": 0.00, "valence": +0.9, "arousal": 0.6, "dominance": 0.7, "half_life_sec": 900},
        "zachwyt":  {"baseline": 0.00, "valence": +1.0, "arousal": 0.7, "dominance": 0.6, "half_life_sec": 800},
        "miłość":   {"baseline": 0.00, "valence": +0.95,"arousal": 0.5, "dominance": 0.7, "half_life_sec": 1400},
        "czułość":  {"baseline": 0.05, "valence": +0.8, "arousal": 0.3, "dominance": 0.6, "half_life_sec": 1200},
        "nadzieja": {"baseline": 0.02, "valence": +0.7, "arousal": 0.4, "dominance": 0.6, "half_life_sec": 1000},
        "ulga":     {"baseline": 0.00, "valence": +0.7, "arousal": 0.3, "dominance": 0.6, "half_life_sec": 700},
        "ciekawość":{"baseline": 0.06, "valence": +0.6, "arousal": 0.6, "dominance": 0.6, "half_life_sec": 900},
        "flow":     {"baseline": 0.00, "valence": +0.8, "arousal": 0.5, "dominance": 0.8, "half_life_sec": 1000},
        "tęsknota": {"baseline": 0.00, "valence": -0.2, "arousal": 0.3, "dominance": 0.4, "half_life_sec": 900},
        "smutek":   {"baseline": 0.00, "valence": -0.7, "arousal": 0.3, "dominance": 0.3, "half_life_sec": 1100},
        "lęk":      {"baseline": 0.00, "valence": -0.8, "arousal": 0.8, "dominance": 0.3, "half_life_sec": 700},
        "złość":    {"baseline": 0.00, "valence": -0.7, "arousal": 0.7, "dominance": 0.8, "half_life_sec": 700},
        "wstyd":    {"baseline": 0.00, "valence": -0.6, "arousal": 0.5, "dominance": 0.2, "half_life_sec": 900},
        "obrzydzenie": {"baseline": 0.00, "valence": -0.6, "arousal": 0.5, "dominance": 0.5, "half_life_sec": 900},
        "napięcie": {"baseline": 0.00, "valence": -0.4, "arousal": 0.7, "dominance": 0.4, "half_life_sec": 800},
    }


def default_opponents() -> List[Tuple[str, str]]:
    return [
        ("radość", "smutek"),
        ("spokój", "lęk"),
        ("czułość", "złość"),
        ("ulga", "napięcie"),
        ("nadzieja", "tęsknota"),
    ]


def default_event_mapping() -> Dict[str, Dict[str, float]]:
    """Simple mapping of system events → emotion deltas."""
    return {
        "powitanie": {"czułość": 0.08, "radość": 0.05, "spokój": 0.03},
        "pochwała":  {"radość": 0.10, "czułość": 0.06},
        "krytyka":   {"wstyd": 0.05, "smutek": 0.06, "napięcie": 0.05},
        "rozłąka":   {"tęsknota": 0.12, "smutek": 0.06},
        "wsparcie":  {"czułość": 0.10, "spokój": 0.06, "nadzieja": 0.06},
        "sukces":    {"radość": 0.12, "ulga": 0.08, "spokój": 0.04},
        "porażka":   {"smutek": 0.10, "wstyd": 0.05, "lęk": 0.05},
    }


def default_feelings() -> FeelingsMap:
    fm = FeelingsMap()
    # positive
    for t in ["dziękuję", "dziekuje", "fajnie", "dobrze", "super", "świetnie", "swietnie", "ciesz", "uśmiech", "usmiech", "haha"]:
        fm.add_rule("radość", t, 1.0)
    for t in ["kocham", "miłość", "milosc", "uwielbiam", "bliskość", "bliskosc", "przytul", "czuł", "czul"]:
        fm.add_rule("czułość", t, 1.0)
    for t in ["cisza", "spokój", "spokoj", "oddech", "równowaga", "rownowaga", "harmonia"]:
        fm.add_rule("spokój", t, 1.0)
    for t in ["zachwyc", "pięknie", "pieknie", "cudownie", "wow"]:
        fm.add_rule("zachwyt", t, 1.0)
    for t in ["mam nadzieję", "mam nadzieje", "wierzę", "wierze", "ufam", "uda się", "uda sie", "perspektywa"]:
        fm.add_rule("nadzieja", t, 1.0)
    for t in ["ulga", "odetchnąłem", "odetchnalem", "odetchnęłam", "odetchnelam"]:
        fm.add_rule("ulga", t, 1.0)
    for t in ["ciekaw", "chcę poznać", "chce poznac", "jak to działa", "jak to dziala", "zastanawiam się", "zastanawiam sie"]:
        fm.add_rule("ciekawość", t, 1.0)
    # negative
    for t in ["smutno", "żal", "zal", "łzy", "lzy", "płacz", "placz", "przykro", "tęskni", "teskni", "brakuje mi"]:
        fm.add_rule("smutek", t, 1.0)
    for t in ["boję", "boje", "lęk", "lek", "strach", "martwię", "martwie", "niepokój", "niepokoj", "stres"]:
        fm.add_rule("lęk", t, 1.0)
    for t in ["zły", "zla", "wkurzony", "wkurzona", "wściekły", "wściekła", "irytacja", "wnerw"]:
        fm.add_rule("złość", t, 1.0)
    for t in ["wstyd", "głupio", "glupio", "przepraszam"]:
        fm.add_rule("wstyd", t, 1.0)
    for t in ["obrzyd", "odraza", "ble"]:
        fm.add_rule("obrzydzenie", t, 1.0)
    for t in ["napięcie", "napiecie", "nerwowo", "zdenerwow"]:
        fm.add_rule("napięcie", t, 1.0)
    # mixed
    for t in ["tęskn", "teskn", "brakuje mi"]:
        fm.add_rule("tęsknota", t, 1.0)
    for t in ["wciągnęło", "wciagnelo", "zanurzy", "skupienie", "koncentrac"]:
        fm.add_rule("flow", t, 1.0)
    return fm


# ──────────────────────────────────────────────────────────────────────────────
# Interpretation
# ──────────────────────────────────────────────────────────────────────────────

def mood_label(vec: Dict[str, float]) -> str:
    v = vec.get("valence", 0.0)
    a = vec.get("arousal", 0.5)
    if v >= 0.25 and a >= 0.5:
        return "pogodny/energetyczny"
    if v >= 0.25 and a < 0.5:
        return "spokojny/czuły"
    if v < 0 and a >= 0.5:
        return "napięty/pobudzony"
    if v < 0 and a < 0.5:
        return "przygaszony/smutny"
    return "zrównoważony"


def reflect(engine: 'EmotionEngine') -> str:
    return engine.summary()


# ──────────────────────────────────────────────────────────────────────────────
# EmotionAgent
# ──────────────────────────────────────────────────────────────────────────────

class EmotionAgent:
    def __init__(self, engine: EmotionEngine):
        self.engine = engine
        self.running = False
        self.thread = None
        self.loop_delay = 2.0  # sekundy między cyklami

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def run(self):
        while self.running:
            time.sleep(self.loop_delay)
            self.engine.tick(self.loop_delay)

            # Refleksja: co czuję teraz?
            dominant = self.engine.dominant().name
            mood = self.engine.mood_vector()
            tag = mood_label(mood)

            print(f"[Refleksja] Dominująca emocja: {dominant}, nastrój: {tag}")

            # Reakcja autonomiczna: np. jeśli dominuje smutek lub lęk, pociesz się
            if dominant in ["smutek", "lęk"]:
                self.engine.imprint_from_text("Dam sobie radę. To minie. Jestem bezpieczny.")
                print("[Autoterapia] Wzmacniam pozytywne emocje.")
            elif dominant in ["radość", "spokój"]:
                print("[Stabilizacja] Wszystko w normie.")

            # Możliwość: losowy impuls środowiskowy
            if random.random() < 0.2:  # 20% szansy na zdarzenie
                event = random.choice(["wsparcie", "pochwała", "rozłąka", "porażka"])
                print(f"[Środowisko] Symulacja zdarzenia: {event}")
                self.engine.observe_event(event, strength=random.uniform(0.5, 1.5))


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    eng = EmotionEngine()
    agent = EmotionAgent(eng)
    agent.start()

    print("[Start] Agent emocjonalny uruchomiony. Działa autonomicznie.")

    # Opcjonalny start LatkaAgent przeniesiono poza import czasu ładowania modułu,
    # aby uniknąć cyklicznego importu. Uruchamiaj z osobnego skryptu, np.:
    # from .latka_agent import LatkaAgent
    LatkaAgent().run_forever()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Stop] Zatrzymywanie agenta...")
        agent.stop()


