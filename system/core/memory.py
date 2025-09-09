# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Iterable, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import hashlib
from .config import DATA_DIR


@dataclass
class MemoryEntry:
    timestamp: str
    typ: str
    kategoria: str
    data: dict[str, Any]
    source: str = "system"  # np. "user", "environment", "system"


class JSONStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")
    def load(self) -> List[Dict[str, Any]]:
        txt = self.path.read_text(encoding="utf-8").strip() or "[]"

        try:
            return json.loads(txt)
        except Exception:
            # awaryjnie: uszkodzony plik pamięci → zwróć pustą listę
            return []
    def append(self, item: Dict[str, Any]):
        data = self.load()
        data.append(item)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_all(self, items: List[Dict[str, Any]]):
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


class EpisodicMemory:
    def __init__(self, store_path: str):
        self.store = JSONStore(store_path)
    def remember(self, entry: MemoryEntry):
        self.store.append(asdict(entry))
    def recall(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.store.load()[-n:]
    def load_all(self) -> List[Dict[str, Any]]:
        return self.store.load()
    def append_many(self, entries: Iterable[MemoryEntry]):
        data = self.store.load()
        data.extend(asdict(e) for e in entries)
        self.store.write_all(data)
    def search(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Proste wyszukiwanie po polu data.text (case-insensitive)."""
        kw = (keyword or "").lower()
        hits: List[Dict[str, Any]] = []
        for e in self.store.load():
            text = str(e.get("data", {}).get("text", ""))
            if kw in text.lower():
                hits.append(e)
                if len(hits) >= limit:
                    break
        return hits

def default_episodic_store(base_dir: str | None = None) -> str:
    from pathlib import Path
    base = Path(base_dir or DATA_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "episodic_memory.json")


# --- Songs analysis: osobny magazyn JSON -------------------------------
class SongsAnalysisStore:
    """
    Warstwa I/O dla /data/songs_analysis.json
    Struktura spodziewana:
    {
      "konfiguracja": {...},
      "analizy": [ {...}, {...} ]
    }
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"konfiguracja": {}, "analizy": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> Dict[str, Any]:
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {"konfiguracja": {}, "analizy": []}
        try:
            return json.loads(raw)
        except Exception:
            # awaryjnie: zwróć pustą strukturę zamiast wyjątku
            return {"konfiguracja": {}, "analizy": []}

    def list_analyses(self) -> List[Dict[str, Any]]:
        obj = self.load()
        return obj.get("analizy", [])

    def add_analysis(self, analysis: Dict[str, Any]) -> None:
        obj = self.load()
        obj.setdefault("analizy", []).append(analysis)
        self.path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        kw = keyword.lower()
        results = []
        for a in self.list_analyses():
            hay = " ".join(str(a.get(k, "")) for k in ["tytul", "analiza", "refleksja_latki", "moje_odczucia_latki", "podsumowanie"])
            if kw in hay.lower():
                results.append(a)
        return results

def default_songs_store(base_dir: str | None = None) -> str:
    base = Path(base_dir or DATA_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "songs_analysis.json")

# --- Journal (dziennik.json) → adapter do pamięci epizodycznej ----------
class JournalAdapter:
    """
    Czyta dziennik.json (klucz "entries") i transformuje wpisy do MemoryEntry.
    Obsługa pól opcjonalnych, automatyczne uzupełnianie timestamp.
    """
    def __init__(self, journal_path: str | Path):
        self.path = Path(journal_path)

    def _load_raw(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"entries": []}
        txt = self.path.read_text(encoding="utf-8").strip() or "{}"
        try:
            return json.loads(txt)
        except Exception:
            # awaryjnie spróbuj naprawić ewentualne przecinki/duplikaty — tutaj minimalnie
            return {"entries": []}

    @staticmethod
    def _as_timestamp(s: Optional[str]) -> str:
        # akceptuje już-gotowe ISO lub tworzy ISO z "YYYY-MM-DD ..." (bez TZ → brak offsetu)
        if not s:
            return datetime.now().isoformat()
        try:
            # jeśli to wygląda na ISO — pozostaw
            datetime.fromisoformat(s.replace("Z", "+00:00"))  # walidacja
            return s
        except Exception:
            # spróbuj sparsować „ludzki” zapis i przepisać do ISO (bez TZ)
            try:
                # Najbardziej elastyczne: weź początek (data + opcj. czas) i konwertuj
                # Uwaga: tu bez strefy (ISO lokalne) — w projekcie timestampa i tak dodajemy przy zapisie
                return datetime.fromisoformat(s.split(" C")[0].replace("  ", " ")).isoformat()
            except Exception:
                return datetime.now().isoformat()

    @staticmethod
    def _category(entry: Dict[str, Any]) -> str:
        return str(entry.get("kategoria") or entry.get("category") or "dziennik")

    @staticmethod
    def _type(entry: Dict[str, Any]) -> str:
        return str(entry.get("typ") or entry.get("type") or "notatka")

    @staticmethod
    def _payload(entry: Dict[str, Any]) -> Dict[str, Any]:
        # zachowujemy główne pola dziennika w "data"
        keep = ("tytuł", "tytul", "treść", "tresc", "scena", "wspomnienie", "emocje", "meta")
        out = {}
        for k in keep:
            if k in entry:
                out[k] = entry[k]
        # dodatkowo pole "text" do ujednoliconego wyszukiwania
        text = entry.get("treść") or entry.get("tresc") or ""
        out["text"] = text
        return out

    @staticmethod
    def _fingerprint(e: Dict[str, Any]) -> str:
        h = hashlib.sha256()
        key = f"{e.get('timestamp','')}|{e.get('typ','')}|{e.get('kategoria','')}|{json.dumps(e.get('data',{}), ensure_ascii=False, sort_keys=True)}"
        h.update(key.encode("utf-8"))
        return h.hexdigest()

    def iter_entries(self) -> Iterable[MemoryEntry]:
        obj = self._load_raw()
        for it in obj.get("entries", []):
            # preferuj jawny 'timestamp'; akceptuj 'data' jako str tylko gdy faktycznie nim jest
            ts = it.get("timestamp") or (it.get("data") if isinstance(it.get("data"), str) else None)
            yield MemoryEntry(
                timestamp=self._as_timestamp(ts),
                typ=self._type(it),
                kategoria=self._category(it),
                data=self._payload(it),
                source="journal"
            )

class MemoryHub:
    """
    Spina:
      - pamięć epizodyczną (/data/episodic_memory.json)
      - analizy utworów (/data/songs_analysis.json)
      - opcjonalny import z dziennik.json
    """
    def __init__(
        self,
        base_dir: str | Path | None = None,
        episodic_path: str | Path | None = None,
        songs_path: str | Path | None = None,
    ):
        base = Path(base_dir or DATA_DIR)
        self.episodic = EpisodicMemory(str(Path(episodic_path) if episodic_path else base / "episodic_memory.json"))
        self.songs = SongsAnalysisStore(str(Path(songs_path) if songs_path else base / "songs_analysis.json"))

    # --- Journal import / sync ---
    def import_from_journal(self, journal_path: str | Path, dedupe: bool = True) -> Tuple[int, int]:
        """
        Zasila pamięć epizodyczną wpisami z dziennik.json.
        Zwraca: (liczba_nowych, liczba_pominiętych_duplikatów)
        """
        adapter = JournalAdapter(journal_path)
        existing = self.episodic.load_all()
        already = {JournalAdapter._fingerprint(e) for e in existing}
        new, skipped = 0, 0
        batch: List[MemoryEntry] = []
        for e in adapter.iter_entries():
            d = asdict(e)
            fp = JournalAdapter._fingerprint(d)
            if dedupe and fp in already:
                skipped += 1
                continue
            batch.append(e)
            already.add(fp)
            new += 1
        if batch:
            self.episodic.append_many(batch)
        return new, skipped

    # --- Wyszukiwanie wspólne ---
    def search_text(self, keyword: str, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        kw = keyword.lower()
        epi_hits = [
            e for e in reversed(self.episodic.load_all())
            if kw in (str(e.get("data", {}).get("text", ""))).lower()
        ][:limit]
        songs_hits = self.songs.search(keyword)[:limit]
        return {"episodic": epi_hits, "songs": songs_hits}

    # --- Skróty do najczęstszych operacji ---
    def remember(self, entry: MemoryEntry) -> None:
        self.episodic.remember(entry)

    def add_song_analysis(self, analysis: Dict[str, Any]) -> None:
        self.songs.add_analysis(analysis)

    def last_episodes(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.episodic.recall(n)

    def list_song_analyses(self) -> List[Dict[str, Any]]:
        return self.songs.list_analyses()