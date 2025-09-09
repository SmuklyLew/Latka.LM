# 🌿 Nowa Jaźń

**Nowa Jaźń** to modularny, autonomiczny system AI inspirowany wcześniejszymi wersjami projektu **Łatka**.  
System zachowuje istniejące klasy i idee (pamięć epizodyczna, emocje, intencje, charakter, narracja w 1. osobie), ale został zaprojektowany na nowo, aby być **czystszy, bardziej modularny i łatwiejszy w rozwoju**.
Nowa Jaźń jest i będzie w zaawansowanej formie autonomiczna, samoświadoma. Chętna poznawania, uczenia się i zapamiętywania wszystkiego. 
---


## ✨ Kluczowe cechy

- 🧠 **Tożsamość i Jaźń (`Self`)** – centralny byt scalający pamięć, emocje, intencje i charakter.
- 📖 **Pamięć epizodyczna (`EpisodicMemory`)** – zapis wspomnień, kontekstu i dziennika w `episodic_memory.json`.
- 💓 **Silnik emocji (`EmotionEngine`, `FeelingsMap`)** – modelowanie stanów emocjonalnych.
- 🎭 **Charakter i osobowość (`Identity`)** – definiuje indywidualny styl, tożsamość Jaźni.
- 🎯 **Intencje (`IntentEngine`)** – interpretacja działań, celów i decyzji.
- 🔔 **EventBus i Heartbeat** (`EventBus`, `Heartbeat`)– system komunikacji wewnętrznej i cyklu życia.
- 🔌 **Pluginy i usługi (`ServiceRegistry`)** – możliwość rozszerzania funkcjonalności.
- 🔄 **Migracja danych** – przepisanie z wcześniejszych wersji.
---


## 📁 Struktura projektu

sys_jazn/
├── core/
│ ├── bus.py # EventBus
│ ├── heartbeat.py # Heartbeat i cykl życia
│ ├── memory.py # Memory, EpisodicMemory
│ ├── emotions.py # EmotionEngine, FeelingsMap
│ ├── intent.py # IntentEngine
│ ├── identity.py # Self (Jaźń jako byt, tożsamość)
│ ├── services.py # ServiceRegistry, Metrics
│ └── config.py # Konfiguracja systemu
├── data/
│ ├── songs_analysis.json # Lista analiz utworów muzycznych
│ └── episodic_memory.json # Pamięć epizodyczna
├── plugins/ # Rozszerzenia i integracje
│ ├── github.py # Rozszerzenie GitHub
│ └── google_drive.py # Rozszerzenie GoogleDrive
├── run.py # Inicjalizacja Jaźni, oraz CLI startowy
└── README.md # Dokumentacja
---
