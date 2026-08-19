'''
     my_brief.py — turns a Pipefy card into the doc model my_pdf.py renders.

     All the "which value, from where, formatted how" logic lives here. It reads
     the allowlist and ordering from my_layout.py and the live labels and field
     types from the pipe's form metadata, so a label change in Pipefy needs no
     code change while a NEW field stays invisible until someone adds it to
     my_layout.py.

     fn_build_doc_model() and everything above it are pure: card in, dict out,
     no HTTP and no reportlab, which is what makes the linked-vs-standalone
     campaign branch testable from a fixture.

     fn_generate_brief() at the bottom is the one orchestrating function —
     read, resolve, render, attach, verify. It lives here rather than in
     main.py so the CLI (make_pdf.py) and the webhook worker run exactly the
     same code path, not two copies of it.
'''
import sys

import my_funcs
import my_layout
import my_pdf
import my_pipefy

# Pipefy field types, grouped by how they should be printed.
L_BLOCK_TYPES = ["long_text", "statement"]
L_LIST_TYPES = ["checklist_vertical", "checklist_horizontal", "radio_vertical",
                "radio_horizontal", "assignee_select", "attachment", "label_select",
                "connector", "database_connection"]
L_DATE_TYPES = ["date"]
L_DATETIME_TYPES = ["datetime", "due_date"]
L_NUMBER_TYPES = ["number", "currency"]
L_ATTACHMENT_TYPES = ["attachment"]

S_NOTE_FROM_CAMPAIGN = "from the linked campaign"


'''
     *****************************************************
           INDEXING
     *****************************************************
'''


def fn_index_card_values(d_card=None) -> dict:
     '''
          {field_id: {"value", "array_value", "type", "label"}} for a card or a
          table record. Returns {}.
     '''
     try:
          d_index = {}
          l_fields = (d_card or {}).get("fields") or (d_card or {}).get("record_fields") or []
          for d_field in l_fields:
               d_meta = d_field.get("field") or {}
               s_field_id = d_meta.get("id")
               if not s_field_id:
                    continue
               d_index[s_field_id] = {
                    "value": d_field.get("value"),
                    "array_value": d_field.get("array_value"),
                    "type": d_meta.get("type") or "",
                    "label": my_funcs.fn_tidy(d_meta.get("label") or d_field.get("name") or ""),
               }
          return d_index
     except Exception:
          return {}


def fn_index_form_meta(d_pipe=None, d_table=None) -> dict:
     '''
          {field_id: {"label", "type"}} from the live start form, phase fields
          and/or table fields. This is where printed LABELS come from, so the
          document tracks Pipefy wording without a deploy. Returns {}.
     '''
     try:
          d_index = {}
          l_all = []
          if d_pipe:
               l_all += list(d_pipe.get("start_form_fields") or [])
               for d_phase in d_pipe.get("phases") or []:
                    l_all += list(d_phase.get("fields") or [])
          if d_table:
               l_all += list(d_table.get("table_fields") or [])
          for d_field in l_all:
               s_field_id = d_field.get("id")
               if not s_field_id:
                    continue
               s_label = my_funcs.fn_tidy(d_field.get("label") or "")
               # Zero-width-label fields are section headers, not fields.
               if not s_label:
                    continue
               d_index[s_field_id] = {"label": s_label, "type": d_field.get("type") or ""}
          return d_index
     except Exception:
          return {}


'''
     *****************************************************
           VALUE RESOLUTION
     *****************************************************
'''


def fn_render_kind(s_type="", s_override="") -> str:
     '''
          "inline" | "block" | "list" for a Pipefy field type.
     '''
     try:
          if s_override:
               return s_override
          if s_type in L_BLOCK_TYPES:
               return "block"
          if s_type in L_LIST_TYPES:
               return "list"
          return "inline"
     except Exception:
          return "inline"


