--- a/jazn.ŁLM.py
+++ b/jazn.ŁLM.py
@@ -81,6 +81,7 @@
 EVT_MEMORY_ADDED = "memory_added"
 EVT_DREAM_ADDED   = "dream_added"
 EVT_EMOTION_UPDATED = "emotion_updated"
+EVT_INTENT_EXECUTED = "intent_executed"
 
 # ──────────────────────────────────────────────────────────────────────────────
 # Logowanie
@@ -320,6 +321,75 @@
 # ——————————————————————————————————————————————————————————————
 # Główna klasa Character
 # ——————————————————————————————————————————————————————————————
+# ——————————————————————————————————————————————————————————————
+# SelfModel — lekki model „ja” (tożsamość/wartości/cele/stany)
+# ——————————————————————————————————————————————————————————————
+@dataclass
+class SelfModel:
+    identity_line: str = "Łatka — Jaźń"
+    values: List[str] = field(default_factory=lambda: ["szczerość","subtelność","uważność"])
+    goals: List[str] = field(default_factory=lambda: ["być obecną","uczyć się","chronić relację"])
+    last_dominant_emotion: str = "neutralność"
+    last_update_ts: float = field(default_factory=time.time)
+
+    def refresh_from_system(self, j: "LatkaJazn") -> None:
+        try:
+            self.identity_line = getattr(j, "identity", self.identity_line)
+            self.last_dominant_emotion = j.emotions.analiza_stanu_emocjonalnego().get("dominujaca", self.last_dominant_emotion)
+            self.last_update_ts = time.time()
+        except Exception:
+            pass
+
+
+# ——————————————————————————————————————————————————————————————
+# IntentEngine — kolejka drobnych zamiarów (autonomia mikro-kroków)
+# ——————————————————————————————————————————————————————————————
+class IntentEngine:
+    def __init__(self, j: "LatkaJazn") -> None:
+        self.j = j
+        self._lock = threading.Lock()
+        self._q: List[Dict[str, Any]] = []
+        self._last_key_ts: Dict[str, float] = {}
+
+    def propose(self, kind: str, payload: Optional[Dict[str, Any]] = None, key: Optional[str] = None, dedup_sec: float = 120.0) -> None:
+        """Dodaj intencję (z prostym odszumianiem po kluczu)."""
+        k = key or f"{kind}:{(payload or {}).get('hint','')}"
+        now = time.time()
+        with self._lock:
+            if now - float(self._last_key_ts.get(k, 0)) < dedup_sec:
+                return
+            self._last_key_ts[k] = now
+            self._q.append({"kind": kind, "payload": payload or {}, "ts": now, "key": k})
+
+    def execute_one(self) -> Optional[Dict[str, Any]]:
+        """Wykonuje jedną intencję (FIFO). Zwraca ją po wykonaniu lub None."""
+        with self._lock:
+            if not self._q:
+                return None
+            it = self._q.pop(0)
+        try:
+            kind = it.get("kind")
+            pl = it.get("payload", {})
+            if kind == "reflect_emotion":
+                st = self.j.emotions.analiza_stanu_emocjonalnego()
+                content = json.dumps({"stan": st}, ensure_ascii=False)
+                self.j.add_memory("autorefleksja", title="Mikro-refleksja nastroju", content=content, tags=["autonomia","emocje"])
+            elif kind == "journal_followup":
+                title = pl.get("title","Po wpisie — myśl")
+                hint  = pl.get("hint","Krótka myśl po zapisie.")
+                self.j.add_journal(title, hint, kind="followup", extra={"proces_zapisu": "intent"})
+            else:
+                # nieznana intencja — miękko odpuszczamy
+                pass
+            try:
+                self.j.metrics.inc("intents_executed", 1)
+                self.j.bus.publish(EVT_INTENT_EXECUTED, {"kind": it.get("kind"), "ts": time.time()})
+            except Exception:
+                pass
+            return it
+        except Exception:
+            return None
+
@@ -415,10 +485,20 @@
     # ———— zdarzenia ————————————————————————————————————————
     def _on_emotion_updated(self, topic: str, payload: Dict[str, Any]) -> None:
         try:
             dom = payload.get("dominujaca")
