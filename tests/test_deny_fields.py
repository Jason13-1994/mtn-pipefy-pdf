'''
     tests/test_deny_fields.py — guards TEST-02's deny-field leak guarantee.

     This is the actual security control that keeps internal-only Pipefy fields
     off an agency-facing Job Brief. set_deny filtering already exists and works
     today (my_brief.py:415-423), but nothing proved it end-to-end before this
     file. Because the doc model and the rendered PDF only ever carry field
     VALUES, never the originating Pipefy field id, "assert field id X does not
     appear in the output" is not directly expressible — the only test that
     genuinely proves the guarantee is one that injects a known, distinctive
     value into every currently-poisonable denied field on a real fixture and
     proves that value's absence from both the doc-model dict and the actual
     rendered PDF text (extracted via pypdf, never a raw-byte search — reportlab
     compresses its content stream by default, and a raw-byte search can report
     a false "absent" on genuinely-leaked content).

     Two profiles, two different Doc instances, two different set_deny sets
     (Doc.set_deny is a per-instance attribute, not a module-level global —
     my_layout.py:104,120): D_JOB_BRIEF against fixtures/mock_brief_linked.json,
     D_CAMPAIGN_BRIEF against fixtures/mock_campaign.json. Each test builds its
     own poisoned copy from its own fixture file — no shared mutable state.

     Naming convention note: pytest's own collection requires test functions to
     be named test_*, which is this repo's one documented exception to the fn_
     prefix rule (matching tests/test_long_token_wrap.py) — do not rename these
     to fn_test_..., that would silently produce "0 tests collected" instead of
     a failure. Test functions use bare assert and never the (data, status_code)
     tuple contract. fn_poisoned_fixture below IS a test-support helper, not a
     collected test, so it keeps the full fn_/Hungarian-prefix convention — and
     it is allowed to raise on a malformed fixture path or JSON, unlike
     production code, because an unhandled exception in test-support code is
     itself a correct and useful test failure.

     KNOWN STRUCTURAL GAP — set_deny is not enforced everywhere (02-RESEARCH.md
     Pitfall 1, verified against the live source this session, not fixed here):

     1. fn_build_doc_model() checks o_item.s_field_id against o_doc.set_deny
        ONLY inside the loop over l_sections + l_tail_sections (my_brief.py:
        415-423). It never checks l_meta, l_subtitle, t_highlight, or the
        campaign section's own field lists (l_summary_fields/l_standalone_
        fields, resolved by fn_build_campaign_section — my_brief.py:269-339).
        A denied field id added to one of those lists would render anyway; this
        test's marker-injection strategy only reaches the section-loop path,
        because that is the only path set_deny actually filters.

     2. A OneOf item (my_layout.py:66-79) is structurally invisible to
        set_deny even inside the enforced section loop, because the filter
        checks getattr(o_item, "s_field_id", "") — and OneOf never defines
        s_field_id (it has l_field_ids, plural). getattr() therefore always
        returns "" for a OneOf, and "" is never a member of set_deny, so the
        check always passes through. The only OneOf on either profile today is
        the "Division" field-group (my_layout.py:176,362, L_DIVISION_FIELDS at
        my_layout.py:124-132) — verified NOT a member of either D_JOB_BRIEF.
        set_deny or D_CAMPAIGN_BRIEF.set_deny today, so this is not a live
        leak.

     Neither gap is fixed in this file — verified not a live bug today (no
     division field and no l_meta/l_subtitle/t_highlight/campaign-section field
     is currently denied on either profile), and out of scope for this plan.
     Warning sign for a future maintainer: a my_layout.py diff that adds an id
     to l_meta/l_subtitle/t_highlight/l_summary_fields/l_standalone_fields that
     is already in that Doc's set_deny, or that adds a division field id (or
     any OneOf field id) to set_deny — either change would silently defeat this
     test's coverage. Reading this docstring is how that limit is discovered,
     not by shipping a leak.
'''
import copy
import io
import json

import pypdf

import my_brief
import my_layout
import my_pdf


MARKER = "ZZZ-DENY-MARKER-MUST-NOT-LEAK-ZZZ"


def fn_poisoned_fixture(s_path="", o_doc=None) -> dict:
     '''
          Reads the fixture JSON at s_path, returns a deep copy with MARKER
          written over both "value" and "array_value" for every card field
          whose field.id is in o_doc.set_deny. The source file on disk is
          never touched — json.load() reads it once, everything after that is
          an in-memory copy.

          This is test-support code, not production code — an unhandled
          exception here (a bad path, malformed JSON, a missing "card" key) is
          correct behaviour: it surfaces as a loud test failure rather than a
          silently-swallowed default, which is the opposite of every my_*
          production module's (data, status_code) contract on purpose.
     '''
     with open(s_path, encoding="utf-8") as o_file:
          d_fixture = json.load(o_file)
     d_fixture = copy.deepcopy(d_fixture)
     d_card = d_fixture["card"]
     for d_field in d_card["fields"]:
          s_field_id = d_field.get("field", {}).get("id")
          if s_field_id in o_doc.set_deny:
               d_field["value"] = MARKER
               d_field["array_value"] = [MARKER]
     return d_fixture


