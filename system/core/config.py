# -*- coding: utf-8 -*-
from __future__ import annotations
import os, logging
from dataclasses import dataclass
from pathlib import Path
import log

BASE_DIR = Path(__file__).resolve().parent   # …/system
DATA_DIR = Path(os.environ.get("JAZN_DATA_DIR", str("/data")))

@dataclass
class Config:
    data_dir: Path = DATA_DIR
    def __post_init__(self):
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log.warning("Nie udało się utworzyć folderu danych %s: %s", self.data_dir, e)

    @classmethod
    def load(cls) -> "Config":
        return cls(data_dir=DATA_DIR)
