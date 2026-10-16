"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronDown, Bell, MessagesSquare, Star, Settings, CreditCard, LogOut } from "lucide-react";
import { Avatar } from "@/components/shared/Avatar";
import { useUiStore } from "@/state/ui";
import { useOnClickOutside } from "@/lib/hooks/use-on-click-outside";
import { useMe } from "@/lib/hooks/use-session";
import { logout } from "@/lib/api/auth";
import { useDashboardSummary } from "@/lib/hooks/use-dashboard";
import { GlobalSearch } from "@/components/shared/GlobalSearch";

export function Topbar() {
  const router = useRouter();
  const { data: me } = useMe();
  const abertos = useDashboardSummary().data?.tickets_abertos ?? 0;
  const [saindo, setSaindo] = useState(false);
  const avatarOpen = useUiStore((s) => s.avatarMenuOpen);
  const toggleAvatarMenu = useUiStore((s) => s.toggleAvatarMenu);
  const closeAvatarMenu = useUiStore((s) => s.closeAvatarMenu);
  const menuRef = useRef<HTMLDivElement>(null);
  useOnClickOutside(menuRef, closeAvatarMenu);

  // `logout` já limpa a sessão local mesmo se a revogação no backend falhar, então
  // a navegação para /login acontece nos dois caminhos.
  async function sair() {
    setSaindo(true);
    await logout();
    router.replace("/login");
  }

  // Até o /auth/me responder, mostra o e-mail vazio em vez de um usuário inventado.
  const nome = me?.nome ?? "";
  const email = me?.email ?? "";

  return (
    <header className="flex h-17 flex-shrink-0 items-center gap-4.5 border-b border-white/5 bg-background px-6">
      <GlobalSearch />

      <div className="ml-auto flex items-center gap-2">
        {/* Sino = chamados abertos (contagem real do /dashboard/summary). */}
        <Link
          href="/tickets"
          aria-label={
            abertos ? `Chamados abertos: ${abertos}` : "Chamados — nenhum aberto"
          }
          title="Chamados abertos"
          className="relative flex h-9.5 w-9.5 items-center justify-center rounded-[9px] border border-white/6 bg-muted text-muted-foreground hover:bg-white/8 hover:text-foreground"
        >
          <Bell className="h-4.5 w-4.5" />
          {abertos > 0 && (
            <span className="absolute -top-1.5 -right-1.5 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground tabular-nums">
              {abertos > 99 ? "99+" : abertos}
            </span>
          )}
        </Link>
        <Link
          href="/ia/assistente"
          aria-label="Assistente IA"
          title="Assistente IA"
          className="flex h-9.5 w-9.5 items-center justify-center rounded-[9px] border border-white/6 bg-muted text-muted-foreground hover:bg-white/8 hover:text-foreground"
        >
          <MessagesSquare className="h-4.5 w-4.5" />
        </Link>

        <div className="mx-1 h-6.5 w-px bg-white/8" />

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={toggleAvatarMenu}
            aria-label="Menu do usuário"
            aria-expanded={avatarOpen}
            className="flex items-center gap-2 rounded-full border-none bg-transparent p-0.75"
          >
            <Avatar name={nome} variant="gradient" className="size-9 text-[13px]" />
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </button>

          {avatarOpen && (
            <div className="absolute top-12 right-0 z-40 w-57 overflow-hidden rounded-[10px] border border-white/8 bg-popover shadow-[0_20px_60px_rgba(0,0,0,0.6)]">
              <div className="border-b border-white/6 px-4 py-3.5">
                <div className="text-sm font-bold">{nome}</div>
                <div className="mt-px text-xs text-muted-foreground">{email}</div>
                {me && (
                  <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-secondary/16 px-2.5 py-0.75 text-[11px] font-bold text-secondary capitalize">
                    <Star className="h-3 w-3" />
                    {me.role}
                  </div>
                )}
              </div>
              <div className="p-1.5">
                <DropdownItem icon={Settings} label="Configurações" disabled />
                <DropdownItem icon={CreditCard} label="Meu plano" disabled />
                <DropdownItem
                  icon={LogOut}
                  label={saindo ? "Saindo…" : "Sair"}
                  danger
                  onClick={sair}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function DropdownItem({
  icon: Icon,
  label,
  danger,
  disabled,
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  danger?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={disabled ? "Em breve" : undefined}
      className={`flex w-full items-center gap-2.75 rounded-[7px] px-2.75 py-2.25 text-left text-[13.5px] font-medium ${
        disabled
          ? "cursor-not-allowed text-muted-foreground/50"
          : `cursor-pointer hover:bg-white/5 hover:text-foreground ${danger ? "text-primary" : "text-subtle-foreground"}`
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}
