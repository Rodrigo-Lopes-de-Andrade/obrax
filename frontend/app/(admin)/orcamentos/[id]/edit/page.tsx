import { OrcamentoBuilder } from "@/components/modules/orcamento/builder/OrcamentoBuilder";

export default async function OrcamentoEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <OrcamentoBuilder orcamentoId={id} />;
}
