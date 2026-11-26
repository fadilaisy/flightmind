import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Api } from "../api/client";
import type { Meta } from "../api/types";
import { STR, TAB_LABEL } from "../strings";
import mark from "../assets/figma/mark.svg";
import optical from "../assets/figma/optical.svg";
import { navigate } from "./nav";

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

  const open = useCallback(
    (next: Tab) => {
      if (next === tab) return;
      navigate({ tab: next });
    },
    [tab],
  );

  const recording = meta?.recordings?.[0];

  return (
    <>
      <header className="appbar">
        <div className="logo">
          <img src={mark} alt="" />
          {STR.brand}
        </div>
        <nav className="tabs" role="tablist" aria-label={STR.tabsLabel}>
          {TABS.map((t) => (
            <button
              key={t}
              id={`tab-${t}`}
              role="tab"
              aria-controls="tabpanel"
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
          <div className="status">
            <span className="mode" title={`${STR.simTime} ${meta.sim_time.slice(11, 19)} UTC`}>
              <img src={optical} alt="" />
              {meta.mode === "live" ? STR.modeLive : STR.modeReplay}
            </span>
            <span>{recording ?? STR.noRecording}</span>
            {usingSample && <span className="muted">{STR.sampleLabel}</span>}
          </div>
        )}
        {metaFailed && <span role="alert">{STR.metaUnavailable}</span>}
        <button type="button" className="fbtn" disabled title={STR.loadRecordingTitle}>
          {STR.loadRecording}
        </button>
      </header>
      <div id="tabpanel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {children(tab)}
      </div>
    </>
  );
}
