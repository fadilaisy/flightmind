import { useRef, useState } from "react";
import { ACCEPTED_EXTENSIONS } from "../api/uploadTypes";
import { STR } from "../strings";

interface Props {
  onFile: (file: File) => void;
  /** The panel in the header uses a shorter box. */
  compact?: boolean;
}

/** Drop zone with a Choose file button (Figma frame 1, 32:1632). */
export function DropZone({ onFile, compact = false }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  function take(files: FileList | null) {
    const file = files?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      className={`dropzone${over ? " over" : ""}${compact ? " compact" : " oneline"}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files);
      }}
    >
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <path d="M7 3h12l6 6v8M7 3v22h10M7 3H7" stroke="#0096c7" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
        <path d="M19 3v6h6M11 12h8M11 16h8M11 20h4" stroke="#03045e" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="23" cy="24" r="6" fill="#00b4d8" stroke="#03045e" strokeWidth="1.6" />
        <path d="M23 21v6M20 24h6" stroke="#03045e" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      <div className="droptext">
        <h2>{STR.dropTitle}</h2>
        <p className="dropnote">{STR.dropAccepts}</p>
      </div>
      <button type="button" className={`fbtn lg${compact ? "" : " solid"}`} onClick={() => input.current?.click()}>
        {STR.chooseFile}
      </button>
      <input
        ref={input}
        type="file"
        hidden
        aria-label={STR.fileInputLabel}
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={(e) => {
          take(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
