# PRD — SaaS Mini-ERP para Construtoras e Reformadoras de Pequeno Porte

**Versão:** 3.0
**Data:** 2026-06-28
**Status:** MVP V1 — Gestão + Agentes de IA Básicos
**Inspiração de mercado:** Obra Prima + Agentes LangChain/LLM
**Total de User Stories:** 24 (10 Módulo 1 core + 3 transversais + 8 Módulo 2 + 3 Módulo 3 Agentes)
**Timeline:** 6 meses

---

## 1. Resumo Executivo

### Visão
Construir um mini-ERP 100% cloud-native, voltado para pequenas empresas de construção, reforma e prestadores de serviço (elétrica, pintura, gesso, hidráulica). O produto substitui o processo artesanal atual — papel, planilhas isoladas, WhatsApp, redes locais — por um sistema digital centralizado que dá controle financeiro real, transparência com o cliente e organização documental.

### Objetivo do Produto
Reduzir estouros de orçamento, eliminar retrabalho administrativo e profissionalizar a comunicação entre construtor, equipe de campo, fornecedor e cliente final. O MVP foca em dois fundamentos: (1) **organizar a obra e seus documentos** com um CRM/GED simples e portal do cliente, e (2) **dar estrutura à engenharia de custos** com EAP, Curva ABC, precificação flexível e versionamento de orçamentos.

### Público-Alvo
Construtoras e empreiteiras de pequeno porte (1 a 30 colaboradores), reformadores autônomos com carteira de clientes recorrente, e prestadores de serviços especializados. Perfil típico: empresário operacional, baixa maturidade digital, gestor financeiro informal, sem ERP atual ou usando combinação de Excel + WhatsApp + Google Drive.

### Diferencial Competitivo
- **Onboarding low-touch:** autoimplantação em minutos, sem consultoria. Basic tier a R$ 99/mês baixa barreira de entrada.
- **Atualizações quinzenais** com export livre de dados (sem aprisionamento). LGPD-compliant.
- **Multiempresas nativo** desde o dia 1 (escritórios que gerenciam obras de várias razões sociais).
- **Portal do cliente com controle granular de visibilidade** (o construtor decide o que cada cliente enxerga).
- **Permissões rigorosas por role** — equipe de campo não vê financeiro, cliente não vê margens.
- **Magic links sem login** para fornecedores e clientes externos — reduz fricção de adoção da cadeia.
- **Engenharia de custos de verdade** (EAP hierárquica, Curva ABC, versionamento), não apenas "planilhas online".
- **Escalabilidade pay-per-seat:** Pro tier cresce com você, pagando apenas pelos usuários que precisa.
- **🤖 Agentes de IA via WhatsApp (Eugno Faz Tudo):** Subagentes especializados (Orçamento, Compras, Atendimento) acionados por linguagem natural. Pro tier + Enterprise. Diferencial brutal vs. Obra Prima.

---

## 2. Personas Detalhadas

### Persona 1 — Carlos, o Admin/Backoffice
- **Contexto:** 42 anos, dono de construtora com 12 colaboradores, toca 4 a 8 obras simultâneas (residenciais e pequenos comerciais). Hoje vive entre WhatsApp, Excel e e-mail. Já teve prejuízo em 2 obras por estouro de orçamento não detectado a tempo.
- **Goals:**
  - Fechar orçamentos rápido, com margem protegida.
  - Saber em tempo real quanto cada obra está custando vs. orçado.
  - Profissionalizar a imagem (PDFs timbrados, portal do cliente).
  - Organizar contratos, NFs e projetos em um único lugar acessível remotamente.
- **Pain Points:**
  - Refazer orçamento do zero a cada revisão (perde histórico).
  - Não consegue precificar com markup diferente por fase.
  - Cliente liga 3x por semana pedindo atualização.
  - Documento importante perdido em pendrive ou notebook que quebrou.
- **Fluxo de uso esperado:** Acessa via web no escritório. Cadastra cliente e obra, monta orçamento por EAP, gera PDF, envia para cliente. Sobe documentos no GED. Configura visibilidade do portal. Recebe tickets pós-obra e despacha para campo.

### Persona 2 — Joana, a Equipe de Campo
- **Contexto:** 35 anos, mestre de obras, fica 90% do tempo em canteiro. Smartphone Android intermediário, conexão de internet estável na maioria dos canteiros.
- **Goals:**
  - Registrar fotos do avanço sem depender de WhatsApp pessoal.
  - Comunicar pendências e solicitações sem precisar voltar ao escritório.
  - Provar entrega de etapas com evidência visual.
- **Pain Points:**
  - Fotos somem no rolo do celular pessoal.
  - Anota medições no caderno e perde.
- **Fluxo de uso esperado:** A equipe de campo acessa a obra via **mobile-web responsivo** para anexar fotos e documentos, com compressão automática e sincronização em tempo real. Acesso autenticado, vinculado à obra.

### Persona 3 — Marcos, o Fornecedor
- **Contexto:** 48 anos, dono de depósito de materiais de construção. Atende 15 a 20 construtoras. Recebe cotações por WhatsApp e e-mail, responde manualmente.
- **Goals:**
  - Receber pedidos de cotação organizados.
  - Responder rápido sem criar mais uma conta/senha.
- **Pain Points:**
  - Cada construtora pede de um jeito diferente.
  - Esquece de responder e perde venda.
- **Fluxo de uso esperado (MVP V1 — limitado):** No MVP V1, o fornecedor **não tem fluxo ativo** (cotação entra na Fase 2). Porém o cadastro de fornecedor já existe no Módulo 1 para uso futuro e referência em documentos.

### Persona 4 — Renata, a Cliente Final
- **Contexto:** 38 anos, contratou reforma de apartamento. Mora em outra cidade durante a obra. Nunca contratou reforma antes, alto nível de ansiedade.
- **Goals:**
  - Ver fotos e cronograma da obra sem precisar pedir.
  - Acessar contrato, orçamento aprovado e NFs.
  - Abrir chamado quando algo dá errado pós-entrega.
- **Pain Points:**
  - Liga toda semana e recebe "tá tudo bem, dona Renata".
  - Não sabe se o que está sendo cobrado bate com o contratado.
- **Fluxo de uso esperado:** Recebe link de acesso ao portal. Faz login simples. Vê apenas os documentos e informações que Carlos liberou. Abre tickets de manutenção pós-obra. Acompanha galeria de fotos.

---

## 3. Requisitos Funcionais — User Stories (24 Total)

> Padrão: "Como [persona], eu quero [ação], para que [benefício]"
> Prioridade: **MH** = Must-Have, **SH** = Should-Have, **NH** = Nice-to-Have
> Complexidade: **P** = Pequena, **M** = Média, **G** = Grande
> **Nota:** US-19, US-20, US-21 são transversais críticas. US-22, US-23, US-24 (Módulo 3) implementam Agentes de IA via WhatsApp.

---

### MÓDULO 1 — Gestão de Clientes e Obras (CRM + GED)

#### US-01 — Cadastro de Cliente PF/PJ
**Como** Carlos (Admin), **eu quero** cadastrar clientes como Pessoa Física ou Jurídica com dados de contato e histórico, **para que** eu tenha uma base única de clientes vinculada às obras.
- **Critérios de aceite:**
  1. Formulário aceita PF (CPF, nome, RG) e PJ (CNPJ, razão social, IE) com validação de documento.
  2. Campos obrigatórios: nome/razão social, documento, telefone, e-mail.
  3. Sistema impede cadastro duplicado pelo documento dentro da mesma empresa.
  4. Cliente cadastrado aparece em listagem paginada com busca por nome/documento.
  5. Histórico de propostas/orçamentos associados é exibido na ficha do cliente.
- **Prioridade:** MH | **Complexidade:** P

#### US-02 — Cadastro de Obra
**Como** Carlos, **eu quero** cadastrar uma obra vinculada a um cliente, com endereço, datas previstas e status, **para que** eu organize todas as informações da obra em um único contexto.
- **Critérios de aceite:**
  1. Obra exige vínculo obrigatório com um cliente existente.
  2. Campos: nome da obra, endereço completo, data prevista início/fim, status (Em proposta, Em execução, Concluída, Pausada).
  3. Permite múltiplas obras por cliente.
  4. Listagem de obras filtrável por status e cliente.
  5. Cada obra tem um identificador único exibido no sistema.
- **Prioridade:** MH | **Complexidade:** P

#### US-03 — Cadastro de Fornecedor
**Como** Carlos, **eu quero** cadastrar fornecedores (PF/PJ) com contato e categoria, **para que** eu tenha a base pronta para futuras cotações e referência em documentos.
- **Critérios de aceite:**
  1. Campos: razão social/nome, documento, contato, categoria (ex: materiais, mão de obra, serviços).
  2. Validação de documento único por empresa.
  3. Listagem com filtro por categoria.
- **Prioridade:** SH | **Complexidade:** P

#### US-04 — Upload de Documentos (GED) com Drag-and-Drop
**Como** Carlos, **eu quero** subir documentos (PDF, DWG, JPG, PNG, XLSX) para uma obra via drag-and-drop, **para que** eu centralize toda a documentação no cloud.
- **Critérios de aceite:**
  1. Aceita arquivos até 50 MB por upload.
  2. Formatos suportados: PDF, DWG, JPG, PNG, XLSX, DOCX.
  3. Upload simultâneo de múltiplos arquivos com barra de progresso.
  4. Arquivo armazenado em storage cloud com URL assinada e tempo de expiração.
  5. Falha em um arquivo não bloqueia os demais do mesmo lote.
- **Prioridade:** MH | **Complexidade:** M

#### US-05 — Organização e Filtros do GED
**Como** Carlos, **eu quero** organizar documentos em categorias (Projeto, Contrato, NF, Foto, Outro) e filtrar/buscar, **para que** eu encontre qualquer arquivo em segundos.
- **Critérios de aceite:**
  1. Cada documento tem categoria obrigatória.
  2. Filtros: categoria, data de upload, nome.
  3. Busca por nome de arquivo retorna resultados em < 1s para até 1000 documentos.
  4. Visualização em lista e em grid (com thumbnail para imagens).
  5. Permite renomear e excluir (com confirmação) documentos.
- **Prioridade:** MH | **Complexidade:** M

#### US-06 — Portal do Cliente com Filtro de Visibilidade
**Como** Carlos, **eu quero** marcar individualmente quais documentos ficam visíveis ao cliente final no portal, **para que** eu controle o que Renata vê sem expor dados internos (cotações, margens).
- **Critérios de aceite:**
  1. Cada documento tem toggle "Visível ao cliente" (default: não).
  2. Cliente final só enxerga no portal o que foi marcado.
  3. Alteração de visibilidade é imediata (sem cache > 1 min).
  4. Log de auditoria registra quem alterou visibilidade e quando.
  5. Bulk-action: marcar/desmarcar visibilidade em múltiplos documentos.
- **Prioridade:** MH | **Complexidade:** M

