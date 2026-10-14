"""Energy grid: products, functions, locations and organisations.

Matches the aspects and schemas of ifdd-be (IFDD_CT_ASPECTS) and the
schema service: every entity is written as a ``base`` document and an
aspect document, with contexts IFDD_CT_SCHEMA_URL/base.jsonld and
IFDD_CT_SCHEMA_URL/<aspect>.jsonld.

Structure: every product has 3 part products and every location 3 part
locations, so product=10 gives 40 products in total.

Times: every entity carries c_created, c_modified and c_validNotBefore
(created within the last year before the anchor). CHANGED_SHARE of the
entities (rounded) changed once since: they get an earlier version with another
description, valid until the change (see Graph.add_past_version).

Domain contexts: every product of the kind "Circuit Breaker" also gets a
document in each of the two example domain contexts of the schema service,
BREAKER and MAINTENANCE (simplified; values from other sources, so with
their own objName, objType and origin). Rated voltage and current are QUDT
quantity values whose units are IRIs of the unit service
(IFDD_CT_UNIT_URL/unit/<name>). ifdd-be gives these documents only to
clients with a matching context pattern.
"""

from __future__ import annotations

import string
from datetime import date

from .. import Entity, EntityType, Graph, Profile, register_profile

ORIGIN = "ifdd-ct/faker/energy-grid"
BREAKER = "breaker.grid.example.ifdd.de"
MAINTENANCE = "maintenance.ops.example.ifdd.de"
PARTS = 3
SCOPES = ["Local", "Regional", "National", "International"]
CHANGED_SHARE = 0.1

TYPES = {
    "product": EntityType("product", "products", 10, ("base", "product")),
    "function": EntityType("function", "functions", 5, ("base", "function")),
    "location": EntityType("location", "locations", 3, ("base", "location")),
    "organisation": EntityType("organisation", "organisations", 3, ("base", "organisation")),
}


def context(namespace: str, settings) -> str:
    return f"{settings.schema_url}/{namespace}.jsonld"


def _common(g: Graph, e: Entity, name: str, description: str, obj_type: str) -> None:
    for key, value in (
        ("objName", name),
        ("description", description),
        ("objType", obj_type),
        ("objScope", g.pick(SCOPES)),
        ("origin", ORIGIN),
    ):
        e.set_all(key, value)
    g.set_times(e)


def _quantity(g: Graph, value: int, unit: str) -> dict:
    """A QUDT quantity value; the unit is an IRI of the unit service."""
    return {
        "type": "qudt:QuantityValue",
        "qudt:numericValue": value,
        "qudt:unit": {"@id": f"{g.settings.unit_url}/unit/{unit}"},
    }


def _breaker_domains(g: Graph, e: Entity, serial: str, manufacturer: str) -> None:
    """The two example domain documents of a circuit breaker."""
    r = g.rnd
    bay = f"Q{r.randint(1, 99)}"
    built = r.randint(1975, 2024)
    e.add_namespace(BREAKER, {
        "objName": bay,
        "objType": "Circuit breaker",
        "objScope": g.pick(SCOPES),
        "origin": f"{ORIGIN}/breaker-register",
        "serialNumber": serial,
        "manufacturer": manufacturer,
        "yearOfManufacture": str(built),
        "ratedVoltage": _quantity(g, g.pick([110, 220, 380]), "KiloV"),
        "ratedCurrent": _quantity(g, g.pick([2000, 3150, 4000]), "A"),
        "operatingMechanism": g.pick(["spring", "hydraulic", "pneumatic"]),
    })
    last = g.day(700)
    years = g.pick([2, 4, 6])
    e.add_namespace(MAINTENANCE, {
        "objName": f"{bay} maintenance",
        "objType": "Maintenance record",
        "objScope": g.pick(SCOPES),
        "origin": f"{ORIGIN}/maintenance",
        "maintenanceInterval": f"P{years}Y",
        "lastInspection": last,
        "nextInspection": _years_later(last, years),
        "condition": g.pick(["good", "fair", "poor"]),
    })


