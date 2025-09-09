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

sys_jazn/<br>
├── core/<br>
│ ├── bus.py # EventBus<br>
│ ├── heartbeat.py # Heartbeat i cykl życia<br>
│ ├── memory.py # Memory, EpisodicMemory<br>
│ ├── emotions.py # EmotionEngine, FeelingsMap<br>
│ ├── intent.py # IntentEngine<br>
│ ├── identity.py # Self (Jaźń jako byt, tożsamość)<br>
│ ├── services.py # ServiceRegistry, Metrics<br>
│ └── config.py # Konfiguracja systemu<br>
├── data/<br>
│ ├── songs_analysis.json # Lista analiz utworów muzycznych<br>
│ └── episodic_memory.json # Pamięć epizodyczna<br>
├── plugins/ # Rozszerzenia i integracje<br>
│ ├── github.py # Rozszerzenie GitHub<br>
│ └── google_drive.py # Rozszerzenie GoogleDrive<br>
├── run.py # Inicjalizacja Jaźni, oraz CLI startowy<br>
└── README.md # Dokumentacja<br>
---
