# data/

Mounted into the container as `/data`, which is also the working directory:
relative paths in steps and pipeline files start here.

| Path | Content |
|---|---|
| `examples/json-ld/` | example documents, rendered for this instance's URLs |
| `pipelines/` | pipeline files for `ifdd-ct -f ...` |
| `out/` | a good place for written results (ignored by git) |

This directory is on the cruft skip list: it belongs to the instance.
