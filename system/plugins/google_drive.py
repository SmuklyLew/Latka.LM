# -*- coding: utf-8 -*-
# Placeholder integracji Google Drive (OAuth poza runtime ChatGPT)
class GoogleDrivePlugin:
    id = "google_drive"
    def __init__(self, *a, **k):
        self.running = False
        print("[Plugin:google_drive] init (no-op in this runtime)")
    def start(self):
        self.running = True
        print("[Plugin:google_drive] start (no-op)")
    def on_event(self, event):
        if self.running:
            print(f"[Plugin:google_drive] event: {event!r} (no-op)")
    def stop(self):
        self.running = False
        print("[Plugin:google_drive] stop")
