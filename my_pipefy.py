'''
     my_pipefy.py — every Pipefy API call the integration makes.

     Auth, endpoint construction, request execution, response parsing and
     Pipefy-shape quirks live here and nowhere else. Nothing in this file knows
     what a "brief" is; nothing outside it issues an HTTP request to Pipefy.

     Every function returns (data, status_code) and never raises.
'''
import configparser
import json
import mimetypes
import os
import sys
from urllib.parse import unquote, urlparse

import requests

import my_funcs

HERE = os.path.dirname(os.path.abspath(__file__))

_config = configparser.ConfigParser()
_config.read(os.path.join(HERE, "segredo.ini"))

S_API_URL = _config.get("Pipefy", "api_url", fallback="https://api.pipefy.com/graphql")
S_ORGANIZATION_ID = _config.get("Pipefy", "organization_id", fallback="")

# Env-var / .env key names used elsewhere in the MTN client folder.
L_TOKEN_VARS = ["MTN_PIPEFY_TOKEN", "PIPEFY_ACCESS_TOKEN", "PIPEFY_TOKEN"]


def fn_resolve_token() -> tuple:
     '''
          Find the Pipefy token. Returns (s_token, s_source) — the SOURCE, never
          the value, is what gets logged.

          Order:
            1. [Pipefy] token in segredo.ini      <- authoritative. This is what
                                                     the EC2 box uses.
            2. MTN_PIPEFY_TOKEN / PIPEFY_ACCESS_TOKEN / PIPEFY_TOKEN env var
            3. .env or .env.txt beside the repo, then one and two levels up

          2 and 3 are a LOCAL DEVELOPER CONVENIENCE and a deliberate deviation
          from the segredo.ini-only rule: the MTN client folder already keeps a
          token at MTN/.env.txt and MTN/pipefy_creations/.env, and asking a dev
          to copy a live credential into a second file is how credentials end
          up pasted somewhere they should not be. On the box segredo.ini is
          populated, so the fallback never fires — and if it ever does, the
          startup banner says so out loud.
     '''
     try:
          s_token = _config.get("Pipefy", "token", fallback="").strip()
          if s_token:
               return s_token, "segredo.ini"

          for s_var in L_TOKEN_VARS:
               if os.environ.get(s_var, "").strip():
                    return os.environ[s_var].strip(), f"${s_var}"

          s_parent = os.path.dirname(HERE)
          for s_dir in (HERE, s_parent, os.path.dirname(s_parent)):
               for s_name in (".env", ".env.txt"):
                    s_path = os.path.join(s_dir, s_name)
                    try:
                         with open(s_path, "r", encoding="utf-8-sig") as o_file:
                              for s_line in o_file:
                                   s_line = s_line.strip()
                                   if not s_line or s_line.startswith("#") or "=" not in s_line:
                                        continue
                                   s_key, s_value = s_line.split("=", 1)
                                   if s_key.strip() in L_TOKEN_VARS:
                                        s_value = s_value.strip().strip('"').strip("'")
                                        if s_value:
                                             return s_value, s_path
                    except (FileNotFoundError, NotADirectoryError, PermissionError):
                         continue
          return "", "not found"
     except Exception:
          return "", "resolution errored"


S_TOKEN, S_TOKEN_SOURCE = fn_resolve_token()
I_HTTP_TIMEOUT = _config.getint("Service", "http_timeout", fallback=120)
I_RETRY_COUNT = _config.getint("Service", "retry_count", fallback=5)

S_USER_AGENT = "mtn-pipefy-pdf/1.0"

# Retried with backoff. Anything else is reported and returned.
L_RETRYABLE_STATUS = [429, 500, 502, 503, 504]

# A field of one of these types holds a link to another card or table record.
L_CONNECTOR_TYPES = ["connector", "database_connection"]


'''
     *****************************************************
           TRANSPORT
     *****************************************************
'''


