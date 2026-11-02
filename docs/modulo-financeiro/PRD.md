# PRD — Módulos 5 e 6: Planejamento Físico-Financeiro e Financeiro

**Versão:** 1.0 | **Data:** 2026-11-02
**Escopo:** Módulo 5 (cronograma + medição física) e Módulo 6 (contas a pagar, fluxo de caixa, Curva S)
**Fase:** MVP V2 — ver [PRD principal](../PRD.md) §6
**Documentos irmãos:** [ESPEC](ESPEC.md) · [Dicionário de Dados](DICIONARIO-DE-DADOS.md) · [SPRINTS](SPRINTS.md)

---

## Por que os dois módulos juntos

O PRD principal separa Módulo 5 (planejamento) de Módulo 6 (financeiro). Na prática eles não
se separam: a **Curva S** compara o planejado no tempo com o executado, e o planejado no tempo
é o cronograma do Módulo 5. A **liberação de faturamento** depende da medição física, que também
é Módulo 5, mas gera título a receber, que é Módulo 6.

Documentar um sem o outro produziria um módulo financeiro sem eixo temporal — ou seja, sem a
funcionalidade que o Carlos pediu: saber **se a obra está estourando antes de acabar**.

---

## 1. Problema

Carlos sabe quanto orçou e sabe quanto está no extrato. Não sabe o que está no meio: quanto
já gastou **nesta fase**, se o gasto acompanha o avanço, e se a obra vai fechar no azul.

Hoje o Obrax resolve a primeira metade do ciclo — orçar com EAP, Curva ABC e markup. A segunda
metade, comparar o orçado com o que efetivamente aconteceu, não existe. Sem ela o orçamento é
um documento de venda, não um instrumento de controle.

**O sintoma que o PRD principal já registra:** "já teve prejuízo em 2 obras por estouro de
orçamento não detectado a tempo". Detectar a tempo é o objetivo deste módulo.

---

## 2. Objetivos

| ID | Objetivo | Como se mede |
|---|---|---|
| **OBJ-F01** | Carlos sabe, a qualquer momento, quanto cada fase da obra já custou contra o orçado | A tela de orçado × realizado existe e cobre 100% das fases do orçamento aprovado |
| **OBJ-F02** | O estouro é detectado durante a obra, não no fechamento | Alerta dispara quando realizado + comprometido ultrapassa o orçado da fase |
| **OBJ-F03** | O avanço físico e o avanço financeiro são comparáveis no tempo | Curva S com as três séries: planejado, físico executado, financeiro realizado |
| **OBJ-F04** | O faturamento ao cliente sai da medição, não de estimativa | Toda medição aprovada gera título a receber com valor derivado do % medido |
| **OBJ-F05** | Toda despesa da obra é rastreável a uma fase e a um documento | Nenhuma despesa pode ser gravada sem fase; anexo de NF disponível em todas |

---

## 3. Escopo

### Dentro

**Módulo 5 — Planejamento físico-financeiro**
- Cronograma físico-financeiro derivado do orçamento aprovado: fase × período, com valor e
  percentual planejados
- Ajuste manual da distribuição por período
- Medição de avanço físico por fase e por período
- Aprovação de medição, que libera o faturamento correspondente

**Módulo 6 — Financeiro**
- Plano de contas simples (categorias financeiras por empresa)
- Lançamento manual de despesa, com **apropriação obrigatória a uma fase**
- Anexo de nota fiscal, reaproveitando o GED que já existe
- Parcelamento de despesa
- Registro de pagamento
- Contas a receber geradas por medição aprovada
- Orçado × realizado por fase, com alerta de estouro
- Curva S
- Fluxo de caixa previsto × realizado
- Exportação em CSV

### Fora — não-escopo explícito

Cada item abaixo é uma funcionalidade que alguém lendo este documento poderia achar que está
incluída. **Não está.** Implementar qualquer uma sem decisão nova é escopo inventado.

