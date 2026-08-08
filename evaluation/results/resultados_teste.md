# Resultados — split teste

| ID | Pergunta | Tipo | Fonte esperada | Fonte obtida | Fonte recuperada | Pontuação |
|---|---|---|---|---|---|---|
| test-rag-01 | What is the minimum car mass, before Nominal Tyre Mass, in F1 sessions other tha | rag | corpus | corpus | fia_2026_f1_regulations_-_section_c_technical_-_iss_18_-_202 | 1.0 |
| test-rag-02 | How many points does the driver finishing 2nd in a full-distance Grand Prix rece | rag | corpus | corpus | fia_2026_f1_regulations_-_section_a_general_provisions_-_iss | 0.3 |
| test-rag-03 | How long is the first segment of Sprint Qualifying (SQ1) and how many cars are e | rag | corpus | corpus | fia_2026_f1_regulations_-_section_b_sporting_-_iss_06_-_2026 | 1.0 |
| test-rag-04 | What does the Cost Cap in the F1 Teams Financial Regulations limit, and what fre | rag | corpus | corpus | fia_2026_f1_regulations_-_section_d_financial_-_f1_teams_-_i | 1.0 |
| test-rag-05 | During which two types of sessions does the higher Minimum Mass of 726kg (plus N | rag | corpus | corpus | fia_2026_f1_regulations_-_section_c_technical_-_iss_18_-_202 | 1.0 |
| test-fb-01 | Which team won the 2025 Formula 1 Constructors' Championship? | fallback | web | web | https://www.formulaonehistory.com/results; https://en.wikipe | 1.0 |
| test-fb-02 | Who is the current CEO of Formula 1 (Liberty Media / Formula One Group)? | fallback | web | web | https://www.libertymedia.com/investors/financial-information | 1.0 |
| test-fb-03 | What is the population of Brazil in 2026? | fallback | web | web | https://api.fia.com/system/files/documents/fia_2026_f1_regul | 1.0 |
| test-fb-04 | Which driver lineup changes were announced for the 2027 Formula 1 season? | fallback | web | corpus | fia_2026_f1_regulations_-_section_a_general_provisions_-_iss | 0.0 |
| test-fb-05 | What was the weather like during the 2024 Abu Dhabi Grand Prix race? | fallback | web | web | https://en.wikipedia.org/wiki/2024_Abu_Dhabi_Grand_Prix; htt | 1.0 |
