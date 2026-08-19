'''
     my_funcs.py — general helper for the MTN Pipefy PDF integration.

     Pure, side-effect-free utilities plus fn_log(), which is the one permitted
     outbound call in this file. NO Pipefy calls, NO database calls, NO
     business logic — those live in my_pipefy.py / my_brief.py.
'''
import configparser
import inspect
import json
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import unquote

import pytz
import requests

HERE = os.path.dirname(os.path.abspath(__file__))

_config = configparser.ConfigParser()
_config.read(os.path.join(HERE, "segredo.ini"))

S_PAPERTRAIL_LOG_URL = _config.get("PaperTrail", "papertrail_log_url",
                                   fallback="https://logs.collector.solarwinds.com/v1/log")
S_PAPERTRAIL_LOG_TOKEN = _config.get("PaperTrail", "papertrail_log_token", fallback="")
S_INTEGRATION_KEYWORD = _config.get("Service", "name", fallback="mtn_pipefy_pdf")

S_TIMEZONE = "Africa/Johannesburg"

# Zero-width and bidi characters. MTN's forms use a zero-width-label field as a
# section header, so these have to be stripped before a label can be tested for
# emptiness.
_RE_INVISIBLE = re.compile(r"[​‌‍‎‏﻿]")
_RE_WHITESPACE = re.compile(r"\s+")
_RE_UNSAFE_FILENAME = re.compile(r"[\\/:*?\"<>|\r\n\t]+")
_RE_MARKDOWN_HEADING = re.compile(r"^#+\s*")


'''
     *****************************************************
           LOGGING
     *****************************************************
'''


def fn_build_stamp(s_card_id="", s_mode=""):
     '''
          Build the context stamp threaded through an integration run.
     '''
     try:
          return {
               "time": int(time.time() * 1_000_000),
               "card_id": str(s_card_id) if s_card_id else "no card_id found",
               "Mode": s_mode,
          }
     except Exception:
          return {"time": 0, "card_id": "no card_id found", "Mode": s_mode}


def fn_log(stamp="stamp", txt="empty", d_details=None) -> tuple:
     '''
          Emit one standard-shape log entry to Papertrail / SolarWinds.
          Never raises.
     '''
     try:
          if not isinstance(stamp, dict):
               stamp = {}
          if stamp.get("Mode") == "DoNothing":
               return None, None
          if stamp.get("Mode") == "PrintOnly":
               print(f'{S_INTEGRATION_KEYWORD}: {stamp.get("card_id")} : {txt}')
               return None, None

          d_extra = d_details if isinstance(d_details, dict) else {}
          d_extra["caller"] = inspect.stack()[1][3]

          d_log_payload = {
               "keyword": S_INTEGRATION_KEYWORD,
               "timestamp": int(stamp.get("time", time.time() * 1_000_000)),
               "card_id": stamp.get("card_id", "no card_id found"),
               "message": txt,
               "details": d_extra,
          }
          d_head = {'content-type': 'application/json; charset=utf-8'}
          resp = requests.post(
               S_PAPERTRAIL_LOG_URL,
               auth=('', S_PAPERTRAIL_LOG_TOKEN),
               headers=d_head,
               data=json.dumps(d_log_payload, default=str).encode('utf-8'),
               timeout=10,
          )
          return resp, resp.status_code
     except requests.exceptions.RequestException as e:
          print(f"Papertrail request failed: {e}")
          return None, 206
     except Exception as e:	## EXCEPTION MUST BE THE LAST HANDLER
          e_type, e_object, e_traceback = sys.exc_info()
          print(f"fn_log returned exception ERROR line {e_traceback.tb_lineno}: {str(e)}.")
          return None, 206


'''
     *****************************************************
           TEXT
     *****************************************************
'''


def fn_tidy(s_text=""):
     '''
          Strip invisible characters and collapse whitespace. Returns "".
     '''
     try:
          return _RE_WHITESPACE.sub(" ", _RE_INVISIBLE.sub("", s_text or "")).strip()
     except Exception:
          return ""


def fn_safe_filename(s_name="", i_max_length=110):
     '''
          Make a string safe to use as a filename on Windows and Linux.
     '''
     try:
          s_clean = _RE_INVISIBLE.sub("", s_name or "")
          s_clean = _RE_UNSAFE_FILENAME.sub(" ", s_clean)
          s_clean = _RE_WHITESPACE.sub(" ", s_clean).strip(" .")
          return s_clean[:i_max_length].strip() or "Brief"
     except Exception:
          return "Brief"


