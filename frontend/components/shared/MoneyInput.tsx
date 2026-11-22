"use client";

import * as React from "react";

import { Input } from "@/components/ui/input";
import { formatMoney } from "@/lib/decimal";

/** Teto de dígitos (centavos incluídos): 13 inteiros + 2 casas. */
const MAX_DIGITS = 15;

/** "1234.50" -> "123450" (só dígitos, sem zeros à esquerda). */
function canonicalToDigits(value: string): string {
  return value.replace(/\D/g, "").replace(/^0+/, "");
}

/** "123450" -> "1234.50". Texto puro, sem passar por Number/float. */
function digitsToCanonical(digits: string): string {
  if (digits === "") return "";
  const padded = digits.padStart(3, "0");
  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

interface MoneyInputProps
  extends Omit<React.ComponentProps<"input">, "value" | "onChange" | "type" | "defaultValue"> {
  /** Decimal canônico ("1234.50") ou "" quando vazio/zero. */
  value: string;
  onValueChange: (canonical: string) => void;
}

/**
 * Campo de dinheiro: digita-se em centavos (1, 2, 3 -> 0,01 / 0,12 / 1,23), exibe
 * pt-BR ("R$ 1.234,50") e devolve o decimal canônico em string ("1234.50") — o formato
 * que o contrato aceita (RN-F10). Zero é devolvido como "" (valor inválido na API).
 *
 * Semântica de centavos: só os dígitos do texto contam; separadores são descartados e a
 * posição da vírgula é sempre "2 casas da direita". Logo, colar "1500.5" vira 150,05
 * (dígitos 15005), e não 1.500,50 — quem cola precisa colar em centavos ou digitar.
 */
export function MoneyInput({ value, onValueChange, ...props }: MoneyInputProps) {
  const digits = canonicalToDigits(value);
  const display = digits === "" ? "" : formatMoney(digitsToCanonical(digits));

  return (
    <Input
      {...props}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      placeholder={props.placeholder ?? "R$ 0,00"}
      value={display}
      onChange={(e) => {
        const next = e.target.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, MAX_DIGITS);
        onValueChange(digitsToCanonical(next));
      }}
    />
  );
}
