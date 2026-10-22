(ifdd-ct-reference)=
# Referenz

Die Variablen des Templates und ihre Werte in dieser Instanz stehen in
{ref}`ifdd-instances-ct`. Diese Seite führt auf, was keine Template-Variable
ist.

## Kommandozeile

```text
ifdd-ct [-v|-vv|-q] STEP [STEP ...]
ifdd-ct [-v|-vv|-q] -f PIPELINE.yaml
ifdd-ct --list | --describe PLUGIN | --markdown | --version
```

| Schritt | Bedeutung |
|---|---|
| `name` | ein Plugin ausführen |
| `name:key=value,key2=value2` | mit Parametern; ein `,` in einem Wert wird `%2C` geschrieben |
| `path/file.json` (`.jsonld`, `.yaml`) | erster Schritt: lesen; letzter Schritt: schreiben |
| `path/directory` | erster Schritt: jede `.json`/`.jsonld`/`.yaml` darunter lesen |

Exit-Codes: `0` in Ordnung, `1` ein Schritt scheiterte, `2` falsche
Kommandozeile oder Pipeline-Datei.

## Eingebaute Plugins

| Plugin | Rolle | Zweck |
|---|---|---|
| `faker` | Quelle | Dokumente aus einem Profil erzeugen (`profile=`, `seed=`, Anzahlen je Typ) |
| `get` | Quelle | Dokumente aus dem Backend holen (`segment=products` oder `id=...`; `at=` ein Zeitpunkt der Fachzeit, Vorgabe jetzt) |
| `put` | Senke | Knoten anlegen oder ersetzen: PUT an Backend + Pfad von `@id` |
| `patch` | Senke | in bestehende Knoten mischen: PATCH an Backend + Pfad von `@id` |
| `post` | Senke | POST an `/nodes/` (besser `put`) |
| `node` | | Dokumente in die Hülle des Backends packen, um zu sehen, was gesendet würde |
| `check` | | Terme melden, die der `@context` nicht definiert (warnt; `fail=true` stoppt) |
| `expand`, `compact` | | JSON-LD-Expansion und -Kompaktierung |
| `head`, `tail` | | die ersten/letzten `count` Datensätze behalten |
| `where` | | Datensätze behalten, deren `key` gleich `value` ist |
| `count` | | die Zahl der Datensätze auf die Standardfehlerausgabe schreiben |
| `stdout` | Senke | die Datensätze zwischen zwei Schritten ausgeben |

`ifdd-ct --describe NAME` zeigt Parameter, Typen, Vorgaben und
Hilfetexte; `ifdd-ct --markdown` alle Plugins auf einmal (unten). `put`,
`patch` und `post` nehmen `dry_run=true` an.

## Plugin-Referenz als Markdown

`ifdd-ct --markdown` schreibt eine MyST-Markdown-Seite auf die
Standardausgabe: den `--help`-Text und für jedes gefundene Plugin Herkunft
und Modul, Rolle, die Namen, unter denen es erreichbar ist, den Aufruf,
seinen Docstring, eine Tabelle seiner Parameter (Typ, Vorgabe, Hilfetext)
und erzeugte Details wie die Faker-Profile. Module, die nicht geladen werden
konnten, stehen am Ende.

```bash
./adm_02_run.sh --markdown > plugins.md            # built-in, private and local plugins
ifdd-ct --markdown > plugins.md                    # in a shell, see the setup chapter
IFDD_CT_PLUGIN_PATH= ifdd-ct --markdown > plugins.md   # without the local plugins
```

Die Seite hat das Label `ifdd-ct-plugins`, jedes Plugin das Label
`ifdd-ct-plugin-<origin>-<name>`, etwa `ifdd-ct-plugin-builtin-faker`. In
das Dokumentationsprojekt kopiert und in einen Toctree aufgenommen, ist sie
mit `{ref}` verlinkbar. Sie wird erzeugt, ist nur englisch und gehört nicht
ins Repository: nach jeder Änderung an einem Plugin neu erzeugen. Ihr Text
kommt aus den Plugins selbst ({ref}`ifdd-ct-pipelines`, „Plugins
schreiben“).

