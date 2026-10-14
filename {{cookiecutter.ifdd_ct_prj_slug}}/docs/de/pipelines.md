(ifdd-ct-pipelines)=
# Pipelines

## Schritte und Datensätze

Eine Kette ist eine Liste von Schritten; zwischen ihnen fließt eine **Liste
von Datensätzen** (JSON-Objekte). Drei Regeln halten Ketten kurz:

- Ist der erste Schritt keine *Quelle* und kommen Daten über eine Pipe, wird
  zuerst die Standardeingabe gelesen: `cat docs.json | ifdd-ct head:count=3`.
- Ist der letzte Schritt keine *Senke*, werden die Datensätze als JSON auf
  die Standardausgabe geschrieben: `ifdd-ct faker:product=1 | jq length`.
- Logs gehen nur auf die Standardfehlerausgabe.

Die Syntax der Schritte und die eingebauten Plugins stehen in
{ref}`ifdd-ct-reference`.

Beispiel, ein Produkt als JSON-LD, nichts wird geschrieben:

```bash
./adm_02_run.sh faker:profile=energy-grid,seed=42,product=1,function=0,location=0,organisation=0 head:count=2 stdout
```

Es gibt das Basis- und das Produktdokument eines Produkts aus. Die anderen
Entitätstypen stehen auf 0, weil das Profil Vorgabe-Anzahlen für sie hat,
und `head:count=2` ist nötig, weil `energy-grid` je Produkt drei Teile
erzeugt; das Produktdokument verweist mit `hasPart` auf sie.

## Pipeline-Dateien

Dieselben Schritte als YAML, versioniert neben den Daten in
`data/pipelines/`:

```yaml
steps:
  - faker: {profile: energy-grid, seed: 42, product: 20}
  - put: {dry_run: true}
  - out/generated.json
```

Ein Schritt ist ein String in Kommandozeilen-Syntax oder eine Abbildung mit
einem Schlüssel `plugin: {parameters}`. Relative Pfade beginnen im
Arbeitsverzeichnis (`/data`). Ausführen mit
`./adm_02_run.sh -f pipelines/<file>.yaml`.

## Dokumente gegen ihren Kontext prüfen

Die JSON-LD-Expansion verwirft stillschweigend jeden Term, den der
`@context` nicht definiert; ein Tippfehler wie `nmae` für `name` ginge
verloren. `check` meldet solche Terme, bevor etwas gesendet wird, und reicht
die Datensätze unverändert weiter:

```bash
./adm_02_run.sh examples/json-ld check put              # warnen, dann trotzdem laden
./adm_02_run.sh examples/json-ld check:fail=true put    # vor dem Laden stoppen
```

Ebenfalls gemeldet: ein fehlender `@context`, ein Kontext, der sich nicht
laden lässt, ungültiges JSON-LD. In einer Pipeline-Datei:
`- check: {fail: true}`.

Grenzen: Nutzt ein Kontext `@vocab`, gilt jeder Term als definiert, und
nichts wird gemeldet. Werte werden nicht gegen ihren erklärten Typ geprüft,
Pflichtfelder und Kardinalitäten auch nicht; dafür braucht es SHACL, das
geplant ist.

## Ins Backend schreiben

`put`, `patch` und `post` nehmen schlichte JSON-LD-Dokumente (mit `@id` und
einer einzigen `@context`-URL) und senden die Hülle, die das Backend
erwartet:

```json
{"id": "<@id>", "context": "<@context>", "aspect": "<aspect>", "json": {"...": "..."}}
```

Der Aspekt kommt aus `aspect=...`, aus einer von `node` erzeugten Hülle, aus
`IFDD_CT_ASPECTS` (Pfadsegment von `@id`, `/products/...` -> `product`) oder
aus einem Feld `aspect` im Dokument, in dieser Reihenfolge. Die Ziel-URL ist
`IFDD_CT_BE_URL` plus der Pfad von `@id`. Das Backend legt Knoten mit
`PUT /{segment}/{id}` an (anlegen oder ersetzen, mit Historie) und hat kein
`POST /nodes/`; `post` bleibt für Backends, die es anbieten.

## Faker-Profile

`faker` ist generisch; ein *Profil* beschreibt eine Domäne. Gleicher Seed,
gleiche Daten, einschließlich IDs und Zeitstempeln.

| Profil | Typen (Vorgaben) | Hinweise |
|---|---|---|
| `energy-grid` | product=10, function=5, location=3, organisation=3 | ein `base`- und ein Aspekt-Dokument je Entität; jedes Produkt und jeder Ort bekommt 3 Teile; Leistungsschalter bekommen zusätzlich zwei Domain-Dokumente |
| `datacenter` | room=2, rack=6, pdu=12, server=24 | nur Dokumentationsbeispiel: Inline-`@context`, keine Schemas, nicht ins Backend ladbar |

