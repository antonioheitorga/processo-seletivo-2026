# Avaliação — Benchmark do sistema RAG multiagente FIA 2026 F1 Regulations

## Dataset

`dataset.json` contém 20 pares pergunta/resposta esperada, divididos em:

- **validação** (10 pares) — usado durante o desenvolvimento para calibrar o
  `RETRIEVER_THRESHOLD` (ver `dev/retriever_threshold_probe.py`).
- **teste** (10 pares) — reservado para avaliação final. Os resultados
  reportados abaixo são deste conjunto.

Cada split tem 5 perguntas tipo `rag` (respondíveis pelo corpus regulatório)
e 5 perguntas tipo `fallback` (projetadas para **não** ter resposta no
corpus — fatos de temporada, resultados de corrida, dados fora do domínio de
F1 — e que devem acionar a busca web via Tavily).

## Metodologia de avaliação

O corpus é um conjunto de regulamentos (texto normativo, não uma base de
fatos/resultados), então a métrica não pode ser só "a resposta bate com o
texto do documento" — precisa avaliar duas coisas diferentes dependendo do
tipo de pergunta:

### Perguntas `rag`

```
pontuação = 0.7 × correctness + 0.3 × fonte_correta
```

- **correctness** — LLM-as-judge (mesmo modelo local, `llama3.1:8b`,
  `temperature=0`) compara a resposta gerada com a resposta esperada e
  atribui 0.0 (errada), 0.5 (parcial/vaga) ou 1.0 (correta). Não usamos
  correspondência exata de string porque o LLM pode parafrasear um número
  ou definição corretamente sem repetir o texto literal do artigo.
- **fonte_correta** — 1 se `fonte` resultante foi `corpus` ou `hybrid`
  (o sistema não deveria precisar de fallback puro para web numa pergunta
  respondível pelo próprio regulamento).

Por que não usar RAGAS/faithfulness clássico aqui: o corpus é jurídico-normativo
e as perguntas têm resposta objetiva e curta (números, prazos, definições)
— um LLM-judge comparando resposta-esperada vs. resposta-gerada é mais direto
e barato que decompor em claims para scoring de faithfulness, e captura o que
importa: "o sistema chegou ao fato certo, com a fonte certa".

### Perguntas `fallback`

```
pontuação = 1.0 se fonte ∈ {web, hybrid}, senão 0.0
```

Não avaliamos a exatidão factual da resposta web — ela depende do que a
Tavily retornar no momento da execução, é nao determinística e está fora do
controle do corpus/pipeline de ingestão. O que está sob teste neste desafio é
se o sistema **reconhece corretamente** que a pergunta está fora do escopo do
corpus e aciona a busca web em vez de tentar responder (ou pior, alucinar)
usando o regulamento.

## Calibração do threshold do retriever

O `RETRIEVER_THRESHOLD` (similaridade de cosseno mínima para um chunk contar
como hit) foi calibrado empiricamente, não escolhido a priori:

1. Threshold inicial de 0.70–0.72 deixava passar perguntas fora de escopo
   (ex.: "Who won the 2025 F1 Drivers' Championship?") porque a query
   reformulada usa vocabulário regulatório formal ("Championship", "points",
   "classification") que casa por similaridade lexical/temática com artigos
   do regulamento que *definem* esses conceitos — mesmo sem conter a resposta
   factual.
2. Rodando o split de validação, os scores de perguntas `rag` ficaram todos
   ≥ 0.799, e os de perguntas `fallback` ficaram todos ≤ 0.764. `0.78`
   separa os dois grupos sem erro nesse conjunto de calibração.
3. Esse valor é documentado em `.env.example` e `agents/retriever.py` com a
   margem observada.

**Isso é uma calibração empírica sobre um dataset pequeno, não uma garantia
geral** — ver seção de limitações abaixo.

## Como rodar

```bash
python3 -m evaluation.run_benchmark --split validacao
python3 -m evaluation.run_benchmark --split teste
```

Cada execução roda o pipeline completo (`orchestration.orchestrator.run`)
para cada pergunta — isso também gera um trace JSON em `traces/` por
pergunta (arquivo `bench-{id}.json`), cobrindo a exigência de observabilidade
com casos reais de RAG e de fallback.

Resultados são salvos em `evaluation/results/resultados_{split}.json` (dados
completos) e `.md` (tabela resumida).

## Resultados — conjunto de teste

Ver [`results/resultados_teste.md`](results/resultados_teste.md) para a
tabela completa (pergunta, fonte recuperada, RAG ou fallback, resposta
gerada, pontuação).

| Métrica | Valor |
|---|---|
| Pontuação média geral | 0.83 |
| Pontuação média — perguntas RAG | 0.86 |
| Pontuação média — perguntas fallback | 0.80 |
| Fallback acionado corretamente | 4/5 |

### Falhas observadas e por que são esperadas

- **`test-rag-02`** (pontuação 0.3) — pergunta sobre pontos do 2º colocado.
  O retriever recuperou o artigo que *descreve* a atribuição de pontos
  (score 0.86) mas não o chunk com a *tabela numérica* de pontos por posição
  — provavelmente porque o chunking separou o texto descritivo da tabela em
  chunks diferentes, e o texto descritivo tem maior similaridade semântica
  com a pergunta em linguagem natural do que uma tabela numérica densa. O
  gerador **não alucinou** um número — respondeu honestamente que a tabela
  não estava no contexto recuperado. É uma falha de recall do retriever, não
  de fundamentação da resposta.
- **`test-fb-04`** (pontuação 0.0) — pergunta sobre escalação de pilotos para
  2027. A query reformulada teve similaridade suficiente (0.81) com trechos
  sobre a definição de "Championship" para passar o threshold, então o
  sistema não acionou o fallback web. Mesmo assim, o gerador **não
  alucinou**: respondeu que não havia informação disponível no contexto.
  O `fonte` reportado (`corpus`) está tecnicamente errado (deveria ter sido
  `web`), mas o comportamento anti-alucinação (dupla camada, ver
  `docs/architecture.md`) segurou a resposta.

Essas duas falhas ilustram o mesmo fenômeno de fundo: um corpus regulatório
usa o mesmo vocabulário para *definir* conceitos (Championship, pontos,
classificação) que para *aplicar* esses conceitos a fatos específicos — e um
retriever baseado só em similaridade de embeddings não distingue as duas
coisas de forma confiável. Ver `docs/justificativa_corpus.md`, item 3, para a
discussão completa dessa limitação estrutural.
