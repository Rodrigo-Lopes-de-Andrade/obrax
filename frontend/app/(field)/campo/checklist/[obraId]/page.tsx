import { ChecklistView } from "@/components/field/ChecklistView";

export default async function ChecklistPage({
  params,
}: {
  params: Promise<{ obraId: string }>;
}) {
  const { obraId } = await params;
  return <ChecklistView obraId={obraId} />;
}
