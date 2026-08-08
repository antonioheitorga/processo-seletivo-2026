# Resultados — Conjunto de Validação

- Perguntas: 10
- Pontuação média: 0.750
- Roteamento correto (RAG/fallback): 9/10

| ID | Pergunta | Fonte | RAG/Fallback | Roteamento OK | Pontuação | Resposta gerada |
|---|---|---|---|---|---|---|
| C01 | How many points does the winner of a Formula 1 race receive, and does the full amount always apply regardless of how much of the race is completed? | corpus | rag | ✅ | 0.5 | The winner of a Formula 1 race receives 25 points. However, this amount does not always apply regardless of how much of the race is completed. According to Arti |
| C02 | What is the minimum mass of an F1 car during Qualifying and Sprint Qualifying sessions in the 2026 Technical Regulations? | corpus | rag | ✅ | 1.0 | The minimum mass of an F1 car during Qualifying and Sprint Qualifying sessions in the 2026 Technical Regulations is 726kg plus the Nominal Tyre Mass. |
| C03 | What does the Cost Cap in the Financial Regulations for F1 Teams limit? | corpus | rag | ✅ | 1.0 | The Cost Cap in the Financial Regulations for F1 Teams limits certain costs that may be incurred by or on behalf of an F1 Team in each Full Year Financial Regul |
| C04 | What is Parc Fermé and when does it apply? | corpus | rag | ✅ | 0.5 | What is Parc Fermé and when does it apply?  Parc Fermé refers to a designated secure area at a Competition where F1 Cars must be kept after qualifying and durin |
| C05 | What is the FIA's definition of 'Sprint' in the F1 Regulations? | corpus | rag | ✅ | 1.0 | According to Article 27.2 of the Formula One Technical and Sporting Regulations, "Sprint" means an FIA Formula One sprint, including sprint qualifying events, a |
| F01 | What team does Lewis Hamilton drive for in the 2026 season? | hybrid | fallback | ✅ | 0.0 | El equipo de Lewis Hamilton en la temporada 2026 es Ferrari. |
| F02 | What was the outcome of the 2025 Monaco Grand Prix? | corpus | rag | ❌ | 0.5 | The outcome of the 2025 Monaco Grand Prix may be uncertain, as there is no information provided in the given context regarding the results or classification of  |
| F03 | What livery colors will Ferrari use for the 2026 season? | hybrid | fallback | ✅ | 1.0 | La livrea ufficiale della Scuderia Ferrari per la stagione 2026 è caratterizzata da un rosso più intenso e brillante, con una finitura lucida dopo sette stagion |
| F04 | What is DRS and how does it work? | hybrid | fallback | ✅ | 1.0 | The Drag Reduction System (DRS) was a feature that allowed drivers to reduce drag on their car's rear wing by opening a flap, increasing straight-line speed and |
| F05 | Who holds the F1 record for most pole positions in history? | hybrid | fallback | ✅ | 1.0 | Según la lista de récords de Fórmula 1 en Wikipedia, Michael Schumacher es el piloto con más pole positions en la historia, con un total de 68. |
