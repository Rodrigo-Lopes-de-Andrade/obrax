import { DocumentosView } from "@/components/modules/documento/DocumentosView";

export default async function DocumentosPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DocumentosView obraId={id} />;
}
