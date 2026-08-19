---
title: Board structures — what's actually there
source: recon.json + agency_recon.json + tables_recon.json (live API capture, 2026-08-05)
last_updated: 2026-08-18
---

# 01 — Board structures

Read from live API captures, not from the Brain. Note: `MTN Brain/03_boards.md`
is **stale** — it lists pipes `307227220` / `307227231`, which are not the pipes
in scope here. Full field-by-field listing → [01a_field-inventory.md](01a_field-inventory.md).

Org `302505741` "MTN". Two databases: `mOUzRnnK` **Campaign Planning DB**
(60 fields, the live one) and `XO4RB1ds` **Campaign Planning** (27 fields, older).

---

## 1. Campaign Planning — `307284211`

61 start-form fields, 5 phases. Self-contained: no connectors in, no connectors out.

**Phases:** Campaign Backlog `343906150` → Campaign Review `343906151` →
**Approved Campaigns** `343906152` → Completed `343906154` / Cancelled `343906153`

**Form sections** (from zero-width-label header fields):

| Section | Fields |
|---|---|
| *(pre-section)* | `campaign_attached`, `approver_email`, `campaign_owner` |
| Campaign Information | 17 — name, OpCo, the 15 division selects, tier |
| Campaign Timelines | 5 — year, go-live, end, product go-live, milestones |
| Campaign Details | 15 — budgets, strategic pillar, objective, background, key message, problem, audience |
| Campaign KPI's | 13 — pillar + 5 KPI families, each with an `_other` |
| Supporting Information | 3 |

**Phase fields worth printing:** `campaign_review_decision`, `reviewer_comments`
(Campaign Review); `campaign_approval_date`, `approval_authority`,
`approval_notes`, `approval_status` (Approved Campaigns).

**On entry to Approved Campaigns**, automation `CP008` creates a matching record
in Campaign Planning DB `mOUzRnnK`. That record — not the card — is what
Campaign Briefing links to.

---

## 2. Campaign Briefing — `307284210`

82 start-form fields, 9 phases. **This is the board with the branching behaviour.**

**Phases:** Brief Backlog `343906140` → Brief Review 1st `343906141` / 2nd `343906146` /
3rd `343906147` → **Brief Submitted** `343906142` → Brief Updates `343906143` →
Completed `343906144` / Cancelled `343906145`

**Form sections:** *(pre)* 2 · Job information 20 · Channels and elements 7 ·
Job timelines 5 · Job details 44

### The branch: linked campaign vs the brief being the campaign

`is_this_job_part_of_an_approved_campaign` (`radio_horizontal`, **required**,
options `Yes` / `No`) drives seven form conditions. Resolved from the live
condition set:

| Answer | Fields shown |
|---|---|
| **Yes** | `campaign` — the connector to Campaign Planning DB |
| **No** | `originating_opco`, `strategic_pillar`, `target_audience`, `target_audience_additional_information`, `kpi_pillar` |

So when the answer is **No, this brief carries its own campaign-level context** —
it *is* the campaign. When **Yes**, that context lives on the linked record and
the brief leaves those fields blank.

**All five of those fields exist with the same field id on Campaign Planning
`307284211`.** They exist on `mOUzRnnK` too. That is what makes a single resolver
possible rather than two layouts — see [02_document-model.md](02_document-model.md).

### The connector

| | |
|---|---|
| Field id | `campaign` (internal `432597924`) |
| Label | *Select campaign* |
| Type | `connector`, `is_multiple: true`, **required** |
| Points at | Campaign Planning DB `mOUzRnnK` |
| Shown when | `is_this_job_part_of_an_approved_campaign == Yes` |

> ⚠ **Verified quirk, carried over from the existing tool:** on a connector field
> Pipefy puts the record **title** in `value` and the record **id** in
> `array_value` — the opposite way round to every other field type. Confirmed on a
> live card, Aug 2026. Take whichever side is all-numeric.

**Phase fields:** three approval rounds, each with `reviewer*`,
`job_review_decision*` and a feedback field. These belong in the document.

---

## 3. Agency Workflow — `307284207`

88 start-form fields, 10 phases. Cards are **created by automation**, one per
agency per job — nobody fills this form in by hand.

**Phases:** **Backlog** `343906124` → Cost & Timing `343906125` → C&T 1st Approval
`343906130` → C&T 2nd Approval `343906131` → Work In Progress `343906126` →
Reporting `343906127` → Recon & Billing `343906132` → Completed `343906128` /
Cancelled `343906129`

### How an agency card is born

On a Campaign Briefing card moving to **Brief Submitted** `343906142`
(guarded by `last_phase_in != 343906143 Brief Updates`, so a return trip from
Brief Updates does not re-fan-out), **17 automations** fire — one per agency:

