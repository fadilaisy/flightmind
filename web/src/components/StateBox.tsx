import type { ReactNode } from "react";

interface Props {
  kind: "loading" | "empty" | "error";
  title: string;
  text?: string;
  children?: ReactNode;
}

/** Loading, empty and error boxes (Figma frame 17:883, light tokens). */
export function StateBox({ kind, title, text, children }: Props) {
  return (
    <div className={`statebox ${kind}`} role={kind === "error" ? "alert" : "status"}>
      <strong>{title}</strong>
      {text && <p className="muted">{text}</p>}
      {children}
    </div>
  );
}