#### US-07 — Acesso do Cliente Final ao Portal
**Como** Renata (Cliente Final), **eu quero** acessar um portal com login simples para ver minha obra, **para que** eu acompanhe o andamento sem precisar ligar.
- **Critérios de aceite:**
  1. Cliente recebe convite por e-mail com link de ativação.
  2. Login via e-mail + senha OU magic link por e-mail.
  3. Portal exibe: dados da obra, documentos liberados, galeria de fotos liberada, tickets abertos.
  4. Cliente não enxerga obras de outros clientes nem dados internos.
  5. Sessão expira em 7 dias de inatividade.
- **Prioridade:** MH | **Complexidade:** M

#### US-08 — Mensageria/Tickets na Obra
**Como** Renata, **eu quero** abrir um chamado/ticket vinculado à minha obra, **para que** eu registre solicitações ou problemas pós-obra de forma rastreável.
- **Critérios de aceite:**
  1. Cliente cria ticket com título, descrição e até 5 anexos (foto/PDF).
  2. Ticket recebe status: Aberto, Em andamento, Resolvido, Fechado.
  3. Carlos recebe notificação por e-mail quando ticket é criado.
  4. Thread de mensagens entre cliente e admin (texto + anexos).
  5. Ticket fica vinculado à obra e aparece no histórico.
- **Prioridade:** MH | **Complexidade:** M

#### US-09 — Equipe de Campo Anexa Fotos pela Obra (com Fila Local)
**Como** Joana (Equipe de Campo), **eu quero** acessar a obra via mobile-web responsivo e subir fotos do avanço, mesmo com conexão instável, **para que** o escritório e o cliente vejam o progresso real assim que a conexão normalizar.
- **Critérios de aceite:**
  1. Interface mobile-web responsiva (100% web, nenhum app nativo).
  2. Login dedicado para perfil "Campo" com acesso restrito às obras vinculadas.
  3. Upload de fotos com compressão automática (máx 2 MB por foto após otimização).
  4. **Arquitetura de Fila Local:**
     - Foto é salva em IndexedDB/SQLite local ANTES de tentar POST ao servidor.
     - Se servidor responder 200: remove da fila local, confirma no UI ("Sincronizado ✓").
     - Se falhar (4xx/5xx/timeout): mantém na fila, exibe status "Pendente de sincronização ⏳" com ícone visual.
     - Retry automático a cada 30s enquanto houver conexão.
     - UI mostra fila local: "3 fotos aguardando sincronização" com opção de tentar agora.
  5. Cada foto registra data/hora e autor.
  6. Foto entra na galeria da obra assim que sincronizar no servidor.
  7. Foto pode ser marcada como visível ao cliente após sincronização.
- **Prioridade:** MH | **Complexidade:** G

#### US-10 — Parceiros Recomendados na Obra
**Como** Carlos, **eu quero** sugerir parceiros recomendados (arquitetos, financiamento, seguros) ao cliente dentro do portal, **para que** eu agregue valor e gere indicações.
- **Critérios de aceite:**
  1. Admin cadastra parceiros (nome, categoria, contato, descrição, link).
  2. Parceiros aparecem em seção dedicada do portal do cliente.
  3. Admin escolhe quais parceiros ficam visíveis por obra.
- **Prioridade:** NH | **Complexidade:** P

#### US-19 — Gestão de Usuários por Role e Permissões
**Como** Carlos (Admin), **eu quero** criar, editar e remover usuários atribuindo roles específicas (Admin, Campo, Cliente), **para que** cada usuário acesse apenas o que precisa e proteja dados sensíveis (financeiro, margens).
- **Critérios de aceite:**
  1. Roles disponíveis: **Admin** (acesso total), **Campo** (apenas upload de fotos e consulta de obra), **Cliente Final** (acesso ao portal restrito).
  2. Admin convida usuários por e-mail com link one-time + instrução pra set password.
  3. Link de convite expira em 7 dias (não é magic link, exige password setup).
  4. Usuário convidado clica no link, seta sua senha (mín 8 caracteres), ativa a conta.
  5. Admin pode ativar/desativar/remover usuário a qualquer momento.
  6. Operações de exclusão registram trilha de auditoria (quem removeu, quando, IP).
  7. Limite de usuários respeita tier: Basic = 2, Pro = ilimitado.
  8. Tentativa de exceder limite exibe mensagem clara: "Limite de 2 usuários no plano Basic. Faça upgrade para adicionar mais."
- **Prioridade:** MH | **Complexidade:** M

#### US-20 — Customizar Templates de E-mail de Notificações
**Como** Carlos, **eu quero** customizar o texto e assunto dos e-mails de notificação (orçamento enviado, cliente aprovou, ticket criado), **para que** a comunicação reflita minha marca e linguagem.
- **Critérios de aceite:**
  1. Admin acessa painel "Templates de E-mail" com lista dos eventos: orçamento enviado, orçamento aprovado, ticket criado, convite de acesso portal.
  2. Para cada template: editor de texto com pré-visualização, variáveis disponíveis (ex: {{cliente.nome}}, {{obra.nome}}, {{orcamento.valor}}).
  3. Cada template tem "Padrão" (read-only) e versão customizada (editável).
  4. Revert para padrão com um clique.
  5. Teste de envio: "Enviar e-mail de teste para {{admin.email}}".
  6. Templates customizados salvos por empresa (multi-tenant safe).
- **Prioridade:** MH | **Complexidade:** M

#### US-21 — Exportar Dados da Empresa (LGPD)
**Como** Carlos, **eu quero** baixar todos os meus dados (clientes, obras, orçamentos, documentos, tickets) em formato aberto (JSON/CSV), **para que** eu tenha portabilidade total e cumpra LGPD.
- **Critérios de aceite:**
  1. Painel "Dados e Privacidade" com botão "Solicitar Exportação".
  2. Sistema gera arquivo .zip contendo:
     - clientes.json
     - obras.json
     - orcamentos.json (todas as versões)
     - documentos.csv (metadados: nome, categoria, data upload)
     - tickets.json
  3. Exportação ocorre em background. Admin recebe e-mail com link de download (válido 7 dias).
  4. Link de download é one-time (revoga após 1º acesso).
  5. Registro de auditoria: quando foi solicitada, quando foi baixada, IP de quem baixou.
  6. Suporta até 5 exportações simultâneas por empresa.
- **Prioridade:** MH | **Complexidade:** M

---

### MÓDULO 2 — Orçamentos e Engenharia de Custos

#### US-11 — Criar Orçamento Vinculado à Obra
**Como** Carlos, **eu quero** criar um orçamento vinculado a uma obra, **para que** eu organize a precificação em um documento estruturado.
- **Critérios de aceite:**
  1. Orçamento exige obra vinculada.
  2. Campos: título, data, validade, observações, dados do cliente (auto-preenchidos).
  3. Orçamento criado entra como Versão 1 (Rev 1).
  4. Status: Rascunho, Enviado, Aprovado, Rejeitado, Substituído.
- **Prioridade:** MH | **Complexidade:** P

#### US-12 — Montar EAP (Fases → Serviços → Insumos/MO)
**Como** Carlos, **eu quero** estruturar o orçamento em hierarquia de Fases, Serviços e Insumos/Mão de Obra, **para que** eu tenha engenharia de custos real e rastreabilidade por componente.
- **Critérios de aceite:**
  1. Hierarquia de 3 níveis: Fase → Serviço → Insumo/MO.
  2. Cada Insumo tem: descrição, unidade, quantidade, custo unitário, custo total calculado.
  3. Subtotais por Serviço, Fase e Total geral recalculados automaticamente em < 200ms.
  4. Operações suportadas por item: criar, editar, duplicar, excluir, reordenar (drag).
  5. Modal fullscreen com abas (Estrutura, Precificação, Resumo) sem recarregar rota.
- **Prioridade:** MH | **Complexidade:** G

#### US-13 — Importação de Itens via Planilha
**Como** Carlos, **eu quero** importar Fases/Serviços/Insumos via planilha (XLSX/CSV), **para que** eu acelere a montagem de orçamentos grandes.
- **Critérios de aceite:**
  1. Sistema oferece template XLSX para download.
  2. Importação valida cabeçalho e tipos de dados, mostrando linhas com erro.
  3. Importação bem-sucedida cria a hierarquia respeitando agrupamentos da planilha.
  4. Suporta até 5000 linhas por importação.
- **Prioridade:** SH | **Complexidade:** M

#### US-14 — Curva ABC Automática
**Como** Carlos, **eu quero** ver a Curva ABC dos insumos do orçamento, **para que** eu identifique os itens que concentram a maior parte do custo.
- **Critérios de aceite:**
  1. Classificação automática: A (até 80% acumulado), B (80–95%), C (95–100%).
  2. Visualização em tabela ordenada por custo decrescente + gráfico de Pareto.
  3. Permite exportar lista ABC em CSV.
  4. Recalcula em tempo real quando itens são alterados.
- **Prioridade:** MH | **Complexidade:** M

#### US-15 — Precificação com Markup Flexível
**Como** Carlos, **eu quero** aplicar markup global, por fase ou por item, somado a uma taxa de administração, **para que** eu controle a margem com a granularidade que cada obra exige.
- **Critérios de aceite:**
  1. Campo de markup global (%) aplicado a todos os itens sem markup específico.
  2. Markup pode ser sobrescrito por Fase ou por Insumo individual.
  3. Taxa de administração (%) aplicada sobre o subtotal pós-markup.
  4. Recálculo em cascata < 300ms para orçamento com até 1000 itens.
  5. Precisão decimal sem erros de ponto flutuante (uso de Decimal ou centavos inteiros).
  6. Resumo final exibe: custo direto, markup total, taxa adm, preço de venda.
- **Prioridade:** MH | **Complexidade:** G

#### US-16 — Versionamento de Orçamento
**Como** Carlos, **eu quero** criar novas revisões (Rev 1, Rev 2, ... Atual) preservando o histórico, **para que** eu negocie com cliente sem perder versões anteriores.
- **Critérios de aceite:**
  1. "Nova revisão" clona a versão atual e incrementa o número.
  2. Apenas uma versão é marcada como "Atual" por vez.
  3. Versões anteriores ficam read-only e acessíveis para consulta.
  4. Comparativo lado a lado entre duas versões (item, custo, diferença).
  5. PDF identifica claramente o número da revisão.
- **Prioridade:** MH | **Complexidade:** G

#### US-17 — Geração de PDF Timbrado
**Como** Carlos, **eu quero** gerar um PDF padronizado do orçamento com minha identidade visual (logo, cores, dados da empresa), **para que** eu envie ao cliente com aparência profissional.
- **Critérios de aceite:**
  1. PDF inclui: capa com logo/empresa, dados do cliente e obra, EAP hierárquica, resumo financeiro, condições, validade, assinatura.
  2. Logo e dados da empresa configurados uma vez por empresa.
  3. Geração de PDF de orçamento com 500 itens em < 5s.
  4. Download do PDF e envio por e-mail diretamente ao cliente.
  5. PDF gerado fica armazenado vinculado à versão do orçamento.
- **Prioridade:** MH | **Complexidade:** M

