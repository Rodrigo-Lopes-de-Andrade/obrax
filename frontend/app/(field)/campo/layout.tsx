import type { Metadata } from "next";

import { BottomNav } from "@/components/field/BottomNav";
import { FieldHeader } from "@/components/field/FieldHeader";

export const metadata: Metadata = {
  title: "Obrax Campo",
  description: "App de campo — checklist e registro offline",
};

export default function FieldLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <FieldHeader />
      {/* pb cobre a BottomNav fixa (56px) + safe-area. */}
      <main className="mx-auto w-full max-w-md flex-1 px-4 pt-4 pb-[calc(72px+env(safe-area-inset-bottom))]">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
