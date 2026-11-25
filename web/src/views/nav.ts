/** Changes URL params (tab, view, profile) and tells listeners. Same value twice adds no history entry. */
export function navigate(params: Record<string, string | null>, mode: "push" | "replace" = "push"): void {
  const next = new URLSearchParams(window.location.search);
  for (const [k, v] of Object.entries(params)) {
    if (v === null) next.delete(k);
    else next.set(k, v);
  }
  const search = `?${next.toString()}`;
  if (search === window.location.search) return;
  if (mode === "push") window.history.pushState(null, "", search);
  else window.history.replaceState(null, "", search);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function readParam(name: string): string | null {
  return new URLSearchParams(window.location.search).get(name);
}