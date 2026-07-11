import { PortalOrcamentoView } from "@/components/portal/PortalOrcamentoView";

export default async function PortalOrcamentoPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <PortalOrcamentoView token={token} />;
}