Jede `energy-grid`-Entität trägt die Quellzeiten der Schemas: `c_created`
(innerhalb eines Jahres vor dem Ankerzeitpunkt), `c_modified` und
`c_validNotBefore` (= `c_created`). Ein Zehntel der Entitäten hat sich
einmal geändert: Sie kommen zuerst mit einer früheren Fassung, die dort
endet, wo die aktuelle beginnt. Das Backend behält beide; die frühere liest
`get:id=...,at=<ihr c_validNotBefore>`.

Jedes Produkt der Art „Circuit Breaker“ bekommt zusätzlich ein Dokument in
jedem Beispiel-Domain-Kontext des Schema-Dienstes,
`breaker.grid.example.ifdd.de` und `maintenance.ops.example.ifdd.de`.
Bemessungsspannung und -strom sind QUDT-Größenwerte, deren Einheit eine IRI
unter `{{ cookiecutter.ifdd_unit_url }}` ist. Das Backend gibt
Domain-Dokumente nur an Clients mit passendem Kontextmuster;
`{{ cookiecutter.ifdd_keycloak_ct_client_id }}` hat im Realm des
Keycloak-Templates das Muster der Wurzel.

Ein privates oder lokales Modul kann mit
`ifdd.ct.faker.register_profile(Profile(...))` ein Profil ergänzen;
`profiles/datacenter.py` im Quelltext ist das kleinste vollständige
Beispiel.

### Testdaten ins Backend laden

```bash
./adm_01_build.sh                                       # einmal und nach Updates
./adm_02_run.sh -f pipelines/generate-energy-grid.yaml
```

Die Pipeline erzeugt das Energienetz mit festem Seed, prüft jedes Dokument
gegen seinen `@context` vom Schema-Dienst (`check` mit `fail: true`: Nichts
wird geschrieben, wenn dort ein Term undefiniert ist) und lädt die Dokumente
mit `put`. Dieselben Daten noch einmal zu laden ändert nichts.

## Plugins schreiben

Ein Plugin ist eine Funktion, die die Datensätze und einen Kontext bekommt
und die neuen Datensätze zurückgibt. Parameter kommen aus ihrer Signatur;
Annotationen legen die Typen fest:

```python
from typing import Annotated

from ifdd.ct import CtError, plugin

@plugin
def only_type(
    records, ctx,
    obj_type: Annotated[str, "value of objType to keep"],
    limit: Annotated[int, "keep at most this many; 0: all"] = 0,
):
    """Keep documents with objType == OBJ_TYPE (at most LIMIT, 0 = all)."""
    kept = [r for r in records if r.get("objType") == obj_type]
    return kept[:limit] if limit else kept
```

Das Plugin dokumentiert sich selbst: Die erste Zeile des Docstrings ist die
Zusammenfassung in `--list`, der Rest wird so gezeigt, wie er geschrieben
ist. `Annotated[type, "help"]` gibt einem Parameter einen Hilfetext; der
Typ wirkt wie ohne. Eine an das Plugin gehängte Funktion `describe_extra`
(`only_type.describe_extra = ...`) ergänzt erzeugten Text, wie bei den
Faker-Profilen. `--describe` und `--markdown` zeigen alles davon.

`@plugin(source=True)` kennzeichnet einen Schritt, der Daten erzeugt (vor ihm
wird die Standardeingabe nicht gelesen), `@plugin(sink=True)` einen, der sie
verbraucht (nach ihm wird nichts ausgegeben). Für eine saubere Fehlermeldung
`CtError` auslösen. Der Kontext bietet `ctx.settings` (Konfiguration),
`ctx.log` (Logger, Standardfehlerausgabe), `ctx.http` (Requests mit Timeout,
CA-Bundle und Token) und `ctx.shared` (ein Dict für den Lauf).

Plugins dieser Instanz gehören nach `private/` (ins Image gebaut),
Experimente nach `plugins/` (eingebunden, kein Build nötig).
`plugins/example_stamp.py` ist ein funktionierendes Beispiel. Ein Paket
(Verzeichnis mit `__init__.py`) geht auch; darin relative Importe nutzen.

## Umstieg vom früheren CT

Plugins bekommen jetzt `(records, ctx, **params)` statt
`(call_params, runtime_infos)` und `trans()`. Die eingebauten Plugins haben
kurze Namen (`put`, `head`, `faker`) statt Pfaden mit Punkten, Dateien sind
eigene Schritte, und das Laden braucht keinen Umwandlungsschritt:
`ifdd-ct examples/json-ld put`. Der Faker aus `ifdd-de/tools-fakedata` ist
durch `faker` ersetzt.
