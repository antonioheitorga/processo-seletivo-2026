# Avaliação — benchmark do sistema

Módulo de avaliação exigido pelo edital: 20 pares pergunta/resposta
gerados a partir do corpus real (FIA F1 2026 Regulations), divididos em
validação e teste, rodados contra o sistema completo (não mockado).

## Dataset (`dataset.json`)

20 perguntas, cada uma com:

```json
{
  "id": "C01",
  "pergunta": "...",
  "resposta_esperada": "...",
  "espera_fallback": false,
  "secao_esperada": "general_provisions",
  "split": "val"
}
```

- **10 perguntas `C01`-`C10`** (`espera_fallback=false`): respondíveis
  pelo corpus. As respostas esperadas foram extraídas rodando o Retriever
  de verdade contra o vector store e lendo os trechos recuperados — não
  são fatos de memória, são gabaritos verificados linha a linha contra o
  texto oficial das regulamentações.
- **10 perguntas `F01`-`F10`** (`espera_fallback=true`): fora do escopo
  regulatório por design (resultados de corrida, contratos de piloto,
  calendário, recordes, branding) — o corpus estruturalmente não contém
  essas respostas. Ver [`docs/corpus.md`](../docs/corpus.md) para a
  justificativa completa, incluindo o caso `F04` (DRS), que testa a
  fronteira de roteamento em vez de só testar um assunto óbvio.
- **Split**: 10 perguntas em `val` (5 corpus + 5 fallback), 10 em `test`
  (5 corpus + 5 fallback). `val` foi usado para depurar threshold do
  Retriever e o prompt do Verificador durante o desenvolvimento; os
  resultados **reportados oficialmente são só os de `test`**
  (`resultados_teste.csv` / `.md`), conforme exigido pelo edital.

## Métrica (`metrica.py`)

**LLM-as-judge de correção factual** (0.0 / 0.5 / 1.0), usando o mesmo
modelo do resto do sistema (`llama3.1:8b` via Ollama, temperatura 0.0):
compara a resposta gerada com o gabarito e pontua se ela captura os fatos
corretos, captura parcialmente, ou está errada/contraditória.

Por que essa métrica e não outra — justificativa completa no topo de
[`metrica.py`](metrica.py). Resumo: *exact match* falha porque os
gabaritos são multi-cláusula e parafraseáveis; *similaridade de
embeddings* foi descartada porque não penaliza bem um número trocado
("25 pontos" vs "18 pontos" ficam semanticamente próximos mesmo estando
errados) — e nesse domínio regulatório o número certo é exatamente o que
mais importa acertar. Faz mais sentido pro domínio um julgamento de
correção factual explícito.

Para as perguntas de fallback, o "gabarito" é conceitual (a resposta não
deveria vir do corpus) — a pontuação nesses casos reflete se a resposta
final é razoável dado o que a busca web trouxe, não um fato numérico
específico.

## Rodando o benchmark

```bash
python3 -m avaliacao.run_eval --split all    # 20 perguntas (val + test)
python3 -m avaliacao.run_eval --split test   # só o conjunto reportado
```

Cada execução roda o grafo completo de verdade (todos os 5 agentes, com
loop de reflexão quando aplicável) — nenhuma parte é mockada. Requer
Ollama rodando localmente com `llama3.1:8b` e `nomic-embed-text`, o
vector store já construído (`dados/pipeline.py`) e `TAVILY_API_KEY`
configurada no `.env` para as perguntas de fallback.

Gera, por split:

- `resultados_{split}.csv` — uma linha por pergunta: id, fonte
  recuperada, RAG ou fallback, se o roteamento bateu com o esperado,
  resposta gerada, pontuação, justificativa da pontuação, se a resposta
  foi considerada fundamentada pelo Verificador.
- `resultados_{split}.md` — a mesma coisa em tabela legível, com o
  resumo agregado (pontuação média, roteamento correto) no topo.

## Resultados

Ver [`resultados_teste.md`](resultados_teste.md) para a tabela oficial
(conjunto de teste). [`resultados_validacao.md`](resultados_validacao.md)
existe só para referência do processo de desenvolvimento.

Se só o critério de pontuação mudar (não o comportamento do sistema),
`python3 -m avaliacao.rescore` repontua as respostas já salvas nos CSVs sem
rodar o pipeline de novo.

## Traces de exemplo (`traces_exemplo/`)

`traces/` (saída em runtime de qualquer execução) está no `.gitignore` —
então uma amostra das 20 execuções do benchmark (10 RAG + 10 fallback, ver
`fallback.acionado` em cada arquivo) foi copiada para
[`traces_exemplo/`](traces_exemplo/), que **não** é ignorado, para
satisfazer o requisito do edital de entregar traces reais no repositório,
incluindo casos que acionaram o fallback.

## Limitações observadas rodando o benchmark de verdade

- **Roteamento nem sempre acerta 10/10.** O Reformulador reescreve a query
  em vocabulário regulatório formal, o que às vezes empurra o score de
  similaridade contra um chunk genérico acima do threshold mesmo quando o
  corpus não tem a resposta — corrigido parcialmente fazendo toda
  retentativa também buscar na web (`orchestration/orchestrator.py`), mas
  1-2 das 10 perguntas de fallback ainda podem cair como `roteamento_ok=False`
  numa execução específica. Ver `docs/corpus.md`, seção 3.
- **Deriva de idioma do modelo local.** Algumas respostas a perguntas em
  inglês saíram em espanhol/italiano/holandês/francês — limitação do
  `llama3.1:8b` local em prompts longos (loop de reflexão + contexto
  corpus+web), não um bug de código. Documentado em `docs/corpus.md`.
- **Julgamento do LLM-as-judge nem sempre segue o critério à risca** (ex:
  penalizou uma resposta correta por não achar o time literal do gabarito
  mesmo com instrução explícita para aceitar qualquer resposta plausível).
  Mesma classe de limitação do Verificador — modelos de 8B parâmetros não
  seguem instruções complexas com 100% de consistência.

Nenhum desses pontos foi escondido ou teve o resultado "arrumado" —
ficaram como saíram da execução real, porque documentar onde o sistema
falha faz parte do que o desafio pede.