#### US-18 — Aprovação do Orçamento pelo Cliente
**Como** Renata, **eu quero** aprovar ou rejeitar o orçamento recebido pelo portal, **para que** eu formalize a decisão sem trocar e-mails.
- **Critérios de aceite:**
  1. Cliente vê PDF do orçamento e botão "Aprovar" / "Rejeitar" com campo de comentário.
  2. Aprovação registra timestamp, IP e identidade do cliente (trilha de aceite).
  3. Carlos recebe notificação por e-mail da decisão.
  4. Status do orçamento muda automaticamente.
- **Prioridade:** SH | **Complexidade:** M

---

### MÓDULO 3 — Agentes de IA (WhatsApp + LangChain/LangGraph)

#### US-22 — Dashboard de Auditoria de Agentes de IA
**Como** Carlos (Admin), **eu quero** ver logs detalhados de todas as interações dos agentes (Eugno), **para que** eu audite automaticamente o que o bot está fazendo na obra e reverta ações se necessário.
- **Critérios de aceite:**
  1. Dashboard "Auditoria de Agentes" exibe: timestamp, número WhatsApp, comando (texto), agente acionado, ação executada, resultado.
  2. Filtros: por obra, por tipo de agente (Orçamento/Compras/Atendimento), por data, por usuário.
  3. Permite reverter ação (ex: "desfazer pedido de compra criado pelo bot").
  4. Log diferencia ações do humano vs. ações do bot.
  5. Notificação ao admin se agente causar erro (ex: pedido duplicado ou valor inconsistente).
- **Prioridade:** MH | **Complexidade:** M

#### US-23 — Configurar Permissões de IA por Usuário/WhatsApp
**Como** Carlos (Admin), **eu quero** definir quais números de WhatsApp podem acionar quais tipos de ações dos agentes (consultar, criar pedidos, aprovar compras), **para que** eu controle automatizações sensíveis e previna erros.
- **Critérios de aceite:**
  1. Roles de IA: **Consultor** (read-only: consultar orçamentos), **Solicitador** (criar pedidos de compra), **Aprovador** (aprovar compras acima de limite).
  2. Admin mapeia número WhatsApp (vinculado a usuário) → role de IA.
  3. Agente rejeita comando se usuário não tem permissão ("Desculpe, você não tem permissão para criar pedidos. Solicite ao administrador").
  4. Auditar tentativas não-autorizadas (log de rejeição).
  5. Limite de gastos: Admin define limite diário/mensal por role (ex: Solicitador pode criar pedidos até R$ 5000/dia).
- **Prioridade:** MH | **Complexidade:** M

#### US-24 — Webhook Uazap + Orquestração de Agentes via LangGraph
**Como** sistema, **eu quero** receber mensagens do WhatsApp via API Uazap, processar via LangGraph (orquestrador) e acionar subagentes, **para que** interações sejam automáticas, em tempo real e resilientes.
- **Critérios de aceite:**
  1. **Webhook:** Endpoint POST `/webhook/uazap` recebe mensagem (texto, áudio com transcrição, imagem com OCR).
  2. **Validação:** Signature HMAC do Uazap é verificada; mensagens inválidas são descartadas.
  3. **Fila de Mensagens:** Mensagem entra em fila (Redis/PostgreSQL) com status "pending".
  4. **LangGraph Orchestration:** Grafo de agentes analisa intenção (ex: "preciso 10 sacos de cimento para a obra Academia").
     - Identifica: tipo de ação (consulta/solicitação/aprovação), obra vinculada, usuário.
     - Aciona subagente apropriado (Orçamento / Compras / Atendimento).
  5. **Subagente Compras (exemplo):**
     - Verifica obra existe e está ativa.
     - Valida orçamento disponível (não ultrapassar limite de gasto).
     - Cria "Solicitação de Compra" no banco (linqável a fornecedores futuros).
     - Retorna: "Pedido registrado! 10 sacos de cimento adicionados à obra Academia. Deseja enviar para cotação?".
  6. **Resposta:** Via Uazap API, mensagem é enviada ao usuário em tempo real.
  7. **Resilência:**
     - Se LLM ou LangGraph falhar: mensagem fica em fila com retry automático (3x, backoff exponencial 30s/60s/120s).
     - Se Uazap API cair: fallback automático para HTTP polling (usuário recebe resposta via SMS ou webhook callback quando API voltar). Alternativamente, pode salvar em banco e notificar admin pra contato manual.
     - Timeout de processamento: 10s (fallback: "Processando sua solicitação, você receberá confirmação em breve").
     - Monitorar health da API Uazap: se status degradado, alertar admin e oferecer modo read-only (apenas respostas de consulta, não criação de ações).
  8. **Logging:** Cada etapa (recebimento, processamento, resposta) é registrada para auditoria (timestamp, entrada, saída, LLM model, versão do prompt, erro se houver).
- **Prioridade:** MH | **Complexidade:** G

---

## 4. Requisitos Não-Funcionais

### RNF-01 — Performance
- Tempo de resposta P95 de telas web < 1,5s em conexão de 10 Mbps.
- Recálculo de orçamento (cascata) < 300ms para até 1000 itens.
- Geração de PDF de até 500 itens < 5s.
- Upload de documento de 50 MB com feedback de progresso em tempo real.
- Suporte simultâneo a 200 usuários ativos por instância sem degradação.

### RNF-02 — Segurança
- Autenticação via e-mail + senha com hash bcrypt/argon2.
- Magic link com JWT de curta duração (validade ≤ 30 min) para clientes e fornecedores externos.
- Isolamento multi-tenant: toda query filtrada por `company_id` no backend (RLS no Postgres ou middleware).
- HTTPS obrigatório em todos os endpoints.
- Senhas mínimo 8 caracteres, com requisitos de complexidade configuráveis.
- URLs de documentos no storage são assinadas e expiram (≤ 1h).
- Trilha de auditoria para: alteração de visibilidade no portal, aprovação de orçamento, exclusão de documentos.
- Logout automático após 7 dias de inatividade (cliente) e 30 dias (admin).

### RNF-03 — Disponibilidade
- SLA de uptime de 99,5% mensal (≈ 3,6h de downtime/mês tolerados).
- Backups automáticos diários do banco com retenção de 30 dias.
- Restore testado mensalmente.
- Deploy com zero downtime (blue-green ou rolling).

### RNF-04 — Compatibilidade
- Browsers suportados: Chrome, Edge, Firefox, Safari (últimas 2 versões).
- Mobile-web responsivo para Joana (Equipe de Campo) em Android 10+ e iOS 14+.
- Suporte a resolução mínima de 360x640 (mobile) e 1280x720 (desktop).
- Toda a plataforma é 100% web — nenhum app nativo necessário.
- **Resiliência mobile:** fila local em IndexedDB/SQLite permite funcionar mesmo com conexão intermitente. Retry automático a cada 30s.
- **Limites por Tier:** Basic (5 obras, 2 usuários, 500 docs, 5GB), Pro (ilimitado, pay-per-seat, 100GB), Enterprise (custom).

### RNF-04b — Isolamento de Dados e Segurança de Permissões
- Todo acesso ao dados filtrado por `company_id` no backend — nenhuma query sem filtro.
- Roles (Admin, Campo, Cliente) implementadas via middleware de autenticação — permissões checadas a cada request.
- Teste automatizado de isolamento: tentar acessar obra de outra empresa deve retornar 403.
- Trilha de auditoria para: criação/remoção de usuários, alteração de permissões, exclusão de documentos, aprovação de orçamento.
- Senhas hasheadas com bcrypt/argon2, nunca armazenadas em plain text.

### RNF-05 — Conformidade (LGPD)
- Aceite explícito de termos de uso e política de privacidade no cadastro.
- Funcionalidade de export de dados do tenant em formato aberto (JSON/CSV).
- Funcionalidade de exclusão de conta com remoção/anonimização de dados pessoais em até 30 dias.
- Registro de consentimento para receber comunicações.
- Dados armazenados em região do Brasil (preferencial) ou país com adequação reconhecida.

### RNF-06 — Escalabilidade
- Arquitetura multi-tenant com `company_id` indexado em todas as tabelas relevantes.
- Storage de documentos em serviço cloud (S3/Supabase Storage/equivalente).
- Banco PostgreSQL com possibilidade de read replicas para relatórios.

### RNF-07 — Usabilidade
- Onboarding low-touch: novo usuário cria empresa, primeiro cliente, primeira obra e primeiro orçamento em menos de 15 min sem ajuda externa.
- Dicas em tela ("pulsantes") guiando primeiros passos.
- Mensagens de erro claras e acionáveis (não exibir stack traces).

### RNF-08 — Agentes de IA (LangChain/LangGraph)
- **Latência de Processamento:** Resposta do agente ao usuário WhatsApp em < 5s (P95) via WebSocket ou polling.
- **Disponibilidade do LLM:** Se LLM provider cair, sistema faz fallback para resposta template ("Processando... você receberá confirmação em breve") e retry automático.
- **Taxa de Sucesso (Interpretação Correta):** Agente interpreta corretamente a intenção do usuário em ≥ 90% dos casos.
  - **Metodologia de Medição:** Admin marca respostas como "Entendi certo" ou "Entendi errado" no dashboard. Cada feedback é registrado em DB.
  - **Cálculo:** (Total de "Entendi certo" / Total de interações) × 100 ≥ 90%.
  - **Feedback Loop:** Respostas marcadas como erradas alimentam retraining de prompts (iterativo, não automático).
  - **Alvo:** Atingir 90% até o fim do mês 2 de produção (30 dias de feedback).
- **Fila de Mensagens:** Redis ou PostgreSQL com retry automático (backoff: 30s, 60s, 120s). Máximo 3 retentativas antes de marcar como "Falha de Processamento".
- **Auditoria Completa:** Cada interação de agente é registrada (timestamp, entrada, saída, modelo usado, versão do prompt, feedback do usuário).
- **Rate Limiting:** Máximo 10 requisições/minuto por número WhatsApp (evita spam ou loops). Excesso retorna erro 429 Throttled.
- **Isolamento de Dados:** Agentes processam apenas dados da `company_id` apropriada (nunca vazam dados entre tenants). Validação obrigatória a cada request.

---

## 5. Métricas de Sucesso (KPIs)

### Adoção
- **Taxa de ativação:** % de novos cadastros que completam o onboarding (empresa + primeiro orçamento) em até 7 dias. **Meta: 60%**.
- **Tempo médio até primeiro orçamento gerado:** **Meta: < 30 min** desde o cadastro.
- **Clientes ativos mensais (MAC):** empresas que fizeram login + criaram ou editaram pelo menos 1 entidade no mês.

### Retenção
- **Churn mensal:** % de clientes pagantes que cancelaram. **Meta: < 5% ao mês** após o 3º mês.
- **Lifetime Value (LTV):** receita média acumulada por cliente até o cancelamento. **Meta: > 12x ticket mensal**.
- **Retenção em 90 dias:** % de cadastros ativos após 90 dias. **Meta: > 50%**.

### Eficiência (valor entregue)
- **Redução de tempo para montar orçamento:** comparativo declarado pelo usuário antes vs. depois. **Meta: redução ≥ 50%**.
- **% de orçamentos com versionamento utilizado:** indicador de profundidade de uso. **Meta: > 40%**.
- **Documentos por obra (médio):** indicador de adoção do GED. **Meta: > 10 documentos por obra ativa**.

