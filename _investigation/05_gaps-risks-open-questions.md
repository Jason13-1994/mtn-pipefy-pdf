---
title: Gaps, risks and decisions needed
last_updated: 2026-08-18
---

# 05 — Gaps, risks, decisions

## A. Decisions needed before build

Each has a recommendation. Say yes or overrule; either way the build can start
once these are closed.

---

### D1 — Where does the Agency Brief attach? *(blocking)*

`brief_attached` on Agency Workflow is already the copy target of `brief_attached`
on Campaign Briefing. The fan-out automation writes the Job Brief PDF there.

| Option | Result |
|---|---|
| **A. New field `agency_brief_attached`** | Agency card ends up with both the Job Brief (copied) and the Agency Brief. Two PDFs, agency opens the wrong one. |
| **B. Reuse `brief_attached`, drop it from the fan-out map** | One brief per agency card, unambiguous. Requires editing 17 automations. If generation fails, the card has no brief at all. |
| **C. New field now, migrate to B once proven** ✅ | Job Brief stays as a fallback while the service beds in; once the run log is clean, drop `brief_attached` from the fan-out and point the service at it. |

**Recommendation: C.** Staged, and the fallback is free during the risky period.
Needs one new attachment field on `307284207` and a note in the backlog to
collapse it later.

---

### D2 — Should the Job Brief PDF exist before the agency fan-out? *(blocking)*

Both currently trigger on entry to Brief Submitted `343906142`.
→ full detail in [04](04_triggers-and-deployment.md) §1.

**Recommendation:** generate the Job Brief on the **final approval decision**
(field-change event) rather than the phase move, so it exists before the fan-out
copies it. Falls away entirely if D1 lands on B.

---

### D3 — Campaign context on the Agency Brief *(blocking)*

The agency card gets `is_this_job_part_of_an_approved_campaign` copied but
**`select_campaign` is never populated** by the fan-out. So an agency card can
claim to be part of a campaign and have nothing to point at.

| Option | Notes |
|---|---|
| **A. Add `select_campaign` to the 17 fan-out field maps** | Right fix at source. 17 automation edits. Also fixes it for anything else that needs the link. |
| **B. Service walks up to the parent briefing card** | No Pipefy changes. Needs the parent relation to be readable from the child — `parent_relations` on the agency card. Must be verified against a live card. |
| **C. No campaign context on the Agency Brief** | The agency gets the job, not the campaign. Defensible — but the brief loses its *why*. |

**Recommendation: A**, with **B** as the runtime fallback so the document is
still right for the ~200 agency cards created before the automations are fixed.

---

### D4 — Does cost & timing go on the Agency Brief?

The Agency Workflow card holds `ugandan_*_budget` / `zambian_*_budget` copied
from the brief, plus phase-level `*_cost_timing` budgets and two internal
approval decisions with feedback.

**Recommendation: brief budgets ON, cost & timing approval OFF.** The agency needs
the budget it is working to; it does not need MTN's internal approval commentary.
Confirm with MTN — this is a commercial call, not a technical one.

---

### D5 — Fix the `creative_team` option list

- **"Curiosity" appears twice** in `creative_team`.
- `creative_team` says **"Internal Studio Team"**; the agency checklists say
  **"Internal MTN studio"**. Two names for the same team.

Harmless today (J109 is inactive), a select-by-value bug later.
**Recommendation:** de-duplicate and align to one name before the Uganda
automations are switched on.

---

### D6 — Hosting region and data residency

Up & Up runs in `us-east-2`. Brief content for MTN Zambia/Uganda would transit
and be processed there.

**Recommendation:** default to matching Up & Up for operational simplicity, but
**ask MTN** whether marketing brief content has a residency constraint. Cheap to
answer now, expensive to answer after go-live. `af-south-1` (Cape Town) is the
alternative and is closer to both opcos.

---

### D7 — Service account for the Pipefy token