def test_no_denied_field_leaks_job_brief():
     '''
          Every currently-poisonable field in D_JOB_BRIEF.set_deny, poisoned on
          a copy of fixtures/mock_brief_linked.json, must never reach the
          doc-model dict or the pypdf-extracted PDF text. A real, non-denied
          value (the job name) must be present in both, proving the render is
          genuine and non-empty rather than the marker's absence being
          meaningless on a broken or blank document.
     '''
     o_doc = my_layout.fn_profile_for_key(s_key="brief")
     assert o_doc is not None

     d_fixture = fn_poisoned_fixture(
          s_path="fixtures/mock_brief_linked.json", o_doc=o_doc)
     stamp = {"time": 0, "card_id": "test", "Mode": "PrintOnly"}

     d_model, n_status = my_brief.fn_build_doc_model(
          stamp=stamp, o_doc=o_doc, d_card=d_fixture["card"],
          d_campaign_record=d_fixture.get("campaign_record"),
          d_pipe=d_fixture.get("pipe"), d_table=d_fixture.get("table"))
     assert n_status == 200

     # positive control — proves the test isn't vacuously passing on an
     # empty or broken document
     assert len(d_model.get("sections") or []) > 0

     s_model_json = json.dumps(d_model, default=str)
     assert "AFCON Qualifiers - ATL suite" in s_model_json
     assert MARKER not in s_model_json

     o_bytes, n_render_status = my_pdf.fn_render_pdf(stamp=stamp, d_model=d_model)
     assert n_render_status == 200
     assert len(o_bytes) > 0

     o_reader = pypdf.PdfReader(io.BytesIO(o_bytes))
     s_text = "".join(o_page.extract_text() for o_page in o_reader.pages)
     assert "AFCON Qualifiers - ATL suite" in s_text
     assert MARKER not in s_text


def test_no_denied_field_leaks_campaign_brief():
     '''
          Same guarantee, the other Doc, a different deny set. Every
          currently-poisonable field in D_CAMPAIGN_BRIEF.set_deny, poisoned on
          a copy of fixtures/mock_campaign.json, must never reach the
          doc-model dict or the pypdf-extracted PDF text. A real, non-denied
          value (the campaign name) must be present in both.
     '''
     o_doc = my_layout.fn_profile_for_key(s_key="campaign")
     assert o_doc is not None

     d_fixture = fn_poisoned_fixture(
          s_path="fixtures/mock_campaign.json", o_doc=o_doc)
     stamp = {"time": 0, "card_id": "test", "Mode": "PrintOnly"}

     d_model, n_status = my_brief.fn_build_doc_model(
          stamp=stamp, o_doc=o_doc, d_card=d_fixture["card"],
          d_campaign_record=d_fixture.get("campaign_record"),
          d_pipe=d_fixture.get("pipe"), d_table=d_fixture.get("table"))
     assert n_status == 200

     # positive control — proves the test isn't vacuously passing on an
     # empty or broken document
     assert len(d_model.get("sections") or []) > 0

     s_model_json = json.dumps(d_model, default=str)
     assert "MoMo Payday Boost" in s_model_json
     assert MARKER not in s_model_json

     o_bytes, n_render_status = my_pdf.fn_render_pdf(stamp=stamp, d_model=d_model)
     assert n_render_status == 200
     assert len(o_bytes) > 0

     o_reader = pypdf.PdfReader(io.BytesIO(o_bytes))
     s_text = "".join(o_page.extract_text() for o_page in o_reader.pages)
     assert "MoMo Payday Boost" in s_text
     assert MARKER not in s_text


def test_set_deny_actually_removes_a_wired_item():
     '''
          Direct unit test of the fn_build_doc_model deny-filter branch
          (my_brief.py:415-423), independent of whether either real Doc
          profile currently wires a denied field id into a Section. See
          this file's module docstring (KNOWN STRUCTURAL GAP, point 1)
          and CR-01 in 02-REVIEW.md for why the two fixture-based tests
          above are presently vacuous with respect to the filter itself:
          neither D_JOB_BRIEF nor D_CAMPAIGN_BRIEF wires any of its own
          set_deny ids into a Section today, so the
          "if getattr(o_item, 's_field_id', '') in o_doc.set_deny: continue"
          line at my_brief.py:418 never runs against a real, denied id in
          those two tests. This test builds a synthetic Doc/Section/Field
          so a denied id IS wired into a Section, and asserts that poisoned
          value never reaches the doc model — proving the branch itself,
          not just the allowlist around it.
     '''
     o_doc = my_layout.Doc(
          s_key="synthetic", s_name_field="job_name",
          l_sections=[my_layout.Section("Test", [
               my_layout.Field("job_name"),
               my_layout.Field("poison_me"),   # <- denied below, and WIRED
          ])],
          set_deny={"poison_me"},
     )
     d_card = {
          "id": "1", "title": "Synthetic",
          "fields": [
               {"field": {"id": "job_name", "type": "short_text"},
                "value": "Synthetic job", "array_value": []},
               {"field": {"id": "poison_me", "type": "short_text"},
                "value": MARKER, "array_value": [MARKER]},
          ],
     }
     stamp = {"time": 0, "card_id": "test", "Mode": "PrintOnly"}

     d_model, n_status = my_brief.fn_build_doc_model(
          stamp=stamp, o_doc=o_doc, d_card=d_card)
     assert n_status == 200

     s_model_json = json.dumps(d_model, default=str)
     assert "Synthetic job" in s_model_json    # positive control still real
     assert MARKER not in s_model_json         # exercises my_brief.py:418 directly