def fn_section_title_from_description(s_description=""):
     '''
          MTN's forms carry the section name in the DESCRIPTION of a
          zero-width-label field (e.g. "___\\n## Campaign Information\\n___").
          Returns the first meaningful line, or "".
     '''
     try:
          for s_line in (s_description or "").splitlines():
               s_line = _RE_MARKDOWN_HEADING.sub("", s_line.strip().strip("_").strip()).strip()
               if s_line:
                    return fn_tidy(s_line)
          return ""
     except Exception:
          return ""


'''
     *****************************************************
           VALUE COERCION
     *****************************************************
'''


def fn_as_list(value=None):
     '''
          Coerce a Pipefy field value into a list of non-empty strings.
          Pipefy returns multi-value fields as a JSON array STRING, so a plain
          str() would print the brackets into the document.
     '''
     try:
          if value is None:
               return []
          if isinstance(value, (list, tuple)):
               return [str(x).strip() for x in value if str(x).strip()]
          s_value = str(value).strip()
          if not s_value:
               return []
          if s_value.startswith("[") and s_value.endswith("]"):
               try:
                    l_parsed = json.loads(s_value)
                    if isinstance(l_parsed, list):
                         return [str(x).strip() for x in l_parsed if str(x).strip()]
               except ValueError:
                    pass
          return [s_value]
     except Exception:
          return []


def fn_first_non_empty(l_values=None):
     '''
          First value in the list that is not blank. Returns "".
     '''
     try:
          for value in (l_values or []):
               if value not in (None, "", [], {}):
                    return value
          return ""
     except Exception:
          return ""


'''
     *****************************************************
           DISPLAY FORMATTING
     *****************************************************
'''


def fn_format_date(s_value=""):
     '''
          "2026-09-01" / ISO datetime -> "01 Sep 2026". Unparseable input is
          returned untouched rather than dropped.
     '''
     try:
          s_raw = str(s_value or "").strip()
          if not s_raw:
               return ""
          s_head = s_raw.replace("Z", "").split("T")[0].split(" ")[0]
          return datetime.strptime(s_head, "%Y-%m-%d").strftime("%d %b %Y")
     except Exception:
          return str(s_value or "").strip()


def fn_format_datetime(s_value=""):
     '''
          ISO datetime -> "01 Sep 2026, 14:30".
     '''
     try:
          s_raw = str(s_value or "").strip()
          if not s_raw:
               return ""
          if "T" not in s_raw and " " not in s_raw:
               return fn_format_date(s_raw)
          s_norm = s_raw.replace("Z", "+00:00")
          try:
               o_parsed = datetime.fromisoformat(s_norm)
          except ValueError:
               o_parsed = datetime.fromisoformat(s_norm.split("+")[0])
          return o_parsed.strftime("%d %b %Y, %H:%M")
     except Exception:
          return fn_format_date(s_value)


def fn_format_number(s_value=""):
     '''
          Space-grouped thousands: 4500000 -> "4 500 000".
          A bare 4-digit value stays as-is so campaign_year prints "2026",
          not "2 026".
     '''
     try:
          s_raw = str(s_value or "").strip().replace(" ", "").replace(",", "")
          if not s_raw:
               return ""
          if re.fullmatch(r"\d{4}", s_raw):
               return s_raw
          f_number = float(s_raw)
          if f_number.is_integer():
               return f"{int(f_number):,}".replace(",", " ")
          return f"{f_number:,.2f}".replace(",", " ")
     except Exception:
          return str(s_value or "").strip()


def fn_attachment_filename(s_value=""):
     '''
          Attachment values are storage paths or signed URLs. The document
          should show the filename only.
     '''
     try:
          s_raw = str(s_value or "").strip()
          if not s_raw:
               return ""
          s_path = s_raw.split("?")[0].rstrip("/")
          s_name = s_path.split("/")[-1]
          try:
               s_name = unquote(s_name)
          except Exception:
               pass
          return s_name or s_raw
     except Exception:
          return str(s_value or "").strip()


def fn_now_sast():
     '''
          Human-readable local timestamp for the cover and footer.
     '''
     try:
          return datetime.now(pytz.timezone(S_TIMEZONE)).strftime("%d %b %Y %H:%M SAST")
     except Exception:
          return ""
