# Security Policy

## Reporting a vulnerability

Please open a private security advisory via GitHub ("Report a vulnerability")
or contact the maintainers. Do not open public issues for vulnerabilities.

## Scope notes

- This repository executes third-party notebooks and downloads third-party
  models. Treat all upstream content as untrusted code.
- Evidence directories are sanitized (no hostname/username/IP/tokens) — see
  `ov_amd/hardware.py`. Please keep it that way in contributions.
- Never commit credentials, tokens, or private paths.
