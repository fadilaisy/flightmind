import { useCallback, useEffect, useState } from "react";
import type { Api } from "../api/client";
import type { Recipe, Recording } from "../api/uploadTypes";
import { QuarantineList } from "../components/QuarantineList";
import { StageList } from "../components/StageList";
import { StateBox } from "../components/StateBox";
import { recipeTotals, shareText, sizeLine, smallerText } from "../domain/recipe";
import { POLL_MS, followRecording, formatSize, isProcessing } from "../domain/upload";
import { STR } from "../strings";

const nf = (n: number) => n.toLocaleString("en-US");

interface Props {
  api: Api;
  recording: Recording;
  /** The stream picked on the Load tab. */
  streamId: string | null;
  /** The recording reached "ready" while this view was open. */
  onReady: () => void;
  onReviewEvents: () => void;
}

/** Clean and reduce (Figma frame 3). The recipe, what each step set aside, the sizes, and "Apply and find events". */
export function CleanView({ api, recording, streamId, onReady, onReviewEvents }: Props) {
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [listing, setListing] = useState(false);
  const [status, setStatus] = useState(recording.status);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setRecipe(null);
    setError(null);
    api
      .recordingRecipe(recording.id)
      .then((r) => live && setRecipe(r))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [api, recording.id, attempt]);

  /** Poll until ready or failed. `scannedMeansWait` is true right after process, when a slow server may still say scanned. */
  const follow = useCallback(
    async (scannedMeansWait: boolean) => {
      try {
        for (let tries = 0; ; tries++) {
          const result = await followRecording(api, recording.id, { onUpdate: (r) => setStatus(r.status) });
          if (result.kind === "ready") onReady();
          else if (result.kind === "failed") setApplyError(result.error);
          else if (result.kind === "scanned" && scannedMeansWait && tries < 5) {
            await new Promise((r) => setTimeout(r, POLL_MS));
            continue;
          }
          return;
        }
      } catch (e) {
        setApplyError((e as Error).message);
      }
    },
    [api, recording.id, onReady],
  );

  // Opened while the server is already working: follow it to the end.
  useEffect(() => {
    if (isProcessing(recording.status)) void follow(false);
    // Once, when the view opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function apply() {
    setApplyError(null);
    const id = streamId ?? recording.streams.find((s) => s.supported)?.id;
    if (!id) {
      setApplyError(STR.noStreamChosen);
      return;
    }
    try {
      const r = await api.processRecording(recording.id, id);
      setStatus(r.status);
      await follow(true);
    } catch (e) {
      setApplyError((e as Error).message);
    }
  }

  const working = isProcessing(status);
  const done = status === "ready";
  const totals = recipe ? recipeTotals(recipe) : null;

  return (
    <div className="wrap">
      <div className="pagehead">
        <div>
          <h1>{STR.cleanTitle}</h1>
          <p className="muted">{STR.cleanIntro}</p>
        </div>
        {done ? (
          <button type="button" className="fbtn lg solid" onClick={onReviewEvents}>
            Review events
          </button>
        ) : (
          <button type="button" className="fbtn lg solid" disabled={!recipe || working} onClick={() => void apply()}>
            {STR.applyFind}
          </button>
        )}
      </div>
      {(working || applyError) && (
        <div className="card applying" role="status" aria-label={STR.applying}>
          {working && (
            <>
              <h2 className="cardtitle flat">{STR.applying}</h2>
              <StageList status={status} />
            </>
          )}
          {applyError && <StateBox kind="error" title={STR.applyError} text={applyError} />}
        </div>
      )}
      {error ? (
        <StateBox kind="error" title={STR.recipeError} text={error}>
          <button type="button" className="btn sm" onClick={() => setAttempt((n) => n + 1)}>
            {STR.retry}
          </button>
        </StateBox>
      ) : !recipe || !totals ? (
        <StateBox kind="loading" title={STR.recipeLoading} />
      ) : (
        <>
          <div className="stats">
            <div className="card">
              <div className="muted">{STR.statDecoded}</div>
              <div className="big">{nf(totals.decoded)}</div>
              <div className="muted cap">{formatSize(recipe.raw_bytes)} raw CAT021</div>
            </div>
            <div className="card">
              <div className="muted">{STR.statAfterCleaning}</div>
              <div className="big">{nf(totals.afterCleaning)}</div>
              <div className="muted cap">
                {nf(totals.setAside)} {STR.statSetAside}
              </div>
            </div>
            <div className="card">
              <div className="muted">{STR.statRawSize}</div>
              <div className="big">{formatSize(recipe.raw_bytes)}</div>
              <div className="muted cap">before reduction</div>
            </div>
            <div className="card">
              <div className="muted">{STR.statStoredSize}</div>
              <div className="big">{formatSize(recipe.stored_bytes)}</div>
              <div className="muted cap">{smallerText(totals.smallerBy)}</div>
            </div>
          </div>
          {listing ? (
            <QuarantineList api={api} recordingId={recording.id} steps={recipe.steps} onClose={() => setListing(false)} />
          ) : (
            <div className="card recipe" aria-label={STR.recipeTitle}>
              <h2 className="cardtitle flat">
                {STR.recipeTitle} <span className="muted small">{recipe.steps.length} {STR.recipeSteps}</span>
              </h2>
              <ul className="steps">
                {recipe.steps.map((s) => (
                  <li key={s.code}>
                    <div>
                      <b>{s.label}</b>
                      <div className="muted small">{s.reason}</div>
                    </div>
                    <div className="stepcount">
                      <button
                        type="button"
                        className="countbtn"
                        disabled={s.set_aside === 0}
                        title={`${nf(s.set_aside)} ${STR.setAside}`}
                        onClick={() => setListing(true)}
                      >
                        {nf(s.set_aside)}
                      </button>
                      <div className="muted small">{shareText(s.set_aside, totals.decoded)}</div>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="reduce">
                <h3>{STR.reduceTitle}</h3>
                <p className="muted">{recipe.tolerance_note}</p>
                <p className="muted small">
                  {sizeLine(recipe)}. SHA-256 of the input <span className="mono">{recipe.input_sha256.slice(0, 8)}...{recipe.input_sha256.slice(-4)}</span>
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