### Satisfação
- **NPS trimestral:** **Meta: > 50**.
- **CSAT pós-onboarding:** **Meta: > 4,2/5**.
- **Tickets de suporte por cliente/mês:** **Meta: < 1**.

### Negócio
- **MRR (Monthly Recurring Revenue):** acompanhamento mensal.
- **ARR (Annual Recurring Revenue):** meta a definir após validação de pricing.
- **CAC (Custo de Aquisição):** **Meta: payback em ≤ 6 meses**.
- **Razão LTV/CAC:** **Meta: > 3**.
- **% de clientes Pro com agentes ativos:** **Meta: > 70%** (indicador de adoção de diferencial)

### Agentes de IA
- **Taxa de Interpretação Correta:** % de comandos compreendidos corretamente pelo LangGraph. **Meta: ≥ 90%**.
- **Latência de Resposta (P95):** Tempo desde recebimento da mensagem até envio de resposta. **Meta: < 5s**.
- **Taxa de Erro dos Agentes:** % de ações que causaram erro ou necessitaram reversão. **Meta: < 2%**.
- **Engajamento com Agentes:** % de usuários Pro que usaram agentes pelo menos 1x na semana. **Meta: > 50%**.
- **Economia de Tempo:** Tempo economizado pelo usuário usando agentes vs. manual (auto-reportado). **Meta: redução ≥ 40%**.

---

## 6. Roadmap (Fases)

### Fase 1 — MVP V1 (Gestão + Agentes Básicos)
**Timeline estimada:** 6 meses
**Escopo:**
- **Módulo 1 — Gestão de Clientes e Obras (CRM + GED)** conforme US-01 a US-10, US-19 a US-21.
- **Módulo 2 — Orçamentos e Engenharia de Custos** completo conforme US-11 a US-18.
- **Módulo 3 — Agentes de IA (V1 Básico)** conforme US-22, US-23, US-24:
  - Subagentes: Orçamento (consulta) + Compras (solicitação simples)
  - Webhook Uazap + LangGraph orchestration
  - Dashboard de auditoria de agentes
  - Permissões por role para IA
  - Disponível em tiers Pro e Enterprise
- **Infraestrutura:**
  - Multi-tenant com isolamento de dados por company_id
  - Autenticação por role (Admin, Campo, Cliente, AI) com permissões granulares
  - Portal do cliente com acesso restrito por obra
  - Mobile-web responsivo com fila local (IndexedDB) e retry automático
  - Sistema de tiers (Basic/Pro/Enterprise) com limites por plano
  - Templates de e-mail customizáveis (Pro+)
  - Fila de mensagens para agentes (Redis/PostgreSQL)
  - Integração Uazap com webhook validation + retry automático
- **Compliance:**
  - LGPD: termos de uso, export de dados, exclusão de conta, trilha de auditoria
- **UX:**
  - Onboarding low-touch (<15 min até primeiro orçamento)
  - Dicas em tela ("pulsantes")
  - Suporte a 200 usuários simultâneos sem degradação
  - Latência de agentes < 5s (P95)

**Critério de saída do MVP V1:**
- 10 clientes pagantes ativos (split: 7+ no Pro com agentes)
- NPS > 30 entre os primeiros 50 usuários
- Agentes operacionais: ≥ 90% taxa de interpretação correta
- Estabilidade: < 2 incidentes críticos/mês

### Fase 2 — MVP V2 (Agentes Avançados + Financeiro)
**Timeline estimada:** +6 a 9 meses após V1.
**Escopo previsto:**
- **Módulo 3 — Agentes de IA (V2 Avançado):**
  - Subagente Atendimento: categorização automática de mensagens de cliente, abertura de tickets, SLA alerts
  - Notificações proativas (ex: "Sua obra está 10% atrasada conforme cronograma")
  - Treinamento contínuo: feedback do usuário melhora interpretação
  - Suporte a mais idiomas/contextos
- **Módulo 4 — Cadeia de Suprimentos Inteligente:** requisição via mobile-web com fotos, portal de cotação via magic link (RFQ + JWT) para fornecedores, motor de decisão Melhor Compra Global vs. Fracionada, ordens de compra automatizadas integradas ao Contas a Pagar.
- **Módulo 5 — Planejamento Físico-Financeiro:** cronograma cruzando custo orçado com semanas/meses, medição de avanço físico (% executado) para liberação de faturamento.
- **Módulo 6 — Financeiro e Dashboards:** fluxo de caixa + contas a pagar, apropriação obrigatória de despesas por fase, Curva S (Planejado vs. Executado), alertas de estouro (variance) em red highlight.

### Fase 3 — Pós-V2 (Visão de longo prazo)
- Integrações com bancos (Open Finance) para conciliação automática.
- Marketplace de parceiros recomendados monetizado.
- IA para sugerir composição de orçamento a partir de obras anteriores.
- Integração com NF-e e e-Social para registro de mão de obra.

---

## 6b. Regras de Monetização e Limites por Tier

### Tiers de Assinatura

#### Tier Basic
- **Preço:** R$ 99/mês (anual) ou R$ 129/mês (mensal)
- **Obras Ativas:** máx 5 por empresa
- **Usuários:** 2 assentos (admin + 1 campo/backoffice)
- **Funcionalidades:** Módulos 1 + 2 (sem templates de e-mail customizados, SEM agentes de IA)
- **Agentes:** Não incluídos
- **Público:** Reformadores autônomos, pequenas equipes testando
- **Limite de Documentos:** 500 por empresa
- **Armazenamento:** 5 GB

#### Tier Pro
- **Preço:** R$ 299/mês (base) + R$ 49/usuário adicional
- **Obras Ativas:** ilimitado
- **Usuários:** ilimitado (pay-per-seat)
- **Funcionalidades:** Módulos 1 + 2 + templates de e-mail customizados + Módulo 3 (Agentes de IA)
- **Agentes Incluídos:** Subagentes Orçamento + Compras acionáveis via WhatsApp. Dashboard de auditoria. Permissões por role.
- **Público:** Construtoras com 2-10 colaboradores, volume alto
- **Limite de Documentos:** ilimitado
- **Armazenamento:** 100 GB
- **Suporte:** Email (24h), chat (business hours)
- **Prioridade de LLM:** Processamento prioritário (latência < 3s)

#### Tier Enterprise
- **Preço:** Custom (contract base mínimo R$ 999/mês)
- **Obras Ativas:** ilimitado
- **Usuários:** ilimitado + SSO (SAML/OAuth)
- **Funcionalidades:** Multi-empresa com isolamento rigoroso, Módulo 3 (Agentes) com customização de prompts, webhooks customizados, integrações privadas
- **Agentes Incluídos:** Todos os subagentes (Orçamento, Compras, Atendimento) com prompt engineering customizado por cliente. SLA de resposta < 2s.
- **Público:** Corporações com múltiplas filiais, volume crítico
- **Suporte:** Telefone, Slack, SLA 2h
- **SLA:** 99,9% uptime

### Regras de Upgrade/Downgrade
- Upgrade: imediato, ajuste proporcional na fatura.
- Downgrade: efetivo no próximo ciclo de faturamento. Sistema avisa se descenda será violado.
- Limite excedido (ex: 4ª obra no Basic): sistema bloqueia criação de nova obra + notifica upgrade.

---

## 7. Escopo Negativo (NÃO faz parte do MVP V1)

Para evitar inflar o MVP, está explicitamente **fora** desta fase:
- **Agentes de Atendimento:** Categorização automática de tickets e notificações proativas (fica para V2).
- **Módulos 4, 5 e 6:** Cadeia de Suprimentos, Planejamento Físico-Financeiro e Financeiro inteiros (futuro).
- Motor de cotação e RFQ para fornecedores (cadastro existe, fluxo não).
- Curva S, fluxo de caixa, contas a pagar.
- Integrações com bancos, NF-e, e-Social.
- IA generativa para sugestão de composição de orçamento (V3).
- Marketplace de parceiros monetizado.
- White-label para revenda.
- Notificações push ou qualquer recurso nativo de app.
- Customização avançada de prompts (fica para Enterprise em V2).

---

## 8. Dependências e Riscos

### Dependências externas
- Provedor de storage cloud (S3, Supabase Storage ou equivalente).
- Provedor de e-mail transacional (SendGrid, Resend, SES) para magic links e notificações.
- Provedor de banco PostgreSQL gerenciado (Supabase, RDS, Neon).
- Biblioteca de geração de PDF (pdfmake, jsPDF ou Puppeteer server-side).
- Biblioteca de gráficos (Recharts ou Chart.js) para Curva ABC.
- **Agentes de IA:**
  - LLM Provider (OpenAI GPT-4, Anthropic Claude, equivalente) para processamento de linguagem.
  - LangChain + LangGraph para orchestração de agentes.
  - API Uazap (ou equivalente: Evolution API, Z-API) para integração WhatsApp.
  - Redis ou PostgreSQL para fila de mensagens (Celery/Bull pra async jobs).
  - Provedor de transcription (Whisper/assembly.ai) se aceitar áudio.

### Riscos técnicos
- **Precisão financeira em ponto flutuante:** uso obrigatório de Decimal ou armazenamento em centavos inteiros para evitar divergências em recálculos em cascata.
- **Performance da hierarquia EAP com muitos itens:** estrutura aninhada de até milhares de linhas exige modelagem cuidadosa (closure table, adjacency list otimizada).
- **Segurança de magic links:** JWT de curta duração + revogação por evento (orçamento aprovado revoga link).
- **Isolamento multi-tenant:** vazamento entre tenants é catastrófico — exige testes automatizados específicos (toda query precisa filtrar por company_id).
- **Fila local (IndexedDB):** sincronização de dados offline pode gerar duplicatas se não for idempotente. Backend deve rejeitar com 409 Conflict para duplicatas detectadas.
- **Permissões por role:** erro em validação permite campo ver financeiro ou cliente ver orçamento — breach grave. Exige testes de negação de acesso em 100% dos endpoints sensíveis.
- **LLM Availability & Cost:** Se LLM provider (OpenAI, Claude API) cair, sistema deve fazer fallback para respostas template e retry. Custo de chamadas LLM precisa ser monitorado (budgets por tier).
- **Interpretação correta da intenção:** LLM pode entender errado "10 sacos de cimento" como "10 obras de cimento". Exige prompt engineering cuidadoso + feedback loop + human-in-the-loop pra ações críticas (pedidos > R$ 5000).
- **Segurança de Webhook Uazap:** Validação de HMAC signature é crítica. Ataque de replay pode criar pedidos duplicados. Rate limiting + idempotência de key obrigatória.
- **Fila de Mensagens:** Se Redis/PostgreSQL fica down, mensagens são perdidas. Exige backup em DB + restore de fila ao ligar. Monitorar depth da fila (alertar se crescer > 1000).

### Riscos de negócio
- **Baixa maturidade digital do público-alvo:** onboarding precisa ser extremamente simples ou churn será alto.
- **Concorrência direta (Obra Prima e similares):** diferenciação pelo portal do cliente granular, magic links sem login e preço acessível.
- **Sazonalidade da construção civil:** crises macroeconômicas afetam volume de obras pequenas.
- **Resistência cultural ao registro digital:** muitos construtores ainda preferem "papel de pão" — exige educação de mercado.

