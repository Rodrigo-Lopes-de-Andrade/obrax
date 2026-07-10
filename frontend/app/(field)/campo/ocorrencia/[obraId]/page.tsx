import { OcorrenciaView } from "@/components/field/OcorrenciaView";

export default async function OcorrenciaPage({
  params,
}: {
  params: Promise<{ obraId: string }>;
}) {
  const { obraId } = await params;
  return <OcorrenciaView obraId={obraId} />;
}
