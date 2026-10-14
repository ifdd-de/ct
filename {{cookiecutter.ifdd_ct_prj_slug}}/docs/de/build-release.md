(ifdd-ct-build-release)=
# Bauen und Freigeben

## Image

Ein Image enthält die Kommandozeile, die eingebauten Plugins, die
Bibliotheken für geplante Plugins und die Plugins aus `private/`.
`Dockerfile` baut in zwei Stufen aus `python:3.14-slim` (`PYTHON_IMAGE`): Die
erste installiert `requirements.txt` und das Paket, die zweite kopiert das
Ergebnis und `private/` und läuft als unprivilegierter Benutzer (UID 10001;
compose überschreibt ihn mit `IFDD_CT_UID`/`IFDD_CT_GID`).

```bash
./adm_01_build.sh
```

Das Skript baut mit `--pull` und taggt
`{{ cookiecutter.ifdd_registry_url }}/{{ cookiecutter.ifdd_ct_prj_slug }}:{{ cookiecutter.ifdd_ct_version }}`,
das Image, das die Produktions-Compose-Datei startet. Für wiederholbare
Builds das Basis-Image per Digest festlegen
(`PYTHON_IMAGE=python:3.14-slim@sha256:...`). Nach jeder Änderung an `src/`,
`private/` oder `requirements.txt` neu bauen; `plugins/` wird eingebunden und
braucht keinen Build.

## Abhängigkeiten

`requirements.txt` legt jede Abhängigkeit mit Hashes fest, aufgelöst für
Python 3.14 auf Linux x86_64 (das Image); sie lässt sich auch unter Python
3.13 installieren, der kleinsten Version, die das Paket annimmt. Nach einer Änderung der Abhängigkeiten in
`pyproject.toml` mit dem Befehl aus ihrem Kopf neu erzeugen
(`uv pip compile ...`).

## Versionen

| Wert | Hier | Quelle |
|---|---|---|
| Version der Instanz | `{{ cookiecutter.ifdd_ct_version }}` | Template-Variable `ifdd_ct_version`; Paketversion, Image-Tag, `ifdd-ct --version` |

Das Schema ist `YY.MM.N`.

## Tests

```bash
pytest                      # offline; scheitert unter 95 % Abdeckung
```

Die Tests sind nach Thema geordnet: eine Datei je eingebautem Plugin unter
`tests/plugins/`, das Kernverhalten unter `tests/core/`, die Kommandozeile
unter `tests/cli/`, echtes HTTP gegen ein lokales Fake-Backend unter
`tests/e2e/`. Tests für die Plugins dieser Instanz gehören nach
`tests/private/` (auf der Skip-Liste). Siehe `tests/README.md`.

`tests/integration/` läuft gegen ein echtes, laufendes Backend und
**schreibt Testdaten hinein**. Es wird übersprungen, solange
`IFDD_IT_BE_URL` nicht gesetzt ist; die Variablen stehen in
`tests/integration/conftest.py`. Gegen diesen Knoten, hinter dem Proxy:

```bash
IFDD_IT_BE_URL={{ cookiecutter.ifdd_be_url }} IFDD_IT_SCHEMA_URL={{ cookiecutter.ifdd_schema_url }} \
IFDD_IT_TOKEN_URL={{ cookiecutter.ifdd_oidc_token_url }} \
IFDD_IT_CLIENT_ID={{ cookiecutter.ifdd_keycloak_ct_client_id }} IFDD_IT_CLIENT_SECRET=<secret> \
IFDD_IT_CA_BUNDLE=certs/ca.crt pytest --no-cov tests/integration
```

## CI der Instanz

`.github/workflows/ci.yml` läuft bei jedem Push und Pull Request:

- **Tests** mit Python 3.14 und den festgelegten, per Hash geprüften
  Abhängigkeiten;
- **Image und Compose-Dateien**: baut das Image, listet die Plugins, startet
  den Faker ohne jeden Dienst, prüft, dass `check` standardmäßig warnt und mit
  `fail=true` scheitert, validiert beide Compose-Dateien;
- **Template drift**: `cruft check` und `cruft diff`, nur informativ.

## Freigabe

`.github/workflows/release.yml` baut das Image und schiebt es nach
`ghcr.io/<owner>/<repository>`, wenn ein Tag `v*` gepusht wird. Der lokale
Image-Name oben (`{{ cookiecutter.ifdd_registry_url }}/...`) ist davon
unabhängig.

```{note}
Hier nicht getestet: der Image-Build und der Release-Workflow. Die
Template-CI baut das Image; die Honesty notes im README führen auf, was
gelaufen ist.
```
