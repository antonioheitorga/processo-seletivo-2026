# TODO - Refatoração para Arquitetura Multiagente (nós + decisões)

- [x] Mapear e refatorar o orquestrador para incluir nó explícito de decisão (`router/planner`)
- [x] Criar agente `judge/verifier` para validação pós-geração
- [x] Atualizar grafo para fluxo multiagente: `reformulator -> retriever -> router -> (web_searcher|generator) -> judge -> END`
- [x] Expandir `GraphState` com campos de decisão (`route_decision`, `judge_result`, `needs_revision`)
- [x] Atualizar `tests/test_orchestrator.py` para cobrir roteamento e validação do judge
- [x] Atualizar documentação em `docs/architecture.md` para refletir a nova arquitetura
- [x] Executar testes de caminho crítico (orchestrator + contratos básicos dos agentes)
- [x] Consolidar resultado técnico e status de testes

# TODO - Requisitos do desafio LAPES (checklist final)

- [x] Ambiente configurado (venv, deps, Ollama, .env) e pipeline de ingestão rodando do zero
- [x] Repositório git próprio do projeto, rastreando o fork oficial (`origin/develop`)
- [x] Calibração empírica do `RETRIEVER_THRESHOLD` (0.78) com evidência documentada
- [x] Justificativa do corpus nos 4 pontos exigidos (`docs/justificativa_corpus.md`)
- [x] Benchmark com 20 pares (10 validação + 10 teste, 5+5 fallback por split) (`evaluation/dataset.json`)
- [x] Metodologia de avaliação documentada (`evaluation/README.md`)
- [x] Resultados do conjunto de teste em tabela (`evaluation/results/resultados_teste.md`)
- [x] Traces de execução versionados, incluindo casos de fallback (`traces/bench-*.json`)
- [ ] Commit convencional das mudanças desta sessão e push para o fork