def fn_format_scalar(s_type="", value=None) -> str:
     '''
          One value formatted for display, by Pipefy field type.
     '''
     try:
          if value in (None, ""):
               return ""
          if s_type in L_DATE_TYPES:
               return my_funcs.fn_format_date(s_value=value)
          if s_type in L_DATETIME_TYPES:
               return my_funcs.fn_format_datetime(s_value=value)
          if s_type in L_NUMBER_TYPES:
               return my_funcs.fn_format_number(s_value=value)
          if s_type in L_ATTACHMENT_TYPES:
               return my_funcs.fn_attachment_filename(s_value=value)
          l_parts = my_funcs.fn_as_list(value)
          if len(l_parts) > 1:
               return ", ".join(l_parts)
          return str(l_parts[0]) if l_parts else ""
     except Exception:
          return str(value or "")


def fn_read_field(d_values=None, s_field_id="") -> tuple:
     '''
          (values_for_a_list, single_display_string, s_type) for one field id.
          Everything empty when the field is not on the card.
     '''
     try:
          d_entry = (d_values or {}).get(s_field_id) or {}
          if not d_entry:
               return [], "", ""
          s_type = d_entry.get("type") or ""
          l_raw = my_funcs.fn_as_list(d_entry.get("array_value"))
          if not l_raw:
               l_raw = my_funcs.fn_as_list(d_entry.get("value"))
          l_display = [fn_format_scalar(s_type=s_type, value=x) for x in l_raw]
          l_display = [x for x in l_display if x]
          return l_display, ", ".join(l_display), s_type
     except Exception:
          return [], "", ""


def fn_resolve_item(o_item=None, d_card_values=None, d_campaign_values=None,
                    d_form_meta=None, d_campaign_meta=None, d_specials=None,
                    b_all_fields=False) -> dict:
     '''
          One Field or OneOf -> a doc-model item, or {} when it should not be
          printed. Returns {}.
     '''
     try:
          d_card_values = d_card_values or {}
          d_campaign_values = d_campaign_values or {}
          d_form_meta = d_form_meta or {}
          d_campaign_meta = d_campaign_meta or {}
          d_specials = d_specials or {}

          # ---- OneOf: first populated field wins ----
          if isinstance(o_item, my_layout.OneOf):
               for s_field_id in o_item.l_field_ids:
                    l_values, s_display, s_type = fn_read_field(
                         d_values=d_card_values, s_field_id=s_field_id)
                    if s_display:
                         return {"label": o_item.s_label, "kind": "inline",
                                 "value": s_display, "note": ""}
               if o_item.b_always or b_all_fields:
                    return {"label": o_item.s_label, "kind": "inline",
                            "value": "", "note": ""}
               return {}

          s_field_id = o_item.s_field_id

          # ---- resolver-supplied pseudo-fields ----
          if s_field_id.startswith("@"):
               s_value = str(d_specials.get(s_field_id, "") or "")
               if not s_value and not (o_item.b_always or b_all_fields):
                    return {}
               return {"label": o_item.s_label or s_field_id.lstrip("@").replace("_", " ").title(),
                       "kind": o_item.s_render or "inline",
                       "value": s_value, "note": o_item.s_note}

          # ---- pick the side to read from ----
          b_from_campaign = False
          if o_item.s_source == "campaign":
               b_from_campaign = True
          elif o_item.s_source == "auto":
               l_card, s_card_display, _ = fn_read_field(
                    d_values=d_card_values, s_field_id=s_field_id)
               if not s_card_display and d_campaign_values:
                    b_from_campaign = True

          d_values = d_campaign_values if b_from_campaign else d_card_values
          d_meta = d_campaign_meta if b_from_campaign else d_form_meta

          l_values, s_display, s_type = fn_read_field(d_values=d_values,
                                                      s_field_id=s_field_id)
          if not s_type:
               s_type = (d_meta.get(s_field_id) or {}).get("type") or ""

          if not s_display and not (o_item.b_always or b_all_fields):
               return {}

          # ---- label: explicit override, else the LIVE form label ----
          s_label = o_item.s_label
          if not s_label:
               s_label = (d_meta.get(s_field_id) or {}).get("label") or ""
          if not s_label:
               s_label = ((d_values.get(s_field_id) or {}).get("label")
                          or s_field_id.replace("_", " ").capitalize())

          s_note = o_item.s_note
          if b_from_campaign and o_item.s_source == "auto":
               s_note = (s_note + " " if s_note else "") + f"({S_NOTE_FROM_CAMPAIGN})"

          s_kind = fn_render_kind(s_type=s_type, s_override=o_item.s_render)
          if s_kind == "list":
               return {"label": s_label, "kind": "list",
                       "values": l_values, "note": s_note}
          return {"label": s_label, "kind": s_kind, "value": s_display, "note": s_note}

     except Exception:
          return {}