### Riscos de produto
- **Subestimar complexidade do versionamento de orçamentos:** clonagem com integridade referencial é não-trivial.
- **GED virar "depósito desorganizado":** exige curadoria de categorias e UX de busca eficiente.
- **Portal do cliente expor algo que não deveria:** toggle de visibilidade precisa de testes exaustivos e log de auditoria.

---

## 9. Especificacao Tecnica

### Backend

Especificacao tecnica detalhada do dominio Backend/servicos/API para o MVP V1 (6 meses, 24 USs). Documento de referencia para o time de engenharia. Toda decisao referencia a US ou RNF relevante do PRD.

---

#### A. Arquitetura Geral

**Stack recomendada: Python 3.12 + FastAPI**

PROs:
- Stack ja dominada pelo time (Python/FastAPI no perfil do usuario).
- Ecosystem maduro para LangChain/LangGraph (US-24) e bibliotecas LLM (oficial em Python).
- Pydantic v2 oferece validacao rigorosa de entrada (RNF-02, mitiga risco de injection).
- Async nativo (asyncio) suporta alto throughput de webhooks (US-24).
- Tipagem estatica via type hints + mypy.

CONs:
- GIL limita CPU-bound, mas o workload aqui e IO-bound (DB, HTTP, LLM).
- Geracao de PDF server-side com Puppeteer exige sidecar Node.

Alternativas avaliadas:
- **Node.js/NestJS:** otimo para WebSocket/realtime, mas LangGraph em JS ainda e menos maduro que Python; perde-se sinergia com Whisper/Pydantic.
- **Go:** performance superior, mas curva de aprendizado e ausencia de bibliotecas LLM nativas tornam custoso para o prazo de 6 meses.

**Decisao final:** Python 3.12 + FastAPI + Uvicorn (worker) + Gunicorn (process manager).

**Padrao arquitetural:** Monolito modular (modular monolith) com fronteiras claras por modulo (gestao, orcamento, agentes). Justificativa: 24 USs em 6 meses + equipe pequena, microservicos seria over-engineering. Saida natural para microservicos no V2 caso necessario (modulo de Agentes ja se beneficia de separacao).

**Estrutura de pastas (top-level):**
```
app/
  core/            (config, security, db, deps)
  modules/
    gestao/        (clientes, obras, fornecedores, GED, tickets, usuarios)
    orcamento/     (EAP, markup, ABC, versoes, PDF)
    agentes/       (webhook uazap, langgraph, subagentes, auditoria)
    portal/        (cliente final, magic links)
  jobs/            (background workers - RQ/Arq)
  integrations/    (uazap, llm, storage, email)
  api/v1/          (routers)
tests/
```

**Multi-tenant:** todas as tabelas tem `company_id UUID NOT NULL` indexado. Isolamento em duas camadas (defense in depth):
1. **PostgreSQL RLS (Row Level Security):** policy obrigatoria em todas as tabelas filtrando por `current_setting('app.company_id')`. SET LOCAL feito no inicio de cada request via dependency do FastAPI.
2. **Middleware de aplicacao:** TenantMiddleware injeta `company_id` no contexto a partir do JWT. Repositories recebem `company_id` explicito; sem ele, raise.

PROs RLS: ultima linha de defesa, mesmo bug de aplicacao nao vaza. CONs: complexidade de migrations, debug mais dificil. A dupla camada vale pelo risco catastrofico de vazamento (Riscos tecnicos do PRD).

**Autenticacao:**
- **Login admin/campo:** e-mail + senha (Argon2id, params m=64MB, t=3, p=4). Resposta: JWT access (15 min) + refresh token rotativo (30 dias) armazenado httpOnly cookie.
- **Magic links (US-07, US-18):** JWT assinado HS256, claim `purpose` (portal_access | budget_approval), `exp` <= 30min (RNF-02). Token e single-use: ao consumir, marca em tabela `consumed_tokens(jti, consumed_at)`. Eventos de revogacao (orcamento aprovado) deletam jti pendentes.
- **Convites de usuario (US-19):** token opaco aleatorio (32 bytes URL-safe), TTL 7 dias, single-use, exige setup de senha.
- **Sessao cliente final:** expira em 7 dias inatividade. Admin 30 dias.

**Roles:**
- `admin`, `campo`, `cliente`, `ai` (nova, para agentes WhatsApp).
- Permissions granulares por recurso/acao (RBAC). Implementadas em decorator `@require(perm)` nos endpoints e checagem em servicos.

---

#### B. APIs REST

**Padrao:** REST + JSON. Versionamento em path: `/api/v1/...`. OpenAPI 3.1 gerado automaticamente pelo FastAPI.

**Convencoes:**
- IDs: UUID v7 (ordenavel temporalmente, melhor para indices).
- Paginacao: cursor-based (`?cursor=...&limit=50`), limit max 100.
- Timestamps: ISO 8601 UTC.
- Erros: RFC 7807 (Problem Details). `{type, title, status, detail, instance, errors[]}`.
- Idempotency-Key header em POSTs criticos (compras, sync de fotos).

**Status codes:**
- 200 OK, 201 Created, 204 No Content
- 400 Validation, 401 Unauthenticated, 403 Forbidden, 404 Not Found
- 409 Conflict (duplicidade, idempotencia), 422 Unprocessable (regra negocio)
- 429 Too Many Requests, 500 Internal, 503 Service Unavailable

**Endpoints principais (resumo por modulo):**

Modulo Gestao:
- `POST /api/v1/clientes` (US-01) | `GET /api/v1/clientes?search=&type=PF|PJ&cursor=`
- `GET/PUT/DELETE /api/v1/clientes/{id}`
- `POST /api/v1/obras` (US-02) | `GET /api/v1/obras?status=&cliente_id=`
- `POST /api/v1/fornecedores` (US-03)
- `POST /api/v1/obras/{id}/documentos` multipart (US-04, US-05); body retorna `upload_url` assinada quando >5MB (direct upload)
- `PATCH /api/v1/documentos/{id}` (categoria, visivel_cliente) (US-06)
- `POST /api/v1/documentos/bulk-visibilidade` body `{ids:[], visivel: bool}` (US-06)
- `POST /api/v1/obras/{id}/tickets` (US-08) | `POST /api/v1/tickets/{id}/mensagens`
- `POST /api/v1/photos/sync` (US-09, ver secao F)
- `POST /api/v1/usuarios/convite` (US-19) | `POST /api/v1/auth/aceitar-convite`
- `GET/PUT /api/v1/templates-email` (US-20)
- `POST /api/v1/exports` (US-21)

Modulo Orcamento:
- `POST /api/v1/obras/{obra_id}/orcamentos` (US-11)
- `POST /api/v1/orcamentos/{id}/versoes` clona versao atual (US-16)
- `GET /api/v1/orcamentos/{id}/versoes/{v}` (read-only se nao for atual)
- `POST /api/v1/orcamentos/versoes/{vid}/fases` (US-12)
- `POST /api/v1/orcamentos/versoes/{vid}/itens/bulk` body batch (DnD, edicoes massa)
- `POST /api/v1/orcamentos/versoes/{vid}/importar-planilha` (US-13)
- `GET /api/v1/orcamentos/versoes/{vid}/curva-abc` (US-14)
- `PUT /api/v1/orcamentos/versoes/{vid}/precificacao` (markup global, fase, item, taxa adm) (US-15)
- `POST /api/v1/orcamentos/versoes/{vid}/pdf` enfileira job (US-17)
- `POST /api/v1/portal/orcamentos/{magic_jti}/decisao` (US-18)
- `GET /api/v1/orcamentos/versoes/comparar?a={v1}&b={v2}` (US-16)

Modulo Agentes:
- `POST /webhook/uazap` (US-24, ver secao C)
- `GET /api/v1/agentes/logs?obra_id=&tipo=&from=&to=` (US-22)
- `POST /api/v1/agentes/logs/{id}/reverter` (US-22)
- `POST /api/v1/agentes/feedback/{interaction_id}` body `{correto: bool}` (RNF-08)
- `PUT /api/v1/agentes/permissoes` mapeia whatsapp -> role IA + limites (US-23)

**Rate limiting:**
- Global API: 600 req/min por usuario autenticado (token bucket via Redis).
- Webhook Uazap: 10 req/min por numero de WhatsApp (US-24, RNF-08). Implementado com sliding window em Redis (key: `rl:wa:{phone}`).
- Endpoints publicos (login, magic): 20 req/min por IP.
- 429 com header `Retry-After`.

---

#### C. Webhook Uazap (US-24)

**Endpoint:** `POST /webhook/uazap`

**Pipeline (sincrono ate enfileirar, depois async):**

1. **Validacao HMAC:** header `X-Uazap-Signature` (HMAC-SHA256 com shared secret). Tolerancia: payload + timestamp <= 5 min para evitar replay. Falha = 401 e log.
2. **Idempotencia:** Uazap envia `message_id`. Checar em Redis SET `wa:msg:seen` (TTL 24h). Se existe, retorna 200 imediato (no-op). Mitiga replay/retries do Uazap (risco listado).
3. **Rate limit:** 10 req/min por numero (RNF-08). Excesso: 429 + log de tentativa.
4. **Resolucao de tenant:** `company_id` resolvido pelo mapeamento `whatsapp_number -> usuario -> company_id`. Numero nao mapeado: resposta template "Numero nao autorizado".
5. **Persistencia + enfileiramento:** insert em `agent_messages(id, company_id, message_id, payload, status='pending', received_at)`. Enfileira job em fila `agent.process`.
6. **Resposta ao Uazap:** 200 com ack rapido (alvo < 500ms). Processamento real e assincrono.

**Fila de mensagens: Redis Streams (decisao)**

PROs Redis Streams (vs PostgreSQL queue):
- Throughput alto (10k+ msg/s), latencia sub-ms.
- Consumer groups nativos (multiplos workers escalam horizontalmente).
- XPENDING + XCLAIM para retry de mensagens travadas.
- Combina com rate limit e cache que ja usaremos.

CONs Redis Streams:
- Persistencia depende de AOF/RDB configurados.
- Mitigacao: **dupla escrita** - registro tambem fica em `agent_messages` (Postgres) como source of truth. Se Redis cair, worker de recovery re-enfileira `status='pending'` mais antigos que 1 min (atende risco "Se Redis/Postgres fica down, mensagens sao perdidas").

Por que nao Postgres-only queue (LISTEN/NOTIFY ou tabela): latencia maior, contencao em alta carga, sem consumer groups nativos. Para o volume previsto (10 req/min/usuario) Postgres aguentaria, mas a estrategia Redis + Postgres backup oferece o melhor dos dois mundos.

**Worker (Arq - async Redis queue para Python):**

Por que Arq vs Celery vs RQ:
- Arq: async-first, integra natural com FastAPI, leve, scheduler embutido.
- Celery: maduro mas pesado, sync-first.
- RQ: simples mas sync.
**Decisao: Arq** para jobs IO-bound (LLM, webhooks). Celery seria escolha se houvesse muito CPU-bound.

**Orquestracao LangGraph:**

