# MTN Pipefy PDF Generator

Renders an MTN-branded PDF brief from a Pipefy card and attaches it back to the
card. FastAPI service triggered by a Pipefy automation, plus a CLI for dry runs
and backfill.

**Deploying this?** Start at [`SERVER_SETUP.md`](SERVER_SETUP.md) — it is the
complete, literal deploy path (provision, configure, wire the Pipefy
automations, verify). Before making any change, run the guardrail suite:
`venv/Scripts/python.exe -m pytest -q` (or `./venv/bin/python -m pytest -q` on
Linux) plus the four `--mock` fixture renders in "Local use" below — that is
the offline gate every change here must clear. House engineering rules —
module layout, naming, the `(data, status_code)` contract — live in
[`CLAUDE.md`](CLAUDE.md).

**What's still unproven:** the presigned upload → attach → verify path has
never executed against live Pipefy. `SERVER_SETUP.md` step 5 is where that
runs for the first time — watch it closely on first live fire.

| Board | Pipe | Document | Attaches to | Generated on entry to |
|---|---|---|---|---|
| Campaign Planning | `307284211` | **Campaign Brief** | `campaign_attached` | Campaign Review `343906151` |
| Campaign Briefing | `307284210` | **Job Brief** | `brief_attached` | Brief Review - 1st Approval `343906141` |

Org `302505741`. Campaign Planning DB `mOUzRnnK`.

**Agency Workflow `307284207` has no profile and needs none.** Agency cards
receive the Job Brief through the existing fan-out automations, which copy
`brief_attached` from the briefing card when it moves to Brief Submitted. That
is why the Job Brief is generated one phase earlier, at first approval: the file
has to be on the card before the fan-out copies it.

It also means **the Job Brief is read by external agencies**. The agency roster
fields and the internal review feedback are in `set_deny` in `my_layout.py` for
that reason — see the comment there before removing anything from it.

---

## Adding a field to a document

One line in `my_layout.py`:

```python
Section("Job details", [
     Field("job_objective", s_render="block"),
     Field("new_field_id"),               # <- this
])
```

The label comes off the live Pipefy form at run time, so re-wording a field in
Pipefy needs no code change. A **new** field stays invisible until someone adds
it here, on purpose — that is what keeps a stray form field out of a document an
agency reads.

`Field(...)` takes: `s_label` to override the live label, `s_source`
(`"card"` / `"campaign"` / `"auto"`), `b_always=True` to print *Not provided*
instead of skipping, `s_render` (`"inline"` / `"block"` / `"list"`), `s_note`.
`OneOf("Division", [...ids])` collapses mutually-exclusive fields into one row.

Then run the drift checker so nothing has quietly diverged:

```bash
python check_drift.py
```

---

## The linked-vs-standalone brief

`is_this_job_part_of_an_approved_campaign` on Campaign Briefing drives the
document, not just the form:

- **Yes** — the `campaign` connector points at a Campaign Planning DB record.
  Campaign context is inherited from it and every inherited value is marked
  *(from the linked campaign)*.
- **No** — the form reveals `originating_opco`, `strategic_pillar`,
  `target_audience`, `target_audience_additional_information` and `kpi_pillar`
  on the brief itself. The brief *is* the campaign, and the section is titled
  **Campaign context (defined by this brief)**.
- **Yes, but nothing linked** — the section stays and says so in the document.
  A brief missing its campaign must look wrong to whoever opens the PDF, not
  quietly omit a section.

All three states render from fixtures — see below.

---

## Files

| File | Job |
|---|---|
| `main.py` | FastAPI. MAIN → WORKER → HEARTBEAT → entry. Validates, dispatches, returns. |
| `my_funcs.py` | General helper: text, value coercion, display formatting, `fn_log()`. No API calls. |
| `my_pipefy.py` | Every Pipefy call: GraphQL, card read, table record read, presigned upload, `updateCardField`, verify. |
| `my_layout.py` | **What goes on each PDF.** The file you edit. |
| `my_brief.py` | Card → doc model, the campaign resolver, and `fn_generate_brief()` — the one code path both the webhook and the CLI run. |
| `my_pdf.py` | MTN brand constants and the reportlab renderer. Knows nothing about Pipefy. |
| `my_state.py` | Replay token and the in-flight / dedup guard. |
| `make_pdf.py` | CLI: dry run, apply, backfill, `--mock`. |
| `check_drift.py` | Layout vs live form. Exit 1 on drift. CI gate. `--scaffold <pipe_id>` for a new profile. |
| `fixtures/` | Realistic cards for `--mock`. Built from the real form structure. |

---

