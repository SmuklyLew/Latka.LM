# -*- coding: utf-8 -*-
from __future__ import annotations

class ThoughtEconomy:
    def __init__(self, budget: int = 100):
        self.budget = budget
    def spend(self, cost: int) -> bool:
        if cost <= self.budget:
            self.budget -= cost
            return True
        return False


class EthicsModule:
    def __init__(self, rules: list[str] | None = None):
        self.rules = rules or ["do_no_harm"]
    def check(self, action: str) -> bool:
        # placeholder: zawsze True
        return True


class IntentEngine:
    def __init__(self):
        self.te = ThoughtEconomy()
        self.ethics = EthicsModule()
    def decide(self, context: str) -> str:
        import random
        ctx = (context or "").lower()
        if "smutek" in ctx or "przygaszony" in ctx:
            return "uspokój się"
        if "napięty" in ctx or "pobudzony" in ctx:
            return "spowolnij"
        if "radość" in ctx and "spokojny" in ctx:
            return "utrzymaj stan"
        # fallback intents
        return random.choice(["save_memory", "reflect", "szukaj wspomnień"])
