'''
     main.py — MTN Pipefy PDF generator.

     A Pipefy automation fires when a card enters its approval phase; this
     service renders an MTN-branded PDF from the card and attaches it back.

          Campaign Planning 307284211 -> Campaign Brief -> campaign_attached
               on entry to Campaign Review 343906151
          Campaign Briefing 307284210 -> Job Brief      -> brief_attached
               on entry to Brief Review - 1st Approval 343906141

     Generation happens at the APPROVAL phase, not at Brief Submitted, for two
     reasons: the approver reviews the document rather than the form, and the
     agency fan-out on Brief Submitted copies brief_attached onto every agency
     card — so the file has to already be there.

     The webhook endpoint is also the retrigger endpoint. Same route, same
     payload; a request carrying the configured replay token skips the
     idempotency window.
'''
import configparser
import ipaddress
import json
import os
import secrets
import sys
from datetime import datetime

import pytz
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request, Response

import my_funcs
import my_layout
import my_brief
import my_state

HERE = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(HERE, "segredo.ini"))

S_INTEGRATION_KEYWORD = config.get("Service", "name", fallback="mtn_pipefy_pdf")
S_BIND = config.get("Service", "bind", fallback="127.0.0.1")
I_PORT = config.getint("Service", "port", fallback=5040)
S_WEBHOOK_SECRET = config.get("Service", "webhook_secret", fallback="")


def fn_is_loopback_bind(s_bind="") -> bool:
     '''
          True when s_bind names an address only this box can reach. An empty
          or unparseable value is treated as NOT loopback, so an unrecognised
          bind fails the guard CLOSED rather than open.
     '''
     try:
          s_raw = str(s_bind or "").strip().strip("[]")
          if s_raw.lower() in ("localhost", "localhost.localdomain"):
               return True
          return ipaddress.ip_address(s_raw).is_loopback
     except Exception:
          return False


# An endpoint with no usable shared secret, reachable from anything other
# than this box, must not start.
if (not S_WEBHOOK_SECRET or len(S_WEBHOOK_SECRET) < 20) and not fn_is_loopback_bind(S_BIND):
     raise RuntimeError(
          f"[Service] webhook_secret is blank or under 20 characters, and "
          f"[Service] bind is '{S_BIND}', which is not a loopback address. "
          "Set a long random webhook_secret (20+ characters) in segredo.ini, "
          "or bind to 127.0.0.1 for local testing. Refusing to start.")

app = FastAPI()


'''
     *****************************************************
     *****************************************************
           MAIN THREAD
     *****************************************************
     *****************************************************
'''


