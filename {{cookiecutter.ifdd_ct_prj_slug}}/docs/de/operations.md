(ifdd-ct-operations)=
# Betrieb

## Eine Kette ausführen

ct ist ein Job-Container: Zwischen den Aufrufen läuft kein Dienst, daher
gibt es keinen Healthcheck, keine Neustart-Regel und nichts zu stoppen.

```bash
./adm_02_run.sh --list                                  # was es gibt
./adm_02_run.sh examples/json-ld put                    # die Beispiele laden
./adm_02_run.sh faker:seed=42,product=500 put           # erzeugte Daten laden
./adm_02_run.sh -f pipelines/generate-energy-grid.yaml  # eine Pipeline-Datei
```

Die Schritte und die Pipeline-Dateien beschreibt {ref}`ifdd-ct-pipelines`.
Exit-Codes: `0` in Ordnung, `1` ein Schritt scheiterte, `2` falsche
Kommandozeile oder Pipeline-Datei. Aufrufe brauchen laufendes Backend,
laufenden Schema-Dienst und laufendes Keycloak.

Wann und wie oft eine Kette läuft (von Hand, per Timer, als Workflow des
Dienstes wf), regelt dieses Template nicht.

## Logs und Ergebnisse

Logs gehen nur auf die Standardfehlerausgabe; die Standardausgabe bleibt
für Pipes frei. Ohne `-v` oder `-q` gilt `IFDD_CT_LOG_LEVEL` (hier
`{{ cookiecutter.ifdd_ct_log_level|upper }}`); `-v` zeigt jeden Schritt, `-vv`
dazu Debug-Ausgaben und Tracebacks, `-q` nur Fehler.

Ergebnisse landen unter `data/`, etwa in `data/out/` (von Git ignoriert).
Die Dateien gehören `IFDD_CT_UID`/`IFDD_CT_GID`.

## Daten erneut laden

Schreiben ist für unveränderte Dokumente idempotent: Das Backend antwortet
`No changes detected` und erneuert nur `c_cacheUpdated`. Denselben
Faker-Seed noch einmal zu laden ändert also nichts. Die schreibenden
Schritte senden jeden Datensatz, protokollieren und zählen Fehler und
scheitern am Ende, wenn welche auftraten.

## Ressourcen

Der Produktions-Container läuft mit schreibgeschütztem Root-Dateisystem und
`/tmp` als tmpfs; nur `data/` ist beschreibbar. Eine Speichergrenze ist
nicht gesetzt.

## Aktualisieren

Template-Updates kommen mit `cruft update`; `.env`, `certs`, `data`,
`plugins`, `private` und `tests/private` stehen auf der Skip-Liste. Danach
das Image neu bauen (`./adm_01_build.sh`).

## Sicherung

`.env` (enthält das Client-Secret), `data/` (Pipelines und Ergebnisse),
`private/` und `plugins/` aufbewahren. Alles Übrige kommt aus dem Template
und aus Git.
