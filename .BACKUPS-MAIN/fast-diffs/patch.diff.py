*** a/jazn.ŁLM.py
--- b/jazn.ŁLM.py
@@
+# ─────────────────────────────────────────────────────────────────────────────
+# LAYER: ŁLM bridge do rdzenia Jaźni (jazn.py)
+# Cel: wciągnąć klasy/funkcje z jazn.py i spiąć je z warstwą Character/Intent.
+# Działa idempotentnie i miękko (fallbacki, gdy czegoś brakuje).
+# ─────────────────────────────────────────────────────────────────────────────
+from __future__ import annotations
+import importlib, types as _types, threading, time, logging, os, json
+from pathlib import Path
+
+# 1) Import rdzenia z jazn.py i re-eksport kluczowych symboli
+try:
+    _jazn = importlib.import_module("jazn")
+except Exception as _e:
+    _jazn = None
+
+def _reexport(name: str, default: object = None):
+    if name not in globals():
+        val = getattr(_jazn, name, default) if _jazn else default
+        if val is not None:
+            globals()[name] = val
+
+# Rdzeń eventów/usług Jaźni (zachowujemy istniejącą implementację jazn.py)
+# Event/EventBus/ServiceRegistry/HeartbeatMixin/IService
+# (definicje w rdzeniu — patrz jazn.py) :contentReference[oaicite:3]{index=3} :contentReference[oaicite:4]{index=4}
+for _sym in ("Event", "EventBus", "ServiceRegistry", "HeartbeatMixin", "IService",
+             "LatkaJazn"):
+    _reexport(_sym)
+
+# Uzupełnienia pomocnicze (korzystamy z wersji rdzeniowych, jeśli są)
+_reexport("now_warsaw")
+_reexport("now_ts")
+
+# 2) Stałe zdarzeń (jeśli nie zdefiniowane w rdzeniu, ustawiamy domyślnie)
+EVT_EMOTION_UPDATED      = globals().get("EVT_EMOTION_UPDATED",      "emotion.updated")
+EVT_DREAM_ADDED          = globals().get("EVT_DREAM_ADDED",          "dream.added")
+EVT_CHARACTER_UPDATED    = globals().get("EVT_CHARACTER_UPDATED",    "character.updated")
+EVT_CHARACTER_APPLIED    = globals().get("EVT_CHARACTER_APPLIED",    "character.applied")
+EVT_MEMORY_ADDED         = globals().get("EVT_MEMORY_ADDED",         "memory.added")
+EVT_INTENT_EXECUTED      = globals().get("EVT_INTENT_EXECUTED",      "intent.executed")
+
+# 3) Mini-metryki (gdy rdzeń nie dostarcza), proste .inc(key, n)
+class _MiniMetrics:
+    def __init__(self): self.c = {}
+    def inc(self, k: str, n: int = 1): self.c[k] = self.c.get(k, 0) + int(n or 1)
+
+# 4) Heartbeat usług — lekki harmonogram
+class _ServicesHeartbeat(threading.Thread):
+    def __init__(self, services: "ServiceRegistry", period_sec: float = 1.0):
+        super().__init__(daemon=True); self.sv = services; self.per = max(0.25, float(period_sec))
+        self._stop = threading.Event()
+    def run(self):
+        while not self._stop.is_set():
+            try:
+                self.sv.heartbeat_all()  # tętno usług (zgodnie z kontraktem) :contentReference[oaicite:5]{index=5}
+            except Exception:
+                pass
+            time.sleep(self.per)
+    def stop(self): self._stop.set()
+
+# 5) Warstwa integracyjna — spina rdzeń Jaźni z Character/Intent
+_LLM_APPLIED_MARK = False
+def apply_llm_layer(j: "LatkaJazn") -> "LatkaJazn":
+    """Podaje EventBus/ServiceRegistry, podpina Character/Intent, włącza heartbeat.
+       Idempotentne: wielokrotne wywołanie nie doda duplikatów."""
+    global _LLM_APPLIED_MARK
+    if j is None or _LLM_APPLIED_MARK:
+        return j
+
+    # Event bus
+    if not hasattr(j, "bus") or j.bus is None:
+        j.bus = EventBus()  # prosty, bezpieczny wątkowo bus :contentReference[oaicite:6]{index=6}
+
+    # Rejestr usług
+    if not hasattr(j, "services") or j.services is None:
+        j.services = ServiceRegistry()  # z metrykami i cyklem życia :contentReference[oaicite:7]{index=7}
+
+    # Metryki (jeśli brak)
+    if not hasattr(j, "metrics") or j.metrics is None:
+        j.metrics = _MiniMetrics()
+
+    # Character + IntentEngine z tego pliku
+    try:
+        if not hasattr(j, "character") or j.character is None:
+            j.character = Character(j).reload_from_sources().apply_to_jazn(j)  # rejestruje usługę i subskrypcje :contentReference[oaicite:8]{index=8}
+    except Exception:
+        pass
+    try:
+        if not hasattr(j, "intents") or j.intents is None:
+            j.intents = IntentEngine(j)
+    except Exception:
+        pass
+
+    # Heartbeat usług: start, jeśli jeszcze nie działa
+    if not hasattr(j, "_llm_hb") or j._llm_hb is None:
+        try:
+            j._llm_hb = _ServicesHeartbeat(j.services, period_sec=1.0)
+            j._llm_hb.start()
+        except Exception:
+            j._llm_hb = None
+
+    _LLM_APPLIED_MARK = True
+    return j
+
+# 6) Auto-bridge po imporcie (gdy istnieje instancja Jaźni lub sama klasa)
+try:
+    # jeżeli rdzeń już stworzył instancję (np. autostart CLI/symulacji) – podepnij warstwę
+    _j = globals().get("jazn_instance", None)
+    if _j and isinstance(_j, LatkaJazn):
+        apply_llm_layer(_j)
+except Exception:
+    pass
@@
 class Character:
