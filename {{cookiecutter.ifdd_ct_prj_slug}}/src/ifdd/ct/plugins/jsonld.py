"""JSON-LD steps. Contexts come from IFDD_CT_CONTEXT_DIR or over HTTP."""

from __future__ import annotations

from typing import Annotated

from ifdd.ct import CtError, plugin
from ifdd.ct.jsonld import compact as _compact
from ifdd.ct.jsonld import expand as _expand
from ifdd.ct.nodes import AspectParam, document_of, to_node


@plugin
def expand(records, ctx):
    """Expand every JSON-LD document (one expanded object per input record)."""
    out = []
    for doc in records:
        expanded = _expand(doc, ctx)
        out.append(expanded[0] if len(expanded) == 1 else {"@graph": expanded})
    return out


@plugin
def compact(
    records, ctx,
    context: Annotated[str, "context URL to compact against; empty: the document's @context"] = "",
):
    """Compact every document against CONTEXT (default: the document's own @context)."""
    out = []
    for doc in records:
        target = context or doc.get("@context")
        if not target:
            raise CtError(f"{doc.get('@id', '?')}: no @context and no context parameter")
        result = _compact(doc, target, ctx)
        if isinstance(target, str):
            result["@context"] = target
        out.append(result)
    return out


@plugin
def node(records, ctx, aspect: AspectParam = "",
         expanded: Annotated[bool, "also add the expanded document as 'expanded'"] = False):
    """Wrap documents in the backend envelope {id, context, aspect, json[, expanded]}.

    Not needed before put/patch/post - they wrap documents themselves. Use it
    to see or store exactly what would be sent.
    """
    out = []
    for doc in records:
        envelope = to_node(doc, ctx, aspect or None)
        if expanded:
            envelope["expanded"] = _expand(envelope["json"], ctx)[0]
        out.append(envelope)
    return out


@plugin
def check(
    records, ctx,
    fail: Annotated[bool, "fail the step after all documents are checked; false: only warn"] = False,
):
    """Check every document against its @context and report what would be lost.

    Reported per document (as a warning on stderr):
      * terms the @context does not define - expansion drops them silently,
        e.g. a typo such as 'nmae' for 'name';
      * a missing @context;
      * a context that cannot be loaded, or invalid JSON-LD.

    The records are passed on unchanged, so the step can sit anywhere in a
    chain: 'examples/json-ld check put'. Envelopes made by 'node' are checked
    by their document.

    Limits: with @vocab in a context every term is defined, so nothing is
    reported for it. Values are not checked against their declared type, and
    required fields or cardinalities are not checked at all.
    """
    findings = []
    for index, record in enumerate(records, 1):
        label, problems = _check_one(record, index, ctx)
        for problem in problems:
            ctx.log.warning("%s: %s", label, problem)
        if problems:
            findings.append({"document": label, "problems": problems})
    ctx.shared["check"] = findings

    if findings:
        summary = f"{len(findings)} of {len(records)} documents with findings"
        if fail:
            raise CtError(f"check: {summary}")
        ctx.log.warning("check: %s", summary)
    else:
        ctx.log.info("check: all %d documents ok", len(records))
    return records


def _check_one(record, index, ctx) -> tuple[str, list[str]]:
    if not isinstance(record, dict):
        return f"record {index}", [f"not a JSON object but {type(record).__name__}"]
    doc = document_of(record)
    label = str(doc.get("@id") or f"record {index}")
    if "@context" not in doc:
        return label, ["no @context - every term would be dropped"]
    dropped: list[str] = []
    try:
        _expand(doc, ctx, on_dropped=lambda term: term and dropped.append(term))
    except CtError as err:
        return label, [f"cannot be expanded: {str(err).split(': ', 1)[-1]}"]
    terms = sorted(set(dropped))
    if terms:
        return label, [f"undefined terms: {', '.join(terms)}"]
    return label, []
