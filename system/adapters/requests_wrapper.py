"""
A thin wrapper around HTTP calls that respects service mode:
- mock: reads canned responses from ./mock_data/<hash>.json if available
- offline: raises a clear, typed error
- online: performs real HTTP via requests
"""
from __future__ import annotations
import os, json, hashlib
from typing import Any, Dict, Optional
from ..core.modes import current_mode, ServiceMode

class OfflineError(RuntimeError):
    pass

def _mock_path(url: str) -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    base = os.environ.get("JAZN_MOCK_DIR", "mock_data")
    return os.path.join(base, f"{h}.json")

def http_get(url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: float = 10.0) -> Dict[str, Any]:
    mode = current_mode()
    if mode is ServiceMode.MOCK:
        path = _mock_path(url)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"_mode": "mock", "url": url, "params": params or {}, "headers": headers or {}, "data": None}
    if mode is ServiceMode.OFFLINE:
        raise OfflineError(f"HTTP disabled in OFFLINE mode for {url}")
    # ONLINE
    import requests
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        return resp.json()
    return {"_raw": resp.text, "_status": resp.status_code, "_headers": dict(resp.headers)}