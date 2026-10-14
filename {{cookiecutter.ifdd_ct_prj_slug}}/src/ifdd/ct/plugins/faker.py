"""Generate realistic test data from a faker profile."""

from __future__ import annotations

from typing import Annotated

from ifdd.ct import plugin
from ifdd.ct.faker import generate, profiles


@plugin(source=True)
def faker(records, ctx,
          profile: Annotated[str, "one of the profiles listed below"] = "energy-grid",
          seed: Annotated[int | None, "same seed, same data: ids, names and timestamps"] = None,
          **counts):
    """Generate JSON-LD documents with a faker profile and add them to the records.

    TYPE=N  number of entities of a type, e.g. product=500,location=20
    """
    return [*records, *generate(profile, ctx, seed=seed, counts=counts)]


def _profiles_help() -> str:
    lines = ["profiles (entity types with default counts):"]
    for p in profiles.all_profiles():
        types = ", ".join(f"{t.name}={t.default}" for t in p.types.values())
        lines += [f"  {p.name}: {types}", f"      {p.description}"]
    return "\n".join(lines)


faker.describe_extra = _profiles_help