def _years_later(day: str, years: int) -> str:
    """The same day ``years`` later; 29 February becomes 28 February."""
    start = date.fromisoformat(day)
    try:
        return start.replace(year=start.year + years).isoformat()
    except ValueError:
        return start.replace(year=start.year + years, day=28).isoformat()


def _props(e: Entity, *pairs: tuple[str, str]) -> None:
    e.set(e.type.name, "properties", [
        {"prop_id": key, "prop_val": value, "prop_validity": "valid"} for key, value in pairs
    ])


def make_product(g: Graph, e: Entity) -> None:
    f, r = g.fake, g.rnd
    kind = g.pick(["Generator", "Transformer", "Switch", "Cable", "Circuit Breaker", "Capacitor Bank"])
    name = g.pick(["Power", "Grid", "Volt", "Amp", "Mega", "Ultra"]) + kind.replace(" ", "") + \
        g.pick(["Master", "Pro", "Max", "Plus", "Advanced", "Premium"])
    _common(g, e, name, f.catch_phrase(), kind)
    manufacturer, serial = f.company(), str(f.uuid4())
    e.set("product", "manufacturer", manufacturer)
    e.set("product", "vendor", f.company())
    e.set("product", "serial_number", serial)
    e.set("product", "equipment_numbers", [f.ean13() for _ in range(3)])
    specific = {
        "Generator": [("Power Output", f"{r.randint(100, 1000)} MW"),
                      ("Fuel Type", g.pick(["Gas", "Hydro", "Wind", "Solar", "Biomass"]))],
        "Transformer": [("Power Rating", f"{r.randint(10, 1000)} MVA"),
                        ("Voltage Ratio", f"{g.pick([380, 220, 110])}/{g.pick([110, 30, 20])} kV")],
        "Switch": [("Voltage Rating", f"{g.pick([110, 220, 380])} kV"),
                   ("Current Rating", f"{r.randint(1000, 5000)} A")],
        "Circuit Breaker": [("Voltage Rating", f"{g.pick([110, 220, 380])} kV"),
                            ("Current Rating", f"{r.randint(1000, 5000)} A")],
        "Cable": [("Length", f"{r.randint(1, 100)} km"),
                  ("Current Capacity", f"{r.randint(500, 3000)} A")],
        "Capacitor Bank": [("Reactive Power", f"{r.randint(10, 200)} MVAr"),
                           ("Voltage Rating", f"{r.randint(11, 33)} kV")],
    }[kind]
    _props(e, *specific,
           ("Efficiency", f"{r.uniform(0.85, 0.99):.2f}"),
           ("Weight", f"{r.randint(1000, 100000)} kg"),
           ("Lifespan", f"{r.randint(10, 50)} years"),
           ("Maintenance Interval", f"{r.randint(1, 24)} months"),
           ("Installation Date", g.day(3650)))
    if kind == "Circuit Breaker":
        _breaker_domains(g, e, serial, manufacturer)


def make_function(g: Graph, e: Entity) -> None:
    f, r = g.fake, g.rnd
    kind = g.pick(["Power Generation", "Power Transmission", "Power Distribution",
                   "Grid Control", "Load Balancing", "Fault Protection"])
    _common(g, e, f"{kind} {f.bs()}", f.catch_phrase(), kind)
    e.set("function", "risk_class", g.pick(["Low", "Medium", "High", "Critical"]))
    if kind in ("Grid Control", "Load Balancing"):
        specific = ("Response Time", f"{r.uniform(0.01, 1.0):.2f} s")
    elif kind == "Fault Protection":
        specific = ("Trigger Current", f"{r.randint(1000, 10000)} A")
    else:
        specific = ("Capacity", f"{r.randint(100, 10000)} MW")
    _props(e, specific,
           ("Reliability", f"{r.uniform(0.9, 0.9999):.4f}"),
           ("Redundancy Level", g.pick(["N", "N+1", "2N"])),
           ("Automation Level", g.pick(["Manual", "Semi-Automated", "Fully Automated"])),
           ("Last Inspection Date", g.day(365)))


