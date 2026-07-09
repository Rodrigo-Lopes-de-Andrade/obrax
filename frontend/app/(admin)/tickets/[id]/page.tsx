import { TicketChat } from "@/components/modules/ticket/TicketChat";

export default async function TicketChatPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <TicketChat ticketId={id} />;
}