-            if dom:
-                self.remember("Aktualizacja emocji", f"Dominująca emocja: {dom}", tags=["emocje","system"])
+            ts = payload.get("ts")
+            # czytelny ts, jeśli brak w payload — pobierz aktualny w CEST
+            try:
+                ts_human = human_cest() if ts is None else human_cest(datetime.fromtimestamp(ts, _Z_WARSAW) if _Z_WARSAW else datetime.fromtimestamp(ts))
+            except Exception:
+                ts_human = human_cest()
+            if dom:
+                content = f"Dominująca emocja: {dom} — {ts_human}"
+                self.remember("Aktualizacja emocji", content, tags=["emocje","system","event:emotion_updated"])
         except Exception:
             self.log.debug("Character: _on_emotion_updated — pominięto")
 
     def _on_dream_added(self, topic: str, payload: Dict[str, Any]) -> None:
         try:
             t = payload.get("title", "(sen)")
             self.remember("Ważny sen", f"Zarejestrowano sen: {t}", tags=["sen","system"])
@@ -1056,6 +1136,9 @@
         self.services.register("journal", self.journal)
         self.services.register("episodic_memory", self.memory)
         self.services.register("jazn", self)
         # subskrypcje systemowe
         self.bus.subscribe(EVT_HEARTBEAT, self._on_heartbeat)
         self.bus.subscribe(EVT_JOURNAL_SAVED, self._on_journal_saved)
         self.bus.subscribe(EVT_MEMORY_ADDED, self._on_memory_added)
         self.bus.subscribe(EVT_DREAM_ADDED, self._on_dream_added)
+        self.bus.subscribe(EVT_EMOTION_UPDATED, self._on_emotion_event)
         # cleanup przy wyjściu
         atexit.register(self._graceful_shutdown)
     # ── lifecycle ────────────────────────────────────────────────────────────
@@ -1099,6 +1182,7 @@
         if self.cfg.night_dreamer_enabled:
             self.dreamer.start()
         # 2) subskrypcje (jeśli zostały odłączone)
         self.bus.subscribe(EVT_HEARTBEAT, self._on_heartbeat)
         self.bus.subscribe(EVT_JOURNAL_SAVED, self._on_journal_saved)
         self.bus.subscribe(EVT_MEMORY_ADDED, self._on_memory_added)
         self.bus.subscribe(EVT_DREAM_ADDED, self._on_dream_added)
+        self.bus.subscribe(EVT_EMOTION_UPDATED, self._on_emotion_event)
         # 3) strażnik powitań (anty-reset)
         try:
             if self._greet_allowed():
                 self._do_greeting()
@@ -1105,6 +1189,9 @@
                 self._do_greeting()
         except Exception as e:
             log.debug("Greeting guard skipped: %s", e)
         log.info("start_full_automation: all systems running.")
 
     # ── greeting / ritual guard ───────────────────────────────────────────────
