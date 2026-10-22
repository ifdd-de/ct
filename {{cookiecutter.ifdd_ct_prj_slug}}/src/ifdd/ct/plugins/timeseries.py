"""Time series: example samples, and writing samples through ts-api.

A *sample record* names its series and store, as ts-api expects them::

    {"store": "temperature.ops.example.ifdd.de", "name": "temperature",
     "ifdd_id": "https://rest/products/...", "ifdd_property": "<type>/climate.ops.example.ifdd.de/temperature",
     "ifdd_unit": "<unit>/unit/DEG_C", "time": "2026-10-22T07:15:00+00:00", "value": 21.5}

``ts-climate`` makes such records for objects of the pipeline (by default the
circuit breakers of the faker profile ``energy-grid``); ``ts-post`` writes
them to ts-api (IFDD_CT_TS_API_URL) with the token of this client.

The properties and units belong to the example vocabulary
``climate.ops.example.ifdd.de`` of the type service and the example units of
the unit service; ts-api checks every sample against them.
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Annotated

from ifdd.ct import CtError, UsageError, plugin

CLIMATE = "climate.ops.example.ifdd.de"
SAMPLE_FIELDS = ("name", "ifdd_id", "ifdd_property", "ifdd_unit", "time", "value")
# name -> (property, unit, mean, daily amplitude, noise, lowest, highest)
SERIES = {
    "temperature": ("temperature", "DEG_C", 12.0, 6.0, 0.8, -50.0, 100.0),
    "humidity": ("relativeHumidity", "PERCENT_RH", 65.0, 15.0, 3.0, 0.0, 100.0),
}


def _context_name(record) -> str:
    context = record.get("@context") if isinstance(record, dict) else None
    if not isinstance(context, str):
        return ""
    name = context.rstrip("/").rsplit("/", 1)[-1]
    return name[: -len(".jsonld")] if name.endswith(".jsonld") else name


def _end(end: str, step: int) -> datetime:
    if end:
        try:
            moment = datetime.fromisoformat(end)
        except ValueError:
            raise UsageError(f"ts-climate:end={end!r} is not an ISO 8601 time") from None
        if moment.tzinfo is None:
            raise UsageError(f"ts-climate:end={end!r} has no offset (add Z or +02:00)")
        return moment.astimezone(timezone.utc)
    now = int(datetime.now(timezone.utc).timestamp())
    return datetime.fromtimestamp(now - now % step, timezone.utc)


@plugin
def ts_climate(records, ctx,
               context: Annotated[str, "objects with a document in this context get series"]
               = "breaker.grid.example.ifdd.de",
               days: Annotated[int, "days of samples, up to end"] = 7,
               step: Annotated[int, "seconds between two samples"] = 900,
               end: Annotated[str, "ISO 8601 time of the last sample; empty: the last full step"] = "",
               seed: Annotated[int, "same seed, same values"] = 42,
               temperature_store: Annotated[str, "store of the temperature series"]
               = "temperature.ops.example.ifdd.de",
               humidity_store: Annotated[str, "store of the humidity series"]
               = "humidity.ops.example.ifdd.de"):
    """Replace the records by example climate samples of their objects.

    Every object (@id) with a document in CONTEXT gets a temperature series
    in TEMPERATURE_STORE and a relative humidity series in HUMIDITY_STORE:
    a daily curve with noise, one sample every STEP seconds over DAYS days.
    The same seed and END give the same samples. Needs IFDD_CT_TYPE_URL and
    IFDD_CT_UNIT_URL.
    """
    ctx.settings.require("type_url", "unit_url")
    if days < 1 or step < 1:
        raise UsageError("ts-climate needs days >= 1 and step >= 1")
    ids = sorted({r["@id"] for r in records if _context_name(r) == context and "@id" in r})
    if not ids:
        ctx.log.warning("ts-climate: no record with the context %s", context)
    last = _end(end, step)
    count = days * 86400 // step
    times = [last - timedelta(seconds=step * i) for i in range(count - 1, -1, -1)]
    stores = {"temperature": temperature_store, "humidity": humidity_store}
    samples = []
    for object_id in ids:
        rnd = random.Random(f"{seed}:{object_id}")
        for name, (prop, unit, mean, amplitude, noise, low, high) in SERIES.items():
            offset = rnd.uniform(-amplitude / 2, amplitude / 2)
            for moment in times:
                day = (moment.timestamp() % 86400) / 86400
                value = mean + offset + amplitude * math.sin(2 * math.pi * (day - 0.375)) \
                    + rnd.gauss(0, noise)
                samples.append({
                    "store": stores[name],
                    "name": name,
                    "ifdd_id": object_id,
                    "ifdd_property": f"{ctx.settings.type_url}/{CLIMATE}/{prop}",
                    "ifdd_unit": f"{ctx.settings.unit_url}/unit/{unit}",
                    "time": moment.isoformat(timespec="milliseconds"),
                    "value": round(min(high, max(low, value)), 2),
                })
    ctx.log.info("ts-climate: %d samples for %d objects", len(samples), len(ids))
    return samples


@plugin(sink=True)
def ts_post(records, ctx,
            batch: Annotated[int, "samples per request (ts-api accepts at most IFDD_TS_MAX_ITEMS)"]
            = 5000,
            dry_run: Annotated[bool, "log what would be sent, send nothing"] = False):
    """Write sample records to ts-api: POST IFDD_CT_TS_API_URL/stores/<store>/samples/batch.

    Every record needs "store" and the six fields of a sample (name,
    ifdd_id, ifdd_property, ifdd_unit, time, value). The records are sent per
    store in lists of BATCH; a refused list is logged with the answer of
    ts-api and reported at the end, the others are still sent.
    """
    ctx.settings.require("ts_api_url")
    if batch < 1:
        raise UsageError("ts-post needs batch >= 1")
    by_store: dict[str, list[dict]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict) or "store" not in record:
            raise CtError(f"ts-post: record {index} has no store")
        missing = [f for f in SAMPLE_FIELDS if f not in record]
        if missing:
            raise CtError(f"ts-post: record {index} lacks {', '.join(missing)}")
        by_store.setdefault(record["store"], []).append(
            {field: record[field] for field in SAMPLE_FIELDS}
        )
    failed = 0
    for store, samples in by_store.items():
        url = f"{ctx.settings.ts_api_url}/stores/{store}/samples/batch"
        for start in range(0, len(samples), batch):
            chunk = samples[start:start + batch]
            if dry_run:
                ctx.log.warning("dry run: POST %s (%d samples)", url, len(chunk))
                continue
            response = ctx.http.request(
                "POST", url, data=json.dumps({"samples": chunk}),
                headers={"Content-Type": "application/json"},
            )
            if response.status_code >= 400:
                ctx.log.error("POST %s -> %s %s", url, response.status_code, response.text[:500])
                failed += len(chunk)
            else:
                ctx.log.info("POST %s -> %s (%d samples)", url, response.status_code, len(chunk))
    if failed:
        raise CtError(f"ts-post: {failed} of {len(records)} samples were refused")
    return records


__all__ = ["ts_climate", "ts_post"]