## Local use

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp segredo.ini.example segredo.ini      # fill in [Pipefy] token, chmod 600
```

**Token resolution order:** `[Pipefy] token` in `segredo.ini` first — that is what
the box uses and the only source that should ever be populated there. Failing
that, a `MTN_PIPEFY_TOKEN` / `PIPEFY_ACCESS_TOKEN` / `PIPEFY_TOKEN` environment
variable, then a `.env` or `.env.txt` beside the repo or one or two levels above
it. The fallback exists because the MTN client folder already holds a token at
`MTN/.env.txt`, and making a dev copy a live credential into a second file is
how credentials end up somewhere they should not be. It is a local convenience,
not a deployment path — the CLI banner prints which source it used.

```bash
python3 make_pdf.py 1425600095                    # dry run -> ./out, writes nothing
python3 make_pdf.py 1425600095 --apply            # upload, attach, verify
python3 make_pdf.py 1425600095 --apply --keep-existing
python3 make_pdf.py 1425600095 --all-fields       # print blanks as "Not provided"
python3 make_pdf.py 1425600095 --profile brief    # force a profile
python3 check_drift.py
python3 -m uvicorn main:app --host 127.0.0.1 --port 5040 --reload  # local dev server
venv/Scripts/python.exe -m pip install -r requirements-dev.txt && venv/Scripts/python.exe -m pytest  # install + run the guardrail test suite
```

No token needed to check a layout change:

```bash
python3 make_pdf.py --mock fixtures/mock_brief_linked.json
python3 make_pdf.py --mock fixtures/mock_brief_standalone.json
python3 make_pdf.py --mock fixtures/mock_brief_claimed_not_linked.json
python3 make_pdf.py --mock fixtures/mock_campaign.json
```

Backfill:

```bash
for C in 1425589636 1425600095; do python3 make_pdf.py $C --apply || echo "FAILED $C"; done
```

Exit `0` means attached **and** verified by a read-back.

---

## Endpoints

```
POST /generate-pdf        header: X-MTN-PDF-Token: <webhook_secret>
POST /generate-pdf?dry=1  render and report, attach nothing
POST /hello               heartbeat
```

Accepts `{"card_id": 1425600095}` or the Pipefy webhook shape
`{"data": {"card": {"id": 1425600095}}}`. The main thread validates and returns;
rendering and attaching happen in a `BackgroundTasks` worker.

**Retrigger uses the same route.** Send the original payload with
`X-MTN-Replay-Token: <replay_token>` to bypass the dedup window. There is no
separate `/retrigger` endpoint to keep in step with this one.

---

## Attach behaviour, deliberately

`updateCardField` **overwrites** an attachment field — it does not append. The
default matches that: one current brief per card, so a re-run or a Pipefy
webhook retry replaces rather than stacks, and a replay cannot produce a second
copy. The log records how many files were removed. `--keep-existing` re-sends
the paths already on the field alongside the new one.

After attaching, the card is re-read and the file confirmed. `200` = attached
and verified, `202` = attached but unverified, and the CLI exits `1`.

---

## Assumptions and things to watch

- **Connector value shape is backwards.** On a connector field Pipefy puts the
  record *title* in `value` and the record *id* in `array_value` — the opposite
  of every other field type, and the opposite of the platform documentation.
  Verified on a live card, Aug 2026. `fn_connected_record_ids()` takes whichever
  side is all-numeric, so it survives Pipefy changing its mind.
- **Presigned upload** has never been exercised against live. `createPresignedUrl`
  has returned the URL under both `url` and `downloadUrl` across versions, and
  some storage backends reject a `Content-Type` they did not sign — both are
  handled, neither is proven. First thing to check if `--apply` fails.
- **Multi-linked campaigns.** `Select campaign` is multi-select. If a brief links
  more than one campaign the first is used and it is logged. Change this if
  multi-campaign briefs turn out to be real.
- **Stale campaign data.** The DB record is a snapshot taken at approval. If the
  campaign is edited afterwards and `CP008` is create-only, an inherited Job
  Brief carries the old values.
- **Token** must be a service account with write on both pipes and read on
  `mOUzRnnK`. A read-only token renders fine and fails at the attach step.
- **Fonts.** MTN Brighter Sans is not redistributable, so the document sets in
  Helvetica. Drop the brand TTFs into `assets/fonts/` and register them at the
  top of `my_pdf.py` — no layout work.
- **Approval routing.** Generation fires on entry to first approval. If a brief
  can reach Brief Submitted without passing through it, no PDF is ever made and
  the fan-out copies an empty field. Confirm the routing before go-live.
- **Do not add `--workers N` to the systemd unit's `ExecStart` line.**
  `my_state.py`'s in-flight/dedup lock only coordinates within a single
  process — multiple uvicorn workers would not share it, and the
  duplicate-render race the lock exists to prevent would silently come back.
