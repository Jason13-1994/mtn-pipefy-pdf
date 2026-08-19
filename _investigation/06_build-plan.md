---
title: Build plan
last_updated: 2026-08-18
---

# 06 — Build plan

Five phases. Each ends in something demonstrable. Nothing touches Pipefy config
until Phase 4.

---

## Phase 0 — Re-verify (before any code)

| # | Task | Output |
|---|---|---|
| 0.1 | Run `tools/recon_pdf_boards.py` on your machine | `recon_live.json` |
| 0.2 | Diff against [01_board-structures.md](01_board-structures.md) | Confirmed or corrected ids |
| 0.3 | Close **D1, D2, D3** | Unblocks Phase 2 and 4 |
| 0.4 | Confirm a live test card id per pipe | Fixtures anchored to real data |

**Exit:** field ids and phase ids are facts, not recollections.

---

## Phase 1 — Skeleton + port

Repo, `layout_dsl.py`, `core/` ported from `pipefy_creations/campaign_pdf/`,
CLI, test harness with fixtures.

**Exit:** `python cli.py <campaign_card_id>` renders a Campaign Brief to `out/`
that is visually equivalent to the existing tool's output. Nothing written to Pipefy.

---

## Phase 2 — The three profiles

| # | Task |
|---|---|
| 2.1 | `profiles/campaign_brief.py` — scaffold from live form, curate |
| 2.2 | `profiles/job_brief.py` — including the `source="auto"` campaign resolver |
| 2.3 | `profiles/agency_brief.py` — agency-aware cover, deny set, exclusions |
| 2.4 | `tools/scaffold_layout.py` + `tools/check_drift.py` |
| 2.5 | Fixtures + tests for the Yes/No branch and the junk-field exclusions |

**Exit — all four must hold:**

- All three documents render from live cards, dry run, no writes
- A **linked** brief shows inherited campaign context, marked as inherited
- A **standalone** brief shows *"Campaign context (defined by this brief)"* from
  its own fields
- A brief that says *Yes* with nothing linked renders a visible, marked gap —
  not a silent omission
- `check_drift.py` exits 0 on all three profiles
- The agency-leakage test passes: no `*_agencies_required`, no `button`, no
  `field_*` in rendered agency output

**Review gate: you and MTN sign off the three PDFs before anything is attached.**

---

## Phase 3 — Attach, verified

`--apply` path: presigned upload → `updateCardField` → **re-read and confirm**.
Non-zero exit if the file isn't there.

**Exit:** one PDF per board attached to a real card and verified. R3 (presigned
upload) confirmed against live — this is the part that has never been tested.

---

## Phase 4 — Service + box

| # | Task |
|---|---|
| 4.1 | `main.py` — endpoints per [04](04_triggers-and-deployment.md) §2, shared-secret auth, per-card lock |
| 4.2 | Provision EC2, Caddy/443, systemd, service-account token (**D7**) |
| 4.3 | Papertrail + run log + `/health` uptime check + "silent for 24h" alert |
| 4.4 | `deploy/RUNBOOK.md` |
| 4.5 | Point one automation at it — Campaign Planning first, lowest volume |
| 4.6 | Soak. Then Campaign Briefing (**D2**), then Agency Workflow |

**Exit:** all three automations live, run log clean for a week.

---

## Phase 5 — Handover

Repo README, runbook, `check_drift` scheduled weekly, "how to add a field" written
down in three lines, MTN Brain spokes updated (`03_boards.md` is stale, `04_integrations.md`
and `05_automations.md` need the PDF service added), and the D1-option-C cleanup
raised as a backlog item.

---

## Test plan (outline — full sheet in `testing/` once the build starts)

| Area | Cases |
|---|---|
| Campaign resolver | linked / standalone / claims-linked-but-empty / multi-linked (first wins) / record deleted |
| Agency identity | `creative_team` set / blank + `card_title` fallback / both blank → **render refused** |
| Field types | long_text, checklist, currency (UGX + ZMW), date, datetime, 4-digit year, attachment filename, assignee |
| Exclusions | agency doc contains no `*_agencies_required`, no `button`, no `field_*`, no attach field |
| Drift | add a field to the form → `check_drift` reports MISSING and exits 1 |
| Attach | fresh field / field with an existing file (replace) / `--keep-existing` / read-only token → clean failure at attach |
| Service | valid payload / both payload shapes / bad token / unknown card / card in an unmapped pipe / double-fire → one render |
| Ops | restart under systemd, `.env` missing a var → refuses to start with a clear message |

---

## Effort

Rough, assuming decisions are closed and no surprises in the live re-verify.

| Phase | Days |
|---|---|
| 0 — Re-verify | 0.5 |
| 1 — Skeleton + port | 1.5 |
| 2 — Three profiles + tooling | 3 |
| 3 — Attach verified | 0.5 |
| 4 — Service + EC2 + automations | 2 |
| 5 — Handover | 1 |
| **Total** | **~8.5 days** |

Phase 2 is where the time is, and Agency Brief is the biggest slice of it —
88 fields, an external audience, and the exclusion rules to get right.