def fn_graphql(stamp, s_query="", d_variables=None) -> tuple:
     '''
          Execute one GraphQL operation. Returns (d_data, n_status).
          Retries 429 and 5xx with exponential backoff; a GraphQL "errors"
          block is a 422, not an exception.
     '''
     try:
          if not S_TOKEN:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt="No Pipefy token found — set [Pipefy] token in segredo.ini, or "
                        "MTN_PIPEFY_TOKEN in the environment or a .env above the repo",
                    d_details={"searched": L_TOKEN_VARS, "source": S_TOKEN_SOURCE},
               )
               return {}, 500

          d_headers = {
               "Authorization": f"Bearer {S_TOKEN}",
               "Content-Type": "application/json",
               "User-Agent": S_USER_AGENT,
          }
          d_body = {"query": s_query, "variables": d_variables or {}}

          import time as _time
          for i_attempt in range(I_RETRY_COUNT):
               resp = requests.post(S_API_URL, headers=d_headers, json=d_body,
                                    timeout=I_HTTP_TIMEOUT)
               if resp.status_code in L_RETRYABLE_STATUS and i_attempt < (I_RETRY_COUNT - 1):
                    _time.sleep(2 ** i_attempt)
                    continue
               break

          if resp.status_code != 200:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"Pipefy GraphQL returned HTTP {resp.status_code}",
                    d_details={"request": d_body, "response_body": resp.text[:2000]},
               )
               return {}, 422

          d_payload = resp.json()
          if d_payload.get("errors"):
               my_funcs.fn_log(
                    stamp=stamp,
                    txt="Pipefy GraphQL returned an errors block",
                    d_details={"request": d_body, "errors": d_payload["errors"]},
               )
               return d_payload.get("data") or {}, 422

          return d_payload.get("data") or {}, 200

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"Pipefy GraphQL call failed at line {e_traceback.tb_lineno}",
               d_details={"error": str(e), "query": (s_query or "")[:500],
                          "variables": d_variables or {}},
          )
          return {}, 500


def fn_whoami(stamp) -> tuple:
     '''
          Token sanity check. Returns (d_me, n_status).
     '''
     try:
          d_data, n_status = fn_graphql(stamp=stamp, s_query="{ me { id name email } }")
          if n_status != 200 or not d_data.get("me"):
               return {}, (n_status if n_status != 200 else 422)
          return d_data["me"], 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Pipefy whoami failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e)})
          return {}, 500


'''
     *****************************************************
           READ — CARDS, FORMS, RECORDS
     *****************************************************
'''

S_CARD_QUERY = '''
query($id: ID!) {
  card(id: $id) {
    id title url created_at updated_at
    current_phase { id name }
    pipe { id name }
    assignees { id name email }
    fields {
      name value array_value
      field { id internal_id label type index }
    }
  }
}'''

S_PIPE_FORM_QUERY = '''
query($id: ID!) {
  pipe(id: $id) {
    id name
    start_form_fields { id internal_id label type index description options required }
    phases { id name index
             fields { id internal_id label type index description options required } }
  }
}'''

S_TABLE_RECORD_QUERY = '''
query($id: ID!) {
  table_record(id: $id) {
    id title url created_at updated_at
    table { id name }
    record_fields { name value array_value
                    field { id internal_id label type index } }
  }
}'''

S_TABLE_FIELDS_QUERY = '''
query($id: ID!) {
  table(id: $id) {
    id name
    table_fields { id internal_id label type index description options }
  }
}'''

S_TABLE_TITLES_QUERY = '''
query($id: ID!, $after: String) {
  table_records(table_id: $id, first: 50, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node { id title } }
  }
}'''


def fn_fetch_card(stamp, s_card_id="0") -> tuple:
     '''
          Fetch one card with every field value. Returns (d_card, n_status).
     '''
     try:
          d_data, n_status = fn_graphql(stamp=stamp, s_query=S_CARD_QUERY,
                                        d_variables={"id": str(s_card_id)})
          if n_status != 200 or not d_data.get("card"):
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"Pipefy card {s_card_id} could not be read",
                    d_details={"card_id": str(s_card_id), "status": n_status},
               )
               return {}, 404 if n_status == 200 else n_status
          return d_data["card"], 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Pipefy card fetch failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "card_id": str(s_card_id)})
          return {}, 500