def fn_resolve_text(o_field=None, **kwargs) -> str:
     '''
          A Field resolved down to a plain display string, for the subtitle and
          the filename. Returns "".
     '''
     try:
          d_item = fn_resolve_item(o_item=o_field, **kwargs)
          if not d_item:
               return ""
          if d_item.get("kind") == "list":
               return ", ".join(d_item.get("values") or [])
          return str(d_item.get("value") or "")
     except Exception:
          return ""


'''
     *****************************************************
           DOC MODEL
     *****************************************************
'''


def fn_build_campaign_section(stamp, o_doc=None, d_card_values=None,
                              d_campaign_values=None, d_form_meta=None,
                              d_campaign_meta=None, d_specials=None,
                              b_all_fields=False) -> dict:
     '''
          The Campaign context section. Three states, all of them visible:

            linked      -> the curated summary off the campaign record
            standalone  -> the brief's own campaign-level fields
            claimed but not linked -> an empty section carrying a loud note,
                                      because a brief missing its campaign must
                                      LOOK wrong to whoever opens the PDF

          Returns {} for a profile with no campaign block (the Campaign Brief).
     '''
     try:
          d_campaign = (o_doc or my_layout.Doc()).d_campaign
          if not d_campaign:
               return {}

          l_gate_values, s_gate, _ = fn_read_field(
               d_values=d_card_values, s_field_id=d_campaign.get("s_gate_field", ""))
          b_claims_campaign = (s_gate.strip().lower()
                               == str(d_campaign.get("s_gate_value", "Yes")).strip().lower())
          b_linked = bool(d_campaign_values)

          if b_linked:
               l_specs = d_campaign.get("l_summary_fields") or []
               s_note = d_campaign.get("s_note_linked", "")
               s_campaign_title = str((d_specials or {}).get("@campaign_title") or "")
               if s_campaign_title:
                    s_note = f"Inherited from campaign \"{s_campaign_title}\". " \
                             f"Campaign Planning is the source of truth for these values."
               s_source = "campaign"
          elif b_claims_campaign:
               l_specs = []
               s_note = d_campaign.get("s_note_missing", "")
               s_source = "card"
          else:
               l_specs = d_campaign.get("l_standalone_fields") or []
               s_note = d_campaign.get("s_note_standalone", "")
               s_source = "card"

          l_items = []
          for o_spec in l_specs:
               o_forced = my_layout.Field(
                    o_spec.s_field_id, s_label=o_spec.s_label, s_source=s_source,
                    b_always=o_spec.b_always, s_render=o_spec.s_render,
                    s_note=o_spec.s_note)
               d_item = fn_resolve_item(
                    o_item=o_forced, d_card_values=d_card_values,
                    d_campaign_values=d_campaign_values, d_form_meta=d_form_meta,
                    d_campaign_meta=d_campaign_meta, d_specials=d_specials,
                    b_all_fields=b_all_fields)
               if d_item:
                    l_items.append(d_item)

          s_title = d_campaign.get("s_section_title", "Campaign context")
          if not b_linked and not b_claims_campaign:
               s_title = f"{s_title} (defined by this brief)"

          return {"title": s_title, "note": s_note, "items": l_items}

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"Campaign section build failed at line {e_traceback.tb_lineno}",
               d_details={"error": str(e)},
          )
          return {}