```{note}
Nicht getestet: `./adm_02_run.sh --markdown` mit Docker. Geprüft: Die Seite
aus einer Shell baut mit Sphinx 9.1.0 und myst-parser 5.1.0 ohne Warnung.
```

## Orte der Plugins

| Verzeichnis | Name | Im Container |
|---|---|---|
| eingebaut | `builtin.<name>` | im Paket |
| `private/` | `private.<name>` | `/opt/ifdd-ct/private`, ins Image gebaut |
| `plugins/` | `local.<name>` | `/plugins`, zur Laufzeit nur lesend eingebunden |

## Umgebung (`.env`)

| Variable | Vorgabe hier | Genutzt von | Bedeutung |
|---|---|---|---|
| `IFDD_CT_LOG_LEVEL` | `{{ cookiecutter.ifdd_ct_log_level|upper }}` | allen | Log-Level ohne `-v`/`-q` |
| `IFDD_CT_BE_URL` | `{{ cookiecutter.ifdd_be_url }}` | Backend, Faker | Basis-URL des Backends; auch die Basis erzeugter `@id`s; Pflicht |
| `IFDD_CT_SCHEMA_URL` | `{{ cookiecutter.ifdd_schema_url }}` | Faker `energy-grid` | Basis der Kontext-URLs |
| `IFDD_CT_UNIT_URL` | `{{ cookiecutter.ifdd_unit_url }}` | Faker `energy-grid` | Basis der Einheiten-IRIs in Größenwerten |
| `IFDD_CT_TYPE_URL` | `{{ cookiecutter.ifdd_type_url }}` | `ts-climate` | Basis der Eigenschafts-IRIs der Beispiel-Samples |
| `IFDD_CT_TS_API_URL` | `{{ cookiecutter.ifdd_ts_api_url }}` | `ts-post` | Zeitreihen-API (ts-api) |
| `IFDD_CT_ASPECTS` | `{{ cookiecutter.ifdd_be_aspects }}` | Backend | JSON: Pfadsegment -> Aspekt |
| `IFDD_CT_OIDC_TOKEN_URL` | `{{ cookiecutter.ifdd_oidc_token_url }}` | Backend | Token-Endpunkt |
| `IFDD_CT_OIDC_CLIENT_ID` | `{{ cookiecutter.ifdd_keycloak_ct_client_id }}` | Backend | Client; leer für ein Backend ohne Authentifizierung |
| `IFDD_CT_OIDC_CLIENT_SECRET` | leer | Backend | Client-Secret, von Hand gesetzt |
| `IFDD_CT_CA_BUNDLE` | `/certs/ca.crt` | jedes HTTP | PEM-Datei mit der internen CA; leer: System-Trust-Store |
| `IFDD_CT_HTTP_TIMEOUT` | `30` | jedes HTTP | Sekunden je Anfrage |
| `IFDD_CT_CONTEXT_DIR` | leer | expand, compact, node | lokale JSON-LD-Kontexte, nach Dateiname |
| `IFDD_CT_UID`, `IFDD_CT_GID` | `1000` | compose | Benutzer und Gruppe, als die der Container läuft |

Im Image gesetzt, nicht in `.env`: `IFDD_CT_PRIVATE_DIR=/opt/ifdd-ct/private`
und `IFDD_CT_PLUGIN_PATH=/plugins` (durch `:` getrennt). In einer Shell
selbst setzen ({ref}`ifdd-ct-setup`).

## Mounts

| Host | Container | |
|---|---|---|
| `data/` | `/data` (Arbeitsverzeichnis) | lesend und schreibend |
| `plugins/` | `/plugins` | nur lesend |
| `certs/` | `/certs` | nur lesend |
| `src/`, `private/` | `/opt/ifdd-ct/src`, `/opt/ifdd-ct/private` | nur lesend, nur in der Entwicklung |
