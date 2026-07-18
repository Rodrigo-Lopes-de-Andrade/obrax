import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Building2,
  Calculator,
  Check,
  Link as LinkIcon,
  ShieldCheck,
  Sparkles,
  WifiOff,
} from "lucide-react";
import type { Metadata } from "next";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// S12.5 — landing de marketing. Página pública (Server Component estático), sem
// dependência de dados: entra na rota "/" no lugar do antigo redirect p/ o app.
// Os CTAs apontam para /dashboard (entrada do app no build mock-first — não há
// rota de login separada). Copy dos tiers fiel ao PRD §6b.

export const metadata: Metadata = {
  title: "Obrax — Mini-ERP para construtoras e reformadoras",
  description:
    "Gestão de obras, orçamentos precisos, portal do cliente e agentes de IA no " +
    "WhatsApp. Feito para equipes de 1 a 30 pessoas. Autoimplantação em minutos.",
};

type Feature = { icon: typeof Building2; title: string; body: string };

const FEATURES: Feature[] = [
  {
    icon: Building2,
    title: "Gestão de obras",
    body: "Clientes, fornecedores, equipes, documentos (GED) e chamados num só lugar, por obra.",
  },
  {
    icon: Calculator,
    title: "Orçamentos precisos",
    body: "EAP hierárquica, markup, taxa administrativa e curva ABC. PDF pronto para assinar.",
  },
  {
    icon: Bot,
    title: "Agentes de IA no WhatsApp",
    body: "Peça orçamentos e solicite compras por mensagem. O Eugno Faz Tudo responde por você.",
  },
  {
    icon: LinkIcon,
    title: "Portal do cliente",
    body: "Seu cliente aprova orçamentos e acompanha a obra por um link mágico — sem criar senha.",
  },
  {
    icon: WifiOff,
    title: "Campo offline",
    body: "Fotos, checklists e ocorrências no canteiro mesmo sem sinal. Sincroniza sozinho depois.",
  },
  {
    icon: ShieldCheck,
    title: "Multi-tenant seguro",
    body: "Isolamento por empresa com RLS no banco. Seus dados nunca cruzam entre contas.",
  },
];

type Tier = {
  name: string;
  price: string;
  priceNote: string;
  tagline: string;
  features: string[];
  cta: string;
  highlight?: boolean;
};

const TIERS: Tier[] = [
  {
    name: "Basic",
    price: "R$ 99",
    priceNote: "/mês no plano anual (R$ 129 mensal)",
    tagline: "Para autônomos e equipes testando.",
    features: [
      "Até 5 obras ativas",
      "2 usuários",
      "Gestão + Orçamentos",
      "500 documentos · 5 GB",
    ],
    cta: "Começar",
  },
  {
    name: "Pro",
    price: "R$ 299",
    priceNote: "/mês + R$ 49 por usuário adicional",
    tagline: "Para construtoras de 2 a 10 pessoas.",
    features: [
      "Obras e usuários ilimitados",
      "Agentes de IA no WhatsApp (Orçamento + Compras)",
      "Templates de e-mail customizados",
      "100 GB · suporte prioritário",
    ],
    cta: "Assinar Pro",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Sob consulta",
    priceNote: "a partir de R$ 999/mês",
    tagline: "Para operações com várias filiais.",
    features: [
      "Multi-empresa + SSO (SAML/OAuth)",
      "Prompts de IA customizados por cliente",
      "Webhooks e integrações privadas",
      "SLA 99,9% · suporte em 2h",
    ],
    cta: "Falar com vendas",
  },
];

