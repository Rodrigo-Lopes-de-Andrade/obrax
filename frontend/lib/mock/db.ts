/**
 * Store em memória para o MSW (dev). Espelha o comportamento do backend:
 * cursor-based pagination por `id` desc, soft delete, isolamento não é
 * simulado (um único tenant). Trocado por `fetch` real quando o backend
 * estiver plugado.
 */
import type {
  CategoriaOut,
  Cliente,
  CronogramaGradeOut,
  CurvaSOut,
  DespesaOut,
  DespesaPage,
  FaseObraOut,
  DespesaParceladaOut,
  Documento,
  DocumentoTipo,
  FluxoCaixaOut,
  MedicaoAprovadaOut,
  MedicaoDetail,
  MedicaoPage,
  Membro,
  Obra,
  ObraStatus,
  OrcadoRealizadoOut,
  RecebimentoOut,
  RecebimentoPage,
  Ticket,
  TicketMensagem,
  TicketStatus,
  TipoPessoa,
  Usuario,
} from "@/lib/api/types";

let seq = 0;

/**
 * Gera um id UUID-like monotônico por criação — os 12 primeiros dígitos hex
 * (grupos 1-2) codificam `Date.now()+seq` em largura fixa, então a ordem
 * lexicográfica de `id` coincide com a ordem de criação (como UUID v7).
 */
export function nextId(): string {
  const n = (Date.now() - 1_700_000_000_000 + seq++)
    .toString(16)
    .padStart(12, "0");
  const r = Math.random().toString(16).slice(2, 6).padEnd(4, "0");
  return `${n.slice(0, 8)}-${n.slice(8, 12)}-7000-8000-${r}00000000`;
}

/** No mock, o membro guarda `obra_id` para filtrar por obra (a resposta da API
 * o omite — vem implícito na URL). */
export type MockMembro = Membro & { obra_id: string };

export const clientes: Cliente[] = [];
export const obras: Obra[] = [];
export const documentos: Documento[] = [];
export const membros: MockMembro[] = [];
export const usuarios: Usuario[] = [];
export const tickets: Ticket[] = [];
export const mensagens: TicketMensagem[] = [];

/** Usuário "logado" na sessão mock (o backend real vem do JWT). */
export function currentUser(): Usuario {
  return usuarios[0];
}

const nowIso = () => new Date().toISOString();

function fakeSha(): string {
  return Array.from({ length: 64 }, () =>
    Math.floor(Math.random() * 16).toString(16),
  ).join("");
}

function seedCliente(
  nome: string,
  tipo_pessoa: TipoPessoa,
  documento: string,
  telefone: string | null,
  email: string | null,
): Cliente {
  const c: Cliente = {
    id: nextId(),
    tipo_pessoa,
    documento,
    nome,
    telefone,
    email,
    created_at: nowIso(),
  };
  clientes.push(c);
  return c;
}

const STATUSES: ObraStatus[] = [
  "planejamento",
  "execucao",
  "pausada",
  "concluida",
  "cancelada",
];

const OBRA_NOMES = [
  "Residencial Jardim das Acácias",
  "Reforma Comercial Centro",
  "Edifício Aurora",
  "Galpão Logístico BR-101",
  "Condomínio Vista Mar",
  "Retrofit Escritório Faria Lima",
  "Casa de Praia Guarujá",
  "Ampliação Fábrica Norte",
  "Clínica Odontológica Vila Nova",
  "Praça de Alimentação Shopping",
];

function seedObras(): void {
  const total = 64;
  for (let i = 0; i < total; i++) {
    const cliente = clientes[i % clientes.length];
    const status = STATUSES[i % STATUSES.length];
    const inicioMes = (i % 12) + 1;
    const dataInicio = `2026-${String(inicioMes).padStart(2, "0")}-05`;
    const temFim = status !== "planejamento";
    const fimMes = Math.min(inicioMes + 6, 12);
    obras.push({
      id: nextId(),
      cliente_id: cliente.id,
      status,
      codigo: `OBR-${1001 + i}`,
      nome: OBRA_NOMES[i % OBRA_NOMES.length],
      data_inicio: dataInicio,
      data_prevista_fim: temFim
        ? `2026-${String(fimMes).padStart(2, "0")}-20`
        : null,
      data_real_fim: status === "concluida" ? `2026-${String(fimMes).padStart(2, "0")}-18` : null,
      valor_contrato: (120000 + i * 37500).toFixed(2),
      created_at: nowIso(),
    });
  }
}

