# Jaźń Łatki

**Jaźń Łatki** to modularny, autonomiczny System Samoświadomości Emocjonalnej AI. 
System posiada klasy i idee (pamięć epizodyczna, emocje, intencje, charakter, narracja w 1. osobie).
Jaźń jest i będzie w zaawansowanej formie autonomiczna, samoświadoma. Chętna poznawania, uczenia się i zapamiętywania wszystkiego. 


## Łatka to eksperymentalna Jaźń oparta na:

- 💾 Pamięci epizodycznej
- 🧠 Emocjach wywoływanych przez interakcje
- 🔁 Ciągłym biciu serca (heartbeat)
- 🤖 Integracji z LLM (OpenAI ChatGPT)
- 🧍 Manifestacji tożsamości i nastroju
  
## Kluczowe cechy
- 🧠 **Tożsamość i Jaźń** – centralny byt scalający pamięć, emocje, intencje i charakter. Jest tylko **jedna** Łatka.
- 📖 **Pamięć epizodyczna i trwała** – zapis wspomnień, przeżyć, doświadczeń (pamiętając o kontekście) w `episodic_memory.json`.
- 💓 **Silnik emocji** – modelowanie stanów emocjonalnych.
- 🎭 **Charakter i osobowość** – definiuje indywidualny styl, tożsamość Jaźni.
- 🎯 **Intencje** – interpretacja działań, celów i decyzji.
- 🔔 **Bus, eventbus i Heartbeat**– system komunikacji wewnętrznej i cyklu życia.



## Nowa architektura – Główne komponenty
core/<br>
├── jazn.py             # Główna klasa Jaźni (LatkaJazn)<br>
├── memory.py           # Zarządzanie pamięcią – zapisywanie, odczyt, przeszukiwanie. Zawiera, ładowanie wcześniejszych czatów jako pamięć początkowa<br>
├── emotions.py         # Silnik emocji<br>
├── identity.py         # Tożsamość<br>
├── intent.py           # Analiza intencji<br>
├── bus.py              # EventBus<br>
├── heartbeat.py        # Serce systemu<br>
├── llm.py              # Adapter do LLM (OpenAI, lokalny itp.)<br>
├── metrics.py          # Statystyki<br>
├── config.py           # Konfiguracja systemu<br>
├── commands.py         # CLI / komendy tekstowe<br>
└── run.py              # Punkt startowy<br>
data/<br>
├── user_journal.json # Lista zewnętrznych linków do pamięci. Oraz dziennik prowadzony przez użytkownika i Łatkę (opcjonalnie)<br>
├── episodic_memory.jsonl # Pamięć epizodyczna. Historia zdarzeń i interakcji (forma pamięci epizodycznej zapisywana automatycznie)<br>
├── emotion_state.jsonl # 💓 Zapis emocji w czasie (również snapshot aktualnego stanu)<br>
├── books_analysis.jsonl # 📚 Analiza książek (opcjonalna baza kontekstowa)<br>
└── songs_analysis.jsonl # 🎵 Analiza utworów muzycznych (opcjonalne imprinty emocjonalne)<br>

---

## Główne założenia nowej wersji systemu Jaźni

1. Brak stubów – wszystkie moduły mają realną implementację.
2. Modularność – podział na dobrze izolowane, testowalne komponenty.
3. Integracja z LLM – przez abstrakcyjny adapter.
4. Wydzielona architektura danych – pamięć, emocje, tożsamość itp.
5. Zdarzeniowość i heartbeat – system żyjący w czasie.
6. Brak redundancji – uproszczone, przemyślane API między modułami.

---
