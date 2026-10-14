# private/

Plugins of this instance. Every module here is loaded at start-up and baked
into the image (`/opt/ifdd-ct/private`). Plugins show up as `private.<name>`.

This directory is on the cruft skip list: template updates leave it alone.

For experiments that should not go into the image, use `plugins/` instead.
