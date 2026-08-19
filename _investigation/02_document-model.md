---
title: The document model — three PDFs, one engine
last_updated: 2026-08-18
---

# 02 — Document model

Three documents. One renderer. The differences live entirely in config.

| | Campaign Brief | Job Brief | Agency Brief |
|---|---|---|---|
| Pipe | `307284211` | `307284210` | `307284207` |
| Audience | MTN internal, approval record | MTN internal + traffic | **External agency** |
| Attach to | `campaign_attached` | `brief_attached` | `agency_brief_attached` *(new — D1)* |
| Campaign context | *is* the campaign | linked record **or** own fields | inherited from parent brief *(D3)* |
| Agency identity | — | agencies requested | **`creative_team` — front and centre** |
| Filename | `Campaign Brief - {campaign_name} - {opco} - {card_id}.pdf` | `Job Brief - {job_name} - {opco} - {card_id}.pdf` | `Agency Brief - {creative_team} - {job_name} - {card_id}.pdf` |

---

## 1. Campaign Brief — `307284211`

The straightforward one. No connectors, no inheritance.

```
COVER      MTN masthead
           Campaign name (H1)
           {Originating OpCo} · Tier {tier} · {campaign_year}
           ─────────────────────────────────────────
           Campaign objective  (highlight block)
           ─────────────────────────────────────────
           Campaign          Card ID          Current phase
           Originating OpCo  Go live          End date
           Campaign budget   Campaign owner   Approval status

BODY       Campaign Information
           Campaign Timelines
           Campaign Details
           Campaign KPI's
           Supporting Information

TAIL       Review & approval   (campaign_review_decision, reviewer_comments,
                                campaign_approval_date, approval_authority,
                                approval_notes, approval_status)
```

Excluded: `campaign_attached` (circular), `approver_email` (internal routing).

**Division fields.** Fifteen `*_division` selects on the form; a campaign fills one
or two. Render as a single **Division** line that picks the populated one, rather
than fifteen "Not provided" rows. Config: a `oneof(...)` field spec — see
[03](03_repo-and-config.md).

---

## 2. Job Brief — `307284210`

Two modes off one required radio. **Not two layouts — one layout with a resolver.**

```
is_this_job_part_of_an_approved_campaign
        │
        ├── "Yes" ──▶ read connector `campaign` ──▶ table_record(mOUzRnnK)
        │             campaign context = the linked record
        │             document says: "Inherited from campaign {name}.
        │                             Campaign Planning is the source of truth."
        │
        └── "No"  ──▶ campaign context = the brief's own fields
                      document says: "This brief is standalone — it defines its
                                      own campaign context."
```

The five fields that switch source are exactly the five the form conditions
reveal on `No`, and all five carry the same id on both boards:

| Field | Yes → from | No → from |
|---|---|---|
| `originating_opco` | linked record | the brief |
| `strategic_pillar` | linked record | the brief |
| `target_audience` | linked record | the brief |
| `target_audience_additional_information` | linked record | the brief |
| `kpi_pillar` | linked record | the brief |

In config that is one keyword per line:

```python
F("originating_opco", source="auto")   # campaign record if linked, else this card
```

`auto` = campaign-if-linked-else-card. `card` and `campaign` force a side.

**The Campaign context section itself.**

- **Yes** → a *Campaign* block before the job's own sections, curated
  (objective, background, key message, problem, audience, KPIs, budget, dates,
  milestones), each row labelled as inherited. Carried over from the existing
  tool's `summary_fields`.
- **No** → the block is titled **"Campaign context (defined by this brief)"** and
  is filled from the brief's own fields. Same section, honest label.
- **Yes but nothing linked** → the block stays, and says so loudly. A brief that
  claims a campaign and has none must *look* wrong to whoever opens the PDF.
  Never silently omit it.

```
COVER      Job name (H1)
           {brief_type} · {opco:auto} · Tier {tier}
           "The brief in a sentence"  (highlight block)
           Job · Brief type · Approved campaign · Card ID · Current phase
           First revert · Go live · Material delivery · Brief owner
           Agencies requested: {zambia_agencies_required + uganda_agencies_required}

BODY       Campaign context            (inherited | defined by this brief)
           Job information
           Channels and elements
           Job timelines
           Job details

TAIL       Approvals   (3 rounds: reviewer, decision, feedback — populated only)
```

