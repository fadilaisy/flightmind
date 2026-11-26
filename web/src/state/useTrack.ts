import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { Track } from "../api/types";
import { useUrlParam } from "../views/nav";

export type TrackState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; track: Track };

/** Loads /api/tracks/{icao24} whenever icao24 changes. */
export function useTrack(api: Api, icao24: string | null): { state: TrackState; retry: () => void } {
  const [state, setState] = useState<TrackState>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);

  const recording = useUrlParam("recording");

  useEffect(() => {
    if (!icao24) {
      setState({ status: "idle" });
      return;
    }
    let current = true;
    setState({ status: "loading" });
    (recording ? api.track(icao24, recording) : api.track(icao24))
      .then((track) => current && setState({ status: "ready", track }))
      .catch((e: Error) => current && setState({ status: "error", message: e.message }));
    return () => {
      current = false;
    };
  }, [api, icao24, recording, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, retry };
}
