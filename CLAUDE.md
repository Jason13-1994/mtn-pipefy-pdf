<!-- GSD:project-start source:PROJECT.md -->
## Project

**MTN Pipefy PDF Brief Service**

A FastAPI webhook service that turns an approved MTN Pipefy card into a branded PDF brief and
attaches it back to that card. Two document profiles exist today: the **Campaign Brief**
(Campaign Planning pipe `307284210`) and the **Job Brief** (Job Briefing pipe). A Pipefy
automation fires on approval, the service renders the PDF from a declarative field allowlist,
uploads it via presigned URL and attaches it to the card. Agencies receive the Job Brief through
an existing Pipefy fan-out that copies `brief_attached` onto agency cards.

The code is written and works offline against fixtures. **It has never been deployed.** This
milestone is about making it safe to put on a box and point MTN's Pipefy automation at it.

**Core Value:** An approved brief becomes a correct, branded PDF attached to the right card — and no
internal-only field ever appears on an agency-facing document.

### Constraints

- **Standard**: dYdX Digital `dydxdev-best-practices`, NEW PROJECT mode, `my_*` lineage — the repo already follows it; changes must not drift from it.
- **Platform authority**: Pipefy API specifics defer to the `platform-pipefy` skill. It is not currently attached — load it before writing any Pipefy API code rather than reconstructing endpoints from memory.
- **Infrastructure**: EC2 + systemd + Nginx + no database. No Docker, no Lambda, no container orchestration.
- **Tech stack**: FastAPI + uvicorn + reportlab + requests + pytz, exact-pinned. Python 3.14 in dev.
- **Indentation**: 5 spaces per level, applied consistently across every file. Match it.
- **Git**: Claude does not run state-changing git commands. Commands are written out for the developer to run, with files named explicitly — never `git add .`, and `segredo.ini` never staged.
- **Destructive operations**: never executed. Handed over as commands with impact stated.
- **Live systems**: no retrigger fired against production unprompted; live-fire runs go against a disposable card only.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14 (dev venv at `venv/`, `venv/pyvenv.cfg` pins `pythoncore-3.14-64`) - entire codebase (`main.py`, `my_*.py`, `make_pdf.py`, `check_drift.py`)
- None. No frontend, no JS/TS, no SQL (no database).
## Runtime
- CPython 3.14, single process, no async workers beyond FastAPI's own event loop + `BackgroundTasks`
- Production target per `SERVER_SETUP.md`: Ubuntu 24.04 LTS, EC2 `t3.small`
- `pip` against `requirements.txt` (no `pyproject.toml`, no `poetry.lock`, no `Pipfile.lock`)
- Lockfile: missing — `requirements.txt` pins exact versions (`==`) but there is no hash-locked/reproducible lockfile
- Install path: `python -m venv venv && ./venv/bin/pip install -r requirements.txt` (README.md, SERVER_SETUP.md)
## Frameworks
- FastAPI `0.115.0` (`requirements.txt`) - HTTP service exposing `/generate-pdf` and `/hello` (`main.py`)
- Uvicorn `0.30.6` - ASGI server; run directly via `uvicorn.run("main:app", ...)` in `main.py:233` for dev, and via systemd `ExecStart=.../uvicorn main:app` in production (`mtn-pipefy-pdf.service`)
- None detected. No `pytest`, `unittest`, or test framework in `requirements.txt`. Verification is done via `check_drift.py` (layout-vs-live-form comparison, exit-code gate) and manual dry runs (`make_pdf.py --mock fixtures/*.json`), not an automated test suite.
- No bundler/transpiler — pure Python, run directly. No `Makefile`, no `tox.ini`, no `Dockerfile`.
- `main.py:266`'s sole `__main__` entry point calls `uvicorn.run("main:app", host=S_BIND, port=I_PORT, timeout_keep_alive=90)` with no `reload` kwarg — the same call runs identically in dev and, via the `systemd` unit's `ExecStart=.../uvicorn main:app`, in production.
## Key Dependencies
- `requests` `2.32.3` - all outbound HTTP: Pipefy GraphQL calls (`my_pipefy.py`), presigned-URL PUT uploads (`my_pipefy.py`), Papertrail/SolarWinds log POSTs (`my_funcs.py:fn_log`)
- `reportlab` `4.2.5` - PDF generation/rendering engine; entire `my_pdf.py` is built on `reportlab.platypus` (`BaseDocTemplate`, `Frame`, `Table`, `Paragraph`, etc.) and `reportlab.pdfgen.canvas`
- `pytz` `2024.2` - timezone handling; all timestamps are rendered in `Africa/Johannesburg` (`my_funcs.py:S_TIMEZONE`)
- `fastapi` `0.115.0` + `uvicorn` `0.30.6` - web service layer (see Frameworks above)
- `configparser` - reads `segredo.ini` in `main.py`, `my_pipefy.py`, `my_funcs.py`, `my_state.py`, `make_pdf.py`
- `secrets` - constant-time token comparison (`secrets.compare_digest`) for webhook auth (`main.py:97`) and replay-token check (`my_state.py:47`)
- `threading` - single in-process `threading.Lock()` guarding the in-flight/dedup dict in `my_state.py`
- `argparse` - CLI argument parsing in `make_pdf.py` and `check_drift.py`
## Configuration
- No `.env`-file-driven config for the service itself. All runtime config is in an INI file, `segredo.ini` (git-ignored; see `.gitignore:1`), read via `configparser` independently in each module (`main.py`, `my_pipefy.py`, `my_funcs.py`, `my_state.py`, `make_pdf.py`) — each module does its own `_config.read(os.path.join(HERE, "segredo.ini"))`, no shared config singleton.
- `segredo.ini.example` (committed) documents the required keys with blank values — copy to `segredo.ini` and `chmod 600` (README.md, SERVER_SETUP.md).
- Sections and key purposes (names only, no values — see SECURITY note below):
- A local-dev-only token fallback chain exists in `my_pipefy.py:fn_resolve_token()`: `segredo.ini` → `MTN_PIPEFY_TOKEN` / `PIPEFY_ACCESS_TOKEN` / `PIPEFY_TOKEN` env var → `.env` / `.env.txt` beside the repo or one/two directories above it. Only the `segredo.ini` value is meant to ever be populated on the production box; the source used is printed (never the value) via `S_TOKEN_SOURCE`.
- Safety guard: `main.py:66-71` refuses to start when `[Service] webhook_secret` is blank or under 20 characters **and** `[Service] bind` is not a loopback address, via `fn_is_loopback_bind()`.
- No build config files — nothing to compile/bundle. `requirements.txt` is the only manifest.
## Platform Requirements
- Python 3.14 (per project `venv/`), pip, network access to `api.pipefy.com` for live runs
- No token/network required for `--mock` fixture-based rendering (`make_pdf.py --mock fixtures/*.json`)
- Windows dev environment observed (`venv/Scripts`), deployed to Linux in production
- EC2 `t3.small`, Ubuntu 24.04 LTS (`SERVER_SETUP.md`)
- systemd service `mtn-pipefy-pdf.service` running `uvicorn main:app --host 127.0.0.1 --port 5040 --timeout-keep-alive 90` as user `ubuntu`, `WorkingDirectory=/home/ubuntu/mtn-pipefy-pdf`, `Restart=always`
- Nginx reverse proxy on port 443 in front of `127.0.0.1:5040`, TLS via Certbot; uvicorn binds loopback only — Nginx is the only thing that should reach it
- No database — service is stateless and rebuilds from the repo; all durable state lives in Pipefy itself
- Logging: journald (via systemd) + Papertrail/SolarWinds (`my_funcs.py:fn_log`)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Module naming: the `my_*` lineage
| Module | Responsibility | Rule enforced by its own docstring |
|---|---|---|
| `my_funcs.py` | Pure text/value/formatting helpers + `fn_log()` | "NO Pipefy calls, NO database calls, NO business logic" (`my_funcs.py:4-6`) |
| `my_pipefy.py` | Every Pipefy GraphQL/HTTP call | "nothing outside it issues an HTTP request to Pipefy" (`my_pipefy.py:4-6`) |
| `my_layout.py` | Declarative field allowlist — "the file you edit" (`my_layout.py:4`) |
| `my_brief.py` | Card → doc model + orchestration (`fn_generate_brief`) |
| `my_pdf.py` | reportlab renderer — "knows NOTHING about Pipefy" (`my_pdf.py:4`) |
| `my_state.py` | In-process replay guard / idempotency lock |
## Function naming: the `fn_` prefix
## Hungarian variable prefixes
| Prefix | Type | Example |
|---|---|---|
| `s_` | string | `s_card_id`, `s_field_id`, `s_label` (`my_brief.py:192`) |
| `d_` | dict | `d_card`, `d_result`, `d_payload`, `d_details` (`main.py:98`) |
| `l_` | list | `l_values`, `l_sections`, `l_paths` (`my_pipefy.py:698`) |
| `i_` | int (count/index/generic) | `i_max_length`, `i_removed`, `i_attempt` (`my_pipefy.py:127`) |
| `n_` | int (status code / numeric result) | `n_status`, `n_now`, `n_seen` (`my_state.py:61`) — used specifically where the int is a status code or a comparison quantity, distinct from `i_` counts |
| `b_` | bool | `b_apply`, `b_claimed`, `b_verified`, `b_is_replay` (`my_brief.py:567`) |
| `o_` | object / instance (non-primitive) | `o_doc`, `o_item`, `o_field`, `o_parser`, `o_pdf_bytes` (`my_layout.py:37`, `make_pdf.py:127`) |
| `t_` | tuple | `t_highlight` (`my_layout.py:103`) |
| `e_` | exception-related | `e_type`, `e_object`, `e_traceback` (every handler, e.g. `my_funcs.py:99`) |
| `set_` | set | `set_deny`, `set_ids`, `set_live` (`my_layout.py:121`, `my_layout.py:543`) |
| `S_`, `I_`, `B_`, `L_`, `D_` | module-level constant, same letter-to-type mapping, uppercase | `S_INTEGRATION_KEYWORD`, `I_PORT`, `L_TOKEN_VARS`, `D_PROFILE_BY_KEY` (`main.py:41-46`, `my_pipefy.py:30`, `my_layout.py:487`) |
- `stamp` — the logging context dict, always called `stamp` (never `d_stamp`) everywhere it is threaded through (`my_funcs.py:48`, every `fn_log(stamp=stamp, ...)` call).
- `value` / `values` inside tight local loops (`my_funcs.py:188`, `my_pipefy.py:499`) — bare, no prefix, when the loop body is one line and the type is obvious from context.
- `resp` for an HTTP response object from `requests` — not `o_resp` (`my_funcs.py:87`, `my_pipefy.py:128`). This is the one place `requests.Response` doesn't get `o_`.
- `config` / `_config` (module-level `configparser.ConfigParser()` instance) — not `o_config` (`main.py:38`, `my_funcs.py:22`). Leading underscore marks "module-private, read once at import time."
## The `(data, status_code)` return contract
- **Every function body is one big `try:` wrapping the whole function**, with `except Exception as e:` as the final handler (`## EXCEPTION MUST BE THE LAST HANDLER`, `my_funcs.py:98`). A narrower exception (e.g. `requests.exceptions.RequestException`) may be caught first and given its own status code — see `fn_log()` returning `206` on a Papertrail network failure vs. `206` on a generic exception (`my_funcs.py:95-101`).
- **The "empty" data value matches the caller's expected type**: `{}` for dict-returning functions, `[]` for list-returning functions, `""` for string-returning functions, `False`/default bool for bool-returning functions. Never `None` as the data half of the tuple.
- **Status codes are meaningful HTTP-style codes even for non-HTTP internal functions** — `200` success, `404` not found, `409` no profile for this pipe (conflict/no-match), `422` unprocessable (bad data, GraphQL errors block, Pipefy rejected the call), `500` unhandled exception. `fn_generate_brief()`'s docstring enumerates its own contract explicitly (`my_brief.py:573-579`).
- **Every failure path logs before returning** — `my_funcs.fn_log(stamp=stamp, txt=..., d_details={...})` — except the small set of pure helpers in `my_funcs.py` itself (`fn_tidy`, `fn_safe_filename`, `fn_format_date`, etc.) which return a safe default silently on exception with no logging, because they are one-liners with no meaningful failure to report and `fn_log()` cannot log itself.
- **Some functions return a 3-tuple** when a third piece of "how it happened" context is useful for logging — `fn_find_connector_field()` returns `(d_field, s_how)` (`my_pipefy.py:451`), `fn_fetch_linked_campaign()` returns `(d_record, d_table, s_route)` (`my_brief.py:472`), `fn_claim()` returns `(b_claimed, s_reason)` (`my_state.py:52`). The last element is always a short string used only for logging/console output, never branched on by the caller.
- **Functions with no failure mode still follow the pattern where it aids symmetry** — e.g. `fn_stats()` returns a plain dict, not a tuple, because there is nothing for a caller to branch on (`my_state.py:105`). Not every function needs the tuple — only ones a caller must react to differently based on outcome.
## Logging: `fn_log()` payload shape
- **`stamp`** is a dict built once per request/run by `fn_build_stamp(s_card_id, s_mode)` (`my_funcs.py:48-59`) — `{"time": <µs epoch int>, "card_id": <str>, "Mode": <str>}` — and threaded as a keyword argument through every function call down the stack, never reconstructed mid-flow. `stamp["card_id"]` gets mutated once known (`main.py:127`), never rebuilt.
- **`txt`** is always a short, human sentence, not a code or key. Error variants append `at line {e_traceback.tb_lineno}` so a log line points at the exact failing line without a full traceback: `f"Pipefy card fetch failed at line {e_traceback.tb_lineno}"` (`my_pipefy.py:257`).
- **`d_details`** is a flat-ish dict of whatever context helps debug the specific event — raw payloads, ids, before/after counts, the caught exception as `str(e)`. Full raw payloads are logged deliberately on rejects (`my_funcs.fn_log(..., d_details={"raw_payload": d_payload})`, `main.py:132`) so nothing is lost even on a malformed request.
- **`fn_log()` never raises and never blocks the caller on a logging failure** — a Papertrail network error is caught and printed to stdout, returning `(None, 206)` rather than propagating (`my_funcs.py:95-97`).
- **Two silent modes exist for local/CLI use**, both driven by `stamp["Mode"]`, checked at the very top of `fn_log()` before doing any network work (`my_funcs.py:70-74`):
- **`d_extra["caller"] = inspect.stack()[1][3]`** (`my_funcs.py:77`) auto-tags every log line with the name of the calling function via stack introspection — never pass a `caller` key manually.
- Log destination is Papertrail/SolarWinds over HTTP, configured via `[PaperTrail]` in `segredo.ini` (`my_funcs.py:25-27`) — see STACK.md/segredo.ini section below.
## Config loading via `segredo.ini`
- **`config.read()` never raises if the file is missing** — every single value is pulled with an explicit `fallback=`, so the service degrades to defaults rather than crashing on a missing `segredo.ini`. There is no startup validation step that checks all required keys are present — missing secrets surface later, at the first call that needs them (e.g. `fn_graphql()` logging "No Pipefy token found" at call time, `my_pipefy.py:110-117`).
- **`config` is module-level and private** in library modules (`_config`, leading underscore — `my_funcs.py:22`, `my_pipefy.py:23`, `my_state.py:27`), but public (`config`, no underscore) in `main.py:38` because `main.py` is the top-level entry point, not something imported elsewhere.
- **`segredo.ini` is git-ignored** (`.gitignore:1`); `segredo.ini.example` is the checked-in template with the same keys and blank/placeholder values, `chmod 600` on the box. **Never copy a live value out of `segredo.ini` into any document, log line, or commit** — only the *source* of a credential is ever logged (`S_TOKEN_SOURCE`, `my_pipefy.py:33-51`), never the value.
- **Startup-time safety check pattern**: `main.py:66-71` raises `RuntimeError` at import if a dangerous combination of config values is detected (`webhook_secret` blank or under 20 characters, and `bind` not loopback, per `fn_is_loopback_bind()`) — config validation that matters for safety happens as an explicit guard clause right after the config block, not buried in a function.
## Error handling, more generally
- **Try/except wraps the entire function body**, one level of indentation, `except Exception as e:` last (see return-contract section above). There is effectively no un-guarded top-level function in any `my_*` module.
- **`sys.exc_info()` + `e_traceback.tb_lineno`** is the idiom for reporting *where* a failure happened, everywhere, instead of `traceback.format_exc()` or re-raising:
- **Fail-open where blocking would be worse than the risk** — the idempotency claim guard explicitly fails open: "a broken guard must not stop briefs being generated" (`my_state.py:79-85`). Not every failure defaults to open; attach/upload failures correctly fail closed (return non-200). Read the surrounding comment before assuming a failure mode.
- **HTTP-style status codes as the vocabulary for "what went wrong"** throughout, even in pure internal functions with no HTTP involved — see the return-contract section. `main.py`'s own route handler also sets `resp.status_code` directly rather than raising `HTTPException` (`main.py:73`, `main.py:97`, `main.py:222`).
## Docstrings and comments
- **Every function has a triple-quoted docstring immediately after the signature**, indented one level further than the `def`, describing: what it does, its return shape, and any non-obvious "why." Example shape:
- **Module-level docstring is a full design note**, not a one-liner — states the module's single responsibility, what it must never do, and often the "why" behind a non-obvious choice (`my_pipefy.py:1-9`, `my_brief.py:1-18`, `my_state.py:1-15`).
- **Section banner comments** divide large modules into named blocks:
- **Inline step comments inside long orchestration functions** use the same triple-quoted-block style at reduced scope, numbered: `'''  Step 1: Read the card  '''` (`my_brief.py:585`, repeated through `fn_generate_brief`, and mirrored in `main.py`'s `main()`/`worker()`).
- **"Why," not "what," in comments.** Comments explain non-obvious platform behaviour or design decisions — e.g. the connector value-shape reversal (`my_pipefy.py:410-419`), why generation happens at approval and not submission (`main.py:1-19`), why there's no database (`my_state.py:1-14`). Comments restating what the next line obviously does do not appear.
## Type hints
## String formatting
## Import order
## Indentation
## Line length
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
```
## Component Responsibilities
| Component | Responsibility | File |
|-----------|----------------|------|
| Webhook + heartbeat service | FastAPI app; validates inbound payload and webhook secret, claims idempotency, dispatches background worker | `main.py` |
| CLI front end | argparse CLI for dry run / `--apply` / `--mock` / backfill; runs the same code path as the webhook | `make_pdf.py` |
| Drift gate | Compares `my_layout.py`'s allowlist against live Pipefy form/table fields; CI/pre-deploy gate | `check_drift.py` |
| Orchestration | `fn_generate_brief()` — read card, resolve profile, fetch linked campaign, build doc model, render, attach, verify | `my_brief.py` |
| Doc model builder | Pure "card in, dict out" transformation; campaign linked / standalone / claimed-not-linked resolver | `my_brief.py` |
| Layout allowlist | Declarative `Doc` / `Field` / `OneOf` / `Section` vocabulary — the only place a field is added to a document | `my_layout.py` |
| Pipefy API client | Every GraphQL call: card read, pipe form read, table record read, presigned upload, `updateCardField`, verify | `my_pipefy.py` |
| PDF renderer | MTN-branded reportlab renderer; doc model dict -> PDF bytes; no Pipefy knowledge | `my_pdf.py` |
| Idempotency guard | In-process replay-token check + in-flight/dedup lock | `my_state.py` |
| Shared utilities | Text/value/date/filename formatting helpers + `fn_log()` to Papertrail | `my_funcs.py` |
## Pattern Overview
- Flat repo, no `src/` nesting — every runtime module lives at the top level, distinguished by the `my_` prefix from third-party packages
- One orchestration function (`fn_generate_brief`) is the single code path for both the production webhook and the CLI — "not two copies of it" per `my_brief.py`'s docstring
- Declarative, human-edited allowlist (`my_layout.py`) decouples "what fields exist on the Pipefy form" from "what appears in the document" — a drift checker (`check_drift.py`) is the mechanism that keeps the two in sync
- Rendering (`my_pdf.py`) has a hard dependency boundary: it imports only `my_funcs.py`, never `my_pipefy.py` or `my_layout.py`, so a layout change can be proven from a JSON fixture with no token and no network call
- No database, no ORM, no message queue — Pipefy itself is the system of record; the service is stateless between requests
## Layers
- Purpose: accept a trigger (Pipefy webhook, human CLI invocation, or CI schedule) and hand off to orchestration
- Location: `main.py`, `make_pdf.py`, `check_drift.py`
- Contains: FastAPI route handlers, argparse CLI parsing, console output formatting
- Depends on: `my_brief.py` (orchestration), `my_layout.py` (profile registry), `my_state.py` (idempotency), `my_funcs.py` (logging)
- Used by: Pipefy automations, human operators, CI pipeline
- Purpose: sequence the read -> resolve -> build -> render -> attach -> verify steps exactly once, shared by every entry point
- Location: `my_brief.py` (`fn_generate_brief`, the bottom third of the file)
- Contains: the one function that calls both `my_pipefy.py` and `my_pdf.py`
- Depends on: `my_pipefy.py`, `my_layout.py`, `my_pdf.py`, `my_funcs.py`
- Used by: `main.py`'s `worker()`, `make_pdf.py`'s `fn_main()`
- Purpose: turn raw Pipefy field data into the exact dict `my_pdf.py` expects, with no I/O
- Location: `my_brief.py` (`fn_build_doc_model` and everything above it in the file)
- Contains: field indexing, value resolution (card vs. campaign vs. auto), the campaign-linkage state machine, filename templating
- Depends on: `my_layout.py` (allowlist), `my_funcs.py` (formatting)
- Used by: `fn_generate_brief()` (live path), `make_pdf.py`'s `fn_run_mock()` (fixture path — bypasses `my_pipefy.py` entirely)
- Purpose: pin exactly which Pipefy fields, in what order and grouping, appear on each document
- Location: `my_layout.py`
- Contains: `Doc`/`Field`/`OneOf`/`Section` classes, two `Doc` instances (`D_CAMPAIGN_BRIEF`, `D_JOB_BRIEF`), the profile registry
- Depends on: nothing (pure data + lookup functions)
- Used by: `my_brief.py`, `check_drift.py`, `make_pdf.py`
- Purpose: own every outbound Pipefy HTTP call, its auth, retry, and response-shape quirks
- Location: `my_pipefy.py`
- Contains: GraphQL transport (`fn_graphql`), read queries (card/pipe/table), connector-value resolution, presigned upload, attach, verify
- Depends on: `my_funcs.py` (logging only)
- Used by: `my_brief.py`, `check_drift.py`, `make_pdf.py`'s `fn_banner()`
- Purpose: turn a doc model dict into MTN-branded PDF bytes
- Location: `my_pdf.py`
- Contains: brand constants, reportlab styles, page templates (`BriefDoc`, `NumberedCanvas`), flowable builders (section bar, inline table, block, list block, cover meta)
- Depends on: `my_funcs.py` (logging only) — explicitly never `my_pipefy.py` or `my_layout.py`
- Used by: `my_brief.py`'s `fn_generate_brief()`, `make_pdf.py`'s `fn_run_mock()`
- Purpose: logging, formatting, and idempotency shared by every layer
- Location: `my_funcs.py` (utilities + `fn_log()`), `my_state.py` (in-process replay guard)
- Depends on: nothing (`my_funcs.py`) / `my_funcs.py` (`my_state.py`, for its own error logging)
- Used by: every other module
## Data Flow
### Primary Request Path (Pipefy webhook)
### Secondary Flow — CLI (dry run / apply / backfill)
### Tertiary Flow — Fixture render (`--mock`, no network)
### Quaternary Flow — Drift gate
## Key Abstractions
- Purpose: the seam between business logic and rendering — the exact shape is documented in `my_pdf.py`'s module docstring (`doc_title`, `pipe_label`, `title`, `subtitle`, `meta`, `highlight`, `sections[]`, `footer_ref`, `generated`, `source_url`, `filename`)
- Examples: contract defined at `my_pdf.py:8-21`, produced by `my_brief.py:439` (`fn_build_doc_model` return), consumed by `my_pdf.py:508` (`fn_render_pdf`)
- Pattern: `my_pdf.py` never imports `my_pipefy.py` or `my_layout.py` — it can only ever see this dict
- Purpose: declarative, human-edited allowlist — "add a field" is one line, not a code change
- Examples: `Field` class at `my_layout.py:37`, `OneOf` at `my_layout.py:67` (collapses MTN's 15 mutually-exclusive division selects into one row), `Section` at `my_layout.py:83`, `Doc` at `my_layout.py:95`
- Pattern: a field with no `Field(...)` entry in `my_layout.py` never renders, even if it exists on the live Pipefy form — this is what keeps a stray form field out of a brief an external agency reads
- Purpose: request-scoped correlation context (`{"time", "card_id", "Mode"}`) built once per run and threaded as the first positional argument through nearly every function, purely for log correlation
- Examples: built by `my_funcs.fn_build_stamp()` (`my_funcs.py:48`); `Mode="PrintOnly"` redirects `fn_log()` to stdout for CLI tools instead of posting to Papertrail
- Pattern: every function signature in `my_pipefy.py`, `my_brief.py`, `my_pdf.py` begins `def fn_x(stamp, ...)`
- Purpose: uniform, exception-free control flow — HTTP-style status codes (200/202/400/401/404/409/422/500) are reused all the way down through internal pure functions, not just at the FastAPI boundary
- Examples: consistent across `my_pipefy.py`, `my_brief.py`, `my_pdf.py`, `my_state.py`; e.g. `my_pipefy.fn_fetch_card()` returns `({}, 404)` when the card doesn't exist
- Pattern: every function body is wrapped in `try/except Exception`, logs, and returns a "safe" tuple rather than raising
- Purpose: work around Pipefy's inconsistent connector field shape (record title and id sometimes swap between `value` and `array_value`)
- Examples: `my_pipefy.fn_connected_record_ids()` (`my_pipefy.py:410`) takes whichever side is all-numeric rather than trusting field position; `my_pipefy.fn_find_connector_field()` (`my_pipefy.py:451`) tries id -> label -> type; `my_brief.fn_fetch_linked_campaign()` (`my_brief.py:472`) adds a title-scan as the last resort
## Entry Points
- Location: `main.py:65`
- Triggers: Pipefy automation on phase entry — Campaign Review `343906151` (Campaign Planning `307284211`), Brief Review - 1st Approval `343906141` (Campaign Briefing `307284210`); also the manual retrigger endpoint via `X-MTN-Replay-Token` (same route, no separate `/retrigger`)
- Responsibilities: parse and validate payload, check webhook secret, claim idempotency, dispatch to a `BackgroundTasks` worker, return `200` immediately
- Location: `main.py:216`
- Triggers: uptime monitor
- Responsibilities: reports loaded profile count and in-flight run count; no side effects, no Pipefy call
- Location: `make_pdf.py:121` (`fn_main`)
- Triggers: manual invocation — dry run, `--apply` (upload + attach + verify), `--mock` (fixture render), backfill (shell loop over card ids)
- Responsibilities: same `fn_generate_brief()` orchestration as the webhook; always writes the PDF to local `./out` in addition to (or instead of) attaching to Pipefy
- Location: `check_drift.py:227` (`fn_main`)
- Triggers: manual run, CI on every push, weekly schedule (per `SERVER_SETUP.md`)
- Responsibilities: read-only comparison of `my_layout.py`'s allowlist against the live Pipefy form/table; exits 1 on drift, gating deploys (`SERVER_SETUP.md` step 7 requires it to pass before `systemctl restart`)
## Architectural Constraints
- **Threading:** FastAPI's async event loop handles the HTTP request/response in `main.py`'s `async def main`; the actual render/attach work runs in `worker()`, a synchronous function dispatched via `BackgroundTasks`, which Starlette executes in a threadpool after the response is already sent. Concurrent renders for different cards run independently; renders for the *same* card serialize through the single `my_state` lock.
- **Global state:** `my_state.py` holds two process-local, module-level structures (`_d_seen` dict, `_set_in_flight` set) behind one `threading.Lock` (`my_state.py:34-36`). This state is not persisted and not shared across processes — if the service were ever run with multiple uvicorn workers or multiple instances, the dedup window and in-flight lock would not coordinate between them. Documented as acceptable in the module's own docstring because `updateCardField` overwrites rather than appends, so a duplicate render is wasteful, not corrupting.
- **Config loading:** every module that needs a config value (`main.py`, `my_funcs.py`, `my_pipefy.py`, `my_state.py`, `make_pdf.py`) independently constructs its own `configparser.ConfigParser()` and re-reads `segredo.ini` at import time — there is no single shared config object.
- **No database:** the service is fully stateless between requests; Pipefy is the system of record for both the card data and the generated PDF (`SERVER_SETUP.md`: "No database — the service is stateless and rebuilds from the repo").
- **Dependency direction:** strictly `main.py` / `make_pdf.py` / `check_drift.py` → `my_brief.py` → `my_pipefy.py` / `my_layout.py` → `my_funcs.py`; `my_pdf.py` depends only on `my_funcs.py` and never on `my_pipefy.py` or `my_layout.py`. No circular imports observed.
## Anti-Patterns
### Duplicated config loading per module
### String-interpolated GraphQL fallback
## Error Handling
- `(data, status_code)` tuple return from virtually every function in `my_pipefy.py`, `my_brief.py`, `my_pdf.py`, `my_state.py` — callers check `n_status`, never rely on exceptions for control flow
- The FastAPI request handler (`main.py:73`) wraps its whole body in `try/except Exception`, returning HTTP 422 with the failing line number in the response body
- `worker()` (`main.py:162`) wraps its whole body in `try/except`, logs to Papertrail on failure, and always runs `my_state.fn_release()` in a `finally` block so a crashed run does not leave the in-flight lock stuck
- Deliberate exception to the "never raise" rule: `NumberedCanvas.showPage()` / `save()` in `my_pdf.py:239-266` are **not** wrapped, so a reportlab failure propagates into `fn_render_pdf()`'s own `try/except` rather than silently producing a truncated PDF that looks like a success (documented in the class docstring)
- "Fail open" on the idempotency guard: `my_state.fn_claim()` catches its own errors and returns `(True, "claim guard errored, processing anyway")` (`my_state.py:79-85`) — a broken dedup lock must not block brief generation
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

## Project constraints — read before writing any code

This repo is a dYdX Digital client integration. The **`dydxdev-best-practices` skill is the
governing standard** — load it at the start of any code task in this directory, before writing a
line. This project is **NEW PROJECT mode, `my_*` lineage**.

**Hard rules that override default behaviour:**

- **Git.** Never run a state-changing git command — no `add`, `commit`, `push`, `branch`,
  `checkout`, `merge`, `reset`, `stash`, `tag`. Write the commands out for Jason to run, naming
  every file explicitly. Never `git add .`. Never stage `segredo.ini`. Read-only git
  (`status`, `diff`, `log`, `remote -v`) is fine and expected.
  This applies to GSD executors too — they must report the commands, not run them.
- **`.planning/` is gitignored.** `commit_docs` is `false`. The git worktree root is the whole
  `Work/Clients` multi-client workspace, not this project — be careful what you touch.
- **Indentation is 5 spaces per level**, not 4, not tabs. Applied with total consistency across
  every file. Match it exactly; do not let an editor default reformat it.
- **Pipefy API specifics defer to the `platform-pipefy` skill.** If it is not attached, say so
  and ask for it rather than reconstructing endpoints, field ids, or mutations from memory.
- **Nothing destructive is executed** — deletions, drops, terminates, `rm -rf` are handed over
  as commands with their impact stated, never run.
- **No retrigger or `--apply` run fires against live MTN Pipefy unprompted.** Live-fire goes
  against a disposable card only, with explicit confirmation first.
- **Secrets.** `segredo.ini` holds real credentials and is gitignored. Read
  `segredo.ini.example` for structure. Never copy a value into a document, log line, or commit.
  Any new config key must be added to `segredo.ini.example`.

**House conventions in this codebase** (documented in full in `.planning/codebase/CONVENTIONS.md`):
`my_<responsibility>.py` modules each opening with a docstring stating their one rule · `fn_`
prefix on every importable function (bare names only for FastAPI routes and `worker`) ·
Hungarian variable prefixes (`s_ d_ l_ i_ n_ b_ o_ t_ e_ set_`) · every function wrapped in one
`try` returning `(data, status_code)` and never raising · `stamp` threaded through every function
that logs · all logging through the single `my_funcs.fn_log()`.

**Before claiming a change works**, run the offline verification path (Windows dev box shown; the
Linux-box equivalent interpreter is `./venv/bin/python`):

```bash
venv/Scripts/python.exe -m pytest -q
venv/Scripts/python.exe make_pdf.py --mock fixtures/mock_brief_linked.json && venv/Scripts/python.exe make_pdf.py --mock fixtures/mock_brief_standalone.json && venv/Scripts/python.exe make_pdf.py --mock fixtures/mock_brief_claimed_not_linked.json && venv/Scripts/python.exe make_pdf.py --mock fixtures/mock_campaign.json
```

`check_drift.py` also gates deploys but needs a live Pipefy token.
