---
title: Repo structure and the field-config model
last_updated: 2026-08-18
---

# 03 — Repo structure and field config

## 1. Repo

`mtn-pipefy-pdf` — same shape as `up-and-up-pdf`, with the layout split per
document instead of one 305-line `layout.py`.

```
mtn-pipefy-pdf/
├── README.md
├── requirements.txt
├── .env.example                     # no secrets, ever
├── .gitignore                       # .env, venv, __pycache__, *.pdf, out/
│
├── main.py                          # FastAPI: /health, /pipefy/generate-pdf
├── cli.py                           # python cli.py <card_id> [--apply] — dev + backfill
│
├── core/
│   ├── pipefy.py                    # GraphQL client, card read, table_record read,
│   │                                #   presigned upload, updateCardField, whoami
│   ├── resolve.py                   # card + linked record + profile -> doc model
│   │                                #   (this is where source="auto" is decided)
│   ├── render.py                    # doc model -> PDF bytes (reportlab). Pipefy-blind.
│   ├── brand.py                     # MTN colours, fonts, logo, footer strings
│   └── errors.py
│
├── profiles/
│   ├── __init__.py                  # PROFILES registry — the only pipe-id lookup
│   ├── campaign_brief.py            # 307284211
│   ├── job_brief.py                 # 307284210
│   └── agency_brief.py              # 307284207
│
├── layout_dsl.py                    # Doc / Section / F / oneof — ~120 lines
│
├── tools/
│   ├── recon.py                     # read-only live board dump -> recon_live.json
│   ├── scaffold_layout.py           # live form -> a starter profiles/*.py
│   └── check_drift.py               # layout vs live form. Exit 1 on drift. CI gate.
│
├── assets/
│   ├── mtn_logo.png
│   ├── mtn_logo_transparent.png
│   └── fonts/                       # MTN Brighter Sans when licensing allows
│
├── tests/
│   ├── fixtures/                    # mock_campaign.json, mock_brief.json,
│   │                                #   mock_agency.json, mock_campaign_record.json
│   ├── test_resolve.py              # incl. the Yes/No campaign branch
│   ├── test_layout_dsl.py
│   └── test_render_smoke.py         # renders each profile from fixtures, asserts
│                                    #   page count > 0 and no junk field ids present
└── deploy/
    ├── mtn-pipefy-pdf.service
    └── RUNBOOK.md
```

**One rule, enforced by review:** `core/` and `layout_dsl.py` never mention a
pipe id, a field id or a document name. Everything client-specific is in
`profiles/`. That is what makes a fourth board a new file rather than a refactor.

---

## 2. The config model — one line per field

This is the up-and-up `sections` list, typed and with the campaign resolver
folded in.

```python
# profiles/agency_brief.py
from layout_dsl import Doc, Section, F, oneof

DOC = Doc(
    key          = "agency",
    pipe_id      = "307284207",
    title        = "Agency Brief",
    attach_field = "agency_brief_attached",
    name_field   = "job_name",
    agency_field = "creative_team",
    filename     = "Agency Brief - {creative_team} - {job_name} - {card_id}.pdf",

    cover = dict(
        prepared_for = "creative_team",
        subtitle     = ["creative_team", "originating_opco", "brief_type"],
        highlight    = ("The brief in a sentence", "the_brief_in_a_sentence"),
        meta = [
            ("Job",               "job_name"),
            ("Agency",            "creative_team"),
            ("Card ID",           "@id"),
            ("Current phase",     "@phase"),
            ("First revert",      "first_revert_date"),
            ("Job go live",       "job_go_live_date"),
            ("Material delivery", "material_delivery_date"),
            ("Job end",           "job_end_date"),
        ],
    ),

    sections = [
        Section("Job information", [
            F("job_name"),                                  # <- adding a field is this line
            F("brief_type"),
            F("tier"),
            F("originating_opco", source="auto"),
            oneof("Division", "uganda_division", "zambia_division",
                              "uganda_marketing_division", "zambia_marketing_division"),
        ]),

        Section("Channels and elements", [
            F("required_channels"),
            F("atl_elements"),
            F("btl_elements"),
            F("digital_elements"),
            F("internal_communications_elements"),
            F("sponsorship_and_activation_elements"),
            F("pr_elements"),
        ]),

        Section("Job timelines", [
            F("first_revert_date",     always=True),
            F("job_go_live_date",      always=True),
            F("material_delivery_date"),
            F("job_end_date"),
            F("key_milestones"),
        ]),
        # ... Job details, Deliverables
    ],

    # Never render these, whatever anyone adds to the form later.
    deny = {"button", "field", "field_1", "field_2", "field_3", "field_4",
            "brief_attached", "agency_brief_attached", "cost_timing_plan",
            "zambia_agencies_required", "uganda_agencies_required",
            "reviewer", "brief_owner", "studio_team"},
)
```