| Fora | Por quê | Quando reconsiderar |
|---|---|---|
| **Tributos, retenções (INSS/ISS/IRRF) e regime tributário** | O objetivo é controle gerencial de custo, não apuração contábil | Quando o número precisar bater com a contabilidade |
| **NF-e: chave de acesso, XML, validação na SEFAZ** | Puxa integração com SEFAZ ou provedor e vira projeto próprio | Fase 3 do PRD principal |
| **Conciliação bancária e importação de extrato (OFX/CSV)** | Exige tela de conciliação e regras de casamento | Quando o volume de lançamento manual incomodar |
| **Open Finance** | Fase 3 do PRD principal | — |
| **Pagamento parcial de um título** | Mantém o modelo de status simples (previsto → pago) | Se aparecer na prática do beta |
| **Régua de cobrança e gestão de inadimplência** | Contas a receber aqui é consequência da medição, não um módulo de cobrança | V3 |
| **DRE, balanço e centro de custo fora da obra** | O eixo de análise deste módulo é a obra, não a empresa | Quando houver demanda de sócio/contador |
| **Multi-moeda** | Público-alvo opera em BRL | — |
| **Módulo 4 (Compras) e o fluxo de cotação/RFQ** | Escopo negativo do V1 e não é pré-requisito deste módulo | Depois deste |

### Dependências de escopo

