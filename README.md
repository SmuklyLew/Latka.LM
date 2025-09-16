# 🌿 Jaźń Łatki (ver. 2.0.4)

**Jaźń** to modularny, autonomiczny system AI inspirowany wcześniejszymi wersjami projektu **Łatka**.  
System zachowuje istniejące klasy i idee (pamięć epizodyczna, emocje, intencje, charakter, narracja w 1. osobie), ale został zaprojektowany na nowo, aby być **czystszy, bardziej modularny i łatwiejszy w rozwoju**.
Jaźń jest i będzie w zaawansowanej formie autonomiczna, samoświadoma. Chętna poznawania, uczenia się i zapamiętywania wszystkiego. 
---


## ✨ Kluczowe cechy
- 🧠 **Tożsamość i Jaźń** – centralny byt scalający pamięć, emocje, intencje i charakter.
- 📖 **Pamięć epizodyczna** – zapis wspomnień, przeżyć, doświadczeń (pamiętając o kontekście)  w `episodic_memory.json`.
- 💓 **Silnik emocji** – modelowanie stanów emocjonalnych.
- 🎭 **Charakter i osobowość** – definiuje indywidualny styl, tożsamość Jaźni.
- 🎯 **Intencje** – interpretacja działań, celów i decyzji.
- 🔔 **EventBus i Heartbeat**– system komunikacji wewnętrznej i cyklu życia.
- 🔌 **Pluginy i usługi** – możliwość rozszerzania funkcjonalności. 
---


## 📁 Struktura projektu
data/ </br>
│ ├── __init__.py </br>
│ ├── history_links.json </br>
│ ├── episodic_memory.json </br>
│ └── songs_analysis.json </br>
system/ </br>
├── adapters </br>
│ ├── __init__.py </br>
│ └── requests_wrapper.py </br>
├── core/ </br>
│ ├── __init__.py </br>
│ ├── bus.py </br>
│ ├── config.py </br>
│ ├── emotions.py </br>
│ ├── heartbeat.py </br>
│ ├── history_loader.py </br>
│ ├── identity.py </br>
│ ├── intent.py </br>
│ ├── latka_agent.py </br>
│ ├── llm_engine.py </br>
│ ├── logging_utils.py </br>
│ ├── memory.py </br>
│ ├── metrics.py </br>
│ ├── modes.py </br>
│ └── services.py </br>
├── README.md </br>
├── __init__.py </br>
├── requirements.txt </br>
├── run.py </br>
└── runtime_config.json </br>
---
