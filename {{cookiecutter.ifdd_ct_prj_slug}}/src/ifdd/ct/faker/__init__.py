"""A small, generic engine for fake JSON-LD graphs.

A :class:`Profile` describes a domain: its entity types, how one entity of a
type is filled with values, how entities are linked, and which @context each
namespace uses. The engine takes care of ids, links, reproducibility and the
JSON-LD documents.

Each entity becomes one document per namespace of its type, all sharing the
same @id. The energy-grid profile, for example, writes a ``base`` and a
``product`` document for every product - the way ifdd-be stores aspects. An
entity may have further namespaces of its own (:meth:`Entity.add_namespace`),
e.g. the domain contexts of a circuit breaker.

An entity may also have an earlier version (:meth:`Graph.add_past_version`).
It is written first, with a valid time that ends where the current version
starts (``c_validNotAfter`` / ``c_validNotBefore``), so ifdd-be keeps both
and a second run of the same seed changes nothing.

Register your own profile from a private or local plugin module::

    from ifdd.ct.faker import EntityType, Profile, register_profile
    register_profile(Profile(...))
"""

from __future__ import annotations

import copy
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from ..errors import UsageError

# With a seed, all timestamps are relative to this fixed point, so the same
# seed gives the same data on every day.
SEED_ANCHOR = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class EntityType:
    name: str                    # aspect name, e.g. "product"
    segment: str                 # REST path segment of the @id, e.g. "products"
    default: int                 # default count
    namespaces: tuple[str, ...]  # one document per namespace


@dataclass
class Profile:
    name: str
    description: str
    types: dict[str, EntityType]
    make: Callable[["Graph", EntityType, "Entity"], None]
    populate: Callable[["Graph", dict[str, int]], None]
    context: Callable[[str, Any], Any]  # (namespace, settings) -> @context
    requires: tuple[str, ...] = ("be_url",)
    locale: str = "en_US"


@dataclass
class Entity:
    id: str
    type: EntityType
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    # fields of an earlier version, if the entity has one (add_past_version)
    earlier: dict[str, dict[str, Any]] | None = None
    # namespaces of this entity beyond those of its type (domain contexts)
    extra_namespaces: list[str] = field(default_factory=list)

    @property
    def namespaces(self) -> tuple[str, ...]:
        """The namespaces of the type, then those of this entity."""
        return self.type.namespaces + tuple(self.extra_namespaces)

    def set(self, namespace: str, key: str, value: Any) -> None:
        self.fields.setdefault(namespace, {})[key] = value

    def set_all(self, key: str, value: Any) -> None:
        """Set the same value in every namespace of the entity's type.

        Namespaces added with add_namespace keep their own values: a domain
        context comes from another source.
        """
        for namespace in self.type.namespaces:
            self.set(namespace, key, value)

    def add_namespace(self, namespace: str, values: dict[str, Any]) -> None:
        """A further namespace with its own values and the c_* times of the entity."""
        self.extra_namespaces.append(namespace)
        times = self.fields[self.type.namespaces[0]]
        self.fields[namespace] = dict(values)
        for key in ("c_created", "c_modified", "c_validNotBefore"):
            if key in times:
                self.fields[namespace][key] = times[key]

    def add(self, namespace: str, key: str, value: Any) -> None:
        values = self.fields.setdefault(namespace, {}).setdefault(key, [])
        if value not in values:
            values.append(value)

    def ref(self) -> dict[str, str]:
        return {"@id": self.id}