Grafo (nodes principais):
1. `intake` - normaliza payload (texto, transcricao Whisper se audio, OCR Tesseract/GPT-4o vision se imagem).
2. `auth` - resolve usuario, role IA (US-23), aplica limites (gasto diario).
3. `intent_classifier` - LLM classifica em: `consulta_orcamento` | `solicitacao_compra` | `aprovacao` | `fora_escopo`.
4. `router` - condicional baseado em intent.
5. `subagent_orcamento` - tools: `get_orcamento_resumo`, `get_status_obra`.
6. `subagent_compras` - tools: `criar_solicitacao_compra`, `validar_limite_orcamento`.
7. `responder` - formata resposta + envia via Uazap API.
8. `audit_log` - persiste interacao completa (US-22, RNF-08).

LLM provider: Anthropic Claude (Sonnet) como primary, OpenAI GPT-4o como fallback automatico. Tools chamadas via function calling com schemas Pydantic gerados.

**Retry logic:**
- Job falha (timeout LLM, erro Uazap, erro DB): re-enfileira com backoff exponencial 30s / 60s / 120s (RNF-08, US-24).
- Max 3 tentativas. Apos esgotar: `status='failed'`, alerta para admin, resposta template ao usuario ("Nao consegui processar, um humano vai te chamar").
- Implementacao: Arq `retry()` + tabela `agent_messages.attempts`.

**Timeout:** processamento total <= 10s. Se ultrapassar 8s sem resposta final, dispara resposta intermediaria ("Processando sua solicitacao, voce recebera confirmacao em breve") e continua em background.

**Fallback se Uazap cair:**
- Health check ativo a cada 30s (`GET /status` da Uazap). Se 3 falhas consecutivas: marca provider como `degraded`.
- Em `degraded`: respostas continuam sendo geradas mas sao armazenadas em `pending_outbound`. Cron tenta entregar a cada 60s ate sucesso ou 24h.
- Modo read-only acionado: subagentes de criacao (compras) sao bloqueados; somente consultas respondidas. Alerta para admin no dashboard.
- SMS como fallback: NAO no MVP V1 (custo + complexidade). Documentado para V2. No MVP, fallback e e-mail para o admin com resumo das interacoes pendentes.

**Health da API Uazap:** metrica `uazap_up` (gauge) + alerta se `degraded` por > 5 min.

---

#### D. Autenticacao e Permissoes

- **Hashing:** Argon2id (passlib). Bcrypt rejeitado por ser mais fraco contra GPU attacks.
- **JWT:** access HS256 (chave em secret manager), claims `sub, company_id, role, perms[], exp, jti`. Refresh em cookie httpOnly + SameSite=Strict.
- **Magic links:** JWT separado com `purpose` claim, single-use via tabela `consumed_tokens(jti PK, consumed_at, expires_at)`. Job de limpeza diario remove expirados.
- **Convite (US-19):** token opaco em tabela `invitations(token_hash, email, company_id, role, expires_at, accepted_at)`. SHA-256 do token armazenado; comparacao constant-time.
- **Authorization middleware:** dependency `get_current_user` valida JWT, hidrata `User`, injeta no request state. Decorator `require_perms("budget.write")` por endpoint. Servicos recebem `User` e revalidam permissao no nivel de objeto (ex: cliente so ve sua obra).
- **Tenant guard:** dependency `get_tenant` extrai `company_id` do JWT, executa `SET LOCAL app.company_id = '...'` na conexao. RLS no Postgres se encarrega do resto.
- **Auditoria:** tabela `audit_log(id, company_id, actor_id, action, resource_type, resource_id, before_jsonb, after_jsonb, ip, ua, created_at)`. Acoes auditadas: alteracao visibilidade (US-06), aprovacao orcamento (US-18), exclusao documento, criacao/remocao usuario (US-19), export (US-21), reverter acao de agente (US-22).

---

#### E. Motor de Calculo (US-12, US-15)

**Precisao:** `Decimal` (Python) com contexto `prec=18, ROUND_HALF_UP`. Armazenamento em Postgres como `NUMERIC(18,6)` para custos unitarios e `NUMERIC(18,2)` para totais consolidados. Por que nao centavos inteiros: orcamentos exigem quantidades fracionarias (0.35 m3 de concreto) e custos com 4-6 decimais; centavos so resolveria parte do problema.

**Hierarquia EAP: Adjacency List + materialized path + cache de subtotais (decisao)**

Avaliacao:
- **Adjacency list pura:** simples, mas recalcular subtotais exige recursao a cada leitura (lento para 1000+ itens).
- **Closure table:** rapido para queries de hierarquia, custoso em escritas (n^2 inserts). EAP edita muito (DnD, bulk), entao escrita pesa.
- **Materialized path + cache:** cada item tem `path` (`fase_id/servico_id/item_id`), `depth`, e `parent_id`. Subtotais (servico, fase, total) sao colunas materializadas em `orcamento_versao` e recalculadas em um pass linear apos cada batch de edicao.

**Decisao:** Adjacency list + materialized path + recalculo em servico dedicado `BudgetCalculator`. Performance alvo: < 300ms para 1000 itens (RNF-01).

**Algoritmo de recalculo (cascata):**
1. Endpoint recebe batch de edicoes (`POST /itens/bulk`).
2. Aplica em memoria (DataFrame ou estrutura propria).
3. Passa 1: calcula custo_total por item (qtd * custo_unit).
4. Passa 2: aplica markup (precedencia: item > fase > global), depois taxa de administracao no subtotal.
5. Passa 3: agrega bottom-up (item -> servico -> fase -> total).
6. Persiste em transacao unica com `SELECT ... FOR UPDATE` na versao do orcamento.
7. Retorna snapshot completo para o front (evita refetch).

Bench obrigatorio: 1000 itens deve completar < 300ms em maquina de producao (RNF-01).

**Cascata de markup:**
- Markup global definido no orcamento.
- Override por fase em `fase.markup_override`.
- Override por item em `item.markup_override`.
- Resolucao: `effective_markup = item.override ?? fase.override ?? global`.
- Taxa de administracao aplicada no subtotal pos-markup.

**Curva ABC (US-14):** computada em memoria pos-recalculo, ordenacao por custo total desc, classificacao A/B/C por percentual acumulado. Cacheada no JSON da versao.

---

#### F. Sincronizacao Mobile - Fila Local (US-09)

**Endpoint:** `POST /api/v1/photos/sync`

**Request:**
```json
{
  "obra_id": "uuid",
  "client_photo_id": "uuid-gerado-no-mobile",
  "captured_at": "ISO8601",
  "sha256": "hex64",
  "size_bytes": 1234567,
  "content_type": "image/jpeg"
}
```

**Fluxo:**
1. Header obrigatorio `Idempotency-Key: {client_photo_id}`.
2. Servidor verifica se `(company_id, client_photo_id)` ja existe -> 409 Conflict + retorna foto existente. Mobile remove da fila local.
3. Se nao existe, verifica se `sha256` ja existe na obra -> 409 (dedup por conteudo).
4. Se ok: cria registro `photos` com status `awaiting_upload` e retorna URL pre-assinada PUT para storage (TTL 15 min).
5. Mobile faz PUT direto no storage.
6. `POST /api/v1/photos/{id}/confirm` finaliza, valida tamanho/hash, marca `synced`.

**Dedup key:** combinacao `client_photo_id` (UUID gerado no device, primario para idempotencia) + `sha256` (secundario para detectar mesma foto duplicada via re-tirada). Por que ambos: cliente pode regerar UUID se reinstalar app; hash protege contra isso.

**Compressao:** feita no client (RNF mobile). Servidor valida `size_bytes <= 2MB` ou rejeita 422.

---

#### G. Storage e Documentos

**Provedor: Supabase Storage** (decisao alinhada com stack do usuario; fallback S3 compativel se necessario).

PROs Supabase:
- Stack ja em uso, integracao nativa com Postgres do projeto.
- URLs assinadas nativas, RLS sobre buckets.
- Region Brasil (sa-east-1 equiv), LGPD-friendly (RNF-05).

CONs:
- Vendor lock-in moderado. Mitigacao: camada de abstracao `StorageClient` permite trocar para S3 puro sem reescrever modulos.

**Buckets:**
- `documents-{env}` - documentos GED. Path `{company_id}/{obra_id}/{doc_id}.{ext}`.
- `photos-{env}` - fotos campo. Path `{company_id}/{obra_id}/{photo_id}.jpg`.
- `pdfs-{env}` - PDFs gerados. Path `{company_id}/orcamentos/{versao_id}.pdf`.
- `exports-{env}` - exports LGPD. TTL automatico 7 dias (US-21).

**URLs assinadas:**
- Upload (PUT): TTL 15 min, content-type lock.
- Download (GET): TTL 1h (RNF-02).
- Geradas sob demanda; nunca armazenadas.

**OCR/Transcricao (US-24 imagens e audios):**
- Audio: Whisper API (OpenAI), 25MB max. Cache de transcricao por sha256 (1 transcricao por arquivo).
- Imagem com texto: GPT-4o Vision (mais robusto que Tesseract para fotos de canteiro).

**PDF (US-17):**
- **Puppeteer server-side** em sidecar Node.js (container separado). Template HTML/CSS + Handlebars. Por que nao pdfmake/ReportLab: layout complexo, logo, tabelas EAP profundas - HTML/CSS e mais produtivo. Custo: 1 container extra.
- Geracao assincrona via job Arq. Resultado salvo em `pdfs-{env}`, vinculado a `orcamento_versao.pdf_url`.
- Target: 500 itens em < 5s (RNF-01). Pool de 3 instancias headless Chrome.

---

#### H. Banco de Dados

**Provedor: PostgreSQL 16 gerenciado via Supabase.**

PROs: ja na stack, RLS nativo, backups gerenciados, conexao pooler (PgBouncer) inclusa.
CONs: limites de conexao no plano basico - mitigado por PgBouncer transaction mode.

**Indices criticos:**
- Todas as FKs.
- `(company_id, status)` em obras, orcamentos, tickets.
- `(company_id, created_at DESC)` para listagens.
- `(obra_id, categoria)` em documentos.
- `(orcamento_versao_id, path)` em itens_eap.
- GIN em `documentos.nome` para busca text (US-05, < 1s para 1000 docs).
- `(whatsapp_number)` em mapeamento agentes.
- `(company_id, received_at)` em agent_messages.

**RLS:** habilitado em todas as tabelas com policy padrao `company_id = current_setting('app.company_id')::uuid`. Tabelas de auth (users, sessions) tem policy especifica.

**Migrations:** Alembic. Forward-only. Cada migration revisada para impacto em RLS.

**Detalhamento de schemas:** delegado para o agente de Database/Arquitetura de Dados.

---

#### I. Jobs e Background Tasks

**Runner: Arq** (mesmo da fila de agentes, simplifica ops).

Filas:
- `agent.process` - mensagens Uazap (alta prioridade).
- `pdf.generate` - geracao PDF (US-17).
- `export.generate` - export LGPD ZIP (US-21).
- `email.send` - notificacoes transacionais (US-08, US-18, US-20).
- `cleanup` - tokens expirados, exports vencidos.
- `agent.retry` - cron 30s checa `agent_messages.status='pending'` mais antigos que 1 min e re-enfileira.

