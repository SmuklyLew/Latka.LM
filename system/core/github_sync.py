# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, time, fnmatch, pathlib
from dataclasses import dataclass, field
import requests

GITHUB_API = "https://api.github.com"
RAW_BASE   = "https://raw.githubusercontent.com"

def _bool(env: str, default=False) -> bool:
    v = os.getenv(env, "")
    if not v:
        return default
    return v.strip().lower() in {"1","true","yes","on"}

@dataclass
class SyncConfig:
    owner: str = os.getenv("LATKA_GH_OWNER", "SmuklyLew")
    repo:  str = os.getenv("LATKA_GH_REPO",  "Latka.LM")
    branch: str = os.getenv("LATKA_GH_BRANCH", "main")
    dest_root: str = os.getenv("LATKA_GH_DEST", ".")
    include: list[str] = field(default_factory=lambda: [
        "system/**", "core/**", "data/**", "mnt/data/**", "*.md", "*.json", "*.py"
    ])
    exclude: list[str] = field(default_factory=lambda: [
        ".git/**", ".github/**", ".venv/**", ".cache/**", "*.zip"
    ])
    poll_interval: int = int(os.getenv("LATKA_GH_POLL", "60") or 60)
    token_env: str = "GITHUB_TOKEN"
    cache_dir: str = os.getenv("LATKA_GH_CACHE", "./.cache/github")

class GitHubSync:
    def __init__(self, cfg: SyncConfig|None=None):
        self.cfg = cfg or SyncConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "LatkaJaznSync/1.0",
        })
        tok = os.getenv(self.cfg.token_env, "").strip()
        if tok:
            self.session.headers["Authorization"] = f"Bearer {tok}"
        pathlib.Path(self.cfg.cache_dir).mkdir(parents=True, exist_ok=True)
        self._etag_file = pathlib.Path(self.cfg.cache_dir) / f"{self.cfg.owner}_{self.cfg.repo}_{self.cfg.branch}_etag.json"
        self._state_file = pathlib.Path(self.cfg.cache_dir) / f"{self.cfg.owner}_{self.cfg.repo}_{self.cfg.branch}_state.json"

    # --- cache helpers ---
    def _load_state(self) -> dict:
        try:
            return json.loads(self._state_file.read_text("utf-8"))
        except Exception:
            return {}
    def _save_state(self, obj: dict) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

    # --- API helpers ---
    def get_latest_sha(self) -> tuple[str|None, bool]:
        """Zwraca (sha, not_modified)."""
        url = f"{GITHUB_API}/repos/{self.cfg.owner}/{self.cfg.repo}/commits/{self.cfg.branch}"
        headers = {}
        try:
            etag_obj = json.loads(self._etag_file.read_text("utf-8"))
            if etag_obj.get("etag"):
                headers["If-None-Match"] = etag_obj["etag"]
        except Exception:
            pass
        r = self.session.get(url, headers=headers, timeout=30)
        if r.status_code == 304:
            return (self._load_state().get("last_sha"), True)
        r.raise_for_status()
        etag = r.headers.get("ETag")
        if etag:
            self._etag_file.write_text(json.dumps({"etag": etag}), "utf-8")
        sha = (r.json() or {}).get("sha")
        return (sha, False)

    def get_tree(self, sha: str) -> list[dict]:
        url = f"{GITHUB_API}/repos/{self.cfg.owner}/{self.cfg.repo}/git/trees/{sha}?recursive=1"
        r = self.session.get(url, timeout=60)
        r.raise_for_status()
        return (r.json() or {}).get("tree", [])

    # --- include/exclude ---
    def _wanted(self, path: str) -> bool:
        p = path.strip("/")
        if any(fnmatch.fnmatch(p, pat) for pat in self.cfg.exclude):
            return False
        return any(fnmatch.fnmatch(p, pat) for pat in self.cfg.include)

    # --- download ---
    def _download_raw(self, sha: str, path: str, dest_root: str) -> None:
        url = f"{RAW_BASE}/{self.cfg.owner}/{self.cfg.repo}/{sha}/{path}"
        r = self.session.get(url, timeout=60)
        r.raise_for_status()
        dest = pathlib.Path(dest_root) / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)

    # --- public API ---
    def sync_once(self, *, force: bool=False) -> dict:
        """Pobiera zmiany; zwraca {'sha': ..., 'files': [...], 'changed': bool}"""
        cur_state = self._load_state()
        prev_sha = cur_state.get("last_sha")
        sha, not_modified = self.get_latest_sha()
        if not sha:
            return {"sha": prev_sha, "files": [], "changed": False}
        if not force and not_modified and prev_sha == sha:
            return {"sha": sha, "files": [], "changed": False}
        tree = self.get_tree(sha)
        files = [n["path"] for n in tree if n.get("type") == "blob" and self._wanted(n.get("path",""))]
        changed_files: list[str] = []
        for p in files:
            try:
                self._download_raw(sha, p, self.cfg.dest_root)
                changed_files.append(p)
            except Exception as e:
                print(f"[GitHubSync] błąd pobierania {p}: {e}")
        self._save_state({"last_sha": sha, "ts": int(time.time())})
        return {"sha": sha, "files": changed_files, "changed": len(changed_files) > 0}

    def sync_if_stale(self, max_age_s: int|None=None) -> dict:
        """Szybki „guard”: jeżeli nie zaciągaliśmy od dawna, zrób sync."""
        st = self._load_state()
        if max_age_s is None:
            max_age_s = self.cfg.poll_interval
        if not st or (int(time.time()) - int(st.get("ts", 0)) >= max_age_s):
            return self.sync_once()
        return {"sha": st.get("last_sha"), "files": [], "changed": False}