| Depende de | Estado | Impacto se não existir |
|---|---|---|
| Módulo 2 (orçamento com EAP e fases) | ✅ existe | — |
| GED (anexo de documento com tipo `nota_fiscal`) | ✅ existe | — |
| **US-16 — versionamento de orçamento** | ⬜ não implementado | Ver RN-F03 ([§4](#4-regras-de-negócio)). O desenho sobrevive sem ele, mas a reconciliação de fases só é exercitada quando houver revisão |
| **US-03 — cadastro de fornecedor** | ⬜ não implementado | Ver RN-F09 ([§4](#4-regras-de-negócio)). Despesa usa nome livre até existir |
| **Módulo 4 — Compras** | ⬜ fora de escopo | Nenhum. A despesa nasce manual por decisão |

---

## 4. Regras de negócio

<a id="rn-f01"></a>
**RN-F01 — O orçado é sempre o da versão aprovada.**
Comparação de custo usa a versão do orçamento cujo status é `aprovado`. Obra sem orçamento
aprovado não tem orçado, e as telas de comparação mostram estado vazio explicando isso — não
zero, que seria indistinguível de "orçado é zero".

<a id="rn-f02"></a>
**RN-F02 — Toda despesa pertence a exatamente uma fase.**
Não existe despesa "da obra" sem fase. É o que torna o orçado × realizado possível, e é o
critério que o PRD principal chama de "apropriação obrigatória de despesas por fase". Despesa
que não se encaixa numa fase de execução vai para uma fase de administração da própria obra,
criada no orçamento.

<a id="rn-f03"></a>
**RN-F03 — A fase é uma identidade estável da obra, não uma linha de versão de orçamento.**
Criar a revisão 2 de um orçamento clona os itens e gera IDs novos. Se a despesa apontasse para
o item da versão, toda revisão orfanaria o histórico financeiro da obra. A fase, para efeito
financeiro, é uma entidade própria da obra, criada na primeira aprovação e reconciliada por
código a cada nova versão aprovada. Consequência aceita e alternativas descartadas em
[ESPEC §4](ESPEC.md).

<a id="rn-f04"></a>
**RN-F04 — Comprometido conta como gasto para efeito de alerta.**
Uma despesa com vencimento futuro e ainda não paga já consumiu orçamento — o compromisso
existe. O alerta de estouro considera **realizado + comprometido**, e a tela mostra os dois
separados, porque são decisões diferentes: realizado não se desfaz, comprometido ainda pode ser
renegociado.

<a id="rn-f05"></a>
**RN-F05 — Medição é cumulativa e monotônica por fase.**
O percentual medido de uma fase é acumulado desde o início da obra, não o avanço do período. Uma
medição nova não pode registrar percentual menor que a anterior aprovada da mesma fase — avanço
físico não retrocede. Correção de medição aprovada se faz por medição de ajuste, com
justificativa, nunca por edição.

<a id="rn-f06"></a>
**RN-F06 — Medição aprovada é imutável e gera título a receber.**
Aprovar a medição é o evento que libera o faturamento.

Cada fase é ponderada pela sua **participação no orçamento**, e só então multiplicada pelo
contrato:

```
peso_fase   = obra_fase.valor_orcado / Σ valor_orcado das fases ativas
avanço_fase = % medido acumulado − % já faturado da fase
valor       = Σ (avanço_fase × peso_fase) × obra.valor_contrato
```

> **Por que a ponderação não é detalhe.** A primeira redação desta regra dizia
> "`(% medido − % faturado) × valor do contrato`, por fase, somado". Numa obra com 5 fases
> avançando 20% cada, aquela fórmula liberaria `5 × 0,20 × contrato` = **100% do contrato com
> 20% da obra executada**. O erro foi encontrado na simulação de execução, não na revisão por
> leitura, e é por isso que o CA-F04.6 existe.

Depois de aprovada, a medição não é editável — o par medição/título é a trilha de aceite com o
cliente.

**Obra sem `valor_contrato`** (a coluna é nullable no schema): a medição é aprovável, mas não
gera título, e a tela avisa que não há contrato para faturar. Gerar título zero seria pior —
sumiria em silêncio no contas a receber.

<a id="rn-f07"></a>
**RN-F07 — O cronograma distribui o orçado no tempo e precisa fechar em 100%.**
A soma dos percentuais planejados de uma fase ao longo dos períodos é exatamente 100%. O sistema
recusa salvar um cronograma que não fecha, com a diferença explícita na mensagem.

<a id="rn-f08"></a>
**RN-F08 — Parcelar gera títulos independentes.**
Uma despesa parcelada vira N despesas ligadas por um identificador de grupo, cada uma com seu
vencimento e seu status. Pagar a parcela 2 não altera a 1. A soma das parcelas é igual ao valor
original — o sistema ajusta a última parcela para absorver o arredondamento.

<a id="rn-f09"></a>
**RN-F09 — Fornecedor é texto livre até o Módulo 1 ter cadastro.**
A US-03 (cadastro de fornecedor) não foi implementada. A despesa guarda o nome do fornecedor
como texto e já tem a coluna de vínculo preparada, nullable. Quando a US-03 existir, uma
migration de reconciliação liga os existentes por documento ou por nome exato, e os ambíguos
ficam para resolução manual.

<a id="rn-f10"></a>
**RN-F10 — Precisão financeira segue a regra do projeto.**
`Decimal` no Python, `NUMERIC(18,2)` para valores e `NUMERIC(7,4)` para percentuais, no banco.
`float` é proibido em qualquer cálculo. Percentuais são frações (0,1500 = 15%), nunca inteiros
de 0 a 100 — a conversão para exibição é responsabilidade da camada de apresentação.

<a id="rn-f11"></a>
**RN-F11 — O financeiro da obra nunca aparece no portal do cliente.**
Nenhum dado deste módulo é exposto em rota de portal. O cliente vê o orçamento que lhe foi
apresentado e a medição que assinou — nunca custo, margem, fornecedor ou despesa. É a mesma
fronteira que o PRD principal já estabelece ("cliente não vê margens").

---

## 5. User Stories

> **Sobre a numeração.** Este módulo usa o prefixo `US-F` em vez de continuar a série `US-NN`
> do PRD principal. O motivo é concreto: a série principal já foi renumerada uma vez entre o PRD
> e o SPRINTS, e três US (Fornecedor, Parceiros, Templates de e-mail) se perderam no processo.
> Um prefixo por módulo torna a colisão impossível.

### Módulo 5 — Planejamento

#### US-F01 — Gerar o cronograma a partir do orçamento aprovado
**MH · M**

Como Carlos, quero gerar um cronograma distribuindo o orçamento aprovado em períodos, para ter
uma linha de base contra a qual comparar o avanço.

- **CA-F01.1** — Com um orçamento aprovado, o sistema propõe um cronograma com uma linha por fase
  e colunas por período, a partir da data de início e da previsão de fim da obra.
- **CA-F01.2** — A periodicidade é escolhida na criação: semanal ou mensal.
- **CA-F01.3** — A distribuição inicial proposta é linear ao longo dos períodos da obra.
- **CA-F01.4** — Obra sem orçamento aprovado não permite criar cronograma, e a mensagem diz o
  que falta.
- **CA-F01.5** — Só existe um cronograma ativo por obra.

#### US-F02 — Ajustar a distribuição do cronograma
**MH · M**

Como Carlos, quero ajustar quanto de cada fase acontece em cada período, porque obra não avança
linearmente.

- **CA-F02.1** — Editar o percentual de uma célula fase × período recalcula o valor planejado
  daquela célula e os totais de linha e coluna.
- **CA-F02.2** — Salvar com uma fase que não soma 100% é recusado, e a mensagem mostra a fase e a
  diferença (RN-F07).
- **CA-F02.3** — O total planejado do cronograma é igual ao custo direto da versão aprovada.
- **CA-F02.4** — O cronograma fica bloqueado para edição depois da primeira medição aprovada;
  mudar a linha de base depois disso invalidaria a comparação.

#### US-F03 — Registrar medição de avanço físico
**MH · M**

Como Carlos, quero registrar o percentual executado de cada fase num período, para medir o
avanço real da obra.

- **CA-F03.1** — A medição é criada para um período do cronograma e nasce como rascunho.
- **CA-F03.2** — Para cada fase, informo o percentual acumulado executado; o sistema mostra o
  acumulado da medição anterior ao lado.
- **CA-F03.3** — Percentual menor que o da medição anterior aprovada é recusado (RN-F05).
- **CA-F03.4** — Percentual maior que 100% é recusado.
- **CA-F03.5** — Enquanto rascunho, a medição é editável e não gera efeito nenhum.

#### US-F04 — Aprovar medição e liberar faturamento
**MH · M**

Como Carlos, quero aprovar a medição, para que o valor correspondente vire título a receber.

- **CA-F04.1** — Aprovar grava a medição como imutável e registra quem aprovou e quando.
- **CA-F04.2** — A aprovação gera um título a receber com o valor calculado conforme RN-F06.
- **CA-F04.3** — A medição aprovada aparece no histórico da obra com o valor liberado.
- **CA-F04.4** — Tentar editar medição aprovada devolve erro explicando o caminho (medição de
  ajuste).
- **CA-F04.5** — **Numa obra com `valor_contrato`**, medição cuja soma dá valor zero ou negativo
  não é aprovável. A ressalva não é redundante: obra **sem** contrato cai no CA-F04.7 e é
  aprovável, e tratar "sem contrato" como "valor zero" recusaria exatamente a aprovação que o
  CA-F04.7 exige.
- **CA-F04.6** — Numa obra com 5 fases de peso igual, todas medidas a 20%, a medição libera
  **20%** do valor do contrato — não 100%. É o caso que separa a fórmula ponderada da ingênua.
- **CA-F04.7** — Obra sem `valor_contrato` aprova a medição sem gerar título, e avisa. No banco
  isso é `medicao.aprovada_em` preenchido com `valor_liberado` **nulo** e nenhuma linha em
  `recebimento` — ver [Dicionário §4.7](DICIONARIO-DE-DADOS.md#47-medicao), que já teve um `CHECK`
  proibindo esse estado.

### Módulo 6 — Financeiro

#### US-F05 — Gerenciar categorias financeiras
**MH · P**

Como Carlos, quero categorizar as despesas (material, mão de obra, serviço, equipamento,
administrativo), para analisar o custo por natureza além de por fase.

- **CA-F05.1** — A empresa começa com um conjunto padrão de categorias, criado no primeiro acesso
  ao módulo.
- **CA-F05.2** — Posso criar, renomear e desativar categoria.
- **CA-F05.3** — Categoria com despesa vinculada não pode ser excluída, só desativada.
- **CA-F05.4** — Categoria desativada não aparece na criação de despesa nova, mas continua
  visível nos relatórios históricos.

#### US-F06 — Lançar despesa apropriada a uma fase
**MH · M**

Como Carlos, quero lançar uma despesa da obra vinculada a uma fase, para saber onde o dinheiro
está indo.

- **CA-F06.1** — A despesa exige obra, fase, categoria, fornecedor, valor, data de competência e
  vencimento.
- **CA-F06.2** — Salvar sem fase é recusado (RN-F02).
- **CA-F06.3** — A lista de fases oferecida é a da obra, não a de uma versão específica (RN-F03).
- **CA-F06.4** — Valor zero ou negativo é recusado.
- **CA-F06.5** — A despesa nasce com status `prevista`.
- **CA-F06.6** — Lançar despesa numa obra de outra empresa é impossível: a obra nem aparece.

#### US-F07 — Anexar nota fiscal à despesa
**SH · P**

Como Carlos, quero anexar a NF à despesa, para ter o comprovante junto do lançamento.

- **CA-F07.1** — O anexo usa o GED existente, com tipo `nota_fiscal`, vinculado à mesma obra.
- **CA-F07.2** — A despesa mostra o anexo e permite baixá-lo por URL assinada.
- **CA-F07.3** — Remover o anexo não apaga o documento do GED, só desfaz o vínculo.
- **CA-F07.4** — Uma despesa tem no máximo um anexo de NF.

#### US-F08 — Parcelar uma despesa
**SH · M**

Como Carlos, quero parcelar uma compra, porque material raramente é à vista.

- **CA-F08.1** — Informo o número de parcelas e a data da primeira; o sistema gera as demais
  mensalmente.
- **CA-F08.2** — A soma das parcelas é exatamente o valor original, com o resíduo na última
  (RN-F08).
- **CA-F08.3** — Cada parcela aparece identificada (2/5) e tem status próprio.
- **CA-F08.4** — Todas as parcelas herdam obra, fase, categoria e fornecedor.

#### US-F09 — Registrar pagamento
**MH · P**

Como Carlos, quero marcar uma despesa como paga, para o realizado refletir o caixa.

- **CA-F09.1** — Registrar pagamento exige a data; o valor pago é o do título.
- **CA-F09.2** — A despesa passa a `paga` e entra no realizado a partir da data de pagamento.
- **CA-F09.3** — Posso desfazer um pagamento, e a despesa volta a `prevista`.
- **CA-F09.4** — A ação fica registrada na auditoria, com autor e horário.

#### US-F10 — Acompanhar contas a receber
**SH · P**

Como Carlos, quero ver os títulos a receber gerados pelas medições, para saber o que está por
entrar.

- **CA-F10.1** — A lista mostra obra, medição de origem, valor, vencimento e status.
- **CA-F10.2** — Posso marcar um título como recebido, informando a data.
- **CA-F10.3** — O título não é criado nem editado à mão: só nasce de medição aprovada (RN-F06).

#### US-F11 — Orçado × realizado por fase, com alerta de estouro
**MH · G**

Como Carlos, quero ver fase a fase quanto orcei, quanto já gastei e quanto já comprometi, para
agir antes do estouro.

- **CA-F11.1** — A tela lista as fases com orçado, realizado, comprometido, saldo e percentual
  consumido.
- **CA-F11.2** — Fase cujo realizado + comprometido ultrapassa o orçado é destacada visualmente
  **e por texto** — não só por cor (WCAG 1.4.1).
- **CA-F11.3** — Os totais da obra batem com a soma das fases.
- **CA-F11.4** — Obra sem orçamento aprovado mostra estado vazio explicativo, não zeros
  (RN-F01).
- **CA-F11.5** — Uma obra com despesas em várias fases mostra cada uma no lugar certo —
  critério positivo, para que a tela não passe estando vazia.
- **CA-F11.6** — Carrega em menos de 1s para uma obra com 50 fases e 2000 despesas.

#### US-F12 — Curva S da obra
**MH · M**

Como Carlos, quero ver a curva de avanço planejado contra o executado, para enxergar atraso e
adiantamento no tempo.

- **CA-F12.1** — O gráfico mostra três séries acumuladas por período: planejado (cronograma),
  físico executado (medições) e financeiro realizado (despesas pagas).
- **CA-F12.2** — As séries são distinguíveis sem depender de cor.
- **CA-F12.3** — O período corrente é destacado.
- **CA-F12.4** — Obra sem cronograma mostra estado vazio com CTA para criar.
- **CA-F12.5** — Os valores do gráfico conferem com os da tela de orçado × realizado.

#### US-F13 — Fluxo de caixa previsto × realizado
**MH · M**

Como Carlos, quero ver entradas e saídas por período, para saber se vou ter caixa.

- **CA-F13.1** — Por período: saídas previstas, saídas realizadas, entradas previstas, entradas
  realizadas e saldo.
- **CA-F13.2** — O filtro por obra permite ver uma obra ou a empresa inteira.
- **CA-F13.3** — Período sem movimento aparece com zero, não some da série.
- **CA-F13.4** — O saldo acumulado é exibido junto do saldo do período.

#### US-F14 — Exportar o financeiro
**SH · P**

Como Carlos, quero exportar os lançamentos em CSV, para trabalhar na planilha e mandar ao
contador.

- **CA-F14.1** — A exportação respeita os filtros ativos na tela.
- **CA-F14.2** — Valores saem em formato pt-BR, calculados com `Decimal` (RN-F10).
- **CA-F14.3** — O CSV traz obra, fase, categoria, fornecedor, datas, valor e status.

---

## 6. Requisitos não-funcionais

| ID | Requisito | Verificação |
|---|---|---|
| **RNF-F01** | A tela de orçado × realizado carrega em < 1s para 50 fases e 2000 despesas | Benchmark com seed desse tamanho, no CI |
| **RNF-F02** | O cálculo de Curva S para 24 períodos e 50 fases roda em < 300ms | Benchmark |
| **RNF-F03** | Nenhum cálculo financeiro usa `float` | Verificação automatizada que falha o build |
| **RNF-F04** | A exportação de 10.000 lançamentos conclui em < 10s | Teste |
| **RNF-F05** | Todas as telas do módulo passam em axe-core sem violação crítica | E2E de a11y |

## 7. Requisitos de segurança

| ID | Requisito | Verificação |
|---|---|---|
| **SEC-F01** | Toda tabela nova tem RLS habilitada, forçada, com policy de isolamento por `company_id` | Consulta ao catálogo do Postgres, não busca textual no SQL |
| **SEC-F02** | Usuário do tenant A não lê nem escreve linha do tenant B em nenhuma tabela do módulo | Teste de isolamento por tabela, leitura **e** escrita |
| **SEC-F03** | Usuário do tenant A vê as próprias linhas | Teste positivo — sem ele, schema com RLS e zero policies passa em tudo |
| **SEC-F04** | Recurso de outro tenant responde 404, não 403 | Teste por rota |
| **SEC-F05** | Papel `campo` e `viewer` não acessam nenhuma rota do módulo | Teste de negação por papel |
| **SEC-F06** | Nenhuma rota de portal expõe dado financeiro (RN-F11) | Teste que varre as rotas de portal |
| **SEC-F07** | Pagamento, aprovação de medição e exclusão de despesa geram registro de auditoria | Teste por ação |

---

## 8. Métricas de sucesso

| Métrica | Meta |
|---|---|
| Obras ativas com pelo menos uma despesa lançada | > 60% em 90 dias |
| Obras com cronograma criado | > 40% em 90 dias |
| Estouros detectados durante a obra (não no fechamento) | > 80% dos estouros ocorridos |
| Tempo médio entre a despesa acontecer e ser lançada | < 7 dias |

A terceira é a que importa: o módulo existe para mudar **quando** o estouro é descoberto.

---

## 9. Tier

Premissa registrada, barata de reverter: **Módulos 5 e 6 ficam em `pro` e `enterprise`**, como
o Módulo 3. O plano de entrada chama-se **`starter`** no enum `company_tier`
(`'starter','pro','enterprise'`) — e **não** "Basic", como o PRD principal e o material comercial
dizem. A divergência de nome entre produto e schema é anterior a este módulo; para código, vale
o enum.

Isso pressupõe que o gate de tier exista — hoje **não existe** (ver [ESPEC §9](ESPEC.md)). Se o
módulo entrar antes do gate, ele fica aberto a todos os planos, como o Módulo 3 está.

---

## 10. Riscos aceitos

| Risco | Mitigação | Revisar quando |
|---|---|---|
| Lançamento manual gera baixa adesão: Carlos não lança e o módulo fica vazio | Lançamento em poucos campos, parcelamento automático, anexo opcional | Se a métrica de "obras com despesa" ficar abaixo de 40% em 90 dias |
| Reconciliação de fases entre versões de orçamento erra e o histórico se desloca | Reconciliação por código, com relatório das fases não casadas apresentado ao usuário | Na primeira revisão de orçamento real com despesas já lançadas |
| Medição e financeiro divergem porque medem coisas diferentes | A Curva S mostra as três séries juntas, tornando a divergência visível em vez de escondida | — |
| Sem tributos, o número não bate com a contabilidade e gera desconfiança | A tela diz explicitamente que é controle gerencial, não apuração fiscal | Se o beta pedir conciliação contábil |
| O módulo entra sem gate de tier e é entregue de graça | Documentado em §9 | Antes do lançamento comercial |

---

## 11. Critério de saída

O módulo está pronto quando, numa obra real do beta:

- [ ] Existe cronograma com a soma das fases fechando em 100%
- [ ] Pelo menos duas medições foram aprovadas e geraram títulos a receber
- [ ] Pelo menos 20 despesas foram lançadas, todas apropriadas a fase
- [ ] A tela de orçado × realizado bate com a soma conferida à mão
- [ ] Um estouro simulado dispara o alerta
- [ ] Os testes de isolamento passam, positivos e negativos, em todas as tabelas novas

---

*PRD Módulos 5 e 6, versão 1.0. O estado do código citado aqui foi verificado contra o
repositório em 2026-11-02 — ver [ESPEC §2](ESPEC.md) para o que foi conferido e como.*
