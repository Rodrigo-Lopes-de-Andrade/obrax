import { api } from "./client";
import type { Me } from "./types";

/**
 * Usuário autenticado da sessão. `nome`/`email` vêm da tabela `users`; `role` é
 * o do vínculo carregado no JWT. Usado pela Topbar e pelo chat de chamados (para
 * saber quais mensagens são "minhas").
 */
export const getMe = (): Promise<Me> => api.get<Me>("/api/v1/auth/me");