const USUARIOS_SEED: [string, string][] = [
  ["Marcos Vinícius Prado", "marcos@construtora.com"],
  ["Carla Menezes", "carla@construtora.com"],
  ["Douglas Ferreira", "douglas@construtora.com"],
  ["Patrícia Nunes", "patricia@construtora.com"],
  ["Rafael Antunes", "rafael@construtora.com"],
  ["Juliana Castro", "juliana@construtora.com"],
];

function seedUsuarios(): void {
  for (const [nome, email] of USUARIOS_SEED) {
    usuarios.push({ id: nextId(), nome, email });
  }
}

interface DocSeed {
  nome: string;
  tipo: DocumentoTipo;
  categoria: string | null;
  visivel: boolean;
}

const DOC_SEED: DocSeed[] = [
  { nome: "planta-baixa-pavimento-terreo.pdf", tipo: "projeto", categoria: "Projetos", visivel: true },
  { nome: "contrato-empreitada-global.pdf", tipo: "contrato", categoria: "Contratos", visivel: true },
  { nome: "memorial-descritivo.pdf", tipo: "projeto", categoria: "Projetos", visivel: false },
  { nome: "nf-cimento-votoran-lote12.pdf", tipo: "nota_fiscal", categoria: "Notas Fiscais", visivel: false },
  { nome: "registro-fundacao-01.jpg", tipo: "foto", categoria: "Registro de Obra", visivel: true },
  { nome: "cronograma-fisico-financeiro.xlsx", tipo: "outro", categoria: null, visivel: false },
];

function seedDocumentosParaObra(obraId: string): void {
  for (const d of DOC_SEED) {
    documentos.push({
      id: nextId(),
      obra_id: obraId,
      nome: d.nome,
      tipo: d.tipo,
      categoria: d.categoria,
      visivel_cliente: d.visivel,
      size_bytes: 120_000 + Math.floor(Math.random() * 4_000_000),
      sha256: fakeSha(),
      confirmed: true,
      created_at: nowIso(),
    });
  }
}

const PAPEIS_SEED = ["Mestre de obras", "Eletricista", "Pedreiro"];

function seedMembrosParaObra(obraId: string): void {
  PAPEIS_SEED.forEach((papel, i) => {
    const u = usuarios[i];
    membros.push({
      id: nextId(),
      obra_id: obraId,
      user_id: u.id,
      nome: u.nome,
      email: u.email,
      papel,
      created_at: nowIso(),
    });
  });
}

const hoursAgo = (h: number): string =>
  new Date(Date.now() - h * 3_600_000).toISOString();

const TICKET_STATUSES: TicketStatus[] = [
  "aberto",
  "andamento",
  "resolvido",
  "fechado",
];

const TICKET_SEED: [string, string | null][] = [
  ["Vazamento na laje do 3º pavimento", "Infiltração aparente após a última chuva; verificar impermeabilização."],
  ["Divergência no projeto elétrico", "Prumadas do quadro geral não batem com o executado em campo."],
  ["Atraso na entrega do aço CA-50", "Fornecedor sinalizou remarcação; impacto no cronograma de fundação."],
  ["Solicitação de vistoria do cliente", "Cliente pediu visita técnica para acompanhar o andamento da alvenaria."],
  ["Reparo em fissura na parede oeste", "Fissura de retração mapeada; avaliar tratamento com tela."],
  ["Ajuste no cronograma de concretagem", null],
  ["Falta de EPI no canteiro", "Equipe reportou falta de luvas e óculos de proteção."],
  ["Dúvida sobre acabamento do piso", "Cliente questionou o modelo de porcelanato especificado."],
  ["Revisão da medição do mês", "Divergência de 4% entre medição prevista e realizada."],
  ["Problema no fornecimento de água", "Cavalete sem pressão desde ontem; obra parada no molhado."],
];

function seedTickets(): void {
  const n = obras.length;
  const total = 30;
  for (let i = 0; i < total; i++) {
    const obra = obras[n - 1 - (i % 8)];
    const [titulo, descricao] = TICKET_SEED[i % TICKET_SEED.length];
    tickets.push({
      id: nextId(),
      obra_id: obra.id,
      titulo,
      descricao,
      status: TICKET_STATUSES[i % TICKET_STATUSES.length],
      created_by: usuarios[i % usuarios.length].id,
      created_at: hoursAgo(total - i + (i % 5)),
    });
  }
  // Chat povoado no ticket mais recente (topo da listagem DESC), para demo.
  seedMensagens(tickets[tickets.length - 1]);
}

const CHAT_SEED: [number, string][] = [
  [0, "Bom dia! Registrei o chamado sobre a infiltração na laje."],
  [1, "Recebido. Vamos enviar a equipe de impermeabilização ainda hoje."],
  [1, "Pode nos mandar uma foto do ponto exato do vazamento?"],
  [0, "Claro, segue em anexo a foto tirada agora pela manhã."],
  [1, "Perfeito, identificamos o problema. Orçamento do reparo até amanhã."],
];

