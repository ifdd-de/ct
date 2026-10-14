(ifdd-ct-index)=
# {{ cookiecutter.ifdd_ct_prj_name }} (ct)

Die Core Tools eines IFDD-Knotens: Der Befehl `ifdd-ct` verkettet kleine
Plugins über JSON-LD-Datensätzen. Er liest oder erzeugt Dokumente, formt und
prüft sie und lädt sie ins Backend. ct ist ein Job-Container, kein Dienst:
Er startet, führt seine Schritte aus und endet. Dieses Kapitel beschreibt die
Instanz `{{ cookiecutter.ifdd_ct_prj_slug }}`, erzeugt aus dem Template
`ifdd-de/ct`, aus Sicht derer, die sie einrichten, bauen, betreiben und
absichern.

| | |
|---|---|
| Version | `{{ cookiecutter.ifdd_ct_version }}` |
| Image | `{{ cookiecutter.ifdd_registry_url }}/{{ cookiecutter.ifdd_ct_prj_slug }}:{{ cookiecutter.ifdd_ct_version }}` |
| Backend | `{{ cookiecutter.ifdd_be_url }}` |
| Kontexte, Einheiten | `{{ cookiecutter.ifdd_schema_url }}`, `{{ cookiecutter.ifdd_unit_url }}` |
| Token-Endpunkt, Client | `{{ cookiecutter.ifdd_oidc_token_url }}`, `{{ cookiecutter.ifdd_keycloak_ct_client_id }}` |
| Netz | `{{ cookiecutter.ifdd_proxy_network }}` |

## Was die Instanz enthält

Das Python-Paket `ifdd.ct` (`src/`) mit der Kommandozeile, den eingebauten
Plugins und den Faker-Profilen; das `Dockerfile` und zwei Compose-Dateien;
die Skripte `adm_01_build.sh` (Image bauen) und `adm_02_run.sh` (eine Kette
ausführen). Vier Verzeichnisse gehören der Instanz und stehen auf der
cruft-Skip-Liste:

| Verzeichnis | Inhalt |
|---|---|
| `data/` | das Arbeitsverzeichnis im Container: Beispieldokumente, Pipeline-Dateien, Ergebnisse |
| `private/` | Plugins dieser Instanz, ins Image gebaut |
| `plugins/` | lokale Plugins, zur Laufzeit eingebunden |
| `certs/` | das CA-Zertifikat für interne Zertifikate |

## Architektur

```{mermaid}
flowchart LR
  Op[Betreiber] -->|adm_02_run.sh| CT[ct: Job-Container]
  CT -->|liest, schreibt| Data[(data/)]
  CT -->|lädt| Plugins[plugins/]
  CT -->|Client Credentials| Proxy[proxy: Traefik]
  Proxy --> KC[Keycloak]
  Proxy --> BE[be]
  Proxy --> Schema[schema]
```

ct ruft jeden Dienst unter seiner öffentlichen URL über den Proxy auf, aus
dem Netz `{{ cookiecutter.ifdd_proxy_network }}` heraus.

| ct ruft auf | Für |
|---|---|
| Keycloak (`{{ cookiecutter.ifdd_oidc_token_url }}`) | ein Access-Token mit Client Credentials |
| be (`{{ cookiecutter.ifdd_be_url }}`) | Lesen (`get`) und Schreiben (`put`, `patch`, `post`) von Dokumenten |
| schema (`{{ cookiecutter.ifdd_schema_url }}`) | die Kontexte der Dokumente, für `check`, `expand`, `compact` |

Die URLs von unit und type kommen nur in erzeugten Daten und in geplanten
Plugins vor; ct ruft sie heute nicht auf.

## Kapitel

```{toctree}
:maxdepth: 2

setup
build-release
operations
security
troubleshooting
reference
pipelines
```

Die Werte der Variablen dieser Instanz und ihre Beziehungen zu den anderen
Diensten stehen im Kapitel über die Dienst-Instanzen
({ref}`ifdd-instances-ct`).
