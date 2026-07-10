import { api } from "./client";
import type {
  ChecklistItem,
  ChecklistItemCreateInput,
  ChecklistItemUpdateInput,
  Page,
} from "./types";

export function getChecklist(obraId: string): Promise<Page<ChecklistItem>> {
  return api.get(`/api/v1/obras/${obraId}/checklist?limit=200`);
}

export function createChecklistItem(
  obraId: string,
  input: ChecklistItemCreateInput,
): Promise<ChecklistItem> {
  return api.post(`/api/v1/obras/${obraId}/checklist`, input);
}

export function updateChecklistItem(
  itemId: string,
  patch: ChecklistItemUpdateInput,
): Promise<ChecklistItem> {
  return api.patch(`/api/v1/checklist/${itemId}`, patch);
}

export function deleteChecklistItem(itemId: string): Promise<void> {
  return api.delete(`/api/v1/checklist/${itemId}`);
}
