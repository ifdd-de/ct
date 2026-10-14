"""check: report what expansion against the @context would silently drop.

Most tests use the fixture context strict.jsonld (no @vocab; defines only
name, size and hasPart), loaded through IFDD_CT_CONTEXT_DIR.
"""

import logging

import pytest
from support import FakeSession, Response, envelope, run_steps

from ifdd.ct.errors import CtError

STRICT = "https://schema.test/v1/strict.jsonld"
CLEAN = "tests/fixtures/documents/check-clean.jsonld"
TYPO = "tests/fixtures/documents/check-typo.jsonld"


def strict_doc(key="1", **fields):
    return {"@context": STRICT, "@id": f"https://rest.test/products/{key}", **fields}


def warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


# -- findings --------------------------------------------------------------

def test_clean_documents_give_no_warning(caplog):
    caplog.set_level(logging.INFO)
    run_steps(CLEAN, "check")
    assert warnings(caplog) == []
    assert "check: all 2 documents ok" in caplog.text


def test_undefined_term_is_reported_with_the_document_id(caplog):
    run_steps(TYPO, "check")
    assert warnings(caplog) == [
        "https://rest.test/products/typo-1: undefined terms: nmae",
        "check: 1 of 2 documents with findings",
    ]


def test_several_terms_are_listed_once_and_sorted(caplog):
    run_steps("check", records=[strict_doc(zeta=1, alpha=2, nmae="x")])
    assert "undefined terms: alpha, nmae, zeta" in caplog.text


def test_undefined_terms_in_nested_objects(caplog):
    nested = strict_doc(hasPart={"@id": "https://rest.test/products/2", "colour": "red"})
    run_steps("check", records=[nested])
    assert "undefined terms: colour" in caplog.text


def test_missing_context(caplog):
    run_steps("check", records=[{"@id": "https://rest.test/products/1", "name": "x"}])
    assert "https://rest.test/products/1: no @context" in caplog.text


def test_context_that_cannot_be_loaded(caplog, http_ctx):
    ctx = http_ctx(FakeSession(Response(200, "not json")))
    run_steps("check", records=[strict_doc() | {"@context": "https://schema.test/v1/gone.jsonld"}],
              ctx=ctx)
    assert "https://rest.test/products/1: cannot be expanded" in caplog.text


def test_records_that_are_not_objects(caplog):
    run_steps("check", records=[strict_doc(name="ok"), "text"])
    assert "record 2: not a JSON object but str" in caplog.text


def test_documents_without_id_are_named_by_position(caplog):
    run_steps("check", records=[{"@context": STRICT, "nmae": "x"}])
    assert "record 1: undefined terms: nmae" in caplog.text


def test_envelopes_are_checked_by_their_document(caplog):
    run_steps("check", records=[envelope(strict_doc(nmae="x"), "product")])
    assert "undefined terms: nmae" in caplog.text


# -- records flow on unchanged ---------------------------------------------

def test_records_are_passed_on_unchanged():
    records = [strict_doc(nmae="x"), strict_doc(key="2", name="y")]
    result, printed = run_steps("check", records=records)
    assert result == records
    assert '"nmae": "x"' in printed  # check is a transform: output is printed


def test_check_in_the_middle_of_a_chain():
    result, _ = run_steps(TYPO, "check", "head:count=1")
    assert [r["@id"] for r in result] == ["https://rest.test/products/typo-1"]


def test_findings_are_left_for_later_steps(ctx):
    run_steps("check", records=[strict_doc(nmae="x")], ctx=ctx)
    assert ctx.shared["check"] == [
        {"document": "https://rest.test/products/1", "problems": ["undefined terms: nmae"]}]


# -- warn or fail ----------------------------------------------------------

@pytest.mark.parametrize("step", ["check", "check:fail=false", "check:fail=no"])
def test_default_and_explicit_warn_mode_do_not_fail(step):
    result, _ = run_steps(TYPO, step)
    assert len(result) == 2


@pytest.mark.parametrize("step", ["check:fail=true", "check:fail=yes", "check:fail=1"])
def test_fail_mode_stops_the_pipeline(step):
    with pytest.raises(CtError, match="check: 1 of 2 documents with findings"):
        run_steps(TYPO, step)


def test_fail_mode_reports_every_document_first(caplog):
    records = [strict_doc("1", nmae="x"), strict_doc("2", sise=3)]
    with pytest.raises(CtError):
        run_steps("check:fail=true", records=records)
    assert "products/1: undefined terms: nmae" in caplog.text
    assert "products/2: undefined terms: sise" in caplog.text


def test_fail_mode_with_clean_documents_passes():
    assert len(run_steps(CLEAN, "check:fail=true")[0]) == 2


def test_fail_mode_in_a_pipeline_file(tmp_path):
    from ifdd.ct.pipeline import load_pipeline, run
    from support.runner import Terminal

    pipeline = tmp_path / "p.yaml"
    pipeline.write_text("- " + TYPO + "\n- check: {fail: true}\n")
    with pytest.raises(CtError, match="1 of 2"):
        run(load_pipeline(pipeline), stdin=Terminal())


# -- documented limits -----------------------------------------------------

def test_limit_vocab_defines_every_term(caplog):
    # the fixture product.jsonld uses @vocab: nothing can be undefined
    run_steps("check", records=[{"@context": "https://schema.test/v1/product.jsonld",
                                 "@id": "https://rest.test/products/1", "nmae": "x"}])
    assert warnings(caplog) == []


def test_limit_values_are_not_checked_against_their_type(caplog):
    run_steps("check", records=[strict_doc(size="not a number")])
    assert warnings(caplog) == []


def test_describe_explains_modes_and_limits():
    from ifdd.ct.registry import resolve

    text = resolve("check").describe()
    assert "fail: bool = False" in text and "@vocab" in text
