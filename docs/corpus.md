# Justificativa do corpus — FIA Formula 1 2026 Regulations

## O corpus

6 documentos oficiais da FIA, um por seção do regulamento de F1 2026 —
Geral, Esportivo, Técnico, Financeiro (Equipes), Financeiro (Fabricantes
de Power Unit) e Operacional — totalizando **590 páginas** e **4.288
chunks** indexados (muito acima do mínimo de 50.000 tokens/20 documentos
exigido pelo edital). Um único domínio coerente: as regras que governam a
Fórmula 1 na temporada 2026.

## 1. Por que esse corpus e o que ele representa como problema real

Regulamento de F1 não é um documento estático: cada seção carrega um
número de *issue* próprio e vive sendo revisado — a Seção C (Técnica), por
exemplo, já está na 18ª revisão (`iss_18`), enquanto a Seção A está na 2ª.
Equipes, jornalistas especializados, comissários e a própria FIA precisam
localizar rapidamente uma cláusula precisa (o cost cap, a massa mínima, a
tabela de pontos, a penalidade por um determinado excesso técnico) dentro
de centenas de páginas de texto legal denso e cheio de referências
cruzadas — errar a leitura tem consequência concreta (multa, penalização
esportiva, exclusão). É essencialmente o mesmo problema de qualquer
corpus de compliance/regulatório: alto custo de erro, alto volume de
texto, alta frequência de revisão. Um sistema RAG bem calibrado tem valor
real aqui — não é um corpus escolhido só por ser "sobre um hobby".

## 2. Por que RAG + busca web resolve algo que nenhum dos dois sozinho resolve bem

- **RAG sozinho** é preciso e citável para tudo que *está* no regulamento
  (massa mínima = 726kg, definição de Parc Fermé, tabela de pontos por %
  de distância completada) — mas o regulamento **não contém** fatos do
  mundo real que mudam a cada corrida ou a cada contrato: quem venceu o
  último GP, qual equipe um piloto specific corre em 2026, calendário,
  recordes históricos. Nada disso é, por natureza, texto regulatório.
- **Busca web sozinha** cobre bem esses fatos correntes, mas é ruim
  exatamente onde o RAG é forte: buscar "regras de DRS 2026" na web tende
  a trazer páginas desatualizadas ou artigos que ainda descrevem o DRS
  clássico — sem saber que a FIA **removeu o DRS da regulamentação 2026**
  em favor de um sistema de aerodinâmica ativa (achado real, verificado
  rodando o sistema — ver seção 3). Uma resposta só-web arrisca citar uma
  regra que já não existe.
- A combinação resolve o problema real: o corpus é a fonte de verdade
  para o que está nas regras (evita alucinação/desatualização da web em
  cima de texto legal), e a web é a fonte de verdade para o que
  estruturalmente nunca vai estar num documento de regras. Nenhum dos
  dois cobre o domínio completo sozinho.

## 3. Onde o sistema vai falhar e por que isso é esperado

- **Falso positivo de similaridade semântica.** O Retriever decide
  fallback por *score* de similaridade, não por "o chunk realmente
  responde a pergunta". Rodando o sistema real: a pergunta *"Who won the
  2025 Formula 1 Drivers Championship?"* recuperou chunks sobre **como os
  pontos são atribuídos** (vocabulário parecido: "championship", "points")
  com score acima do threshold — então o Retriever não acionou o fallback,
  mesmo o corpus não tendo a resposta. O Verificador pega esse caso (marca
  `grounded=False`), e o loop de reflexão tenta de novo, mas como o
  problema é de vocabulário e não de fraseado, a reformulação nem sempre
  resolve — o sistema pode terminar em `low_confidence=True` numa pergunta
  que, no fundo, deveria ter ido para a web. É uma falha estrutural do
  approach "similaridade de embedding como proxy de fallback", não um bug.
- **"Parece que está no domínio, mas não está."** A pergunta sobre DRS é o
  caso mais interessante: é sobre F1, sobre um sistema técnico, no
  vocabulário certo — e mesmo assim o corpus 2026 não define "DRS" porque
  o mecanismo foi substituído. Isso é exatamente o tipo de fronteira
  ambígua que um sistema ingênuo (que decide fallback só por palavra-chave
  "é sobre F1 → deve estar no corpus") erraria.
- **Tabelas numéricas fragmentadas pelo chunking.** A tabela de pontos por
  %-de-distância-completada é densa e pode ficar cortada entre chunks
  adjacentes; nos testes, isso gerou respostas parcialmente corretas
  (pontuação 0.5 no benchmark — acerta o "depende da distância completada"
  mas erra o valor exato de uma faixa). Esperado para qualquer chunking de
  tabelas em texto corrido.
- **Cláusulas discricionárias não têm gabarito único.** Perguntas como
  "qual a penalidade por causar uma colisão" não têm resposta numérica
  fixa — o regulamento deixa a critério dos comissários. O benchmark
  reflete isso com uma resposta esperada qualitativa, e a métrica de
  avaliação (LLM-as-judge, ver `avaliacao/`) é mais generosa nesses casos
  por design.
- **Deriva de idioma do modelo local.** Rodando o benchmark completo,
  algumas respostas a perguntas em inglês saíram em espanhol, francês,
  italiano ou holandês — mesmo com instrução explícita no prompt para
  responder no idioma da pergunta original. Tentei reforçar essa
  instrução (regra em destaque, repetida no início e no fim do prompt) e
  o resultado **piorou**: o modelo chegou a alucinar "minha pergunta está
  em espanhol" antes de responder em espanhol a uma pergunta em inglês. É
  uma limitação real e específica do `llama3.1:8b` local (não custou nada
  trocar de modelo para o desafio, mas fica registrado): prompts mais
  longos, principalmente após o loop de reflexão combinando contexto de
  corpus + web, aumentam a instabilidade de geração de um modelo pequeno.
  A instrução original (mais simples) ficou como está porque, empiricamente,
  performou melhor que a versão reforçada — ver `avaliacao/resultados_teste.md`
  para casos reais.
- **Corpus estático vs. regulamento vivo.** Qualquer índice construído
  hoje fica desatualizado no próximo boletim da FIA — limitação estrutural
  de qualquer vector store sem pipeline de re-ingestão agendada (fora do
  escopo deste desafio).

## 4. Por que esse corpus exercita todas as partes obrigatórias do desafio, incluindo o fallback

O corpus tem uma fronteira de domínio nítida e ao mesmo tempo genuinamente
difícil: é regulamento de F1 (um único tema coerente), mas regulamento não
contém resultados, contratos, calendário, marcas ou recordes — todas
perguntas legitimamente fora do que o texto pode responder, não fallbacks
"forçados" artificialmente. Isso permite montar as 10 perguntas de
fallback do benchmark (`avaliacao/dataset.json`, IDs `F01`-`F10`) com
confiança de que **o corpus realmente não contém a resposta** (requisito
explícito do edital), incluindo o caso DRS, que testa a decisão de
roteamento em vez de só testar "pergunta obviamente de outro assunto". Ao
mesmo tempo, o volume e a precisão legal do texto (590 páginas, cláusulas
numeradas, tabelas, definições formais) sustentam as 10 perguntas
respondíveis por RAG com gabarito verificável trecho a trecho — exercitando
também o Verificador (grounding real contra o texto) e o loop de reflexão
quando a primeira tentativa de resposta não bate com o contexto recuperado.
