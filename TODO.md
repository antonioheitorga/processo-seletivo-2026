# TODO - Refatoração para Arquitetura Multiagente (nós + decisões)

- [x] Mapear e refatorar o orquestrador para incluir nó explícito de decisão (`router/planner`)
- [x] Criar agente `judge/verifier` para validação pós-geração
- [x] Atualizar grafo para fluxo multiagente: `reformulator -> retriever -> router -> (web_searcher|generator) -> judge -> END`
- [x] Expandir `GraphState` com campos de decisão (`route_decision`, `judge_result`, `needs_revision`)
- [x] Atualizar `tests/test_orchestrator.py` para cobrir roteamento e validação do judge
- [x] Atualizar documentação em `docs/architecture.md` para refletir a nova arquitetura
- [ ] Executar testes de caminho crítico (orchestrator + contratos básicos dos agentes)
- [ ] Consolidar resultado técnico e status de testes
