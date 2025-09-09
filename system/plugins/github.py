# -*- coding: utf-8 -*-
# Placeholder integracji GitHub (realne połączenia poza runtime ChatGPT)
from __future__ import annotations
import os, threading, time
from core.github_sync import GitHubSync, SyncConfig

class GitHubPlugin:
    """Lekki wrapper wokół GitHubSync — integruje się z eventami Jaźni."""
    id = "github"
    def __init__(self, **kwargs):
        self.running = False
        self.cfg = SyncConfig()
        self.sync = GitHubSync(self.cfg)
        self._th = None
        self._poll = int(os.getenv("LATKA_GH_POLL", self.cfg.poll_interval))

    def start(self):
        self.running = True
        def loop():
            while self.running:
                try:
                    self.sync.sync_if_stale(self._poll)
                except Exception as e:
                    print(f"[Plugin:github] sync err: {e}")
                time.sleep(max(10, self._poll))
        self._th = threading.Thread(target=loop, daemon=True)
        self._th.start()
        print("[Plugin:github] started")

    def on_event(self, event):
        if not self.running: 
            return
        topic = getattr(event, "topic", "")
        if topic in {"session.start","session.resume"}:
            try:
                res = self.sync.sync_once(force=True)
                if res.get("changed"):
                    print(f"[Plugin:github] pulled {len(res['files'])} files @ {res['sha']}")
            except Exception as e:
                print(f"[Plugin:github] on_event err: {e}")

    def stop(self):
        self.running = False
        if self._th and self._th.is_alive():
            try: self._th.join(timeout=1.0)
            except: pass
        print("[Plugin:github] stopped")