def fn_build_doc_model(stamp, o_doc=None, d_card=None, d_campaign_record=None,
                       d_pipe=None, d_table=None, b_all_fields=False) -> tuple:
     '''
          Card (+ optional linked campaign record) -> the dict my_pdf renders.
          Returns (d_model, n_status).
     '''
     try:
          if not o_doc or not d_card:
               my_funcs.fn_log(stamp=stamp,
                               txt="Doc model build called without a profile or a card",
                               d_details={})
               return {}, 500

          d_card_values = fn_index_card_values(d_card=d_card)
          d_campaign_values = fn_index_card_values(d_card=d_campaign_record)
          d_form_meta = fn_index_form_meta(d_pipe=d_pipe)
          d_campaign_meta = fn_index_form_meta(d_table=d_table)

          d_specials = {
               "@id": str(d_card.get("id") or ""),
               "@phase": str((d_card.get("current_phase") or {}).get("name") or ""),
               "@assignees": ", ".join(
                    [str(d_user.get("name") or "") for d_user in d_card.get("assignees") or []]),
               "@campaign_title": str((d_campaign_record or {}).get("title") or ""),
               "@current_date": my_funcs.fn_now_sast(),
          }

          d_common = {
               "d_card_values": d_card_values,
               "d_campaign_values": d_campaign_values,
               "d_form_meta": d_form_meta,
               "d_campaign_meta": d_campaign_meta,
               "d_specials": d_specials,
          }

          # ---- title, subtitle, highlight, meta ----
          l_name_values, s_name, _ = fn_read_field(d_values=d_card_values,
                                                   s_field_id=o_doc.s_name_field)
          if not s_name:
               s_name = my_funcs.fn_tidy(d_card.get("title") or "")
          if not s_name:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"Refusing to render — no name on the card "
                        f"(field '{o_doc.s_name_field}' and card title are both empty)",
                    d_details={"card_id": d_specials["@id"], "profile": o_doc.s_key},
               )
               return {}, 422

          l_subtitle = [fn_resolve_text(o_field=o_field, b_all_fields=False, **d_common)
                        for o_field in o_doc.l_subtitle]
          l_subtitle = [x for x in l_subtitle if x]

          d_highlight = {}
          if o_doc.t_highlight:
               s_highlight = fn_resolve_text(o_field=o_doc.t_highlight[1],
                                             b_all_fields=False, **d_common)
               if s_highlight:
                    d_highlight = {"label": o_doc.t_highlight[0], "value": s_highlight}

          l_meta = []
          for s_label, o_field in o_doc.l_meta:
               s_value = fn_resolve_text(o_field=o_field, b_all_fields=False, **d_common)
               if s_value or o_field.b_always:
                    l_meta.append((s_label, s_value or "Not provided"))

          # ---- body ----
          l_sections = []
          d_campaign_section = fn_build_campaign_section(
               stamp=stamp, o_doc=o_doc, b_all_fields=b_all_fields, **d_common)
          if d_campaign_section:
               l_sections.append(d_campaign_section)

          for o_section in list(o_doc.l_sections) + list(o_doc.l_tail_sections):
               l_items = []
               for o_item in o_section.l_items:
                    if getattr(o_item, "s_field_id", "") in o_doc.set_deny:
                         continue
                    d_item = fn_resolve_item(o_item=o_item, b_all_fields=b_all_fields,
                                             **d_common)
                    if d_item:
                         l_items.append(d_item)
               if l_items:
                    l_sections.append({"title": o_section.s_title,
                                       "note": o_section.s_note, "items": l_items})

          # ---- filename ----
          s_opco = fn_resolve_text(
               o_field=my_layout.Field("originating_opco", s_source="auto"),
               b_all_fields=False, **d_common)
          s_filename = o_doc.s_filename_template.format(
               name=my_funcs.fn_safe_filename(s_name=s_name, i_max_length=60),
               originating_opco=my_funcs.fn_safe_filename(s_name=s_opco or "OpCo TBC",
                                                          i_max_length=20),
               card_id=d_specials["@id"],
          )

          d_model = {
               "doc_title": o_doc.s_doc_title,
               "pipe_label": o_doc.s_pipe_label,
               "profile": o_doc.s_key,
               "title": s_name,
               "subtitle": " · ".join(l_subtitle),
               "meta": l_meta,
               "highlight": d_highlight,
               "sections": l_sections,
               "footer_ref": f"Card #{d_specials['@id']}",
               "generated": d_specials["@current_date"],
               "source_url": d_card.get("url") or "",
               "filename": my_funcs.fn_safe_filename(s_name=s_filename, i_max_length=180),
          }
          return d_model, 200

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"Doc model build failed at line {e_traceback.tb_lineno}",
               d_details={"error": str(e), "card_id": str((d_card or {}).get("id") or "")},
          )
          return {}, 500


