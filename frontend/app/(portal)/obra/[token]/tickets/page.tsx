import { PortalTicketsView } from "@/components/portal/PortalTicketsView";

export default async function PortalTicketsPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <PortalTicketsView token={token} />;
}
