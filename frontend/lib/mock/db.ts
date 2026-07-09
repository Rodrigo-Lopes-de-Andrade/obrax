/**
 * Store em memória para o MSW (dev). Espelha o comportamento do backend:
 * cursor-based pagination por `id` desc, soft delete, isolamento não é
 * simulado (um único tenant). Trocado por `fetch` real quando o backend
 * estiver plugado.
 */
import type {
  Cliente,
  Documento,
  DocumentoTipo,
  Membro,
  Obra,
  ObraStatus,
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
}