'''
     *****************************************************
           CAMPAIGN LOOKUP
     *****************************************************
'''


def fn_fetch_linked_campaign(stamp, o_doc=None, d_card=None) -> tuple:
     '''
          Follow the connector to the linked Campaign Planning DB record.

          Returns (d_record, d_table, s_route). Everything empty when the brief
          is standalone, when nothing is linked, or when the record cannot be
          read — all three are legitimate and the document reports each of them
          differently rather than failing.

          Four routes are tried, and the one that worked is returned so it lands
          in the log:
            1. the connector inside card.fields, by field id
            2. same, by label, then by field type
            3. the value is a title rather than an id -> scan the table for it
     '''
     try:
          d_campaign = (o_doc or my_layout.Doc()).d_campaign
          if not d_campaign:
               return {}, {}, "no connector on this profile"

          d_card_values = fn_index_card_values(d_card=d_card)
          l_gate, s_gate, _ = fn_read_field(
               d_values=d_card_values, s_field_id=d_campaign.get("s_gate_field", ""))
          if s_gate.strip().lower() != str(d_campaign.get("s_gate_value", "Yes")).strip().lower():
               return {}, {}, "standalone brief - no campaign expected"

          d_field, s_how = my_pipefy.fn_find_connector_field(
               d_card=d_card,
               s_preferred_id=d_campaign.get("s_field_id", ""),
               s_label_hint=d_campaign.get("s_label_hint", ""),
          )
          if not d_field:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt="Brief claims an approved campaign but no connector field "
                        "was found on the card",
                    d_details={"expected_field": d_campaign.get("s_field_id", "")},
               )
               return {}, {}, "connector field not found"

          l_ids = my_pipefy.fn_connected_record_ids(d_field=d_field)
          l_titles = my_pipefy.fn_connected_record_titles(d_field=d_field)
          s_route = f"connector by {s_how}"

          if len(l_ids) > 1:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"Brief links {len(l_ids)} campaigns — using the first",
                    d_details={"record_ids": l_ids, "titles": l_titles},
               )

          s_record_id = l_ids[0] if l_ids else ""
          if s_record_id and not s_record_id.isdigit() and l_titles:
               s_record_id = ""
          if not s_record_id and l_titles:
               s_record_id, n_status = my_pipefy.fn_find_record_id_by_title(
                    stamp=stamp, s_table_id=d_campaign.get("s_table_id", ""),
                    s_title=l_titles[0])
               s_route = "title scan of the campaign table"

          if not s_record_id:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt="Brief claims an approved campaign but nothing is linked",
                    d_details={"connector_value": d_field.get("value"),
                               "connector_array_value": d_field.get("array_value")},
               )
               return {}, {}, "nothing linked"

          d_record, n_status = my_pipefy.fn_fetch_table_record(
               stamp=stamp, s_record_id=s_record_id)
          if n_status != 200 or not d_record:
               return {}, {}, f"record {s_record_id} unreadable"

          d_table, n_table_status = my_pipefy.fn_fetch_table_fields(
               stamp=stamp, s_table_id=d_campaign.get("s_table_id", ""))
          return d_record, (d_table if n_table_status == 200 else {}), s_route

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"Linked campaign lookup failed at line {e_traceback.tb_lineno}",
               d_details={"error": str(e), "card_id": str((d_card or {}).get("id") or "")},
          )
          return {}, {}, "lookup errored"


'''
     *****************************************************
           ORCHESTRATION
     *****************************************************
'''


