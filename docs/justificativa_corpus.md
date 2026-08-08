# Justificativa do corpus — FIA 2026 Formula 1 Regulations

## O corpus

6 documentos oficiais da FIA, o Regulamento da Fórmula 1 para a temporada 2026,
separados por seção (`dados/corpus/`):

| Seção | Conteúdo | Páginas aprox. |
|---|---|---|
| A — General Provisions | Definições, pontuação, campeonatos | ~60 |
| B — Sporting | Procedimentos de corrida, qualificação, penalidades | ~130 |
| C — Technical | Especificações técnicas do carro | ~180 |
| D — Financial (F1 Teams) | Cost Cap, reporting | ~60 |
| E — Financial (PU Manufacturers) | Regras financeiras de fabricantes de motor | ~60 |
| F — Operational | Procedimentos operacionais | ~40 |

4.288 chunks indexados após ingestão — muito acima do mínimo de 20
documentos/50.000 tokens exigido. Um único domínio (regulamentação da F1
2026), sem mistura de assuntos.

## 1. Por que esse corpus e o que ele representa como problema real

Regulamentos técnicos longos e densos (aqui, ~500 páginas somadas) são um
problema real e recorrente: equipes de F1, jornalistas especializados,
comissários e até fãs avançados precisam localizar rapidamente uma cláusula
específica ("qual é a massa mínima do carro na qualifying?", "quanto é o Cost
Cap?") sem ler o documento inteiro. É o mesmo problema de qualquer regulação
técnica/jurídica de acesso ao público (normas ISO, regulamentos financeiros,
contratos-padrão): a informação existe, é autoritativa, mas está enterrada em
centenas de páginas de linguagem formal e cross-references entre artigos.

Escolhi esse corpus especificamente (em vez de, por exemplo, documentação de
software) porque ele tem uma propriedade que muitos corpora técnicos não têm:
**o regulamento define conceitos que ele mesmo não resolve com fatos**. Ele
define "Championship" e como pontos são atribuídos, mas não diz quem venceu.
Isso cria uma fronteira nítida e natural entre "isso está no documento" e
"isso não está e nunca vai estar", que é exatamente o que o desafio pede para
exercitar o fallback — sem precisar inventar perguntas artificialmente fora
do tema.

## 2. Como RAG + busca web resolve algo que nenhum dos dois sozinho resolve bem

- **RAG sozinho** garante precisão e rastreabilidade da fonte quando a
  resposta está no regulamento (cita o artigo, o trecho exato), mas é cego a
  qualquer coisa publicada depois do corte do documento ou fora do escopo
  regulatório — resultados de corrida, contratações de pilotos, notícias.
  Um sistema só-RAG nesse domínio, ao ser perguntado "quem venceu o campeonato
  de 2025", só tem duas saídas ruins: alucinar uma resposta usando o
  conhecimento paramétrico do LLM (sem fonte, sem rastreabilidade) ou recusar
  tudo que não está no documento, mesmo quando a busca web resolveria
  trivialmente.
- **Busca web sozinha** encontra fatos de temporada, mas é ruim exatamente
  onde o regulamento é bom: buscar "o que diz o Artigo C4.1 sobre massa
  mínima" na web devolve blogs e resumos de terceiros, não o texto normativo
  exato — sem garantia de estar citando a versão vigente (Issue 18, maio de
  2026) do documento.
- **A combinação** resolve o caso de uso real de quem consulta esse tipo de
  documento: primeiro tenta a fonte autoritativa (o regulamento), e só
  recorre à web quando a pergunta é sobre fato de mundo real que o documento
  estruturalmente não pode conter. O corpus FIA 2026 é bom para testar essa
  combinação porque a fronteira entre os dois casos é conceitualmente clara
  (regra vs. fato), mesmo que, como mostrado no benchmark
  (`evaluation/README.md`), a fronteira **não seja trivial de detectar
  automaticamente** por similaridade de embeddings — o que é o próprio ponto
  de interesse do desafio.

## 3. Onde o sistema vai falhar e por que isso é esperado

O benchmark (`evaluation/results/resultados_teste.md`) já expõe duas classes
de falha reais, não hipotéticas:

1. **Falso negativo de fallback** — perguntas fora de escopo mas que
   compartilham vocabulário regulatório ("Championship", "points",
   "classification") podem pontuar acima do threshold de similaridade e não
   acionar a busca web, mesmo quando o corpus não contém a resposta factual.
   Isso é esperado porque o retriever mede similaridade semântica de
   superfície (embeddings), não se a pergunta é *respondível* pelo texto —
   um regulamento que *define* um conceito extensivamente vai sempre ter alta
   similaridade com perguntas *sobre* esse conceito, mesmo que a resposta
   específica não esteja lá.
2. **Recall incompleto em conteúdo tabular** — perguntas sobre valores em
   tabelas (ex.: pontos por posição) podem recuperar o artigo descritivo
   correto mas não o chunk com a tabela numérica, se o chunking os separar.
   É esperado porque o chunking é baseado em tamanho/estrutura de texto, não
   em unidades semânticas completas (uma tabela + seu parágrafo de contexto
   podem cair em chunks diferentes).

Em ambos os casos, a rede de segurança anti-alucinação (dupla camada:
Orquestrador + Gerador, ver `docs/architecture.md`) impede que o sistema
*invente* uma resposta — ele responde "não tenho essa informação no
contexto" em vez de chutar. A falha é de **roteamento/recall**, não de
**fundamentação** — o que é a falha aceitável neste desenho: preferimos um
sistema que às vezes erra a fonte, mas nunca inventa fatos.

Esse tipo de falha é esperado *dado o corpus escolhido* porque regulamentos
são texto denso, cheio de definições circulares e tabelas, exatamente o
cenário em que a distinção entre "define o conceito" e "responde o fato"
colapsa para um retriever puramente vetorial — diferente de, por exemplo, um
corpus de FAQ, onde pergunta e resposta têm estrutura muito mais alinhada.

## 4. Por que esse corpus exercita todas as partes obrigatórias do desafio

- **RAG puro** — perguntas técnicas/normativas (massa mínima, Cost Cap,
  pontuação, procedimentos) têm resposta objetiva no corpus, permitindo
  testar recuperação + geração fundamentada com resposta verificável.
- **Fallback por design** — a natureza do documento (regra, não fato) cria um
  conjunto natural e abundante de perguntas sem resposta possível no corpus
  (resultados, contratações, notícias, dados fora do domínio de F1),
  suficiente para as 10 perguntas de fallback exigidas sem forçar perguntas
  artificiais.
- **Múltiplos agentes com papéis distintos** — o corpus tem seções com
  vocabulário e granularidade diferentes (técnico vs. financeiro vs.
  esportivo), o que faz o Reformulador (adequar a query ao registro formal do
  documento) e o Retriever (avaliar confiança por seção) terem trabalho real
  a fazer, não apenas repassar a pergunta adiante.
- **Observabilidade e avaliação** — por ter respostas objetivas e
  verificáveis (números, prazos, definições), o corpus permite escrever um
  benchmark com resposta esperada exata e um LLM-judge determinístico,
  evitando avaliação subjetiva de "a resposta parece boa".
