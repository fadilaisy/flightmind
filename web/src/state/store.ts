import { useSyncExternalStore } from "react";
import {
  loadAllStates,
  saveState,
  type EventState,
  type KeyValueStorage,
} from "../domain/eventState";

export interface AppState {
  eventId: string | null;
  icao24: string | null;
  /** ISO time. Only the scrubber writes this. */
  scrubTs: string | null;
  rawRef: string | null;
  /** Events not listed here are "to_review". Persisted under flightmind.eventStates. */
  eventStates: Record<string, EventState>;
}

export interface Store {
  getState(): AppState;
  subscribe(listener: () => void): () => void;
  selectEvent(eventId: string | null, icao24: string | null): void;
  setScrubTs(ts: string | null): void;
  setRawRef(rawRef: string | null): void;
  setEventState(eventId: string, state: EventState): void;
}

export function createStore(storage: KeyValueStorage): Store {
  let state: AppState = {
    eventId: null,
    icao24: null,
    scrubTs: null,
    rawRef: null,
    eventStates: loadAllStates(storage),
  };
  const listeners = new Set<() => void>();

  function update(patch: Partial<AppState>) {
    state = { ...state, ...patch };
    listeners.forEach((l) => l());
  }

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    selectEvent: (eventId, icao24) => update({ eventId, icao24 }),
    setScrubTs: (scrubTs) => update({ scrubTs }),
    setRawRef: (rawRef) => update({ rawRef }),
    setEventState(eventId, s) {
      saveState(storage, eventId, s);
      const next = { ...state.eventStates };
      if (s === "to_review") delete next[eventId];
      else next[eventId] = s;
      update({ eventStates: next });
    },
  };
}

/** App-wide store. Tests build their own with createStore. */
let shared: Store | null = null;
export function getStore(): Store {
  shared ??= createStore(localStorage);
  return shared;
}

/**
 * The selector must return a single value (a string, number or a stored object), never a new
 * object or array built on each call. useSyncExternalStore compares with Object.is, so a fresh
 * object every time loops forever. Call useStore once per value.
 */
export function useStore<T>(select: (s: AppState) => T): T {
  const s = getStore();
  return useSyncExternalStore(s.subscribe, () => select(s.getState()));
}
