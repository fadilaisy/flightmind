import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { Track } from "../api/types";

export type TrackState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; track: Track };

/** Loads /api/tracks/{icao24} whenever icao24 changes. */
export function useTrack(api: Api, icao24: string | null): { state: TrackState; retry: () => void } {
  const [state, setState] = useState<TrackState>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!icao24) {
      setState({ status: "idle" });
      return;
    }
    let current = true;
    setState({ status: "loading" });
    api
      .track(icao24)
      .then((track) => current && setState({ status: "ready", track }))
      .catch((e: Error) => current && setState({ status: "error", message: e.message }));
    return () => {
      current = false;
    };
  }, [api, icao24, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, retry };
}
