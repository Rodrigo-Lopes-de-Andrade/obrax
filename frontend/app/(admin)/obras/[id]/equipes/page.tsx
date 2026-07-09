import { EquipesView } from "@/components/modules/equipe/EquipesView";

export default async function EquipesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <EquipesView obraId={id} />;
}