def fn_fetch_pipe_form(stamp, s_pipe_id="0") -> tuple:
     '''
          Start-form and phase-field metadata for a pipe. Supplies the live
          LABELS and section headers the document prints — the field allowlist
          itself comes from my_layout.py, not from here.
          Returns (d_pipe, n_status).
     '''
     try:
          d_data, n_status = fn_graphql(stamp=stamp, s_query=S_PIPE_FORM_QUERY,
                                        d_variables={"id": str(s_pipe_id)})
          if n_status != 200 or not d_data.get("pipe"):
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"Pipefy pipe {s_pipe_id} form metadata could not be read",
                    d_details={"pipe_id": str(s_pipe_id), "status": n_status},
               )
               return {}, 422
          return d_data["pipe"], 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Pipefy pipe form fetch failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "pipe_id": str(s_pipe_id)})
          return {}, 500


def fn_fetch_table_record(stamp, s_record_id="0") -> tuple:
     '''
          Read a Pipefy database record. Falls back to card() in case the
          connector is ever repointed at a pipe instead of a table.
          Returns (d_record, n_status) where record_fields is always present.
     '''
     try:
          d_data, n_status = fn_graphql(stamp=stamp, s_query=S_TABLE_RECORD_QUERY,
                                        d_variables={"id": str(s_record_id)})
          if n_status == 200 and d_data.get("table_record"):
               return d_data["table_record"], 200

          d_card, n_card_status = fn_graphql(
               stamp=stamp,
               s_query=S_CARD_QUERY,
               d_variables={"id": str(s_record_id)},
          )
          if n_card_status == 200 and d_card.get("card"):
               d_result = dict(d_card["card"])
               d_result["record_fields"] = d_result.pop("fields", [])
               return d_result, 200

          my_funcs.fn_log(
               stamp=stamp,
               txt=f"Linked campaign record {s_record_id} could not be read as a "
                   f"table record or a card",
               d_details={"record_id": str(s_record_id),
                          "table_status": n_status, "card_status": n_card_status},
          )
          return {}, 422
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Pipefy table record fetch failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "record_id": str(s_record_id)})
          return {}, 500


def fn_fetch_table_fields(stamp, s_table_id="") -> tuple:
     '''
          Field metadata for a Pipefy database, for labels on inherited
          campaign values. Returns (d_table, n_status).
     '''
     try:
          d_data, n_status = fn_graphql(stamp=stamp, s_query=S_TABLE_FIELDS_QUERY,
                                        d_variables={"id": str(s_table_id)})
          if n_status != 200 or not d_data.get("table"):
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"Pipefy table {s_table_id} fields could not be read",
                    d_details={"table_id": str(s_table_id), "status": n_status},
               )
               return {}, 422
          return d_data["table"], 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Pipefy table fields fetch failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "table_id": str(s_table_id)})
          return {}, 500


def fn_find_record_id_by_title(stamp, s_table_id="", s_title="", i_max_pages=20) -> tuple:
     '''
          Last-resort lookup when a connector hands back a display title rather
          than a record id. Returns (s_record_id, n_status); ("", 404) if the
          title is not in the table.
     '''
     try:
          s_want = " ".join(str(s_title or "").split()).strip().lower()
          if not s_want:
               return "", 404
          s_after = None
          for _ in range(i_max_pages):
               d_data, n_status = fn_graphql(
                    stamp=stamp, s_query=S_TABLE_TITLES_QUERY,
                    d_variables={"id": str(s_table_id), "after": s_after},
               )
               if n_status != 200:
                    return "", n_status
               d_records = d_data.get("table_records") or {}
               for d_edge in d_records.get("edges") or []:
                    d_node = d_edge.get("node") or {}
                    s_node_title = " ".join(str(d_node.get("title") or "").split()).strip().lower()
                    if s_node_title == s_want:
                         return str(d_node.get("id")), 200
               d_page = d_records.get("pageInfo") or {}
               if not d_page.get("hasNextPage"):
                    return "", 404
               s_after = d_page.get("endCursor")
          return "", 404
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Pipefy table title scan failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "table_id": str(s_table_id),
                                     "title": str(s_title)})
          return "", 500


'''
     *****************************************************
           CARD FIELD SHAPES
     *****************************************************
'''


def fn_card_field(d_card=None, s_field_id="") -> dict:
     '''
          The raw field entry for one field id on a card or table record.
          Returns {} when the field is not on the card.
     '''
     try:
          l_fields = (d_card or {}).get("fields") or (d_card or {}).get("record_fields") or []
          for d_field in l_fields:
               if (d_field.get("field") or {}).get("id") == s_field_id:
                    return d_field
          return {}
     except Exception:
          return {}


