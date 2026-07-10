import { PortalObraView } from "@/components/portal/PortalObraView";

export default async function PortalObraPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <PortalObraView token={token} />;
}