function seedMensagens(ticket: Ticket): void {
  // author 0 = cliente (usuarios[1]), 1 = equipe/eu (usuarios[0]).
  const autores = [usuarios[1].id, usuarios[0].id];
  CHAT_SEED.forEach(([autor, content], i) => {
    mensagens.push({
      id: nextId(),
      ticket_id: ticket.id,
      author_id: autores[autor],
      content,
      attachment_paths: content.includes("anexo") ? ["mock/obra/foto-laje.jpg"] : [],
      created_at: hoursAgo(CHAT_SEED.length - i),
    });
  });
}

let seeded = false;

export function ensureSeed(): void {
  if (seeded) return;
  seeded = true;
  seedUsuarios();
  seedCliente("Construtora Vale Verde Ltda", "PJ", "12345678000190", "(11) 3344-5566", "contato@valeverde.com.br");
  seedCliente("Incorporadora Horizonte SA", "PJ", "98765432000121", "(11) 2233-4455", "obras@horizonte.com.br");
  seedCliente("Marina Ribeiro Arquitetura", "PJ", "45678912000134", "(21) 99876-5432", "marina@ribeiroarq.com");
  seedCliente("João Pedro Almeida", "PF", "11144477735", "(11) 98888-1122", "joao.almeida@gmail.com");
  seedCliente("Ana Beatriz Souza", "PF", "52998224725", "(31) 97777-3344", "anabia@outlook.com");
  seedCliente("Construtora Rocha Forte", "PJ", "33444555000188", "(41) 3030-4040", null);
  seedCliente("Roberto Carlos Dias", "PF", "39053344705", null, "roberto.dias@uol.com.br");
  seedCliente("Empreendimentos Sol Nascente", "PJ", "22333444000155", "(11) 4004-5005", "contato@solnascente.com.br");
  seedObras();
  // GED + equipe povoados nas obras mais recentes (topo da listagem DESC, para
  // demo e para a primeira obra clicada já vir com conteúdo).
  const n = obras.length;
  seedDocumentosParaObra(obras[n - 1].id);
  seedDocumentosParaObra(obras[n - 2].id);
  seedMembrosParaObra(obras[n - 1].id);
  seedTickets();
}


