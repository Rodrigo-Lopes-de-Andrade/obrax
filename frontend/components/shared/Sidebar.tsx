"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  HardHat,
  LayoutDashboard,
  Building2,
  Users,
  FileText,
  MessageSquare,
  ShoppingCart,
  Wallet,
  BarChart3,
  Bot,
  ShieldCheck,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/state/ui";

const navGestao = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { label: "Obra", icon: Building2, href: "/obras" },
  { label: "Chamados", icon: MessageSquare, href: "/tickets" },
  { label: "Clientes", icon: Users, href: "#" },
  { label: "Orçamentos", icon: FileText, href: "/orcamentos" },
];

const navV2 = [
  { label: "Compras", icon: ShoppingCart, href: "#", disabled: true },
  { label: "Financeiro", icon: Wallet, href: "#", disabled: true },
];

const navRelatorios = [{ label: "Relatórios", icon: BarChart3, href: "#" }];

const navIa = [
  { label: "Assistente IA", icon: Bot, href: "#" },
  { label: "Auditoria IA", icon: ShieldCheck, href: "#" },
];

export function Sidebar() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const pathname = usePathname();
  const isActive = (href: string) => href !== "#" && pathname.startsWith(href);

  return (
    <aside
      className={cn(
        "flex flex-shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar p-3.5 transition-[width] duration-200",
        collapsed ? "w-16 px-2" : "w-62",
      )}
    >
      <div className="flex items-center gap-2.5 px-2 pt-1.5 pb-3.5">
        <div className="flex h-9.5 w-9.5 flex-shrink-0 items-center justify-center rounded-[9px] bg-primary shadow-[0_4px_14px_rgba(255,107,107,0.35)]">
          <HardHat className="h-5.5 w-5.5 text-white" />
        </div>
        {!collapsed && (
          <div className="text-xl font-extrabold tracking-tight">
            Obra<span className="text-primary">x</span>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={toggleSidebar}
        title="Recolher menu"
        className={cn(
          "mb-2 flex items-center px-2 py-1 text-muted-foreground/70 hover:text-foreground",
          collapsed ? "justify-center" : "justify-end",
        )}
      >
        {collapsed ? <PanelLeftOpen className="h-4.5 w-4.5" /> : <PanelLeftClose className="h-4.5 w-4.5" />}
      </button>

      {!collapsed && (
        <div className="px-2 pt-2 pb-2 text-[10px] font-bold tracking-[0.09em] text-muted-foreground/70 uppercase">
          Gestão
        </div>
      )}
      <nav className="flex flex-col gap-0.5">
        {navGestao.map((item) => (
          <SidebarLink
            key={item.label}
            {...item}
            active={isActive(item.href)}
            collapsed={collapsed}
          />
        ))}
        {navV2.map((item) => (
          <SidebarLink key={item.label} {...item} collapsed={collapsed} />
        ))}
      </nav>

      {!collapsed && (
        <div className="px-2 pt-4 pb-2 text-[10px] font-bold tracking-[0.09em] text-muted-foreground/70 uppercase">
          Análise
        </div>
      )}
      <nav className="flex flex-col gap-0.5">
        {navRelatorios.map((item) => (
          <SidebarLink
            key={item.label}
            {...item}
            active={isActive(item.href)}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {!collapsed && (
        <div className="px-2 pt-4 pb-2 text-[10px] font-bold tracking-[0.09em] text-muted-foreground/70 uppercase">
          Inteligência
        </div>
      )}
      <nav className="flex flex-col gap-0.5">
        {navIa.map((item) => (
          <SidebarLink
            key={item.label}
            {...item}
            active={isActive(item.href)}
            collapsed={collapsed}
          />
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-0.5">
        <SidebarLink label="Configurações" icon={Settings} href="#" collapsed={collapsed} />
        <div className="mt-1.5 flex items-center gap-2.5 rounded-[10px] border border-white/5 bg-popover px-2.5 py-2.5">
          <div className="flex h-8.5 w-8.5 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-secondary to-[var(--chart-4)] text-[13px] font-bold">
            MA
          </div>
          {!collapsed && (
            <div className="min-w-0 leading-tight">
              <div className="truncate text-[13px] font-semibold">Marina Alves</div>
              <div className="text-[11px] text-muted-foreground">Engenheira</div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function SidebarLink({
  label,
  icon: Icon,
  href,
  active,
  disabled,
  collapsed,
  onClick,
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  active?: boolean;
  disabled?: boolean;
  collapsed?: boolean;
  onClick?: () => void;
}) {
  const content = (
    <>
      {active && (
        <span className="absolute top-[9px] bottom-[9px] left-0 w-[3px] rounded-[3px] bg-primary" />
      )}
      <Icon className="h-4.5 w-4.5 flex-shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </>
  );

  const className = cn(
    "relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
    collapsed && "justify-center",
    active
      ? "bg-primary/12 font-semibold text-foreground"
      : disabled
        ? "cursor-not-allowed text-muted-foreground/50"
        : "text-muted-foreground hover:bg-white/5 hover:text-foreground",
  );

  if (disabled) {
    return (
      <div className={cn(className, "group")} title="Em breve">
        {content}
      </div>
    );
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {content}
      </button>
    );
  }

  return (
    <Link href={href} className={className}>
      {content}
    </Link>
  );
}