**Export LGPD (US-21):**
- Job pega snapshot por `company_id`, gera arquivos (clientes.json, obras.json, orcamentos.json, documentos.csv, tickets.json), zipa, upload em `exports-{env}`.
- Gera token download single-use, envia e-mail. Link TTL 7 dias, single-use (revoga apos 1 download).
- Max 5 jobs simultaneos por empresa (semaforo via Redis).

**Cron jobs:**
- A cada 30s: retry de fila Uazap.
- A cada 60s: entrega de outbound pendente (Uazap degradado).
- A cada 5 min: health check Uazap, LLM provider, storage.
- Diario 03:00 UTC: limpeza tokens expirados, exports antigos.
- Diario 04:00 UTC: snapshot de metricas de uso (KPIs).

**Backup:** Supabase managed daily backup + PITR 7 dias. Adicionalmente, job semanal exporta `pg_dump` para bucket separado com retention 30 dias (RNF-03). Restore drill mensal (RNF-03).

---

#### J. Monitoring e Observability

**Stack:**
- **Logs:** structlog (JSON) -> stdout -> Grafana Loki (managed via Grafana Cloud free tier inicialmente). Cada log carrega `request_id`, `company_id`, `user_id`, `route`.
- **Metricas:** Prometheus client + Grafana Cloud. Endpoint `/metrics` protegido.
- **Tracing:** OpenTelemetry com exporter para Grafana Tempo. Spans em: HTTP, DB queries lentas (> 100ms), LLM calls, jobs.
- **Erros:** Sentry para exception tracking + alertas.

**Metricas chave:**
- `http_request_duration_seconds` por rota (P95 alvo < 1.5s, RNF-01).
- `budget_recalc_duration_seconds` (alvo P95 < 300ms).
- `agent_response_duration_seconds` (alvo P95 < 5s, RNF-08).
- `agent_interpretation_correct_ratio` (alvo >= 90%).
- `agent_error_ratio` (alvo < 2%).
- `agent_queue_depth` (alerta > 1000).
- `uazap_up`, `llm_up`, `storage_up`.
- `db_pool_in_use`, `db_query_p95`.

**Alertas (PagerDuty ou Discord/Slack webhook no MVP):**
- Fila agente > 1000 por 5 min.
- LLM provider down (3 falhas em 1 min).
- Uazap degraded > 5 min.
- Erro 5xx > 1% por 5 min.
- DB connection saturation > 80%.
- Custo LLM diario > budget configurado (US-23).

---

#### K. Seguranca

- **HTTPS obrigatorio:** TLS 1.2+, HSTS habilitado, redirect 308 de http.
- **CORS:** allowlist explicita: dominio prod, staging, localhost dev. Sem wildcard.
- **SQL injection:** queries parametrizadas via SQLAlchemy Core/ORM exclusivamente. Proibido string concat.
- **Validacao de entrada:** Pydantic v2 schemas com `extra='forbid'` (whitelist). Tamanhos max em strings, listas. Sanitize HTML em campos rich-text (bleach).
- **Rate limiting:** ja descrito secao B.
- **Secrets:** nunca em codigo. Provider: AWS Secrets Manager (ou Doppler/Infisical para MVP). Carregados via env no boot.
- **CSP, X-Frame-Options, X-Content-Type-Options:** headers seguros padrao via middleware.
- **Webhook signature:** HMAC obrigatorio Uazap (secao C), tambem em provider de e-mail e LLM se aplicavel.
- **PII em logs:** redacao automatica de CPF, CNPJ, e-mail, telefone via processor structlog.
- **Senhas:** politica configuravel, min 8 chars, bloqueio temporario apos 5 tentativas (RNF-02).
- **CSRF:** SameSite=Strict + double-submit cookie para endpoints state-changing chamados via cookie.
- **Audit log imutavel:** tabela append-only, sem UPDATE/DELETE em producao (policy nega).

---

#### L. Escalabilidade

- **API stateless:** sessao em JWT + Redis (revogacoes). Permite N replicas atras de load balancer.
- **Horizontal scaling:** Gunicorn 2 workers * 4 threads por container. Autoscale baseado em CPU > 70% e P95 latencia > 1s. Alvo: 200 usuarios simultaneos (RNF-01) com 2-4 containers no MVP.
- **DB connection pool:** PgBouncer transaction mode, pool 25 conexoes por container API, 10 por worker. Total max 200 conexoes no Postgres (compativel com Supabase Pro).
- **Read replicas:** nao no MVP V1. Reservado para V2 quando relatorios pesados (Curva S, Fluxo de caixa) entrarem. RLS funciona em replica.
- **Cache:** Redis usado para rate limit + cache de leitura curta (resumo de orcamento, 30s TTL) + dedup de webhooks.
- **CDN:** documentos servidos via CDN do Supabase Storage (CloudFlare na frente). Reduz egress.
- **LLM cost control:** budget mensal por tier; quando atingir 80% alerta admin, 100% degrada para read-only (US-23).

---

#### M. Deployment e DevOps

**Hosting:**
- API + workers: containers Docker em **Fly.io** (region GRU - Sao Paulo, LGPD friendly, deploy simples, autoscale). Alternativa: Render. Avitar AWS no MVP por custo de ops.
- DB + storage: Supabase (region sa-east-1).
- Redis: Upstash (serverless, multi-region) ou Fly.io Redis.
- Puppeteer sidecar: container separado no mesmo Fly app.

**CI/CD:** GitHub Actions.
- Pipeline: lint (ruff) -> typecheck (mypy) -> unit tests (pytest) -> integration tests (testcontainers Postgres + Redis) -> build imagem -> deploy staging -> smoke tests -> deploy prod (manual approval para prod).
- Cobertura minima: 70% modulos criticos (auth, calculo, agentes).
- Testes obrigatorios: isolamento multi-tenant (tentar acessar obra de outra empresa = 403, RNF-04b), permissoes por role em 100% endpoints sensiveis.

**Estrategia de deploy:** Rolling deploy (Fly.io padrao) - zero downtime (RNF-03). Health check `/health` + `/ready`. Blue-green considerado overkill para MVP.

**Ambientes:**
- `dev` - local docker-compose (Postgres, Redis, MinIO).
- `staging` - replica de prod, dados sinteticos, deploy automatico em merge para main.
- `prod` - deploy manual com approval.

**Secrets:** Doppler ou Infisical no MVP (free tier). Injetados no Fly via integracao. Rotacao: JWT secret a cada 90 dias (com janela de sobreposicao de 7 dias para tokens validos).

**Feature flags:** Unleash self-hosted ou PostHog para liberar Agentes apenas para Pro/Enterprise.

**Observability ja descrita secao J.**

---

#### Resumo de decisoes-chave

| Tema | Decisao |
|---|---|
| Linguagem/Framework | Python 3.12 + FastAPI |
| Arquitetura | Monolito modular |
| Multi-tenant | RLS Postgres + middleware (dupla camada) |
| Auth | Argon2id + JWT access/refresh + magic link single-use |
| API | REST JSON, OpenAPI 3.1, paginacao cursor |
| Fila agentes | Redis Streams + backup em Postgres |
| Worker | Arq (async) |
| Orquestracao IA | LangGraph, LLM primary Claude Sonnet, fallback GPT-4o |
| Calculo orcamento | Decimal + Adjacency list + materialized path |
| Storage | Supabase Storage com URLs assinadas |
| PDF | Puppeteer sidecar |
| OCR/STT | GPT-4o Vision + Whisper |
| DB | PostgreSQL 16 Supabase, RLS |
| Hosting | Fly.io region GRU |
| Observability | Grafana Cloud (Loki + Prometheus + Tempo) + Sentry |
| CI/CD | GitHub Actions, rolling deploy |
| Secrets | Doppler/Infisical |

---

## 10. Especificacao Tecnica — Frontend

Especificacao tecnica detalhada do Frontend/cliente web para o MVP V1. Stack: Next.js 15 (App Router) + React 19 + TypeScript + Tailwind v4 + shadcn/ui.

### Frontend — Arquitetura & Stack

| Camada | Escolha | Versão | Justificativa |
|---|---|---|---|
| Framework | Next.js App Router | 15.x | RSC, streaming, edge-ready, server actions |
| UI runtime | React | 19.x | useFormStatus, useOptimistic, Actions |
| Linguagem | TypeScript strict | 5.6+ | Zero any, type safety end-to-end |
| Estilos | Tailwind v4 | 4.x | CSS-first config, build nativo, tokens OKLCH |
| Componentes | shadcn/ui + Radix | latest | Copy-paste, ownership total, A11y nativo WCAG 2.1 AA |
| Server state | TanStack Query v5 | 5.x | Cache, retry, realtime mutations otimistas |
| Client state | Zustand | 4.x | Stores leves para UI (filtros, drawers, toasts) |
| Forms | RHF + Zod | 7 / 3 | Validação isomórfica client/server |
| Tabelas | TanStack Table v8 | 8.x | Headless, virtualization para 10k+ linhas |
| Datas | date-fns + tz | 3.x | Tree-shakeable, timezone America/Sao_Paulo |
| Realtime | @supabase/supabase-js | 2.x | Channels para tickets, sync de fotos |
| Offline | Dexie v4 | 4.x | IndexedDB wrapper tipado, fila local |
| PWA | @serwist/next | 9.x | Service worker moderno, manifest |
| Testes unit | Vitest + RTL | latest | ESM, rápido, compatível com Next.js |
| Testes E2E | Playwright | latest | Cross-browser, mobile emulation |
| Mock API | MSW v2 | 2.x | Service worker para dev/testes |
| Observability | Sentry + PostHog | latest | Erros + product analytics |

### Frontend — Estrutura de Rotas

```
app/
├─ (auth)/login/page.tsx
├─ (auth)/magic/[token]/page.tsx
├─ (admin)/
│  ├─ dashboard/page.tsx
│  ├─ obras/page.tsx, [id]/page.tsx
│  ├─ orcamentos/page.tsx, [id]/edit/page.tsx
│  ├─ ia/assistente, insights, copiloto
│  └─ tickets/page.tsx
├─ (field)/
│  ├─ minhas-obras/page.tsx
│  ├─ obra/[id]/(checklist|foto|ocorrencia)
│  └─ fila/page.tsx
├─ (portal)/
│  ├─ obra/[token]/page.tsx
│  ├─ obra/[token]/(orcamento|tickets)
└─ api/auth, presign, webhook
```

**Convenções:** Route groups isolam layouts/auth por audiência. Streaming SSR + Suspense em páginas data-heavy. Server Components default, "use client" apenas onde necessário (hooks, browser APIs).

### Frontend — Componentes (Inventário)

