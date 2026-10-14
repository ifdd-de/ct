(ifdd-ct-security)=
# Sicherheit

## Der Client

ct meldet sich mit dem OAuth-2.0-Grant Client Credentials als
`{{ cookiecutter.ifdd_keycloak_ct_client_id }}` an. Im Realm des
Keycloak-Templates hat dieser Client die Lese- und die Schreibrolle und das
Kontextmuster der Wurzel: Wer sein Secret hat, kann jedes Dokument des
Knotens schreiben. ct nutzt ein Token bis kurz vor seinem Ablauf und erneuert
es bei einem 401 einmal.

- Das Secret steht nur in `.env` (`IFDD_CT_OIDC_CLIENT_SECRET`), nie als
  Template-Variable, nie in Git oder `.cruft.json`.
- `put`, `patch` und `post` nehmen `dry_run=true` an: eine Kette zuerst ohne
  Schreiben ausprobieren.

## TLS

Die Zertifikatsprüfung wird nie abgeschaltet. Mit
`IFDD_CT_CA_BUNDLE=/certs/ca.crt` wird nur dieser CA vertraut; leer gilt der
System-Trust-Store des Images.

## Plugins

Aufrufbar sind nur Plugins aus drei Orten: die eingebauten, `private/` (ins
Image gebaut) und `plugins/` (zur Laufzeit eingebunden); beliebige
Python-Pfade gibt es nicht. Ein Plugin läuft mit den Rechten des Clients:
Wer nach `private/` oder `plugins/` schreiben kann, kann ins Backend
schreiben.

## Container

| Maßnahme | Einstellung |
|---|---|
| Benutzer | der aufrufende Benutzer (`IFDD_CT_UID`, `IFDD_CT_GID`); das Image nimmt sonst UID 10001 |
| Dateisystem | Root nur lesend, `/tmp` als tmpfs (Produktion); `plugins/` und `certs/` nur lesend, `data/` beschreibbar |
| Rechte | `no-new-privileges` |
| Netz | nur `{{ cookiecutter.ifdd_proxy_network }}`, keine veröffentlichten Ports |

`.dockerignore` hält `.env`, `data`, `plugins`, `certs` und `tests` aus dem
Image heraus.
