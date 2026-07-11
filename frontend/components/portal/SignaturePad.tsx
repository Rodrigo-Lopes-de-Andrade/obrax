"use client";

import * as React from "react";
import { Eraser, Undo2 } from "lucide-react";

import { Button } from "@/components/ui/button";

type Point = { x: number; y: number };

/**
 * Assinatura em canvas (F9.4). Touch-friendly (pointer events + touch-action
 * none), com desfazer (por traço) e limpar. Exporta a assinatura como data URL
 * PNG via `onChange` (null quando vazia) — o pai valida "preenchida".
 */
export function SignaturePad({ onChange }: { onChange: (dataUrl: string | null) => void }) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const strokesRef = React.useRef<Point[][]>([]);
  const drawingRef = React.useRef(false);
  const [strokeCount, setStrokeCount] = React.useState(0);

  const redraw = React.useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.scale(dpr, dpr);
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#e5e7eb";
    for (const stroke of strokesRef.current) {
      if (stroke.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(stroke[0].x, stroke[0].y);
      for (let i = 1; i < stroke.length; i++) ctx.lineTo(stroke[i].x, stroke[i].y);
      ctx.stroke();
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0); // reset scale
  }, []);

  // Ajusta a resolução do canvas ao tamanho exibido (nitidez em telas retina).
  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    redraw();
  }, [redraw]);

  const emit = React.useCallback(() => {
    const canvas = canvasRef.current;
    const empty = strokesRef.current.length === 0;
    onChange(empty || !canvas ? null : canvas.toDataURL("image/png"));
  }, [onChange]);

  const pointFrom = (e: React.PointerEvent<HTMLCanvasElement>): Point => {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drawingRef.current = true;
    strokesRef.current.push([pointFrom(e)]);
    setStrokeCount(strokesRef.current.length);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current) return;
    strokesRef.current[strokesRef.current.length - 1].push(pointFrom(e));
    redraw();
  };

  const onPointerUp = () => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    emit();
  };

  const undo = () => {
    strokesRef.current.pop();
    setStrokeCount(strokesRef.current.length);
    redraw();
    emit();
  };

  const clear = () => {
    strokesRef.current = [];
    setStrokeCount(0);
    redraw();
    emit();
  };

  return (
    <div>
      <div className="relative">
        <canvas
          ref={canvasRef}
          className="h-40 w-full touch-none rounded-lg border border-dashed border-border bg-muted/40"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        />
        {strokeCount === 0 ? (
          <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
            Assine aqui
          </span>
        ) : null}
      </div>
      <div className="mt-1.5 flex justify-end gap-1">
        <Button type="button" variant="ghost" size="sm" onClick={undo} disabled={strokeCount === 0}>
          <Undo2 className="size-4" /> Desfazer
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={clear} disabled={strokeCount === 0}>
          <Eraser className="size-4" /> Limpar
        </Button>
      </div>
    </div>
  );
}
