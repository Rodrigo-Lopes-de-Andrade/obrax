"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { login } from "@/lib/api/auth";

/** Separa "a culpa é da credencial" de "a culpa é do sistema": com um 5xx genérico
 * o usuário acha que errou a senha e fica tentando de novo. */
function loginErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return "E-mail ou senha inválidos.";
    if (err.status === 422) return "Confira o e-mail e a senha informados.";
    if (err.status === 429) return "Muitas tentativas. Aguarde alguns minutos e tente de novo.";
    if (err.status >= 500) {
      return "O sistema está indisponível no momento. Sua senha não é o problema — tente novamente em alguns minutos.";
    }
  } else if (err instanceof TypeError) {
    // fetch rejeita com TypeError quando não chega ao servidor (rede/CORS).
    return "Não foi possível falar com o servidor. Verifique sua conexão e tente de novo.";
  }
  return "Não foi possível entrar. Tente novamente.";
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(loginErrorMessage(err));
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-6 text-foreground">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center justify-center gap-2 font-bold tracking-tight">
          <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
            <Building2 aria-hidden className="size-4.5" />
          </span>
          <span className="text-xl">Obrax</span>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-border bg-card p-8 shadow-lg shadow-black/20"
        >
          <h1 className="text-lg font-semibold">Entrar</h1>
          <p className="mt-1 text-sm text-muted-foreground">Acesse o painel da sua obra.</p>

          <div className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="voce@empresa.com.br"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && (
            <p role="alert" className="mt-4 text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" disabled={loading} className="mt-6 h-10 w-full text-sm">
            {loading && <Loader2 aria-hidden className="size-4 animate-spin" />}
            Entrar
          </Button>
        </form>
      </div>
    </div>
  );
}