| US | Componentes principais | Estados |
|---|---|---|
| US-01 Dashboard | KpiCard, ObrasOverview, AlertList | loading (skeleton), empty, error, success |
| US-02/03 Obras | DataTable, ObraForm (RHF+Zod), FilterBar | form validation, submission |
| US-04 Detalhe obra | ObraHeader, Tabs (cronograma, equipe, docs) | realtime via Supabase channels |
| US-07 Documentos | FileDropzone (drag-drop), DocViewer (PDF/imagem) | upload progress, dedup SHA256 |
| US-08/09 Tickets | TicketForm, TicketChat (realtime via WebSocket) | thread de mensagens, attachments |
| US-11/12 Orçamentos | OrcamentoBuilder (wizard), BdiCalculator (sliders) | recalcula totais < 200ms, denorm em orcamento_versao |
| US-14 Curva ABC | RechartsPareto (gráfico), table ordenada | recalc real-time |
| US-17 PDF | button "Gerar PDF" → `POST /v1/orcamentos/{id}/pdf` | async job, download signed URL |
| US-16/17 Campo | PhotoCapture (input capture), ChecklistItem (toggle) | compressão client-side <400KB, IndexedDB queue |
| US-19/20 Portal | OrcamentoViewer, SignaturePad | magic-link auth, RSC cache 60s |
| US-22/23/24 IA | AssistantChat (streaming SSE), InsightCard, CopilotInline | LLM token streaming, mock via MSW |

**Estados obrigatórios:** Loading (Suspense + skeleton), Empty (CTA), Error (retry button), Offline (SyncStatusBadge + fila).

### Frontend — Mobile-web Responsivo

- **Breakpoints:** `<360px` (field), 360–639 (mobile std), 640–1023 (tablet), 1024+ (admin desktop).
- **Captura de fotos:** `<input type="file" accept="image/*" capture="environment" />` + compressão browser-image-compression (alvo 1600px, q=0.7, <400KB).
- **Fila offline:** Dexie v4 (IndexedDB) + worker de sync 30s retry + `SyncStatusBadge` (X itens pendentes).
- **PWA:** manifest.webmanifest + Serwist service worker (precache app-shell, runtime stale-while-revalidate).
- **Touch targets:** ≥44×44px em (field).

### Frontend — Segurança & Performance

| Aspecto | Implementação |
|---|---|
| XSS | DOMPurify em HTML renderizado (chat IA, notas) |
| CSRF | SameSite=Lax + double-submit em mutações sensíveis |
| CSP | `default-src 'self'; img-src 'self' data: blob: <storage>; connect-src 'self' <api> <supabase>` |
| Secrets | JWT em cookie HttpOnly, nunca localStorage |
| Logs | Mascarar PII (CPF, telefone) em Sentry beforeSend |
| LCP | <2.5s (RSC + streaming, next/image, next/font local) |
| INP | <200ms (useTransition em filtros, evitar handlers pesados) |
| CLS | <0.1 (reservar altura de imagens) |
| JS inicial | <200KB gzip admin, <120KB field (code-split Gantt/Chart) |

**Testes:** Vitest (unit 80%), RTL (componentes), Playwright (12 fluxos críticos), MSW v2 (mocks). Budget falha se JS exceder limites.

---

## 11. Especificacao Tecnica — Database

Especificacao tecnica detalhada do PostgreSQL 16 (Supabase managed, sa-east-1) para o MVP V1.

### Database — Topologia

| Item | Decisão | Justificativa |
|------|---------|---------------|
| Engine | PostgreSQL 16.4 | LTS, RLS nativo, JSONB, logical replication, suporte denorm |
| Hosting | Supabase Pro (managed) | PITR nativo, PgBouncer, Auth integrada, region BR, backups gerenciados |
| Region | sa-east-1 (São Paulo) | LGPD compliance, latência <20ms clientes BR |
| Pooling | PgBouncer transaction mode :6543 | Pool 200 conexões app, 20 admin |
| TLS | sslmode=require obrigatório | RNF-02 segurança em trânsito |
| Replicação | Streaming sync + PITR 7d | RPO <1min, RTO <30min failover automático |
| Backup | pg_dump diário -> S3 30d + managed Supabase | RPO <5min, RTO <60min |

### Database — Schema (21+ tabelas)

**Enums:** user_role (owner, admin, gestor, orcamentista, financeiro, viewer), company_tier (starter, pro, enterprise), obra_status, orcamento_status, invoice_status, documento_tipo, agent_kind, message_role, audit_action.

**Tabelas core:**

1. **companies** — tenant root (cnpj unique, tier enum, is_active)
2. **users** — global, sem company_id direto (email unique, password_hash Argon2id)
3. **user_company_role** — pivot user <-> company (role enum)
4. **clientes** — contratantes (tipo_pessoa PF/PJ, documento unique per company)
5. **obras** — projetos (cliente_id FK, status enum, data_inicio/prevista_fim/real_fim, valor_contrato)
6. **obra_membro** — equipe da obra (obra_id, user_id, papel)
7. **insumo** — catálogo (company_id, codigo unique, categoria, preco_unitario NUMERIC(12,4))
8. **orcamento** — cabeçalho (obra_id FK, versao_atual INT, status enum)
9. **orcamento_versao** — snapshot imutável (numero INT, subtotais denormalizados, is_locked BOOL)
10. **orcamento_item** — linhas EAP (versao_id FK, quantidade, preco_unitario, subtotal GENERATED)
11. **invoice** — NF (numero unique, status enum, data emissao/vencimento/pagamento)
12. **invoice_item** — itens NF
13. **documento** — arquivos GED (storage_path TEXT, sha256 dedup, ocr_text, uploaded_by FK users)
14. **agent_session** — chat IA (company_id, user_id, obra_id, agent_kind enum)
15. **agent_message** — mensagens IA [PARTITIONED RANGE monthly] (role enum, content TEXT, tokens_in/out)
16. **email_template** — templates notificação (company_id nullable=default global)
17. **lgpd_request** — export/deletion/rectification (subject_email, status, payload_path)
18. **audit_log** — append-only [PARTITIONED RANGE monthly] (action enum, entity, entity_id, before/after JSONB)

**Índices críticos:** todas FKs, `(company_id, status)`, `(company_id, created_at DESC)`, GIN trigram nome/descrição, GIN tsvector ocr_text.

### Database — Multi-tenant & RLS

**Defesa em profundidade:**
1. **Middleware (FastAPI):** `SET LOCAL app.company_id = '<uuid>'` no init de cada request
2. **RLS (PostgreSQL):** policy padrão `company_id = current_setting('app.company_id')`

**Exemplo policy (obras):**
```sql
ALTER TABLE obras ENABLE ROW LEVEL SECURITY;
CREATE POLICY obras_tenant_isolation ON obras
  USING (company_id = current_setting('app.company_id', true)::uuid)
  WITH CHECK (company_id = current_setting('app.company_id', true)::uuid);
```

**Teste de isolamento:** SELECT com company_id A, depois B — deve retornar dados diferentes apenas. Testado no CI a cada PR via pytest.

### Database — Garantias de Integridade

| Garantia | Implementação |
|---|---|
| Orçamento aprovado imutável | Trigger bloqueia UPDATE/DELETE se `is_locked=true` |
| Auditoria append-only | REVOKE UPDATE, DELETE on audit_log; insert via SECURITY DEFINER trigger |
| Recalc cascata subtotais | Trigger AFTER INSERT/UPDATE/DELETE on orcamento_item recalcula orcamento_versao |
| FKs com políticas | ON DELETE RESTRICT (tenant, obra) / CASCADE (item de versão) / SET NULL (documento se obra deletada) |

### Database — Performance & Escalabilidade

- **Autovacuum tuning:** hot tables (orcamento_item, agent_message) com `scale_factor=0.05`, audit_log append-only manual vacuum mensal.
- **Particionamento:** audit_log + agent_message particionadas por RANGE (created_at) mensal — drop antiga instantâneo.
- **Denormalizações:** subtotais em orcamento_versao (evita JOIN + recalc em cada SELECT), cache de curva ABC em JSON.
- **PgBouncer transaction mode:** permite N replicas FastAPI stateless.
- **Monitoramento:** pg_stat_statements (queries lentas), pg_stat_user_indexes (índices nunca usados), cache hit ratio (alvo >97%), lag replica (<500ms).

### Database — Compliance (LGPD)

- **PII classification:** users.email, users.phone, clientes.documento (CPF/CNPJ), clientes.endereco = masking em dev dump.
- **Export (US-21):** job coleta linhas por subject_email → ZIP JSON → S3 signed URL TTL 72h.
- **Deletion (right to be forgotten):** soft-delete 30 dias (regret window), depois hard-delete + tombstone em audit_log (retenção legal 5 anos).
- **Data retenção:** invoices/contratos 5 anos (CTN), audit_log 2 anos online + 5 anos cold, agent_messages 90 dias (config tier).

### Database — Backup & PITR (RNF-03)

| Camada | Frequência | Retenção | RTO |
|---|---|---|---|
| WAL archive Supabase | contínuo | 7 dias | <5 min |
| Snapshot Supabase | diário | 7 dias | <30 min |
| pg_dump off-site | diário 03h | 30 dias | <60 min |
| pg_dump GLACIER | mensal | 12 meses | <120 min |

**Restore drill:** mensal (1ª segunda) em DR project — validar checksums críticos, documentar RTO efetivo.

### Database — Migrations (Alembic)

- **Forward-only:** sem downgrade() em prod
- **Zero-downtime:** `CREATE INDEX CONCURRENTLY`, `ADD COLUMN` com default, `SET lock_timeout = 3s`
- **Expand-Contract:** add (nullable/new table) → deploy → backfill → drop (release separado +7 dias)
- **Linter SQL:** squawk bloqueia ADD COLUMN NOT NULL sem default, CREATE INDEX não-concorrente
- **CI gate:** `alembic upgrade head` em base limpa + pytest schema tests

### Database — Operação & Troubleshooting

**Queries diagnóstico:**
- Conexões: `SELECT state, count(*) FROM pg_stat_activity GROUP BY state`
- Locks: `SELECT bl.pid, a.query FROM pg_locks bl JOIN pg_stat_activity a`
- Índices nunca usados: `SELECT indexrelname FROM pg_stat_user_indexes WHERE idx_scan=0`

**Playbooks:** connection pool exausto (kill idle >5m) → disco cheio (pg_repack + resize) → query degradou (ANALYZE + índice?) → replica lag (check transação longa).

---

## 12. Decisões-chave Técnicas (Consolidado)

| Tema | Decisão | Trade-off |
|---|---|---|
| **Backend** | Python/FastAPI + Supabase | DX excelente vs. performance CPU (mitigado: IO-bound workload) |
| **Frontend** | Next.js 15 App Router + shadcn | Setup mais pesado vs. RSC + streaming reduz LCP mobile |
| **Database** | PostgreSQL 16 + RLS + Supabase | Vendor lock-in moderado vs. PITR turn-key + LGPD região BR |
| **Multi-tenant** | Shared schema + RLS dupla camada | Overhead RLS ~5% vs. isolamento criptográfico (safety net) |
| **Orçamento** | Decimal(18,6) + denorm subtotais | Mais storage vs. precision financeira + recalc rápido |
| **Agentes IA** | LangGraph + Claude Sonnet primary + GPT-4o fallback | Latência <5s vs. custo LLM monitorado per tier |
| **Fila Offline** | Dexie + IndexedDB (frontend) + Postgres backup | Duração sync até 30s vs. zero perda em offline |