@app.post("/generate-pdf")
async def main(req: Request, resp: Response, bg_tasks: BackgroundTasks):

     resp.status_code = 200
     stamp = my_funcs.fn_build_stamp()
     d_payload = {}

     '''
          Catch REQUEST
     '''
     try:
          '''
               Authenticate. Nothing reads the body until this passes, so an
               unauthenticated caller's bytes never reach json.loads() and
               never reach a Papertrail details payload. The check is
               unconditional: a blank S_WEBHOOK_SECRET does not skip it, it
               means compare_digest never matches, so every request is
               rejected rather than every request being let through.
          '''
          s_sent = req.headers.get("x-mtn-pdf-token", "")
          if not s_sent or not secrets.compare_digest(s_sent, S_WEBHOOK_SECRET):
               my_funcs.fn_log(stamp=stamp,
                               txt="Rejected a request with a missing or bad token",
                               d_details={"remote": str(req.client.host if req.client else "")})
               resp.status_code = 401
               return "Unauthorised"

          '''
               Read and parse the PAYLOAD
          '''
          body = await req.body()
          if len(body) < 3:
               resp.status_code = 400
               return "No data or bad data received"
          try:
               d_payload = json.loads(body)
          except ValueError:
               my_funcs.fn_log(stamp=stamp, txt="Request body was not valid JSON",
                               d_details={"raw_body": body[:2000].decode("utf-8", "replace")})
               resp.status_code = 400
               return "Body is not valid JSON"

          '''
               Extract KEY DATA needed for worker
          '''
          d_data = d_payload.get("data") or {}
          s_card_id = str(d_data.get("card", {}).get("id")
                          or d_payload.get("card_id") or "").strip()
          if not s_card_id or s_card_id == "0":
               my_funcs.fn_log(stamp=stamp, txt="No card id in the payload",
                               d_details={"raw_payload": d_payload})
               resp.status_code = 400
               return "Could not find a card id in the payload"

          stamp["card_id"] = s_card_id
          s_profile_key = str(d_payload.get("profile") or "")
          b_dry_run = str(req.query_params.get("dry", "")) in ("1", "true", "yes")
          b_is_replay = my_state.fn_is_replay(
               s_sent_token=req.headers.get("x-mtn-replay-token", ""))

          b_claimed, s_reason = my_state.fn_claim(
               stamp=stamp, s_key=f"pdf:{s_card_id}", b_is_replay=b_is_replay)
          if not b_claimed:
               my_funcs.fn_log(stamp=stamp,
                               txt=f"Skipping card {s_card_id} — {s_reason}",
                               d_details={"raw_payload": d_payload})
               return f"Skipped: {s_reason}"

          my_funcs.fn_log(
               stamp=stamp,
               txt=f"PDF generation requested for card {s_card_id}"
                   f"{' (replay)' if b_is_replay else ''}"
                   f"{' (dry run)' if b_dry_run else ''}",
               d_details={"raw_payload": d_payload},
          )

          '''
               When LIVE: Add to BackgroundTasks
          '''
          bg_tasks.add_task(worker, stamp=stamp, s_card_id=s_card_id,
                            s_profile_key=s_profile_key, b_dry_run=b_dry_run,
                            d_payload=d_payload)
          return "OK"

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"ERROR in main at line {e_traceback.tb_lineno}: {str(e)}",
               d_details={"route": "/generate-pdf", "raw_payload": d_payload or {}},
          )
          resp.status_code = 422
          return f"Internal error. Ref {stamp.get('time')}"


'''
     *****************************************************
     *****************************************************
           WORKER THREAD
     *****************************************************
     *****************************************************
'''


def worker(stamp, s_card_id="0", s_profile_key="", b_dry_run=False, d_payload=None):

     b_success = False
     try:
          '''
               Step 1: Render, and attach unless this is a dry run
          '''
          d_result, n_status = my_brief.fn_generate_brief(
               stamp=stamp, s_card_id=s_card_id, s_profile_key=s_profile_key,
               b_apply=(not b_dry_run),
          )
          if n_status not in (200, 202):
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"PDF generation returned {n_status} for card {s_card_id}",
                    d_details={"result": d_result, "raw_payload": d_payload or {}},
               )
               return f"Failed with {n_status}"

          '''
               Step 2: Report what landed
          '''
          d_result.pop("pdf_bytes", None)
          b_success = True
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"{d_result.get('document')} "
                   f"{'rendered (dry run)' if b_dry_run else 'attached'} for card "
                   f"{s_card_id}: {d_result.get('filename')}",
               d_details=d_result,
          )
          return json.dumps(d_result)

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"ERROR in worker at {e_traceback.tb_lineno}: {str(e)}",
               d_details={"raw_payload": d_payload or {}, "card_id": str(s_card_id)},
          )
          return str(e)
     finally:
          my_state.fn_release(stamp=stamp, s_key=f"pdf:{s_card_id}", b_success=b_success)


'''
     *****************************************************
     *****************************************************
           HEARTBEAT
     *****************************************************
     *****************************************************
'''


@app.post("/hello")
async def hello(req: Request, resp: Response):
     stamp = my_funcs.fn_build_stamp()
     try:
          tz = pytz.timezone(my_funcs.S_TIMEZONE)
          t = str(datetime.now(tz).strftime("%H:%M:%S"))
          resp.status_code = 200
          d_stats = my_state.fn_stats()
          return (f"Hello from MTN Pipefy PDF, it's {t}. "
                  f"{len(my_layout.L_PROFILES)} profiles loaded, "
                  f"{d_stats.get('in_flight')} in flight.")
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"ERROR in hello at line {e_traceback.tb_lineno}: {str(e)}",
               d_details={"route": "/hello"},
          )
          resp.status_code = 500
          return f"Internal error. Ref {stamp.get('time')}"


if __name__ == "__main__":
     uvicorn.run("main:app", host=S_BIND, port=I_PORT, timeout_keep_alive=90)
