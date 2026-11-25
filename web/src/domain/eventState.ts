export type EventState = "to_review" | "confirmed" | "dismissed";

export const STATE_LABEL: Record<EventState, string> = {
  to_review: "To review",
  confirmed: "Confirmed by you",
  dismissed: "Dismissed by you",
};

export const STORAGE_KEY = "flightmind.eventStates";

export interface KeyValueStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

type Saved = Record<string, "confirmed" | "dismissed">;

function readAll(storage: KeyValueStorage): Saved {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Saved) : {};
  } catch {
    return {};
  }
}

export function loadState(storage: KeyValueStorage, eventId: string): EventState {
  return readAll(storage)[eventId] ?? "to_review";
}

export function saveState(storage: KeyValueStorage, eventId: string, state: EventState): void {
  const all = readAll(storage);
  if (state === "to_review") delete all[eventId];
  else all[eventId] = state;
  storage.setItem(STORAGE_KEY, JSON.stringify(all));
}

export function loadAllStates(storage: KeyValueStorage): Record<string, EventState> {
  return { ...readAll(storage) };
}
