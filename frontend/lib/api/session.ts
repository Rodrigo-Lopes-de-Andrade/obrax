import { api } from "./client";
import type { Usuario } from "./types";

/**
 * Usuário autenticado da sessão. No mock, é um `/me` de conveniência (o
 * backend real expõe o contexto do JWT); o chat usa isso para saber quais
 * mensagens são "minhas".
 */
export const getMe = (): Promise<Usuario> => api.get<Usuario>("/api/v1/auth/me");