class Graph:
    """The working area of one generation run."""

    def __init__(self, profile: Profile, settings: Any, seed: int | None):
        from faker import Faker

        self.profile = profile
        self.settings = settings
        effective = seed if seed is not None else int.from_bytes(os.urandom(8), "big")
        self.rnd = random.Random(effective)
        self.fake = Faker(profile.locale)
        self.fake.seed_instance(effective)
        self.anchor = SEED_ANCHOR if seed is not None else datetime.now(timezone.utc)
        self.entities: list[Entity] = []

    # -- helpers for profiles ---------------------------------------------

    def new_id(self, etype: EntityType) -> str:
        value = uuid.UUID(int=self.rnd.getrandbits(128), version=4)
        return f"{self.settings.be_url}/{etype.segment}/{value}"

    def timestamp(self, days_back: int = 30) -> str:
        return self.moment(days_back).isoformat()

    def moment(self, days_back: int = 30) -> datetime:
        """A whole second up to ``days_back`` days before the anchor."""
        moment = self.anchor - timedelta(seconds=self.rnd.randint(0, days_back * 86400))
        return moment.replace(microsecond=0)

    def between(self, start: datetime, end: datetime) -> datetime:
        """A whole second after ``start`` and not after ``end``."""
        span = max(int((end - start).total_seconds()), 1)
        return start + timedelta(seconds=self.rnd.randint(1, span))

    # -- versions ---------------------------------------------------------

    def set_times(self, entity: Entity, days_back: int = 365) -> None:
        """Give an entity the c_* source times of the IFDD schemas.

        c_created up to ``days_back`` days before the anchor, c_modified after
        it, and a valid time from c_created on (c_validNotBefore).
        """
        created = self.moment(days_back)
        for key, value in (
            ("c_created", created),
            ("c_modified", self.between(created, self.anchor)),
            ("c_validNotBefore", created),
        ):
            entity.set_all(key, value.isoformat())

    def add_past_version(self, entity: Entity, change: Callable[[dict[str, Any]], None]) -> None:
        """Let the entity have changed once, at a moment after c_created.

        ``change`` receives the fields of one namespace of the *earlier*
        version and turns them into what they were before the change. The
        earlier version is valid [c_created, change), the current one
        [change, infinity); c_modified of each is when it came about.
        """
        base = entity.fields[entity.type.namespaces[0]]
        created = datetime.fromisoformat(base["c_created"])
        changed = self.between(created, self.anchor).isoformat()
        earlier = copy.deepcopy(entity.fields)
        for fields in earlier.values():
            change(fields)
            fields["c_modified"] = fields["c_created"]
            fields["c_validNotAfter"] = changed
        entity.earlier = earlier
        # every namespace, domain contexts included: the versions must not overlap
        for namespace in entity.namespaces:
            entity.set(namespace, "c_modified", changed)
            entity.set(namespace, "c_validNotBefore", changed)

    def day(self, days_back: int) -> str:
        moment: date = (self.anchor - timedelta(days=self.rnd.randint(0, days_back))).date()
        return moment.isoformat()

    def pick(self, items: list[Any]) -> Any:
        return self.rnd.choice(items)

    # -- building ---------------------------------------------------------

    def create(self, type_name: str, count: int) -> list[Entity]:
        etype = self.profile.types[type_name]
        created = []
        for _ in range(count):
            entity = Entity(self.new_id(etype), etype)
            self.profile.make(self, etype, entity)
            created.append(entity)
        self.entities.extend(created)
        return created

    def link(
        self,
        source: Entity,
        predicate: str,
        target: Entity,
        inverse: str | None = None,
        many: bool = True,
        inverse_many: bool = True,
    ) -> None:
        """Link source -> target (and target -> source with ``inverse``).

        Links are written into the entity's own aspect namespace.
        """
        _put(source, source.type.name, predicate, target.ref(), many)
        if inverse:
            _put(target, target.type.name, inverse, source.ref(), inverse_many)

    def documents(self) -> list[dict[str, Any]]:
        """All documents; an earlier version comes before the current one."""
        docs = []
        for entity in self.entities:
            versions = [entity.earlier, entity.fields] if entity.earlier else [entity.fields]
            for fields in versions:
                for namespace in entity.namespaces:
                    doc = {
                        "@context": self.profile.context(namespace, self.settings),
                        "@id": entity.id,
                    }
                    doc.update(fields.get(namespace, {}))
                    docs.append(doc)
        return docs


def _put(entity: Entity, namespace: str, key: str, value: Any, many: bool) -> None:
    if many:
        entity.add(namespace, key, value)
    else:
        entity.set(namespace, key, value)


def register_profile(profile: Profile) -> Profile:
    from . import profiles

    return profiles.register(profile)


def generate(
    name: str, ctx: Any, seed: int | None = None, counts: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    from . import profiles

    profile = profiles.get(name)
    ctx.settings.require(*profile.requires)
    wanted = {t.name: t.default for t in profile.types.values()}
    for key, value in (counts or {}).items():
        if key not in profile.types:
            valid = ", ".join(profile.types)
            raise UsageError(f"profile '{name}' has no entity type '{key}' (valid: {valid})")
        try:
            wanted[key] = int(value)
        except (TypeError, ValueError):
            raise UsageError(f"{key}={value}: expected a whole number") from None
        if wanted[key] < 0:
            raise UsageError(f"{key}={value}: must not be negative")
    graph = Graph(profile, ctx.settings, seed)
    profile.populate(graph, wanted)
    docs = graph.documents()
    ctx.log.info(
        "profile %s: %d entities, %d documents", name, len(graph.entities), len(docs)
    )
    return docs


__all__ = ["Entity", "EntityType", "Graph", "Profile", "generate", "register_profile"]