function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-tight">
          <span className="grid size-7 place-items-center rounded-lg bg-primary text-primary-foreground">
            <Building2 aria-hidden className="size-4" />
          </span>
          <span className="text-lg">Obrax</span>
        </Link>
        <nav aria-label="Principal" className="flex items-center gap-1 sm:gap-2">
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <a href="#recursos">Recursos</a>
          </Button>
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <a href="#precos">Preços</a>
          </Button>
          <Button asChild size="sm" className="h-9 px-4">
            <Link href="/dashboard">Entrar</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* brilho de fundo com os acentos da marca */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-40 mx-auto h-80 max-w-4xl rounded-full bg-primary/20 blur-3xl"
      />
      <div className="relative mx-auto max-w-6xl px-6 py-24 text-center sm:py-32">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-subtle-foreground">
          <Sparkles aria-hidden className="size-3.5 text-secondary" />
          Mini-ERP para construtoras e reformadoras
        </span>
        <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-extrabold tracking-tight text-balance sm:text-6xl">
          Controle cada obra do orçamento à entrega.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground text-pretty">
          O Obrax reúne gestão de obras, orçamentos precisos, portal do cliente e agentes de IA no
          WhatsApp — para equipes de 1 a 30 pessoas. Autoimplantação em minutos, sem consultoria.
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button asChild className="h-11 px-6 text-sm">
            <Link href="/dashboard">
              Começar grátis
              <ArrowRight aria-hidden className="size-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" className="h-11 px-6 text-sm">
            <a href="#precos">Ver preços</a>
          </Button>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          A partir de R$ 99/mês · sem cartão para testar
        </p>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section id="recursos" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Tudo o que a obra precisa, sem planilha solta.
        </h2>
        <p className="mt-4 text-muted-foreground text-pretty">
          Do canteiro ao cliente final, em módulos que conversam entre si.
        </p>
      </div>
      <ul className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <li
            key={title}
            className="rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary/40"
          >
            <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
              <Icon aria-hidden className="size-5" />
            </span>
            <h3 className="mt-4 font-semibold">{title}</h3>
            <p className="mt-2 text-sm text-muted-foreground text-pretty">{body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AiBand() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-8">
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card px-8 py-14 text-center">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 mx-auto h-40 max-w-2xl rounded-full bg-secondary/20 blur-3xl"
        />
        <div className="relative">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary/15 px-3 py-1 text-xs font-medium text-secondary">
            <Bot aria-hidden className="size-3.5" />
            Eugno Faz Tudo
          </span>
          <h2 className="mx-auto mt-5 max-w-2xl text-3xl font-bold tracking-tight text-balance">
            Um orçamento por mensagem de WhatsApp.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted-foreground text-pretty">
            Subagentes especializados em Orçamento e Compras acionados por linguagem natural — com
            permissões por papel, limites de gasto e auditoria de cada ação. Disponível nos planos
            Pro e Enterprise.
          </p>
        </div>
      </div>
    </section>
  );
}

function TierCard({ tier }: { tier: Tier }) {
  return (
    <div
      className={cn(
        "flex flex-col rounded-2xl border p-8",
        tier.highlight
          ? "border-primary bg-card shadow-lg shadow-primary/10"
          : "border-border bg-card",
      )}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{tier.name}</h3>
        {tier.highlight && (
          <span className="rounded-full bg-primary/15 px-2.5 py-1 text-xs font-medium text-primary">
            Mais popular
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{tier.tagline}</p>
      <div className="mt-6 flex items-baseline gap-1.5">
        <span className="text-4xl font-extrabold tracking-tight">{tier.price}</span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{tier.priceNote}</p>
      <ul className="mt-6 flex flex-1 flex-col gap-3">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2.5 text-sm">
            <Check aria-hidden className="mt-0.5 size-4 shrink-0 text-success" />
            <span className="text-subtle-foreground">{f}</span>
          </li>
        ))}
      </ul>
      <Button
        asChild
        variant={tier.highlight ? "default" : "outline"}
        className="mt-8 h-11 px-6 text-sm"
      >
        <Link href="/dashboard">{tier.cta}</Link>
      </Button>
    </div>
  );
}

function Pricing() {
  return (
    <section id="precos" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Preço que cabe na primeira obra.
        </h2>
        <p className="mt-4 text-muted-foreground text-pretty">
          Comece no Basic e faça upgrade quando crescer. Sem fidelidade, sem consultoria.
        </p>
      </div>
      <div className="mt-14 grid gap-6 lg:grid-cols-3">
        {TIERS.map((tier) => (
          <TierCard key={tier.name} tier={tier} />
        ))}
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <div className="rounded-2xl border border-border bg-gradient-to-b from-card to-background px-8 py-16 text-center">
        <h2 className="mx-auto max-w-2xl text-3xl font-bold tracking-tight text-balance sm:text-4xl">
          Sua próxima obra pode começar organizada.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground text-pretty">
          Crie sua conta e configure a primeira obra em minutos.
        </p>
        <Button asChild className="mt-8 h-11 px-6 text-sm">
          <Link href="/dashboard">
            Começar agora
            <ArrowRight aria-hidden className="size-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 text-sm text-muted-foreground sm:flex-row">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          <span className="grid size-6 place-items-center rounded-md bg-primary text-primary-foreground">
            <Building2 aria-hidden className="size-3.5" />
          </span>
          Obrax
        </div>
        <nav aria-label="Rodapé" className="flex items-center gap-6">
          <a href="#recursos" className="hover:text-foreground">
            Recursos
          </a>
          <a href="#precos" className="hover:text-foreground">
            Preços
          </a>
          <Link href="/dashboard" className="hover:text-foreground">
            Entrar
          </Link>
        </nav>
        <p>© 2026 Obrax</p>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <Header />
      <main>
        <Hero />
        <Features />
        <AiBand />
        <Pricing />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}
