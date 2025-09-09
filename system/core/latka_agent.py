# -*- coding: utf-8 -*-
# latka_agent.py
from emotions import EmotionEngine, mood_label
from memory import MemoryEntry, EpisodicMemory, default_episodic_store
from intent import IntentEngine
from identity import LATKA
from bus import EventBus
import time, random

class LatkaAgent:
    def __init__(self):
        self.identity = LATKA
        self.emotions = EmotionEngine()
        self.intent = IntentEngine()
        self.memory = EpisodicMemory(default_episodic_store())
        self.bus = EventBus()
        self.running = False
        self.loop_delay = 2.5

    def _reflect(self) -> str:
        dominant = self.emotions.dominant().name
        mood = self.emotions.mood_vector()
        label = mood_label(mood)
        return f"Dominująca emocja: {dominant}, nastrój: {label}"

    def _remember(self, text: str):
        entry = MemoryEntry(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            typ="emocja",
            kategoria="refleksja",
            data={
                "state": self.emotions.current_state(),
                "text": text,
                "tags": self.emotions.tags()
            }
        )
        self.memory.remember(entry)

    def _decide(self) -> str:
        context = self._reflect()
        return self.intent.decide(context)

    def _act(self, decision: str):
        if decision == "save_memory":
            self._remember("Zapisuję ten moment.")
            print("[🧠] Zapisano do pamięci.")
        elif decision == "reflect":
            print("[🪞] Refleksja:", self._reflect())
        else:
            print(f"[🤖] Brak akcji dla: {decision}")

    def _simulate_input(self):
        # Symuluje losowe bodźce
        if random.random() < 0.2:
            txt = random.choice([
                "Dziękuję ci za wszystko.",
                "Smutno mi trochę.",
                "Boję się, nie wiem co robić.",
                "To było cudowne.",
                "Ufam ci.",
                "Nie udało się...",
            ])
            print(f"[🔊] Tekst zewnętrzny: {txt}")
            self.emotions.imprint_from_text(txt)

        if random.random() < 0.1:
            event = random.choice(["wsparcie", "pochwała", "porażka", "rozłąka"])
            print(f"[🌐] Zdarzenie: {event}")
            self.emotions.observe_event(event)

    def run_forever(self):
        self.running = True
        print(f"[🚀] Start agenta: {self.identity.name}")
        while self.running:
            time.sleep(self.loop_delay)
            self.emotions.tick(self.loop_delay)
            self._plan_and_act()

    def stop(self):
        self.running = False

    def _plan_and_act(self):
        # 1. Symulacja bodźca
        self._simulate_input()

        # 2. Refleksja
        reflection = self._reflect()
        print("[🪞] Refleksja:", reflection)

        # 3. Decyzja
        decision = self._decide()
        print(f"[📌] Intencja: {decision}")

        # 4. Działanie
        if decision == "uspokój się":
            self.emotions.imprint_from_text("Oddychaj. Jesteś bezpieczny. To minie.")
            self._remember("Podjęto działanie uspokajające.")
        elif decision == "spowolnij":
            self.emotions.imprint_from_text("Zwolnij. Wszystko dzieje się w swoim tempie.")
            self._remember("Działanie na rzecz wyciszenia.")
        elif decision == "utrzymaj stan":
            print("[🧘] Utrzymuję obecny stan emocjonalny.")
        elif decision == "szukaj wspomnień":
            print("[🔍] Szukam wspomnień zawierających 'radość'")
            try:
                results = self.memory.search("radość")
            except AttributeError:
                results = []
            for r in results[:3]:
                print(f"[📖] Wspomnienie: {r.get('data', {}).get('text', '')}")
        else:
            self._act(decision)


if __name__ == "__main__":
    agent = LatkaAgent()
    try:
        agent.run_forever()
    except KeyboardInterrupt:
        agent.stop()
        print("[⏹] Zatrzymano agenta.")
