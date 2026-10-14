(ifdd-ct-troubleshooting)=
# Fehlersuche

Beginnen mit `-v` (jeder Schritt) oder `-vv` (Debug-Ausgaben und Tracebacks).

## Start

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `.env missing - cp dotenv.dist .env` | keine `.env` | aus `dotenv.dist` anlegen und das Secret eintragen |
| `set IFDD_CT_BE_URL in .env` | die Backend-URL fehlt | sie setzen |
| Exit-Code 2 | falsche Kommandozeile oder Pipeline-Datei | `ifdd-ct --describe <plugin>` zeigt die Parameter |
| ein Plugin steht unter „not available“ | sein Modul ließ sich nicht importieren (etwa eine fehlende Bibliothek) | `-vv` zeigt warum; die anderen Plugins funktionieren weiter |
| ein Plugin-Name ist mehrdeutig | zwei Herkünfte definieren denselben Kurznamen | qualifizieren: `builtin.head`, `local.head` oder `<module>.head` |
| ein `,` in einem Parameterwert teilt ihn | `,` trennt Parameter | als `%2C` schreiben |

## Backend und Dienste

| Symptom | Ursache | Abhilfe |
|---|---|---|
| 401 vom Backend | kein oder falsches Client-Secret, falscher Token-Endpunkt | `IFDD_CT_OIDC_CLIENT_SECRET` aus der Keycloak-Instanz; `IFDD_CT_OIDC_TOKEN_URL` |
| 403 vom Backend | dem Client fehlt die Schreibrolle oder ein Kontextmuster für einen Domain-Kontext | den Client im Realm prüfen |
| Zertifikatsfehler | die CA des Proxys liegt nicht in `certs/`, oder `IFDD_CT_CA_BUNDLE` zeigt woandershin | `certs/ca.crt` der Proxy-Instanz kopieren; die Variable prüfen |
| ein Dienst ist aus dem Container nicht erreichbar, oder ct erreicht sich selbst | sein Host ist kein Netz-Alias des Proxys | ihn in `ifdd_proxy_internal_hosts` der Proxy-Instanz eintragen |
| `post` scheitert | das Backend hat kein `POST /nodes/` | `put` nehmen |
| `No changes detected` für jedes Dokument | die Dokumente sind unverändert | erwartet |

## Daten

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `check` meldet `undefined terms` | das Dokument nutzt Terme, die sein `@context` nicht definiert (Tippfehler oder ein Schema ohne sie) | Dokument oder Schema korrigieren; `check:fail=true` stoppt vor dem Schreiben |
| `check` meldet nichts, obwohl ein Term falsch ist | der Kontext nutzt `@vocab`, dann gilt jeder Term als definiert | erwartet; `check` hilft dort nicht |
| ein Kontext lässt sich nicht laden | der Schema-Dienst ist nicht erreichbar, oder die URL stimmt nicht | `IFDD_CT_SCHEMA_URL` prüfen; `IFDD_CT_CONTEXT_DIR` nutzt stattdessen lokale Kopien |
| Dateien in `data/` gehören einem anderen Benutzer | `IFDD_CT_UID`/`IFDD_CT_GID` passen nicht zu Ihnen | auf `id -u` und `id -g` setzen |
| ein relativer Pfad wird nicht gefunden | relative Pfade beginnen im Container bei `/data` | Pfade unter `data/` ohne das Präfix `data/` angeben |
