# certs/

Put the PEM file of the CA that signed the internal certificates here, e.g.
`certs/ca.pem`, and set `IFDD_CT_CA_BUNDLE=/certs/ca.pem` in `.env`.
Mounted read-only into the container as `/certs`.

Certificate verification is never switched off; without a CA bundle the
system trust store of the image is used.
