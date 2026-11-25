import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Api } from "../api/client";
import type { Meta } from "../api/types";
import { STR, TAB_LABEL } from "../strings";

export type Tab = keyof typeof TAB_LABEL;
export const TABS = Object.keys(TAB_LABEL) as Tab[];

/** Reads ?tab= from a query string. Anything unknown falls back to the Map tab. */
export function parseTab(search: string): Tab {
  const value = new URLSearchParams(search).get("tab");
  return TABS.find((t) => t === value) ?? "map";
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

  return (
    <div className="shell">
      <header className="appbar">
        <span className="brand">{STR.brand}</span>
        <nav role="tablist" aria-label={STR.tabsLabel}>
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              className="tab"
              aria-selected={t === tab}
              onClick={() => open(t)}
            >
              {TAB_LABEL[t]}
            </button>
          ))}
        </nav>
        <span className="spacer" />
        <div className="status">
          {meta && (
            <>
              <span>
                <span className="dot" aria-hidden="true" />
                {meta.mode === "live" ? STR.modeLive : STR.modeReplay}
              </span>
              <span className="data" title={meta.sim_time}>
                {STR.simTime} {meta.sim_time.slice(11, 19)} UTC
              </span>
            </>
          )}
          {metaFailed && <span role="alert">{STR.metaUnavailable}</span>}
          {usingSample && <span className="sample">{STR.sampleData}</span>}
        </div>
      </header>
      <div role="tabpanel">{children(tab)}</div>
    </div>
  );
}
