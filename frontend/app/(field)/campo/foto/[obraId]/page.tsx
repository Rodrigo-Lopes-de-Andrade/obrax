import { FotosView } from "@/components/field/FotosView";

export default async function FotoPage({
  params,
}: {
  params: Promise<{ obraId: string }>;
}) {
  const { obraId } = await params;
  return <FotosView obraId={obraId} />;
}