### `F(...)` — the whole spec

| Arg | Default | What it does |
|---|---|---|
| `field_id` | — | The Pipefy field id. **The only required argument.** |
| `label` | live form label | Override the printed label |
| `source` | `"card"` | `"card"` · `"campaign"` · `"auto"` (campaign if linked, else card) |
| `always` | `False` | Print *Not provided* when blank instead of skipping |
| `render` | by type | Force `"bullets"`, `"block"`, `"inline"`, `"date"`, `"money"` |
| `when` | `None` | Only render if a predicate on the card holds |
| `note` | `None` | Small grey line under the value (e.g. *"from campaign"*) |

`F("job_name")` is the minimum. Label comes from the live form, so the document
tracks a label change in Pipefy without a code change — the **allowlist** is
pinned, the **wording** is not. That is the right split: you want to know when a
new field appears, you do not want to re-deploy because someone fixed a typo.

`oneof("Division", *ids)` collapses the fifteen division selects into one row —
first populated wins.

### Why not derive it from the live form

The existing tool does, and for two internal boards it works. It stops working
here:

- `307284207` carries a `button` field and five blank-label checklists. They would
  print into a document sent to an external agency.
- The agency PDF must **exclude** `*_agencies_required`. An allowlist excludes by
  omission; a derive-everything model needs a deny list that someone has to
  remember to extend — and the failure is silent and outbound.
- Field order on the live form is `index`-ordered and moves when anyone drags a
  field in the form builder. Client-facing document order should not.

**The drift checker gives back what auto-derive was for.** You still find out the
moment the form changes — you just find out in CI instead of in a client's inbox.

---

## 3. Scaffold and drift check

**Scaffold** — write the first draft of a profile from the live form, sections
and all, junk commented out:

```bash
python tools/scaffold_layout.py 307284207 --out profiles/agency_brief.py
```

**Drift check** — compare every profile against the live form:

```bash
python tools/check_drift.py
```

```
Agency Brief (307284207)
  MISSING  on form, not in layout:
    creative_inspiration_free_text_link_s   long_text     added 2026-08-14
  STALE    in layout, not on form:
    strategic_pillar                        (renamed to strategic_element?)
  DENIED   on form, explicitly excluded:    6 fields  (ok)
FAIL — 2 differences. Add or deny each field, then re-run.
```

Runs in CI on every push, and as a weekly scheduled job that posts to Slack.
`MISSING` is the one that matters: it means Pipefy grew a field and three PDFs
have quietly stopped being complete.

---

## 4. What ports from `pipefy_creations/campaign_pdf/`

| Existing file | Fate |
|---|---|
| `lib_pipefy.py` | → `core/pipefy.py`. **Port as-is.** Connector value/array_value quirk, presigned-upload retry, four-route connector resolution — all hard-won. |
| `pdf_render.py` | → `core/render.py`. Port; add the cover *Prepared for* block. |
| `brand.py` | → `core/brand.py`. Unchanged. |
| `card_model.py` | → `core/resolve.py`. **Rewrite.** Form-derived → layout-driven, plus the `source="auto"` resolver. The value-formatting half ports; the structure half does not. |
| `common.py` | → `profiles/*.py`. Concept survives, split three ways and typed. |
| `make_pdf.py` | → `cli.py`. Keep every flag — they are good flags. |
| `mock_*.json` | → `tests/fixtures/`. Reuse. |
| `probe_connector.py` | → `tools/`. Keep — it earned its place. |
| `out/*.pdf` | Reference output for visual regression. |

Roughly 60% of the existing code carries over. The rewrite is `card_model.py`
and the config layer.
