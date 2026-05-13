# TODO — Sprint 3: Agente Retriever

- [x] Atualizar branch `develop` local (`git checkout develop && git pull origin develop`)
- [x] Mapear estrutura do projeto e localizar padrões de agentes existentes
- [x] Implementar `agents/retriever.py`:
  - [x] Busca vetorial no ChromaDB persistente
  - [x] Leitura de `RETRIEVER_THRESHOLD` do `.env`
  - [x] Retorno em formato `retriever_result`
  - [x] Inclusão de `trace` no padrão dos agentes existentes
- [x] Criar testes unitários para o retriever
- [x] Executar testes para validar implementação
- [x] Atualizar documentação mínima (README) sobre o novo agente