Excluded: `brief_attached`, and the `campaign` connector itself (it holds a
record id, not information).

---

## 3. Agency Brief — `307284207`

Same underlying job, addressed to one agency. **The only document an external
party reads — so it is the strictest about what appears on it.**

### Agency identity

`creative_team` is set statically by the creating automation to the agency name.
It drives four things:

1. **Cover** — agency name in the masthead block: *Prepared for **Curiosity***
2. **Subtitle** — `{creative_team} · {originating_opco} · {brief_type}`
3. **Filename** — `Agency Brief - Curiosity - AFCON Qualifiers - 1425600095.pdf`
4. **Footer** — *Confidential — prepared for Curiosity. Not for distribution.*

`card_title` is already `"{agency} | {job_name}"`, so the agency name is
recoverable even if `creative_team` is ever blank. Use `creative_team` first,
fall back to the prefix of `card_title`, and if both are empty **fail the render**
rather than issue an unaddressed brief to an external party.

> **Naming mismatch to fix:** `creative_team` options list "Internal Studio Team"
> while the agency checklists say "Internal MTN studio", and "Curiosity" appears
> **twice** in `creative_team`. Automation `J109` (Internal MTN studio) is
> inactive, so nothing is broken today — but the duplicate will bite a
> select-by-value automation later. → [05](05_gaps-risks-open-questions.md) **D5**.

### What is on it

```
COVER      MTN masthead
           Prepared for: {creative_team}
           Job name (H1)
           {originating_opco} · {brief_type} · Tier {tier}
           "The brief in a sentence"  (highlight block)
           Job · Agency · Card ID · Current phase
           First revert · Go live · Material delivery · Job end

BODY       Campaign context            (see D3 — inherited from parent brief)
           Job information
           Channels and elements
           Job timelines
           Job details
           Deliverables

TAIL       Cost & timing               (budgets + approval decisions, per D4)
```

### What is deliberately **off** it

| Excluded | Why |
|---|---|
| `button`, `field`, `field_1`–`field_4` | Junk. Cannot be allowed near an external document. |
| `zambia_agencies_required`, `uganda_agencies_required` | Curiosity does not need to know EXP is also on the job. |
| `brief_attached`, `cost_timing_plan`, `agency_brief_attached` | Attachments, circular |
| `reviewer`, `brief_owner`, `studio_team` | Internal routing — unless D4 says otherwise |
| `*_cost_timing` budget fields, `cost_and_timing_*_review`, `feedback*` | **Internal cost approval.** Default OFF. → D4 |

**The agency-competitor point is the reason the allowlist is not negotiable.**
An auto-derived layout puts every agency on the job into a PDF sent to each of
them, the first time nobody checks.

---

## 4. Shared rendering rules

Ported from the existing `pdf_render.py` — proven, unchanged.

| Field type | Rendering |
|---|---|
| `long_text`, `statement` | full-width block, MTN-yellow rule above |
| `checklist_*`, `radio_*`, `assignee_select`, `attachment`, `connector` | bulleted list |
| `date` | `01 Sep 2026` |
| `datetime` | `01 Sep 2026, 14:30` |
| `currency` | `4 500 000` (space-grouped, no symbol — mixed UGX/ZMW) |
| `number` | plain; a bare 4-digit year stays `2026`, not `2,026` |
| `attachment` | filename only, decoded from the S3 URL |
| everything else | label / value row |

**Empty fields are skipped by default** (`--all-fields` prints them as
*Not provided*). Exception: a field marked `always=True` in config prints
*Not provided* even when blank — use it for anything whose absence is itself
information (dates, budget, the campaign block).

**Branding:** `brand.py` as-is. A4 portrait, MTN yellow `#FFCB05` on black,
logo from `assets/`. MTN Brighter Sans is not redistributable, so it sets in
Helvetica until the brand TTFs are dropped into `assets/fonts/` — at which point
it is a two-line change in `brand.py`, no layout work. Frontify is the source for
those files.
