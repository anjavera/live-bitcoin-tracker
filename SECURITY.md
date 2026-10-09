# Security policy

## Reporting a vulnerability
Please **do not open a public issue** for a security problem. Use GitHub's private reporting instead:
**[Report a vulnerability](../../security/advisories/new)** (repository > Security > Report a vulnerability). Only the maintainer can see it.

Please include what you found, the version (`bitcoin-tracker --version`), your system, and the steps to reproduce it. You can expect an
acknowledgement within a few days; this is a small volunteer project, so fixes follow as fast as the maintainer can manage.

## What the app does and does not do
- It only **reads public market data** (Polymarket US and four public exchange price APIs). It places no orders and has no account or login.
- It stores a small cache of settled results and its window settings on your computer.
- Optional Polymarket API keys, if you choose to add them, are used only to sign requests to Polymarket. Never share or commit them. If a key is
  ever exposed, revoke it at <https://polymarket.us/developer>.

## Supported versions
Only the latest release receives fixes.

## Downloads and signing
Release files are built by the public workflow in `.github/workflows/release.yml` from this repository, so you can read exactly what produced them.
They are **not code-signed yet** (see the README's code signing policy), and the builds are not byte-for-byte reproducible, so a rebuilt file will
not match a download. If you would rather not trust a binary, install from source with `uv` (see the README), which runs the code you can read.
