# Kiro CLI session logs

One file per Kiro CLI session run in this repository, written by `scripts/kiro-sessions-export`.
Each log has every prompt and assistant text in full, one line per tool call, and tool errors.
Home folders, temp folders, secrets and email addresses are redacted. Prompt files that a
session read are copied to `docs/kiro/sessions/prompts/`.

Refresh: `python scripts/kiro-sessions-export --also-cwd <other clone of this repo>`

| Date | Session | First prompt | Prompts | Tool calls | Log |
| --- | --- | --- | ---: | ---: | --- |
| 2026-11-25 | `03a94859` | Read the file docs/kiro/sessions/prompts/A-map-charts-scrubber.md and carry out every step in it, in this r... | 2 | 41 | [2026-11-25-03a94859.md](2026-11-25-03a94859.md) |
| 2026-11-26 | `3ad7175d` | Read the file docs/kiro/sessions/prompts/B-3d-records.md and carry out every step in it, in this repository. | 2 | 92 | [2026-11-26-3ad7175d.md](2026-11-26-3ad7175d.md) |
| 2026-11-26 | `2032e2bf` | Read the file docs/kiro/sessions/prompts/D-trajectory-figma.md and carry out every step in it, in this repo... | 3 | 85 | [2026-11-26-2032e2bf.md](2026-11-26-2032e2bf.md) |
| 2026-11-26 | `b4de76e4` | [C | 3 | 2 | [2026-11-26-b4de76e4.md](2026-11-26-b4de76e4.md) |
| 2026-11-26 | `4a2e9ee7` | Read the file docs/kiro/sessions/prompts/E-final.md and carry out every step in it, in this repository. | 1 | 52 | [2026-11-26-4a2e9ee7.md](2026-11-26-4a2e9ee7.md) |
| 2026-11-26 | `c51295d5` | Read the file docs/kiro/sessions/prompts/F-deploy-fixes.md and carry out every step in it, in this repository. | 1 | 57 | [2026-11-26-c51295d5.md](2026-11-26-c51295d5.md) |
| 2026-11-26 | `a673814a` | Read the file docs/kiro/sessions/prompts/U-scrum66-upload.md and carry out every step in it, in this reposi... | 1 | 82 | [2026-11-26-a673814a.md](2026-11-26-a673814a.md) |
| 2026-11-26 | `ccfdb42a` | Read the file docs/kiro/sessions/prompts/V-scrum69-preview-clean-export.md and carry out every step in it, ... | 1 | 61 | [2026-11-26-ccfdb42a.md](2026-11-26-ccfdb42a.md) |
| 2026-11-26 | `c6bcabfe` | Read the file docs/kiro/sessions/prompts/K-kiro-proof.md and carry out every step in it, in this repository. | 1 | 62 | [2026-11-26-c6bcabfe.md](2026-11-26-c6bcabfe.md) |