def fn_connected_record_ids(d_field=None) -> list:
     '''
          Record ids sitting in a connector field.

          VERIFIED against a live Campaign Briefing card, Aug 2026: on a
          connector Pipefy puts the connected record's TITLE in `value` and its
          ID in `array_value` — the opposite way round to every other field
          type, and the opposite of what the platform docs describe. So take
          whichever side is all-numeric rather than trusting either position.
     '''
     try:
          if not d_field:
               return []
          l_array = my_funcs.fn_as_list(d_field.get("array_value"))
          l_value = my_funcs.fn_as_list(d_field.get("value"))
          for l_candidate in (l_array, l_value):
               if l_candidate and all(x.isdigit() for x in l_candidate):
                    return l_candidate
          return l_array or l_value
     except Exception:
          return []


def fn_connected_record_titles(d_field=None) -> list:
     '''
          Display titles on a connector field — used for the console line and
          as the key for the title-scan fallback.
     '''
     try:
          if not d_field:
               return []
          l_array = my_funcs.fn_as_list(d_field.get("array_value"))
          l_value = my_funcs.fn_as_list(d_field.get("value"))
          for l_candidate in (l_value, l_array):
               if l_candidate and not all(x.isdigit() for x in l_candidate):
                    return l_candidate
          return []
     except Exception:
          return []


def fn_find_connector_field(d_card=None, s_preferred_id="", s_label_hint="") -> tuple:
     '''
          Locate the connector on a card. Pipefy does not always return the
          connection under the id shown on the form, so: exact id -> label
          match -> any field typed as a connector.
          Returns (d_field, s_how_it_was_found).
     '''
     try:
          l_fields = (d_card or {}).get("fields") or []
          if s_preferred_id:
               for d_field in l_fields:
                    if (d_field.get("field") or {}).get("id") == s_preferred_id:
                         return d_field, "id"
          if s_label_hint:
               s_hint = s_label_hint.strip().lower()
               for d_field in l_fields:
                    s_label = str((d_field.get("field") or {}).get("label")
                                  or d_field.get("name") or "")
                    if s_label.strip().lower() == s_hint:
                         return d_field, "label"
          l_connectors = [d_field for d_field in l_fields
                          if (d_field.get("field") or {}).get("type") in L_CONNECTOR_TYPES]
          if l_connectors:
               return l_connectors[0], f"type (1 of {len(l_connectors)})"
          return {}, ""
     except Exception:
          return {}, ""


def fn_existing_attachment_paths(d_field=None) -> list:
     '''
          Storage paths already on an attachment field, so they can be re-sent
          alongside a new file. updateCardField OVERWRITES an attachment field —
          it does not append — so anything omitted here is removed.
     '''
     try:
          if not d_field:
               return []
          l_out = []
          value = d_field.get("value")
          l_parsed = None
          if isinstance(value, str) and value.strip().startswith("["):
               try:
                    l_parsed = json.loads(value)
               except ValueError:
                    l_parsed = None
          if l_parsed is None:
               l_parsed = d_field.get("array_value") or ([value] if value else [])
          for item in l_parsed:
               if not item:
                    continue
               s_item = str(item)
               if s_item.startswith("http"):
                    s_item = fn_storage_path_from_url(s_url=s_item)
               l_out.append(s_item)
          return l_out
     except Exception:
          return []


'''
     *****************************************************
           UPLOAD AND ATTACH
     *****************************************************
'''


def fn_storage_path_from_url(s_url="") -> str:
     '''
          An attachment field stores the object path, not the signed URL.
          Everything from "orgs/" onwards, query string dropped.
     '''
     try:
          s_path = unquote(urlparse(s_url).path).lstrip("/")
          i_index = s_path.find("orgs/")
          return s_path[i_index:] if i_index >= 0 else s_path
     except Exception:
          return str(s_url or "")