def fn_generate_brief(stamp, s_card_id="0", s_profile_key="", b_apply=False,
                      b_keep_existing=False, b_all_fields=False) -> tuple:
     '''
          Read the card, resolve the document, render it, and — when b_apply —
          attach it to the card and verify the read-back.

          Returns (d_result, n_status).
            200 rendered (and attached and verified when b_apply)
            202 attached but the read-back could not confirm it
            404 card not found
            409 the card is in a pipe this integration has no profile for
            422 the card cannot produce a document, or Pipefy rejected a call
            500 we broke

          d_result always carries "pdf_bytes" on a 200/202 so the caller can
          write it to disk or return it for preview.
     '''
     try:
          '''
               Step 1: Read the card
          '''
          d_card, n_status = my_pipefy.fn_fetch_card(stamp=stamp, s_card_id=s_card_id)
          if n_status != 200:
               return {"error": f"card {s_card_id} could not be read"}, n_status

          '''
               Step 2: Pick the profile from the pipe the card is in
          '''
          s_pipe_id = str((d_card.get("pipe") or {}).get("id") or "")
          o_doc = (my_layout.fn_profile_for_key(s_key=s_profile_key) if s_profile_key
                   else my_layout.fn_profile_for_pipe(s_pipe_id=s_pipe_id))
          if not o_doc:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt=f"Card {s_card_id} is in pipe {s_pipe_id}, which has no profile",
                    d_details={"pipe_id": s_pipe_id,
                               "known_pipes": sorted(my_layout.D_PROFILE_BY_PIPE)},
               )
               return {"error": f"no profile for pipe {s_pipe_id}"}, 409

          '''
               Step 3: Live form metadata — supplies the printed labels
          '''
          d_pipe, n_form_status = my_pipefy.fn_fetch_pipe_form(stamp=stamp,
                                                               s_pipe_id=o_doc.s_pipe_id)
          if n_form_status != 200:
               my_funcs.fn_log(
                    stamp=stamp,
                    txt="Form metadata unavailable — falling back to the labels on the card",
                    d_details={"pipe_id": o_doc.s_pipe_id},
               )
               d_pipe = {}

          '''
               Step 4: Follow the connector to the approved campaign, if any
          '''
          d_record, d_table, s_route = fn_fetch_linked_campaign(
               stamp=stamp, o_doc=o_doc, d_card=d_card)

          '''
               Step 5: Build the doc model and render
          '''
          d_model, n_status = fn_build_doc_model(
               stamp=stamp, o_doc=o_doc, d_card=d_card, d_campaign_record=d_record,
               d_pipe=d_pipe, d_table=d_table, b_all_fields=b_all_fields)
          if n_status != 200:
               return {"error": "document could not be assembled"}, n_status

          o_pdf_bytes, n_status = my_pdf.fn_render_pdf(stamp=stamp, d_model=d_model)
          if n_status != 200:
               return {"error": "PDF render failed"}, n_status

          d_result = {
               "card_id": str(d_card.get("id") or s_card_id),
               "profile": o_doc.s_key,
               "document": o_doc.s_doc_title,
               "filename": d_model.get("filename"),
               "attach_field": o_doc.s_attach_field,
               "campaign_route": s_route,
               "campaign_linked": bool(d_record),
               "sections": len(d_model.get("sections") or []),
               "bytes": len(o_pdf_bytes),
               "applied": False,
               "verified": False,
               "pdf_bytes": o_pdf_bytes,
          }

          '''
               Step 6: Attach — only when explicitly asked to
          '''
          if not b_apply:
               return d_result, 200

          d_attach, n_status = my_pipefy.fn_attach_pdf(
               stamp=stamp, s_card_id=d_result["card_id"],
               s_field_id=o_doc.s_attach_field, o_pdf_bytes=o_pdf_bytes,
               s_file_name=d_model.get("filename") or "Brief.pdf",
               b_keep_existing=b_keep_existing,
          )
          if n_status not in (200, 202):
               return {"error": "PDF rendered but could not be attached",
                       "filename": d_model.get("filename")}, n_status

          d_result["applied"] = True
          d_result["verified"] = bool(d_attach.get("verified"))
          d_result["replaced_files"] = d_attach.get("replaced_files", 0)
          return d_result, n_status

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"Brief generation failed at line {e_traceback.tb_lineno}",
               d_details={"error": str(e), "card_id": str(s_card_id),
                          "profile_key": s_profile_key, "apply": b_apply},
          )
          return {"error": str(e)}, 500
