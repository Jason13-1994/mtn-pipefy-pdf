'''
     my_state.py — replay guard and in-flight lock.

     There is no database in this integration, so run state is in-process and
     deliberately small.

     Why that is enough here: updateCardField OVERWRITES an attachment field, it
     does not append. Re-running for the same card therefore leaves one current
     PDF either way, so a Pipefy webhook retry cannot produce a second copy.
     What this file prevents is the wasteful case — the same card being rendered
     twice concurrently because Pipefy fired twice inside a few seconds.

     A deliberate replay carrying the configured replay_token skips the window
     and is always processed.
'''
import configparser
import os
import secrets
import sys
import threading
import time

import my_funcs

HERE = os.path.dirname(os.path.abspath(__file__))

_config = configparser.ConfigParser()
_config.read(os.path.join(HERE, "segredo.ini"))

I_IDEMPOTENCY_TTL_SECONDS = _config.getint("Service", "idempotency_ttl_seconds",
                                           fallback=60)
S_REPLAY_TOKEN = _config.get("Service", "replay_token", fallback="")

_o_lock = threading.Lock()
_d_seen = {}        # {idempotency_key: n_epoch_seconds}
_set_in_flight = set()


def fn_is_replay(s_sent_token="") -> bool:
     '''
          True when the caller presented the configured replay token. Compared
          with compare_digest, never ==.
     '''
     try:
          if not S_REPLAY_TOKEN or not s_sent_token:
               return False
          return secrets.compare_digest(str(s_sent_token), str(S_REPLAY_TOKEN))
     except Exception:
          return False


def fn_claim(stamp, s_key="", b_is_replay=False) -> tuple:
     '''
          Claim the right to process s_key. Returns (b_claimed, s_reason).

          b_claimed False means another run has it in flight, or the same key
          was processed inside the dedup window. A deliberate replay always
          claims, unless the key is genuinely in flight right now.
     '''
     try:
          n_now = int(time.time())
          with _o_lock:
               if s_key in _set_in_flight:
                    return False, "already in flight"

               if not b_is_replay:
                    n_seen = _d_seen.get(s_key)
                    if n_seen is not None and (n_now - int(n_seen)) <= I_IDEMPOTENCY_TTL_SECONDS:
                         return False, (f"processed {n_now - int(n_seen)}s ago, inside the "
                                        f"{I_IDEMPOTENCY_TTL_SECONDS}s window")

               # Drop expired keys so the dict cannot grow without bound.
               for s_old in [k for k, v in _d_seen.items()
                             if (n_now - int(v)) > (I_IDEMPOTENCY_TTL_SECONDS * 10)]:
                    _d_seen.pop(s_old, None)

               _set_in_flight.add(s_key)
               return True, "claimed"
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Idempotency claim failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "key": s_key})
          # Fail open: a broken guard must not stop briefs being generated.
          return True, "claim guard errored, processing anyway"


def fn_release(stamp, s_key="", b_success=True):
     '''
          Release the in-flight claim. Only a successful run is recorded in the
          dedup window — a failure should be retryable immediately.
     '''
     try:
          with _o_lock:
               _set_in_flight.discard(s_key)
               if b_success:
                    _d_seen[s_key] = int(time.time())
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Idempotency release failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "key": s_key})


def fn_stats() -> dict:
     '''
          Small snapshot for the heartbeat.
     '''
     try:
          with _o_lock:
               return {"in_flight": len(_set_in_flight), "seen_keys": len(_d_seen)}
     except Exception:
          return {"in_flight": 0, "seen_keys": 0}
