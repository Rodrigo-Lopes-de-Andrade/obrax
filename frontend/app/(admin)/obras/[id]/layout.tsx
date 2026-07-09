import { ObraDetailHeader } from "@/components/modules/obra/ObraDetailHeader";

export default async function ObraDetailLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="space-y-6">
      <ObraDetailHeader obraId={id} />
      {children}
    </div>
  );
}