def fn_create_presigned_url(stamp, s_file_name="") -> tuple:
     '''
          Ask Pipefy for a signed PUT URL. Returns (s_url, n_status).

          Pipefy has shipped this payload with the URL under both `url` and
          `downloadUrl` across versions, so ask for both and take whichever
          comes back looking like a URL.
     '''
     try:
          s_query = ('mutation($org: ID!, $fn: String!) {'
                     ' createPresignedUrl(input: {organizationId: $org, fileName: $fn})'
                     ' { url downloadUrl } }')
          d_data, n_status = fn_graphql(
               stamp=stamp, s_query=s_query,
               d_variables={"org": str(S_ORGANIZATION_ID), "fn": s_file_name},
          )
          if n_status != 200 or not d_data.get("createPresignedUrl"):
               # Older schemas expose `url` only; asking for downloadUrl 422s.
               s_query = ('mutation($org: ID!, $fn: String!) {'
                          ' createPresignedUrl(input: {organizationId: $org, fileName: $fn})'
                          ' { url } }')
               d_data, n_status = fn_graphql(
                    stamp=stamp, s_query=s_query,
                    d_variables={"org": str(S_ORGANIZATION_ID), "fn": s_file_name},
               )
          d_payload = (d_data or {}).get("createPresignedUrl") or {}
          for s_key in ("url", "downloadUrl"):
               s_candidate = d_payload.get(s_key)
               if isinstance(s_candidate, str) and s_candidate.startswith("http"):
                    return s_candidate, 200
          my_funcs.fn_log(
               stamp=stamp,
               txt="createPresignedUrl returned no usable URL",
               d_details={"response": d_payload, "file_name": s_file_name,
                          "organization_id": str(S_ORGANIZATION_ID)},
          )
          return "", 422
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"createPresignedUrl failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "file_name": s_file_name})
          return "", 500


def fn_put_bytes(stamp, s_url="", o_data=b"", s_content_type="") -> tuple:
     '''
          Upload bytes to a signed URL. Returns (b_ok, n_status).

          Some Pipefy storage backends sign the URL without a Content-Type;
          sending one then invalidates the signature and the PUT 403s. Try with
          the header, fall back to without.
     '''
     try:
          l_attempts = [s_content_type, ""] if s_content_type else [""]
          n_last_status = 500
          s_last_body = ""
          for s_type in l_attempts:
               d_headers = {"Content-Type": s_type} if s_type else {}
               resp = requests.put(s_url, data=o_data, headers=d_headers,
                                   timeout=I_HTTP_TIMEOUT)
               if 200 <= resp.status_code < 300:
                    return True, 200
               n_last_status = resp.status_code
               s_last_body = resp.text[:500]
               if resp.status_code not in (400, 403):
                    break
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"Upload to Pipefy storage returned HTTP {n_last_status}",
               d_details={"status": n_last_status, "response_body": s_last_body,
                          "bytes": len(o_data or b"")},
          )
          return False, 422
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Upload to Pipefy storage failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e)})
          return False, 500


def fn_upload_bytes(stamp, o_data=b"", s_file_name="") -> tuple:
     '''
          presign -> PUT -> return the storage path to write into a field.
          Returns (s_storage_path, n_status).
     '''
     try:
          s_url, n_status = fn_create_presigned_url(stamp=stamp, s_file_name=s_file_name)
          if n_status != 200:
               return "", n_status
          s_content_type = mimetypes.guess_type(s_file_name)[0] or "application/octet-stream"
          b_ok, n_status = fn_put_bytes(stamp=stamp, s_url=s_url, o_data=o_data,
                                        s_content_type=s_content_type)
          if not b_ok:
               return "", n_status
          return fn_storage_path_from_url(s_url=s_url), 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Pipefy upload failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "file_name": s_file_name})
          return "", 500