**Recommendation:** a dedicated Pipefy service user with write access to the three
pipes and read on `mOUzRnnK`. Not a personal PAT.

---

### D8 — The nine inactive fan-out automations

Eight Uganda agencies plus Curiosity (UG) have automations built but switched off,
so ticking those agencies on a brief creates no card and generates no Agency
Brief. Is that intentional (not live yet) or an oversight? Affects go-live scope.

---

## B. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **Competitor leakage.** Agency Brief includes `*_agencies_required` and Curiosity sees EXP is on the job. | Commercial / relationship | Explicit allowlist + `deny` set + a test that fails if either field id appears in rendered agency output. Non-negotiable. |
| R2 | **Junk fields reach an external document** — `button`, `field_1`–`field_4`. | Credibility | Same allowlist. `check_drift.py` reports them as DENIED, so they stay visibly handled. |
| R3 | **Presigned upload.** `createPresignedUrl` has returned both `url` and `downloadUrl` across Pipefy versions; some backends reject a `Content-Type` they didn't sign. | Attach fails | Already handled in the existing `lib_pipefy.py` (introspects payload, retries PUT without the header on 400/403). **Never verified against live** — first thing to test on the box. |
| R4 | **Stale campaign data.** The DB record is a snapshot at approval. If the campaign is edited afterwards and `CP008` is create-only, the Job Brief inherits old values. | Wrong brief | Print the record's last-updated date on the inherited block. Longer-term: make `CP008` update-on-change. Same issue flagged in `AUTOMATION_FIELD_MAP.md`. |
| R5 | **Form drift.** Someone adds a field in Pipefy; three PDFs quietly stop being complete. | Silent incompleteness | `check_drift.py` in CI + weekly scheduled run to Slack. This is the single most valuable piece of tooling in the repo. |
| R6 | **Field-id drift across boards** — `strategic_pillar` / `strategic_element`, seven `_please_specify` renames. | Blank sections | Per-profile ids, never shared constants. Drift checker catches a rename as MISSING + STALE together. |
| R7 | **Unauthenticated endpoint** (as Up & Up is today). | Anyone can trigger generation | Shared-secret header + 443-only + reverse proxy. |
| R8 | **Single EC2 box, no HA.** | Briefs stop generating | Acceptable at this volume — but `Restart=always`, an uptime check on `/health`, and a "zero generations today" alert. Recovery is `git clone` + `.env`. |
| R9 | **Font licensing.** MTN Brighter Sans isn't redistributable. | Off-brand type | Ships in Helvetica; drop the TTFs into `assets/fonts/` and register in `brand.py`. Get the files from Frontify — **no code change needed**, so this can't block go-live. |
| R10 | **Recon is 13 days old** and the API is unreachable from the sandbox. | Coding against stale ids | Run `tools/recon_pdf_boards.py` and diff against [01](01_board-structures.md) before writing any profile. |

---

## C. Assumptions

`[ASSUMPTION]` — flag anything here that's wrong.

1. Org `302505741`; pipes `307284211` / `307284210` / `307284207`; DB `mOUzRnnK`
   (URL id `307284208`). From live capture, to re-verify.
2. `MTN Brain/03_boards.md` is stale (pipes `307227220`, `307227231`) and these
   three pipes supersede it. **The Brain needs updating either way** — separate task.
3. The Agency Brief is read by external agency staff with no Pipefy licence.
   That drives the exclusions in [02](02_document-model.md).
4. `select_campaign` on the briefing form is multi-select; if a brief links more
   than one campaign the first is used and the console says so. Carried from the
   existing tool. Multi-campaign briefs are assumed not to be a real scenario.
5. Volume is low — tens of PDFs a day, not thousands. Drives the single-box,
   synchronous design. If it's hundreds an hour, this needs a queue.
6. MTN is happy for brief content to be rendered on a dYdX-operated EC2 instance.
   → D6.
7. No PDF/A, no digital signature, no password protection required.
8. English only. No RTL, no localisation.