@@
-        # spójność tożsamości
-        ident = self.
+        # spójność tożsamości
+        ident = self.update_identity()
         # sygnalizacja zastosowania postaci (EVT_CHARACTER_APPLIED) — dokładnie raz
         try:
             if hasattr(j, "bus"):
                 payload = {
                     "name": self.persona.name or "Łatka",
                     "version": _try_get_version_from_instance(j, default="1.0"),
                 }
-                pub = getattr(j.bus, "publish_sync", getattr(j.bus, "publish", None))
+                pub = getattr(j.bus, "publish_sync", getattr(j.bus, "publish", None))
                 if callable(pub):
                     pub(EVT_CHARACTER_APPLIED, payload)
         except Exception:
             pass
         # bezpieczny eksport aktualnej persony (dla trwałości tożsamości)
         try:
             self.export_json()
         except Exception:
             pass
         return self
@@
 class IntentEngine:
@@
-            try:
-                self.j.metrics.inc("intents_executed", 1)
-                self.j.bus.publish(EVT_INTENT_EXECUTED, {"kind": it.get("kind"), "ts": time.time()})
-            except Exception:
-                pass
+            try:
+                # metryka + zdarzenie intencji
+                if hasattr(self.j, "metrics"): self.j.metrics.inc("intents_executed", 1)
+                if hasattr(self.j, "bus"): self.j.bus.publish(EVT_INTENT_EXECUTED, {"kind": it.get("kind"), "ts": time.time()})
+            except Exception:
+                pass
             return it
         except Exception:
            return None
@@
     def add_memory(self, kind: str, title: str, content: str, tags: Optional[List[str]] = None) -> Episode:
         ep = self.memory.add(kind=kind, title=title, content=content, tags=tags)
-        self.bus.publish(EVT_MEMORY_ADDED, {"title": title, "ts": ep.timestamp})
+        try:
+            if hasattr(self, "bus"):
+                self.bus.publish(EVT_MEMORY_ADDED, {"title": title, "ts": ep.timestamp})
+        except Exception:
+            pass
         return ep
@@
     def add_journal(self, title: str, content: str, kind: str = "notatka", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
         entry = self.journal.add(title=title, content=content, kind=kind, extra=extra)
         # odcisk emocji z normalnych wpisów
         try:
             self.emotions.imprint_from_text(f"{title}\n\n{content}")
-            self.metrics.inc("emotion_imprints", 1)
+            if hasattr(self, "metrics"): self.metrics.inc("emotion_imprints", 1)
             try:
-                self.bus.publish(EVT_EMOTION_UPDATED, {
+                if hasattr(self, "bus"): self.bus.publish(EVT_EMOTION_UPDATED, {
                     "dominujaca": self.emotions.analiza_stanu_emocjonalnego().get("dominujaca"),
                     "ts": now_ts()
                 })
             except Exception:
                 pass
         except Exception:
             log.debug("Emotion imprint skipped (journal)")
         return entry
+
+# 7) Sugestia użycia z rdzeniem:
+#    from jazn import LatkaJazn; from jazn.ŁLM import apply_llm_layer; j = apply_llm_layer(LatkaJazn())
