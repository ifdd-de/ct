"""Data centre: rooms, racks, PDUs and servers.

A deliberately small documentation example of a second domain. It shows how
a profile is built; it is not meant to be loaded into ifdd-be: there are no
schemas for it and its @context is an inline object with a placeholder
vocabulary, which the backend (one context URL per node) does not accept.

Structure: racks are spread over the rooms, every PDU sits in a rack, every
server sits in a rack and is fed by the PDUs of that rack (A/B feed).
"""

from __future__ import annotations

from .. import Entity, EntityType, Graph, Profile, register_profile

VOCAB = "https://example.org/ifdd/datacenter#"

TYPES = {
    "room": EntityType("room", "rooms", 2, ("room",)),
    "rack": EntityType("rack", "racks", 6, ("rack",)),
    "pdu": EntityType("pdu", "pdus", 12, ("pdu",)),
    "server": EntityType("server", "servers", 24, ("server",)),
}


def context(namespace: str, settings) -> dict:
    return {"@vocab": VOCAB}


def make(g: Graph, etype: EntityType, e: Entity) -> None:
    f, r, ns = g.fake, g.rnd, etype.name
    e.set(ns, "@type", etype.name.capitalize())
    if ns == "room":
        e.set(ns, "name", f"Room {f.random_uppercase_letter()}{r.randint(1, 9)}")
        e.set(ns, "floor", r.randint(-1, 3))
        e.set(ns, "area_m2", r.randint(80, 600))
        e.set(ns, "cooling", g.pick(["CRAC", "In-Row", "Liquid"]))
    elif ns == "rack":
        e.set(ns, "name", f"R{r.randint(1, 40):02d}-{f.random_uppercase_letter()}")
        e.set(ns, "height_u", g.pick([42, 47]))
        e.set(ns, "max_power_kw", g.pick([8, 12, 20]))
    elif ns == "pdu":
        e.set(ns, "name", f"PDU-{f.bothify('??##').upper()}")
        e.set(ns, "phases", g.pick([1, 3]))
        e.set(ns, "rated_current_a", g.pick([16, 32, 63]))
        e.set(ns, "outlets", g.pick([12, 24, 42]))
    elif ns == "server":  # pragma: no branch - every namespace of the profile is handled
        e.set(ns, "hostname", f"{f.word()}-{r.randint(1, 999):03d}")
        e.set(ns, "vendor", g.pick(["Vendor A", "Vendor B", "Vendor C"]))
        e.set(ns, "height_u", g.pick([1, 2]))
        e.set(ns, "cpu_cores", g.pick([16, 32, 64, 128]))
        e.set(ns, "ram_gb", g.pick([128, 256, 512, 1024]))
        e.set(ns, "serial", f.bothify("SN-########"))


def populate(g: Graph, counts: dict[str, int]) -> None:
    rooms = g.create("room", counts["room"])
    racks = g.create("rack", counts["rack"])
    pdus = g.create("pdu", counts["pdu"])
    servers = g.create("server", counts["server"])
    if rooms:
        for i, rack in enumerate(racks):
            g.link(rooms[i % len(rooms)], "hasPart", rack, inverse="isPartOf", inverse_many=False)
    if not racks:
        return
    feeds: dict[str, list[Entity]] = {rack.id: [] for rack in racks}
    for i, pdu in enumerate(pdus):
        rack = racks[i % len(racks)]
        g.link(rack, "hasPart", pdu, inverse="isPartOf", inverse_many=False)
        feeds[rack.id].append(pdu)
    for server in servers:
        rack = g.pick(racks)
        g.link(rack, "hasPart", server, inverse="isPartOf", inverse_many=False)
        for pdu in feeds[rack.id]:
            g.link(pdu, "feeds", server, inverse="fedBy")


register_profile(Profile(
    name="datacenter",
    description="documentation example: rooms, racks, PDUs, servers (not loadable into ifdd-be)",
    types=TYPES,
    make=make,
    populate=populate,
    context=context,
))
