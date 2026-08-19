---
title: MTN Pipefy PDF Generator — Investigation
client: MTN (direct — Zambia & Uganda)
status: Investigation / design agreement
last_updated: 2026-08-18
owner: Jason Blignaut
---

# MTN Pipefy PDF Generator — Investigation

Generate MTN-branded PDF briefs from Pipefy cards and attach them back to the
card, for three boards. Modelled on the Up & Up Group service
(`github.com/upandupbot/up-and-up-pdf`), rebuilt for MTN's board shapes.

**This folder is the design agreement. Nothing is built from it until it is signed off.**

---

## Read order

| # | Doc | What it settles |
|---|---|---|
| 1 | [01_board-structures.md](01_board-structures.md) | What the three boards actually look like — queried, not remembered |
| 2 | [02_document-model.md](02_document-model.md) | The three documents, and how campaign context resolves |
| 3 | [03_repo-and-config.md](03_repo-and-config.md) | Repo layout + the one-line-per-field config model |
| 4 | [04_triggers-and-deployment.md](04_triggers-and-deployment.md) | What fires it, and the EC2 box it runs on |
| 5 | [05_gaps-risks-open-questions.md](05_gaps-risks-open-questions.md) | **Decisions needed from you / MTN** |
| 6 | [06_build-plan.md](06_build-plan.md) | Phases, effort, acceptance criteria |
| — | [tools/recon_pdf_boards.py](tools/recon_pdf_boards.py) | Read-only script to refresh 01 from the live API |

---

## Scope

| Board | Pipe | Document | Attach target |
|---|---|---|---|
| Campaign Planning | `307284211` | **Campaign Brief** | `campaign_attached` |
| Campaign Briefing | `307284210` | **Job Brief** | `brief_attached` |
| Agency Workflow | `307284207` | **Agency Brief** | `agency_brief_attached` *(to be created — see 05)* |

Org `302505741`. Campaign Planning DB `mOUzRnnK` (URL id `307284208`).

---

## Decisions already taken

| Decision | Choice | Rationale |
|---|---|---|
| Agency documents | **One Agency Brief profile, agency-aware** | Agency Workflow is a single pipe. Each card already carries the agency in `creative_team`; the document renders that, rather than 16 near-identical layouts existing to be maintained. |
| Where it runs | **New repo `mtn-pipefy-pdf`, Up & Up pattern** — FastAPI, EC2, systemd | Same shape you already operate and support. One deploy story across two clients. |
| Field config | **Explicit declarative layout + form drift check** | Add a line = add a field, exactly like `layout.py` in the Up & Up repo. The drift checker stops the form and the document silently diverging. See [03](03_repo-and-config.md). |
| Triggers | **Pipefy automation on phase entry** — but CLI-first | EC2 isn't provisioned yet. Build and prove the three documents on the CLI, stand the box up in parallel, wire automations last. |

---

## What changed since the last round of work

There is already a working generator at
`MTN/pipefy_creations/campaign_pdf/` covering Campaign Planning and
Campaign Briefing, with rendered output in `out/`. It is a local CLI, not a
service, and it derives its layout from the live form rather than a config file.

**It is not thrown away.** The renderer (`pdf_render.py`), MTN branding
(`brand.py`), GraphQL client and presigned-upload path (`lib_pipefy.py`) are
proven and port straight across. What changes is the layout model
(auto-derived → declarative) and the delivery model (CLI → service).
See [06_build-plan.md](06_build-plan.md) for what ports and what is rewritten.

---

## Provenance of the findings in 01

Structure in this folder was read from `pipefy_creations/pipefy_audit/recon.json`
and `agency_automations/agency_recon.json` — live API captures taken **2026-08-05**,
13 days before this investigation.

`api.pipefy.com` is not reachable from the Claude sandbox, so it could not be
re-queried here. **Run [tools/recon_pdf_boards.py](tools/recon_pdf_boards.py)
on your machine before build starts** and diff it against
[01_board-structures.md](01_board-structures.md). Field ids and phase ids in this
folder are treated as facts to re-verify, not facts to code against.