def make_location(g: Graph, e: Entity) -> None:
    f, r = g.fake, g.rnd
    kind = g.pick(["Power Plant", "Substation", "Control Center", "Distribution Center"])
    _common(g, e, f"{f.city()} {kind}", f.address().replace("\n", ", "), kind)
    _props(e,
           ("Latitude", str(f.latitude())),
           ("Longitude", str(f.longitude())),
           ("Area", f"{r.randint(1000, 1000000)} m²"),
           ("Elevation", f"{r.randint(0, 3000)} m"),
           ("Grid Connection Capacity", f"{r.randint(100, 10000)} MW"),
           ("Last Upgrade Date", g.day(1825)))


def make_organisation(g: Graph, e: Entity) -> None:
    f, r = g.fake, g.rnd
    kind = g.pick(["Utility Company", "Power Generator", "Grid Operator", "Energy Trader",
                   "Regulatory Body"])
    _common(g, e, f"{f.company()} {kind}", f.catch_phrase(), kind)
    pairs = [("Employees", str(r.randint(50, 100000))),
             ("Founded", f.year()),
             ("Headquarters", f.city())]
    if kind == "Grid Operator":
        pairs += [("Transmission Lines", f"{r.randint(1000, 50000)} km")]
    elif kind == "Energy Trader":
        pairs += [("Trading Volume", f"{r.randint(1, 1000)} TWh/year")]
    elif kind == "Regulatory Body":
        pairs += [("Jurisdiction", g.pick(["State", "Federal", "International"]))]
    else:
        pairs += [("Generation Capacity", f"{r.randint(1000, 50000)} MW"),
                  ("Stock Symbol", "".join(r.choices(string.ascii_uppercase, k=4)))]
    _props(e, *pairs)


MAKERS = {
    "product": make_product,
    "function": make_function,
    "location": make_location,
    "organisation": make_organisation,
}


def make(g: Graph, etype: EntityType, e: Entity) -> None:
    MAKERS[etype.name](g, e)


def populate(g: Graph, counts: dict[str, int]) -> None:
    products = g.create("product", counts["product"])
    product_parts = g.create("product", counts["product"] * PARTS)
    functions = g.create("function", counts["function"])
    locations = g.create("location", counts["location"])
    location_parts = g.create("location", counts["location"] * PARTS)
    organisations = g.create("organisation", counts["organisation"])

    # every whole gets its own, disjoint set of parts
    for wholes, parts in ((locations, location_parts), (products, product_parts)):
        for i, whole in enumerate(wholes):
            for part in parts[i * PARTS:(i + 1) * PARTS]:
                g.link(whole, "hasPart", part, inverse="isPartOf", inverse_many=False)

    all_locations = locations + location_parts
    for product in products:
        if functions:
            g.link(product, "providesFunction", g.pick(functions), inverse="implementedBy")
            g.link(product, "usesFunction", g.pick(functions), inverse="usedBy")
        if all_locations:
            g.link(product, "containedIn", g.pick(all_locations),
                   inverse="containsProduct", many=False)
        if organisations:
            g.link(product, "responsibleOrganisation", g.pick(organisations),
                   inverse="productResponsibility", many=False)
    for function in functions:
        if organisations:
            g.link(function, "responsibleOrganisation", g.pick(organisations),
                   inverse="functionalResponsibility", many=False)
    for organisation in organisations:
        others = [o for o in organisations if o is not organisation]
        if others:
            g.link(organisation, "roleDeliversTo", g.pick(others),
                   inverse="roleClientOf", many=False)

    _change_some(g)


def _change_some(g: Graph) -> None:
    """Give CHANGED_SHARE of the entities (rounded) an earlier description."""
    chosen = g.rnd.sample(g.entities, round(len(g.entities) * CHANGED_SHARE))
    for entity in sorted(chosen, key=g.entities.index):
        earlier_description = g.fake.catch_phrase()

        def change(fields, text=earlier_description):
            if "description" in fields:  # the domain contexts have none
                fields["description"] = text

        g.add_past_version(entity, change)


register_profile(Profile(
    name="energy-grid",
    description="transmission grid assets as stored by ifdd-be (base + aspect documents)",
    types=TYPES,
    make=make,
    populate=populate,
    context=context,
    requires=("be_url", "schema_url", "unit_url"),
))