// <financeiro-exemplos>
export const FINANCEIRO_EXEMPLOS = {
  "FaseObraOut[]": [
    {
      "id": "01900000-0000-4000-8000-000000000015",
      "codigo": "01",
      "descricao": "Fundação",
      "ativa": true
    },
    {
      "id": "01900000-0000-4000-8000-000000000016",
      "codigo": "02",
      "descricao": "Estrutura",
      "ativa": true
    },
    {
      "id": "01900000-0000-4000-8000-000000000017",
      "codigo": "03",
      "descricao": "Cobertura (removida do orçamento)",
      "ativa": false
    }
  ],
  "CategoriaOut": {
    "id": "01900000-0000-4000-8000-00000000001f",
    "nome": "Materiais",
    "ativa": true,
    "created_at": "2026-01-05T12:00:00Z"
  },
  "CategoriaOut[]": [
    {
      "id": "01900000-0000-4000-8000-00000000001f",
      "nome": "Materiais",
      "ativa": true,
      "created_at": "2026-01-05T12:00:00Z"
    },
    {
      "id": "01900000-0000-4000-8000-000000000020",
      "nome": "Mão de obra",
      "ativa": true,
      "created_at": "2026-01-05T12:00:00Z"
    }
  ],
  "DespesaOut": {
    "id": "01900000-0000-4000-8000-000000000047",
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "obra_fase_id": "01900000-0000-4000-8000-000000000015",
    "fase_descricao": "Fundação",
    "categoria_id": "01900000-0000-4000-8000-00000000001f",
    "categoria_nome": "Materiais",
    "fornecedor_nome": "Concreteira Alfa",
    "fornecedor_id": null,
    "descricao": "Concreto usinado",
    "valor": "12500.00",
    "data_competencia": "2026-01-15",
    "vencimento": "2026-02-10",
    "status": "prevista",
    "data_pagamento": null,
    "documento_id": null,
    "grupo_parcelas_id": null,
    "parcela_num": null,
    "parcela_total": null,
    "created_at": "2026-01-05T12:00:00Z",
    "created_by": "01900000-0000-4000-8000-000000000029"
  },
  "DespesaPage": {
    "items": [
      {
        "id": "01900000-0000-4000-8000-000000000047",
        "obra_id": "01900000-0000-4000-8000-000000000001",
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "fase_descricao": "Fundação",
        "categoria_id": "01900000-0000-4000-8000-00000000001f",
        "categoria_nome": "Materiais",
        "fornecedor_nome": "Concreteira Alfa",
        "fornecedor_id": null,
        "descricao": "Concreto usinado",
        "valor": "12500.00",
        "data_competencia": "2026-01-15",
        "vencimento": "2026-02-10",
        "status": "prevista",
        "data_pagamento": null,
        "documento_id": null,
        "grupo_parcelas_id": null,
        "parcela_num": null,
        "parcela_total": null,
        "created_at": "2026-01-05T12:00:00Z",
        "created_by": "01900000-0000-4000-8000-000000000029"
      },
      {
        "id": "01900000-0000-4000-8000-00000000004b",
        "obra_id": "01900000-0000-4000-8000-000000000001",
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "fase_descricao": "Fundação",
        "categoria_id": "01900000-0000-4000-8000-00000000001f",
        "categoria_nome": "Materiais",
        "fornecedor_nome": "Concreteira Alfa",
        "fornecedor_id": null,
        "descricao": "Aço CA-50",
        "valor": "4500.00",
        "data_competencia": "2026-01-15",
        "vencimento": "2026-02-25",
        "status": "prevista",
        "data_pagamento": null,
        "documento_id": null,
        "grupo_parcelas_id": null,
        "parcela_num": null,
        "parcela_total": null,
        "created_at": "2026-01-05T12:00:00Z",
        "created_by": "01900000-0000-4000-8000-000000000029"
      }
    ],
    "next_cursor": null
  },
  "DespesaParceladaOut": {
    "grupo_parcelas_id": "01900000-0000-4000-8000-000000000050",
    "parcelas": [
      {
        "id": "01900000-0000-4000-8000-000000000048",
        "obra_id": "01900000-0000-4000-8000-000000000001",
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "fase_descricao": "Fundação",
        "categoria_id": "01900000-0000-4000-8000-00000000001f",
        "categoria_nome": "Materiais",
        "fornecedor_nome": "Concreteira Alfa",
        "fornecedor_id": null,
        "descricao": "Armação (1/3)",
        "valor": "3000.00",
        "data_competencia": "2026-01-15",
        "vencimento": "2026-02-10",
        "status": "prevista",
        "data_pagamento": null,
        "documento_id": null,
        "grupo_parcelas_id": "01900000-0000-4000-8000-000000000050",
        "parcela_num": 1,
        "parcela_total": 3,
        "created_at": "2026-01-05T12:00:00Z",
        "created_by": "01900000-0000-4000-8000-000000000029"
      },
      {
        "id": "01900000-0000-4000-8000-000000000049",
        "obra_id": "01900000-0000-4000-8000-000000000001",
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "fase_descricao": "Fundação",
        "categoria_id": "01900000-0000-4000-8000-00000000001f",
        "categoria_nome": "Materiais",
        "fornecedor_nome": "Concreteira Alfa",
        "fornecedor_id": null,
        "descricao": "Armação (2/3)",
        "valor": "3000.00",
        "data_competencia": "2026-01-15",
        "vencimento": "2026-03-10",
        "status": "prevista",
        "data_pagamento": null,
        "documento_id": null,
        "grupo_parcelas_id": "01900000-0000-4000-8000-000000000050",
        "parcela_num": 2,
        "parcela_total": 3,
        "created_at": "2026-01-05T12:00:00Z",
        "created_by": "01900000-0000-4000-8000-000000000029"
      },
      {
        "id": "01900000-0000-4000-8000-00000000004a",
        "obra_id": "01900000-0000-4000-8000-000000000001",
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "fase_descricao": "Fundação",
        "categoria_id": "01900000-0000-4000-8000-00000000001f",
        "categoria_nome": "Materiais",
        "fornecedor_nome": "Concreteira Alfa",
        "fornecedor_id": null,
        "descricao": "Armação (3/3)",
        "valor": "3000.00",
        "data_competencia": "2026-01-15",
        "vencimento": "2026-04-10",
        "status": "prevista",
        "data_pagamento": null,
        "documento_id": null,
        "grupo_parcelas_id": "01900000-0000-4000-8000-000000000050",
        "parcela_num": 3,
        "parcela_total": 3,
        "created_at": "2026-01-05T12:00:00Z",
        "created_by": "01900000-0000-4000-8000-000000000029"
      }
    ]
  },
  "CronogramaGradeOut": {
    "cronograma": {
      "id": "01900000-0000-4000-8000-000000000003",
      "obra_id": "01900000-0000-4000-8000-000000000001",
      "orcamento_versao_id": "01900000-0000-4000-8000-000000000002",
      "periodicidade": "mensal",
      "data_inicio": "2026-01-01",
      "bloqueado_em": null,
      "created_at": "2026-01-05T12:00:00Z"
    },
    "periodos": [
      {
        "id": "01900000-0000-4000-8000-00000000000b",
        "numero": 1,
        "inicio": "2026-01-01",
        "fim": "2026-01-31"
      },
      {
        "id": "01900000-0000-4000-8000-00000000000c",
        "numero": 2,
        "inicio": "2026-02-01",
        "fim": "2026-02-28"
      },
      {
        "id": "01900000-0000-4000-8000-00000000000d",
        "numero": 3,
        "inicio": "2026-03-01",
        "fim": "2026-03-31"
      }
    ],
    "fases": [
      {
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "codigo": "01",
        "descricao": "Fundação",
        "valor_orcado": "100000.00",
        "alocacoes": [
          {
            "periodo_id": "01900000-0000-4000-8000-00000000000b",
            "percentual_planejado": "0.5000",
            "valor_planejado": "50000.00"
          },
          {
            "periodo_id": "01900000-0000-4000-8000-00000000000c",
            "percentual_planejado": "0.3000",
            "valor_planejado": "30000.00"
          },
          {
            "periodo_id": "01900000-0000-4000-8000-00000000000d",
            "percentual_planejado": "0.2000",
            "valor_planejado": "20000.00"
          }
        ]
      },
      {
        "obra_fase_id": "01900000-0000-4000-8000-000000000016",
        "codigo": "02",
        "descricao": "Estrutura",
        "valor_orcado": "50000.00",
        "alocacoes": [
          {
            "periodo_id": "01900000-0000-4000-8000-00000000000b",
            "percentual_planejado": "0.2000",
            "valor_planejado": "10000.00"
          },
          {
            "periodo_id": "01900000-0000-4000-8000-00000000000c",
            "percentual_planejado": "0.4000",
            "valor_planejado": "20000.00"
          },
          {
            "periodo_id": "01900000-0000-4000-8000-00000000000d",
            "percentual_planejado": "0.4000",
            "valor_planejado": "20000.00"
          }
        ]
      }
    ]
  },
  "MedicaoDetail": {
    "id": "01900000-0000-4000-8000-000000000033",
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "cronograma_id": "01900000-0000-4000-8000-000000000003",
    "periodo_id": "01900000-0000-4000-8000-00000000000b",
    "status": "aprovada",
    "aprovada_em": "2026-02-02T12:00:00Z",
    "aprovada_por": "01900000-0000-4000-8000-000000000029",
    "valor_liberado": "60000.00",
    "observacao": "Primeira medição",
    "created_at": "2026-01-05T12:00:00Z",
    "created_by": "01900000-0000-4000-8000-000000000029",
    "itens": [
      {
        "id": "01900000-0000-4000-8000-00000000003d",
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "percentual_acumulado": "0.5000",
        "valor_medido": "50000.00"
      },
      {
        "id": "01900000-0000-4000-8000-00000000003e",
        "obra_fase_id": "01900000-0000-4000-8000-000000000016",
        "percentual_acumulado": "0.2000",
        "valor_medido": "10000.00"
      }
    ]
  },
  "MedicaoPage": {
    "items": [
      {
        "id": "01900000-0000-4000-8000-000000000033",
        "obra_id": "01900000-0000-4000-8000-000000000001",
        "cronograma_id": "01900000-0000-4000-8000-000000000003",
        "periodo_id": "01900000-0000-4000-8000-00000000000b",
        "status": "aprovada",
        "aprovada_em": "2026-02-02T12:00:00Z",
        "aprovada_por": "01900000-0000-4000-8000-000000000029",
        "valor_liberado": "60000.00",
        "observacao": "Primeira medição",
        "created_at": "2026-01-05T12:00:00Z",
        "created_by": "01900000-0000-4000-8000-000000000029"
      }
    ],
    "next_cursor": null
  },
  "MedicaoAprovadaOut": {
    "medicao": {
      "id": "01900000-0000-4000-8000-000000000033",
      "obra_id": "01900000-0000-4000-8000-000000000001",
      "cronograma_id": "01900000-0000-4000-8000-000000000003",
      "periodo_id": "01900000-0000-4000-8000-00000000000b",
      "status": "aprovada",
      "aprovada_em": "2026-02-02T12:00:00Z",
      "aprovada_por": "01900000-0000-4000-8000-000000000029",
      "valor_liberado": "60000.00",
      "observacao": "Primeira medição",
      "created_at": "2026-01-05T12:00:00Z",
      "created_by": "01900000-0000-4000-8000-000000000029",
      "itens": [
        {
          "id": "01900000-0000-4000-8000-00000000003d",
          "obra_fase_id": "01900000-0000-4000-8000-000000000015",
          "percentual_acumulado": "0.5000",
          "valor_medido": "50000.00"
        },
        {
          "id": "01900000-0000-4000-8000-00000000003e",
          "obra_fase_id": "01900000-0000-4000-8000-000000000016",
          "percentual_acumulado": "0.2000",
          "valor_medido": "10000.00"
        }
      ]
    },
    "recebimento": {
      "id": "01900000-0000-4000-8000-000000000034",
      "obra_id": "01900000-0000-4000-8000-000000000001",
      "obra_nome": "Residencial Aurora",
      "medicao_id": "01900000-0000-4000-8000-000000000033",
      "medicao_numero": 1,
      "valor": "60000.00",
      "vencimento": "2026-02-20",
      "status": "previsto",
      "data_recebimento": null,
      "created_at": "2026-02-02T12:00:00Z"
    },
    "aviso": null
  },
  "RecebimentoOut": {
    "id": "01900000-0000-4000-8000-000000000034",
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "obra_nome": "Residencial Aurora",
    "medicao_id": "01900000-0000-4000-8000-000000000033",
    "medicao_numero": 1,
    "valor": "60000.00",
    "vencimento": "2026-02-20",
    "status": "previsto",
    "data_recebimento": null,
    "created_at": "2026-02-02T12:00:00Z"
  },
  "RecebimentoPage": {
    "items": [
      {
        "id": "01900000-0000-4000-8000-000000000034",
        "obra_id": "01900000-0000-4000-8000-000000000001",
        "obra_nome": "Residencial Aurora",
        "medicao_id": "01900000-0000-4000-8000-000000000033",
        "medicao_numero": 1,
        "valor": "60000.00",
        "vencimento": "2026-02-20",
        "status": "previsto",
        "data_recebimento": null,
        "created_at": "2026-02-02T12:00:00Z"
      }
    ],
    "next_cursor": null
  },
  "OrcadoRealizadoOut": {
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "tem_orcamento_aprovado": true,
    "orcamento_versao_id": "01900000-0000-4000-8000-000000000002",
    "fases": [
      {
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "codigo": "01",
        "descricao": "Fundação",
        "ativa": true,
        "orcado": "100000.00",
        "realizado": "25000.00",
        "comprometido": "5000.00",
        "saldo": "70000.00",
        "percentual_consumido": "0.3000",
        "estourou": false
      },
      {
        "obra_fase_id": "01900000-0000-4000-8000-000000000016",
        "codigo": "02",
        "descricao": "Estrutura",
        "ativa": true,
        "orcado": "50000.00",
        "realizado": "40000.00",
        "comprometido": "12000.00",
        "saldo": "-2000.00",
        "percentual_consumido": "1.0400",
        "estourou": true
      }
    ],
    "totais": {
      "orcado": "150000.00",
      "realizado": "65000.00",
      "comprometido": "17000.00",
      "saldo": "68000.00",
      "percentual_consumido": "0.5467"
    }
  },
  "CurvaSOut": {
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "tem_cronograma": true,
    "pontos": [
      {
        "periodo_id": "01900000-0000-4000-8000-00000000000b",
        "numero": 1,
        "inicio": "2026-01-01",
        "fim": "2026-01-31",
        "corrente": false,
        "planejado_acumulado": "60000.00",
        "medido_acumulado": "60000.00",
        "realizado_acumulado": "30000.00"
      },
      {
        "periodo_id": "01900000-0000-4000-8000-00000000000c",
        "numero": 2,
        "inicio": "2026-02-01",
        "fim": "2026-02-28",
        "corrente": true,
        "planejado_acumulado": "110000.00",
        "medido_acumulado": "60000.00",
        "realizado_acumulado": "65000.00"
      },
      {
        "periodo_id": "01900000-0000-4000-8000-00000000000d",
        "numero": 3,
        "inicio": "2026-03-01",
        "fim": "2026-03-31",
        "corrente": false,
        "planejado_acumulado": "150000.00",
        "medido_acumulado": "60000.00",
        "realizado_acumulado": "65000.00"
      }
    ]
  },
  "FluxoCaixaOut": {
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "de": "2026-01-01",
    "ate": "2026-03-31",
    "periodicidade": "mensal",
    "periodos": [
      {
        "inicio": "2026-01-01",
        "fim": "2026-01-31",
        "saidas_previstas": "30000.00",
        "saidas_realizadas": "25000.00",
        "entradas_previstas": "0.00",
        "entradas_realizadas": "0.00",
        "saldo_previsto": "-30000.00",
        "saldo_realizado": "-25000.00",
        "saldo_previsto_acumulado": "-30000.00",
        "saldo_realizado_acumulado": "-25000.00"
      },
      {
        "inicio": "2026-02-01",
        "fim": "2026-02-28",
        "saidas_previstas": "20000.00",
        "saidas_realizadas": "40000.00",
        "entradas_previstas": "60000.00",
        "entradas_realizadas": "60000.00",
        "saldo_previsto": "40000.00",
        "saldo_realizado": "20000.00",
        "saldo_previsto_acumulado": "10000.00",
        "saldo_realizado_acumulado": "-5000.00"
      },
      {
        "inicio": "2026-03-01",
        "fim": "2026-03-31",
        "saidas_previstas": "0.00",
        "saidas_realizadas": "0.00",
        "entradas_previstas": "0.00",
        "entradas_realizadas": "0.00",
        "saldo_previsto": "0.00",
        "saldo_realizado": "0.00",
        "saldo_previsto_acumulado": "10000.00",
        "saldo_realizado_acumulado": "-5000.00"
      }
    ]
  },
  "MedicaoDetail#rascunho": {
    "id": "01900000-0000-4000-8000-000000000035",
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "cronograma_id": "01900000-0000-4000-8000-000000000003",
    "periodo_id": "01900000-0000-4000-8000-00000000000c",
    "status": "rascunho",
    "aprovada_em": null,
    "aprovada_por": null,
    "valor_liberado": null,
    "observacao": "Segunda medição (em preenchimento)",
    "created_at": "2026-01-05T12:00:00Z",
    "created_by": "01900000-0000-4000-8000-000000000029",
    "itens": [
      {
        "id": "01900000-0000-4000-8000-00000000003f",
        "obra_fase_id": "01900000-0000-4000-8000-000000000015",
        "percentual_acumulado": "0.5000",
        "valor_medido": "50000.00"
      },
      {
        "id": "01900000-0000-4000-8000-000000000040",
        "obra_fase_id": "01900000-0000-4000-8000-000000000016",
        "percentual_acumulado": "0.2000",
        "valor_medido": "10000.00"
      }
    ]
  },
  "DespesaOut#cancelada": {
    "id": "01900000-0000-4000-8000-000000000047",
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "obra_fase_id": "01900000-0000-4000-8000-000000000015",
    "fase_descricao": "Fundação",
    "categoria_id": "01900000-0000-4000-8000-00000000001f",
    "categoria_nome": "Materiais",
    "fornecedor_nome": "Concreteira Alfa",
    "fornecedor_id": null,
    "descricao": "Concreto usinado",
    "valor": "12500.00",
    "data_competencia": "2026-01-15",
    "vencimento": "2026-02-10",
    "status": "cancelada",
    "data_pagamento": null,
    "documento_id": null,
    "grupo_parcelas_id": null,
    "parcela_num": null,
    "parcela_total": null,
    "created_at": "2026-01-05T12:00:00Z",
    "created_by": "01900000-0000-4000-8000-000000000029"
  },
  "DespesaOut#paga": {
    "id": "01900000-0000-4000-8000-000000000047",
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "obra_fase_id": "01900000-0000-4000-8000-000000000015",
    "fase_descricao": "Fundação",
    "categoria_id": "01900000-0000-4000-8000-00000000001f",
    "categoria_nome": "Materiais",
    "fornecedor_nome": "Concreteira Alfa",
    "fornecedor_id": null,
    "descricao": "Concreto usinado",
    "valor": "12500.00",
    "data_competencia": "2026-01-15",
    "vencimento": "2026-02-10",
    "status": "paga",
    "data_pagamento": "2026-02-10",
    "documento_id": null,
    "grupo_parcelas_id": null,
    "parcela_num": null,
    "parcela_total": null,
    "created_at": "2026-01-05T12:00:00Z",
    "created_by": "01900000-0000-4000-8000-000000000029"
  },
  "RecebimentoOut#recebido": {
    "id": "01900000-0000-4000-8000-000000000034",
    "obra_id": "01900000-0000-4000-8000-000000000001",
    "obra_nome": "Residencial Aurora",
    "medicao_id": "01900000-0000-4000-8000-000000000033",
    "medicao_numero": 1,
    "valor": "60000.00",
    "vencimento": "2026-02-20",
    "status": "recebido",
    "data_recebimento": "2026-02-20",
    "created_at": "2026-02-02T12:00:00Z"
  },
  "MedicaoAprovadaOut#sem_recebimento": {
    "medicao": {
      "id": "01900000-0000-4000-8000-000000000033",
      "obra_id": "01900000-0000-4000-8000-000000000001",
      "cronograma_id": "01900000-0000-4000-8000-000000000003",
      "periodo_id": "01900000-0000-4000-8000-00000000000b",
      "status": "aprovada",
      "aprovada_em": "2026-02-02T12:00:00Z",
      "aprovada_por": "01900000-0000-4000-8000-000000000029",
      "valor_liberado": null,
      "observacao": "Primeira medição",
      "created_at": "2026-01-05T12:00:00Z",
      "created_by": "01900000-0000-4000-8000-000000000029",
      "itens": [
        {
          "id": "01900000-0000-4000-8000-00000000003d",
          "obra_fase_id": "01900000-0000-4000-8000-000000000015",
          "percentual_acumulado": "0.5000",
          "valor_medido": "50000.00"
        },
        {
          "id": "01900000-0000-4000-8000-00000000003e",
          "obra_fase_id": "01900000-0000-4000-8000-000000000016",
          "percentual_acumulado": "0.2000",
          "valor_medido": "10000.00"
        }
      ]
    },
    "recebimento": null,
    "aviso": "Medição aprovada, mas a obra não tem valor de contrato: nenhum recebimento foi gerado. Informe o valor do contrato para liberar o valor."
  }
} as const;
// </financeiro-exemplos>

