"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Building,
  ChevronDown,
  Search,
  Bell,
  MessagesSquare,
  Star,
  Settings,
  CreditCard,
  LogOut,
} from "lucide-react";
import { Avatar } from "@/components/shared/Avatar";
import { useUiStore } from "@/state/ui";
import { useMe } from "@/lib/hooks/use-session";
import { logout } from "@/lib/api/auth";
import { useOnClickOutside } from "@/lib/hooks/use-on-click-outside";

export function Topbar() {
  const router = useRouter();
  const { data: me } = useMe();
  const avatarOpen = useUiStore((s) => s.avatarMenuOpen);
  const toggleAvatarMenu = useUiStore((s) => s.toggleAvatarMenu);
  const closeAvatarMenu = useUiStore((s) => s.closeAvatarMenu);
  const menuRef = useRef<HTMLDivElement>(null);
  useOnClickOutside(menuRef, closeAvatarMenu);

  const nome = me?.nome ?? "";
  const email = me?.email ?? "";

  async function handleLogout() {
    closeAvatarMenu();
    await logout();
    router.push("/login");
  }

  return (
    <header className="flex h-17 flex-shrink-0 items-center gap-4.5 border-b border-white/5 bg-background px-6">
      <button
        type="button"
        onClick={() => router.push("/obras")}
        className="flex items-center gap-2 rounded-lg border border-white/7 bg-muted px-3.5 py-2 text-[13.5px] font-semibold"
      >
        <Building className="h-4 w-4 text-primary" />
        Obras
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
      </button>

      <div className="relative max-w-110 flex-1">
        <Search className="absolute top-1/2 left-3.5 h-4.5 w-4.5 -translate-y-1/2 text-muted-foreground/70" />
        <input
          type="text"
          placeholder="Buscar obras, clientes, insumos…"
          className="w-full rounded-lg border border-white/6 bg-muted py-2.5 pr-3 pl-10 text-[13.5px] outline-none placeholder:text-muted-foreground/70"
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          aria-label="Notificações"
          className="relative flex h-9.5 w-9.5 items-center justify-center rounded-[9px] border border-white/6 bg-muted text-muted-foreground hover:bg-white/8 hover:text-foreground"
        >
          <Bell className="h-4.5 w-4.5" />
          <span className="absolute top-2 right-2 h-1.75 w-1.75 rounded-full border-[1.5px] border-muted bg-primary" />
        </button>
        <button
          type="button"
          aria-label="Mensagens"
          className="flex h-9.5 w-9.5 items-center justify-center rounded-[9px] border border-white/6 bg-muted text-muted-foreground hover:bg-white/8 hover:text-foreground"
        >
          <MessagesSquare className="h-4.5 w-4.5" />
        </button>

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
                <div className="text-sm font-bold">{nome || "—"}</div>
                <div className="mt-px text-xs text-muted-foreground">{email}</div>
                {me?.role && (
                  <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-secondary/16 px-2.5 py-0.75 text-[11px] font-bold text-secondary capitalize">
                    <Star className="h-3 w-3" />
                    {me.role}
                  </div>
                )}
              </div>
              <div className="p-1.5">
                <DropdownItem icon={Settings} label="Configurações" onClick={closeAvatarMenu} />
                <DropdownItem icon={CreditCard} label="Meu plano" onClick={closeAvatarMenu} />
                <DropdownItem icon={LogOut} label="Sair" danger onClick={handleLogout} />
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
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  danger?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full cursor-pointer items-center gap-2.75 rounded-[7px] px-2.75 py-2.25 text-left text-[13.5px] font-medium hover:bg-white/5 hover:text-foreground ${
        danger ? "text-primary" : "text-subtle-foreground"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}
