import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Api } from "../api/client";
import type { Meta } from "../api/types";
import { STR, TAB_LABEL } from "../strings";

export type Tab = keyof typeof TAB_LABEL;
export const TABS = Object.keys(TAB_LABEL) as Tab[];

/** Reads ?tab= from a query string. Anything unknown falls back to Trajectory. */
export function parseTab(search: string): Tab {
  const value = new URLSearchParams(search).get("tab");
  return TABS.find((t) => t === value) ?? "trajectory";
}

export function tabUrl(search: string, tab: Tab): string {
  const params = new URLSearchParams(search);
  params.set("tab", tab);
  return `?${params.toString()}`;
}

export function Shell({
  api,
  usingSample,
  children,
}: {
  api: Api;
  usingSample: boolean;
  children: (tab: Tab) => ReactNode;
}) {
  const [tab, setTab] = useState<Tab>(() => parseTab(window.location.search));
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaFailed, setMetaFailed] = useState(false);

  useEffect(() => {
    const onPop = () => setTab(parseTab(window.location.search));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => setMetaFailed(true));
  }, [api]);

  const open = useCallback((next: Tab) => {
    window.history.pushState(null, "", tabUrl(window.location.search, next));
    setTab(next);
  }, []);

  const recording = meta?.recordings?.[0];

  return (
    <>
      <header className="appbar">
        <div className="logo">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M2 14 L10 4 L18 14" fill="none" stroke="#1d4ed8" strokeWidth="2" />
            <circle cx="10" cy="4" r="2" fill="#0aa2c0" />
          </svg>
          {STR.brand}
        </div>
        {meta && <span className="file">{recording ?? STR.noRecording}</span>}
        <nav className="tabs" role="tablist" aria-label={STR.tabsLabel}>
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              className={t === tab ? "on" : undefined}
              aria-selected={t === tab}
              onClick={() => open(t)}
            >
              {TAB_LABEL[t]}
            </button>
          ))}
        </nav>
        <div className="spacer" />
        {meta && (
          <span className="muted" style={{ fontSize: 12.5 }}>
            {meta.mode === "live" ? STR.modeLive : STR.modeReplay}
            {" · "}
            <span className="mono" title={meta.sim_time}>
              {STR.simTime} {meta.sim_time.slice(11, 19)} UTC
            </span>
          </span>
        )}
        {metaFailed && <span role="alert">{STR.metaUnavailable}</span>}
        {usingSample && <span className="badge b-grey">{STR.sampleData}</span>}
      </header>
      <div role="tabpanel">{children(tab)}</div>
    </>
  );
}