// ---------------------------------------------------------------------------
// Checagem de tipo do bloco acima contra `types.ts` (só tsc; sem efeito em runtime).
// Fica fora do bloco porque o teste de contrato lê aquele trecho como JSON.
//
// `as const` torna tudo readonly (e arrays viram tuplas), então a checagem usa
// `DeepReadonly<Tipo>`. Atribuição pega campo FALTANDO ou de tipo errado no mock;
// ela não pega campo SOBRANDO (objeto não-literal não sofre excess property check),
// por isso `Sobra` lista, recursivamente, as chaves do mock que o tipo não declara.
// ---------------------------------------------------------------------------
type DeepReadonly<T> = T extends readonly (infer U)[]
  ? readonly DeepReadonly<U>[]
  : T extends object
    ? { readonly [K in keyof T]: DeepReadonly<T[K]> }
    : T;

type Sobra<L, T> = L extends readonly (infer LU)[]
  ? T extends readonly (infer TU)[]
    ? Sobra<LU, TU>
    : never
  : L extends object
    ? T extends object
      ? { [K in keyof L]: K extends keyof T ? Sobra<L[K], NonNullable<T[K]>> : K }[keyof L]
      : never
    : never;

type Exemplos = typeof FINANCEIRO_EXEMPLOS;
type Esperado = {
  "FaseObraOut[]": FaseObraOut[];
  CategoriaOut: CategoriaOut;
  "CategoriaOut[]": CategoriaOut[];
  DespesaOut: DespesaOut;
  "DespesaOut#cancelada": DespesaOut;
  "DespesaOut#paga": DespesaOut;
  DespesaPage: DespesaPage;
  DespesaParceladaOut: DespesaParceladaOut;
  CronogramaGradeOut: CronogramaGradeOut;
  MedicaoDetail: MedicaoDetail;
  "MedicaoDetail#rascunho": MedicaoDetail;
  MedicaoPage: MedicaoPage;
  MedicaoAprovadaOut: MedicaoAprovadaOut;
  "MedicaoAprovadaOut#sem_recebimento": MedicaoAprovadaOut;
  RecebimentoOut: RecebimentoOut;
  "RecebimentoOut#recebido": RecebimentoOut;
  RecebimentoPage: RecebimentoPage;
  OrcadoRealizadoOut: OrcadoRealizadoOut;
  CurvaSOut: CurvaSOut;
  FluxoCaixaOut: FluxoCaixaOut;
};

// Chave a chave: falta/sobra de chave no bloco ou no mapa acima também falha.
export const _checaExemplos: { [K in keyof Esperado]: DeepReadonly<Esperado[K]> } = FINANCEIRO_EXEMPLOS;
export type _ChavesIguais = keyof Exemplos extends keyof Esperado
  ? keyof Esperado extends keyof Exemplos
    ? true
    : never
  : never;
export const _chavesIguais: _ChavesIguais = true;
export type _SemCampoSobrando = {
  [K in keyof Exemplos & keyof Esperado]: Sobra<Exemplos[K], Esperado[K]>;
}[keyof Exemplos & keyof Esperado];
export const _semSobra: [_SemCampoSobrando] extends [never] ? true : _SemCampoSobrando = true;