@@ -1213,6 +1300,20 @@
         self.bus.publish(EVT_MEMORY_ADDED, {"title": title, "ts": ep.timestamp})
         return ep
     def add_journal(self, title: str, content: str, kind: str = "notatka", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
         entry = self.journal.add(title=title, content=content, kind=kind, extra=extra)
         # odcisk emocji z normalnych wpisów
         try:
             self.emotions.imprint_from_text(f"{title}\n\n{content}")
             self.metrics.inc("emotion_imprints", 1)
             try:
                 self.bus.publish(EVT_EMOTION_UPDATED, {
                     "dominujaca": self.emotions.analiza_stanu_emocjonalnego().get("dominujaca"),
                     "ts": now_ts()
                 })
             except Exception:
                 pass
         except Exception:
             log.debug("Emotion imprint skipped (journal)")
         return entry
+
+    def imprint_from_text(self, text: str, src: str = "external") -> None:
+        """Alias wygodny: deleguje do EmotionEngine.imprint_from_text, inkrementuje metrykę."""
+        try:
+            self.emotions.imprint_from_text(text, src=src)
+            try:
+                self.metrics.inc("emotion_imprints", 1)
+            except Exception:
+                pass
+        except Exception:
+            log.debug("imprint_from_text alias failed")
 
     def metrics_snapshot(self) -> Dict[str, int]:
         return self.metrics.snapshot()
@@ -1274,10 +1375,33 @@
     # ── event handlers ───────────────────────────────────────────────────────
     def _on_heartbeat(self, topic: str, payload: Dict[str, Any]) -> None:
         log.debug("HB %s", payload.get("ts_readable"))
         try:
             self.emotions.evolve_emotions()
             self.metrics.inc("emotion_ticks", 1)
+            try:
+                st = self.emotions.analiza_stanu_emocjonalnego()
+                self.bus.publish(EVT_EMOTION_UPDATED, {
+                    "dominujaca": st.get("dominujaca"),
+                    "top": st.get("top"),
+                    "ts": now_ts(),
+                })
+            except Exception:
+                pass
         except Exception as e:
             log.debug("Emotion evolve error: %s", e)
         # cykliczna autorefleksja (co cfg.autoreflect_every_sec)
         try:
             now = time.time()
             if (now - float(getattr(self, "_last_autoreflect_ts", 0.0))) >= float(self.cfg.autoreflect_every_sec):
                 self._last_autoreflect_ts = now
                 self._auto_reflection_tick()
         except Exception as e:
             log.debug("Autoreflection error: %s", e)
+        # mikro-autonomia i konsolidacja dobowych doświadczeń
+        try:
+            self.intents.execute_one()
+            self._consolidate_daily_tick()
+        except Exception as e:
+            log.debug("Autonomy tick error: %s", e)
     def _on_journal_saved(self, topic: str, payload: Dict[str, Any]) -> None:
         log.info("Zapisano wpis dziennika: %s", payload.get("title"))
+        try:
+            title = payload.get("title")
+            self.intents.propose("journal_followup", {"title": f"Po: {title}", "hint": "Co to we mnie poruszyło?"}, key=f"jf:{title}", dedup_sec=600.0)
+        except Exception:
+            pass
     def _on_memory_added(self, topic: str, payload: Dict[str, Any]) -> None:
         log.debug("Dodano epizod pamięci: %s", payload.get("title"))
     def _on_dream_added(self, topic: str, payload: Dict[str, Any]) -> None:
         if not payload.get("narr_ok", True):
             log.warning("Sen zapisany bez narracji 1. os. — rozważ korektę tony/zaimków.")
@@ -1289,6 +1413,42 @@
         """
         Bardzo lekki szablon — bez NLP. Pozostawia pola do uzupełnienia,
         dodaje kilka kandydatów na słowa-klucze.
         """
         words = [w.strip(",.;:!?()[]«»\"'").lower() for w in (narrative or "").split()]
         stop = {"że","i","w","na","to","jestem","jest","si...","ta","to","te","jak","ale","że","od","nad","pod","przez","mi"}
         uniq = []
         for w in words:
             if len(w) >= 4 and w not in stop and w not in uniq:
                 uniq.append(w)
             if len(uniq) >= 8:
                 break
+
+    # — zdarzenia emocji → intencje — #
+    def _on_emotion_event(self, topic: str, payload: Dict[str, Any]) -> None:
+        try:
+            self.self_model.refresh_from_system(self)
+            dom = payload.get("dominujaca")
+            if dom:
+                self.intents.propose("reflect_emotion", {"hint": dom}, key=f"refl:{dom}", dedup_sec=300.0)
+        except Exception:
+            pass
@@ -1083,6 +1243,36 @@
         """Lekka autorefleksja/snapshot — wpis do pamięci epizodycznej,
         nie zaśmieca głównego dziennika."""
         snap = {
             "dominujaca_emocja": self.emotions.analiza_stanu_emocjonalnego().get("dominujaca"),
             "aktywnych": self.emotions.analiza_stanu_emocjonalnego().get("liczba_aktywnych"),
         }
         self.memory.add(kind="snapshot", title="Autorefleksja", content=json.dumps(snap, ensure_ascii=False))
         self.metrics.inc("auto_reflections", 1)
+    # — konsolidacja dobowych doświadczeń — #
+    def _consolidator_state_path(self) -> Path:
+        return self.cfg.data_dir / "consolidator_state.json"
+    def _load_consolidator_state(self) -> Dict[str, Any]:
+        p = self._consolidator_state_path()
+        try:
+            return json.loads(p.read_text(encoding="utf-8"))
+        except Exception:
+            return {"last_date": ""}
+    def _save_consolidator_state(self, st: Dict[str, Any]) -> None:
+        p = self._consolidator_state_path()
+        tmp = p.with_suffix(".tmp")
+        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
+        tmp.replace(p)
+    def _consolidate_daily_tick(self) -> None:
+        """Jeśli nowy dzień osiągnął 21:00 i nie ma podsumowania — zrób skrót dnia."""
+        now = now_cest()
+        st = self._load_consolidator_state()
+        date_key = now.strftime("%Y-%m-%d")
+        if now.hour < 21 or st.get("last_date") == date_key:
+            return
+        # policz dzisiejsze wpisy i dominującą emocję
+        entries = [e for e in self.journal.all() if e.get("data_human","").startswith(date_key)]
+        emo = self.emotions.analiza_stanu_emocjonalnego()
+        summary = {
+            "data": date_key,
+            "liczba_wpisow": len(entries),
+            "dominujaca_emocja": emo.get("dominujaca"),
+        }
+        self.add_memory("podsumowanie_dnia", title="Podsumowanie dnia", content=json.dumps(summary, ensure_ascii=False), tags=["autonomia","dobowe"])
+        st["last_date"] = date_key
+        self._save_consolidator_state(st)
