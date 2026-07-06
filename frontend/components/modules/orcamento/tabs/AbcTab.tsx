import { CurvaAbcList } from "@/components/modules/orcamento/CurvaAbcList";
import { curvaAbc } from "@/lib/mock/dashboard-obra";

export function AbcTab() {
  return <CurvaAbcList itens={curvaAbc} />;
}
