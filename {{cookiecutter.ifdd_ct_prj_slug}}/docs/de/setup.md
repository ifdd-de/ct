(ifdd-ct-setup)=
# Einrichtung

## Voraussetzungen

| Was | Warum |
|---|---|
| Docker mit Compose | ct läuft als Container |
| das externe Netz `{{ cookiecutter.ifdd_proxy_network }}` und eine laufende Proxy-Instanz | ct erreicht jeden Dienst darüber |
| der Proxy führt die Hosts von Backend, Schema-Dienst und Keycloak in `ifdd_proxy_internal_hosts` | im Container müssen diese Namen zu Traefik führen |
| der Client `{{ cookiecutter.ifdd_keycloak_ct_client_id }}` im Realm und sein Secret | das Keycloak-Template legt den Client an; sein Secret ist `IFDD_KEYCLOAK_CT_CLIENT_SECRET` in der `.env` der Keycloak-Instanz |
| das CA-Zertifikat des Proxys, wenn er eine eigene CA nutzt | `certs/ca.crt` der Proxy-Instanz |

## Instanz anlegen

Üblicherweise legt das Meta-Repository alle Instanzen in einem Zug an
(`.adm_meta_01_all.sh`, Schritt `.adm_01_create_services.sh`): Es ruft
`cruft create` mit der gemeinsamen Variablendatei `.cookiecutter_all.yaml`
auf, kopiert die CA des Proxys nach `certs/` und das Client-Secret in `.env`.

Von Hand, im Verzeichnis der Instanzen:

```bash
cruft create --no-input --config-file .cookiecutter_all.yaml \
  https://github.com/ifdd-de/ct
cp proxy/certs/ca.crt {{ cookiecutter.ifdd_ct_prj_slug }}/certs/
```

`.env`, `certs`, `data`, `plugins`, `private` und `tests/private` gehören der
Instanz; `pyproject.toml` führt sie unter `[tool.cruft]`, daher rühren
Template-Updates sie nie an.

## Konfiguration

Der Post-Generation-Hook schreibt `.env` aus `dotenv.dist`. Alle
Einstellungen sind Umgebungsvariablen, gelesen, wenn ein Schritt sie braucht;
`--list` funktioniert ohne. Die vollständige Liste steht in
{ref}`ifdd-ct-reference`; die Werte aus den Template-Variablen erklärt
{ref}`ifdd-instances-ct`.

Von Hand zu setzen:

| Eintrag | Was |
|---|---|
| `IFDD_CT_OIDC_CLIENT_SECRET` | das Secret von `{{ cookiecutter.ifdd_keycloak_ct_client_id }}`, aus `IFDD_KEYCLOAK_CT_CLIENT_SECRET` der Keycloak-Instanz; das Template lässt es leer |
| `IFDD_CT_CA_BUNDLE` | `/certs/ca.crt` (Vorgabe): nur dieser Datei wird vertraut. Leer: der System-Trust-Store des Images, für öffentlich vertraute Zertifikate |
| `IFDD_CT_UID`, `IFDD_CT_GID` | Ihr Benutzer und Ihre Gruppe (`id -u`, `id -g`), damit nach `data/` geschriebene Dateien Ihnen gehören |

`IFDD_CT_OIDC_CLIENT_ID` nur für ein Backend ohne Authentifizierung leer
lassen.

## Erster Lauf

```bash
./adm_01_build.sh                    # das Image bauen oder aus der Registry holen
./adm_02_run.sh --list               # die Plugins
./adm_02_run.sh examples/json-ld check put:dry_run=true
```

`adm_02_run.sh` ist `docker compose run --rm ct ...` mit der `.env` dieser
Instanz, `./data` (als `/data`, das Arbeitsverzeichnis), `./plugins` (als
`/plugins`) und `./certs` (als `/certs`), im Netz
`{{ cookiecutter.ifdd_proxy_network }}`.
`IFDD_CT_COMPOSE=development ./adm_02_run.sh ...` nutzt die
Entwicklungs-Compose-Datei, die das Image lokal baut und `src/` und
`private/` über die installierten Kopien legt.

## Lokale Entwicklung

```bash
python3 -m venv .venv && . .venv/bin/activate   # Python 3.13 or later
pip install --require-hashes -r requirements.txt
pip install --no-deps -e . && pip install pytest pytest-cov
pytest                      # misst die Abdeckung, scheitert unter 95 %
IFDD_CT_PRIVATE_DIR=./private IFDD_CT_PLUGIN_PATH=./plugins ifdd-ct --list
```

## Lokal in einer Shell ausführen

ct läuft auch ohne Docker aus einer virtuellen Umgebung (Python 3.13 oder
neuer). Drei Dinge, die der Container einrichtet, liegen dann bei Dir:

1. **Konfiguration.** docker compose liest `.env`, eine Shell nicht. Laden
   mit `set -a; . ./.env; set +a`. `IFDD_CT_ASPECTS` steht in einfachen
   Anführungszeichen, damit das JSON dabei heil bleibt; in einer Instanz,
   die vor dieser Änderung erzeugt wurde, die Anführungszeichen von Hand
   setzen: `IFDD_CT_ASPECTS='{"products": "product", ...}'`.
2. **CA-Bundle.** `IFDD_CT_CA_BUNDLE=/certs/ca.crt` ist der Pfad im
   Container. In der Shell auf `certs/ca.crt` der Instanz zeigen lassen;
   sonst bricht jeder Schritt, der einen Dienst aufruft, mit
   `IFDD_CT_CA_BUNDLE: file not found` ab. Leer: der System-Trust-Store.
3. **Plugin-Verzeichnisse.** Die Vorgaben `/opt/ifdd-ct/private` und
   `/plugins` sind Pfade im Image. `IFDD_CT_PRIVATE_DIR` und
   `IFDD_CT_PLUGIN_PATH` auf `private/` und `plugins/` der Instanz setzen;
   ein leeres `IFDD_CT_PLUGIN_PATH` lässt die lokalen Plugins weg.
   `private/` gehört nicht zum installierten Paket.

Schritt für Schritt, im Verzeichnis der Instanz:

```bash
python3 -m venv .venv && . .venv/bin/activate   # Python 3.13 or later
pip install --require-hashes -r requirements.txt
pip install --no-deps .        # or -e . while you change src/
set -a; . ./.env; set +a
export IFDD_CT_CA_BUNDLE=$PWD/certs/ca.crt
export IFDD_CT_PRIVATE_DIR=$PWD/private IFDD_CT_PLUGIN_PATH=$PWD/plugins
ifdd-ct --list
cd data                        # the working directory of the container
ifdd-ct examples/json-ld check put:dry_run=true
```

Die Pfade sind absolut, `ifdd-ct` funktioniert danach aus jedem
Verzeichnis. In einer neuen Shell die Umgebung aktivieren, `.env` laden und
die drei Variablen erneut setzen.

```{note}
Nicht getestet: die Dienste vom Host aus zu erreichen. Die Hostnamen in den
URLs der `.env` (hier `{{ cookiecutter.ifdd_be_url }}`,
`{{ cookiecutter.ifdd_schema_url }}` und die Token-URL) müssen auf dem Host
zum Proxy auflösen, etwa über `/etc/hosts`, und der Proxy muss sie routen.
In einer Shell geprüft: Installation, `--list`, `--describe`, `--markdown`
und `faker`.
```
