import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Api } from "../api/client";
import type { Meta } from "../api/types";
import { STR, TAB_LABEL } from "../strings";
import { RecordingPicker } from "../components/RecordingPicker";
import mark from "../assets/figma/mark.svg";
import optical from "../assets/figma/optical.svg";
import { navigate } from "./nav";

export type Tab = keyof typeof TAB_LABEL;
export const TABS = Object.keys(TAB_LABEL) as Tab[];

/** Tabs that only make sense once a recording is selected. */
export const RECORDING_TABS: Tab[] = ["preview", "clean", "export"];

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
  hasRecording = true,
  activeTab = null,
  recordingName,
  selectedId = null,
  onSelectRecording,
  onPickFile,
  children,
}: {
  api: Api;
  /** True only when the mock sample dataset is what the screen shows. */
  usingSample: boolean;
  /** Preview, Clean and Export show only when a recording is selected. */
  hasRecording?: boolean;
  /** Forces the active tab, for example Load while the Load screen is up. */
  activeTab?: Tab | null;
  /** Filename of the selected recording. null: none loaded. undefined: the server has no recordings API, so use meta. */
  recordingName?: string | null;
  selectedId?: string | null;
  onSelectRecording?: (id: string) => void;
  onPickFile?: (file: File) => void;
  children: (tab: Tab) => ReactNode;
}) {
  const [urlTab, setTab] = useState<Tab>(() => parseTab(window.location.search));
  const tab = activeTab ?? urlTab;
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaFailed, setMetaFailed] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const closePicker = useCallback(() => setPickerOpen(false), []);

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

  const recording = recordingName === undefined ? meta?.recordings?.[0] : recordingName;

  return (
    <>
      <header className="appbar">
        <div className="logo">
          <img src={mark} alt="" />
          {STR.brand}
        </div>
        <nav className="tabs" role="tablist" aria-label={STR.tabsLabel}>
          {TABS.filter((t) => hasRecording || !RECORDING_TABS.includes(t)).map((t) => (
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
            <span>{recording ?? STR.noRecordingLoaded}</span>
            {usingSample && <span className="muted">{STR.sampleLabel}</span>}
          </div>
        )}
        {metaFailed && <span role="alert">{STR.metaUnavailable}</span>}
        <button type="button" className="fbtn" aria-expanded={pickerOpen} onClick={() => setPickerOpen((o) => !o)}>
          {STR.loadRecording}
        </button>
      </header>
      {pickerOpen && (
        <RecordingPicker
          api={api}
          selectedId={selectedId}
          onClose={closePicker}
          onSelect={(id) => {
            setPickerOpen(false);
            onSelectRecording?.(id);
          }}
          onFile={(file) => {
            setPickerOpen(false);
            onPickFile?.(file);
          }}
        />
      )}
      <div id="tabpanel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {children(tab)}
      </div>
    </>
  );
}

