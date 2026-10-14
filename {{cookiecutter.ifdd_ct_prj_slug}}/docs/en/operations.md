(ifdd-ct-operations)=
# Operations

## Running a chain

ct is a job container: no service runs between calls, so there is no health
check, no restart policy and nothing to stop.

```bash
./adm_02_run.sh --list                                  # what is there
./adm_02_run.sh examples/json-ld put                    # load the examples
./adm_02_run.sh faker:seed=42,product=500 put           # load generated data
./adm_02_run.sh -f pipelines/generate-energy-grid.yaml  # a pipeline file
```

The steps and the pipeline files are described in {ref}`ifdd-ct-pipelines`.
Exit codes: `0` ok, `1` a step failed, `2` wrong command line or pipeline
file. Calls need the backend, the schema service and Keycloak to be up.

When and how often a chain runs (by hand, a timer, a workflow of the wf
service) is not part of this template.

## Logs and results

Logs go to standard error only, so standard output stays clean for pipes.
Without `-v` or `-q` the level is `IFDD_CT_LOG_LEVEL` (here
`{{ cookiecutter.ifdd_ct_log_level|upper }}`); `-v` shows each step, `-vv`
adds debug output and tracebacks, `-q` only errors.

Results are written below `data/`, for example `data/out/` (ignored by Git).
Files belong to `IFDD_CT_UID`/`IFDD_CT_GID`.

## Loading data again

Writing is idempotent for unchanged documents: the backend answers
`No changes detected` and only renews `c_cacheUpdated`. Loading the same
faker seed again therefore changes nothing. The writing steps send every
record, log and count failures, and fail at the end if any occurred.

## Resources

The production container runs with a read-only root file system and `/tmp`
as tmpfs; only `data/` is writable. No memory limit is set.

## Updates

Template updates arrive with `cruft update`; `.env`, `certs`, `data`,
`plugins`, `private` and `tests/private` are on the skip list. Rebuild the
image afterwards (`./adm_01_build.sh`).

## Backup

Keep `.env` (it holds the client secret), `data/` (pipelines and results),
`private/` and `plugins/`. Everything else comes from the template and Git.