```
J114 | Brief Submitted | Zambia agencies = Curiosity | Create agency card
J101 | Brief Submitted | Uganda agencies = Baitu Group | Create agency card
...
```

Each is `card_moved` → `create_connected_card` into `307284207`, conditional on
the agency appearing in `zambia_agencies_required` (`432597993`) or
`uganda_agencies_required` (`432597994`). Each copies **78 fields** from the
briefing card and sets two statically:

```
creative_team = "Curiosity"                    <- the agency name, hard-coded per automation
card_title    = "Curiosity | %{job_name}"
```

**`creative_team` (label "Team", `select`, internal `432597798`) is the
authoritative answer to "which agency has this brief gone to".** It is the field
the Agency Brief keys off.

**Live automation status — 8 of 17 are switched on:**

| Active | Inactive |
|---|---|
| Curiosity (ZM), Fulcrum, Plus Narrative, Baitu Group, Creatabuzz, Events Warehouse, EXP, Fenon | Curiosity (UG), Garage Group, Globtek, Internal MTN studio, Mediage, Moving Ads, Swivel, Talent Africa |

### Field-id drift, briefing → agency

The copy is not id-for-id. Five renames to carry in config:

| Campaign Briefing `307284210` | Agency Workflow `307284207` |
|---|---|
| `strategic_pillar` | `strategic_element` |
| `kpi_pillar_other_please_specify` | `kpi_pillar_other` |
| `awareness_kpi_other_please_specify` | `awareness_kpi_other` |
| `acquisition_growth_kpi_other_please_specify` | `acquisition_growth_kpi_other` |
| `digital_communication_kpi_other_please_specify` | `digital_communication_kpi_other` |
| `brand_desire_kpi_other_please_specify` | `brand_desire_kpi_other` |
| `nps_kpi_other_please_specify` | `nps_kpi_other` |
| `uganda_corporate_services_division` | `uganda_corporate_services_division_1` |

Campaign Planning uses `acquisition_and_growth_kpi_other`; Briefing uses
`acquisition_growth_kpi_other_please_specify`; Agency uses
`acquisition_growth_kpi_other`. Three boards, three ids, one field.

### Ten agency fields the automation does not populate

```
cost_timing_plan   reviewer   brief_owner   button
select_campaign
field   field_1   field_2   field_3   field_4
```

Two things fall out of that list:

1. **`select_campaign` (`432597813`) is never set.** An agency card has no link to
   the campaign, even when the parent brief had one. `is_this_job_part_of_an_approved_campaign`
   *is* copied — so the agency card can say "yes, part of a campaign" and have
   nothing to point at. Campaign context on the Agency Brief has to come from
   somewhere else. → [05](05_gaps-risks-open-questions.md), decision **D3**.
2. **`button`, `field`, `field_1`–`field_4` are junk** — a long_text called
   "Button" and five blank-label checklists. These are exactly the fields that a
   form-derived layout would print into a document an external agency reads.
   This is the case for the explicit allowlist. → [03](03_repo-and-config.md).

### The attachment collision

`brief_attached` on `307284207` is **already the copy target** of `brief_attached`
on `307284210`. Whatever PDF is on the briefing card lands there. Writing the
Agency Brief to the same field either overwrites the Job Brief or stacks a second
PDF next to it. → [05](05_gaps-risks-open-questions.md), decision **D1**.

---

## 4. Campaign Planning DB — `mOUzRnnK`

60 fields. Superset of the Campaign Planning form plus `segment_business_unit`,
`uganda_products`, `zambia_products`, `target_audience_core`,
`target_audience_internal`, `new_target_audience`. Field ids match the pipe for
everything the Job Brief needs. Contains its own junk: `field`, `field_1`–`field_4`.

Read with `table_record(id:)`. Keep the `card(id:)` fallback the existing tool has,
in case the connector is ever repointed at a pipe.

---

## 5. Summary — the three shapes

| | Campaign Planning | Campaign Briefing | Agency Workflow |
|---|---|---|---|
| Pipe | `307284211` | `307284210` | `307284207` |
| Start-form fields | 61 | 82 | 88 |
| Created by | Human | Human | **Automation (17 rules)** |
| Campaign context | Is the campaign | Linked record **or** own fields | **Neither — no link** |
| Agency identity | — | `*_agencies_required` (multi) | `creative_team` (single) |
| Junk fields | none | none | 6 |
| Existing generator | ✅ built | ✅ built | ❌ not built |
| Trigger phase | Approved Campaigns `343906152` | Brief Submitted `343906142` | Backlog `343906124` |