def fn_set_card_field(stamp, s_card_id="0", s_field_id="", l_new_value=None) -> tuple:
     '''
          updateCardField with a list value (attachment / multi-value fields).
          Returns (d_result, n_status).
     '''
     try:
          s_query = ('mutation($card: ID!, $field: ID!, $value: [UndefinedInput]!) {'
                     ' updateCardField(input: {card_id: $card, field_id: $field,'
                     ' new_value: $value}) { success card { id } } }')
          d_data, n_status = fn_graphql(
               stamp=stamp, s_query=s_query,
               d_variables={"card": str(s_card_id), "field": s_field_id,
                            "value": l_new_value or []},
          )
          if n_status == 200 and d_data.get("updateCardField"):
               return d_data["updateCardField"], 200

          # Older schema types new_value loosely — inline it instead.
          s_inline = ('mutation { updateCardField(input: {card_id: %s, field_id: "%s",'
                      ' new_value: %s}) { success card { id } } }'
                      % (json.dumps(str(s_card_id)), s_field_id,
                         json.dumps(l_new_value or [])))
          d_data, n_status = fn_graphql(stamp=stamp, s_query=s_inline)
          if n_status == 200 and d_data.get("updateCardField"):
               return d_data["updateCardField"], 200

          my_funcs.fn_log(
               stamp=stamp,
               txt=f"updateCardField failed for field '{s_field_id}'",
               d_details={"card_id": str(s_card_id), "field_id": s_field_id,
                          "new_value": l_new_value or [], "status": n_status},
          )
          return {}, 422
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"updateCardField failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "card_id": str(s_card_id),
                                     "field_id": s_field_id})
          return {}, 500


def fn_attach_pdf(stamp, s_card_id="0", s_field_id="", o_pdf_bytes=b"",
                  s_file_name="", b_keep_existing=False) -> tuple:
     '''
          Upload the PDF, write it onto an attachment field, then RE-READ the
          card and confirm it is actually there.

          updateCardField overwrites an attachment field. Default behaviour
          matches that: one current brief per card, so a re-run (or a Pipefy
          webhook retry) replaces rather than stacks. b_keep_existing re-sends
          the paths already on the field alongside the new file.

          Returns (d_result, n_status). 200 = attached and verified,
          202 = attached but the read-back could not confirm it.
     '''
     try:
          s_new_path, n_status = fn_upload_bytes(stamp=stamp, o_data=o_pdf_bytes,
                                                 s_file_name=s_file_name)
          if n_status != 200:
               return {}, n_status

          l_paths = [s_new_path]
          i_removed = 0
          if b_keep_existing:
               d_card, n_card_status = fn_fetch_card(stamp=stamp, s_card_id=s_card_id)
               if n_card_status == 200:
                    l_existing = fn_existing_attachment_paths(
                         d_field=fn_card_field(d_card=d_card, s_field_id=s_field_id))
                    l_paths = l_existing + [s_new_path]
          else:
               d_card, n_card_status = fn_fetch_card(stamp=stamp, s_card_id=s_card_id)
               if n_card_status == 200:
                    i_removed = len(fn_existing_attachment_paths(
                         d_field=fn_card_field(d_card=d_card, s_field_id=s_field_id)))

          d_result, n_status = fn_set_card_field(
               stamp=stamp, s_card_id=s_card_id, s_field_id=s_field_id,
               l_new_value=l_paths,
          )
          if n_status != 200:
               return {}, n_status

          b_verified, n_verify_status = fn_verify_attachment(
               stamp=stamp, s_card_id=s_card_id, s_field_id=s_field_id,
               s_file_name=s_file_name,
          )
          d_out = {
               "card_id": str(s_card_id),
               "field_id": s_field_id,
               "filename": s_file_name,
               "storage_path": s_new_path,
               "replaced_files": i_removed,
               "verified": bool(b_verified),
          }
          if not b_verified:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt="PDF attached but read-back could not confirm it on the field",
                    d_details=d_out,
               )
               return d_out, 202
          return d_out, 200

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Attach PDF failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "card_id": str(s_card_id),
                                     "field_id": s_field_id, "file_name": s_file_name})
          return {}, 500


def fn_verify_attachment(stamp, s_card_id="0", s_field_id="", s_file_name="") -> tuple:
     '''
          Re-read the card and confirm the filename is on the attachment field.
          Returns (b_found, n_status).
     '''
     try:
          d_card, n_status = fn_fetch_card(stamp=stamp, s_card_id=s_card_id)
          if n_status != 200:
               return False, n_status
          l_paths = fn_existing_attachment_paths(
               d_field=fn_card_field(d_card=d_card, s_field_id=s_field_id))
          s_want = my_funcs.fn_attachment_filename(s_value=s_file_name)
          for s_path in l_paths:
               if my_funcs.fn_attachment_filename(s_value=s_path) == s_want:
                    return True, 200
          return False, 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Attachment verification failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "card_id": str(s_card_id)})
          return False, 500
