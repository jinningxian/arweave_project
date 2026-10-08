# Security handover — 0.0.1

This release candidate is an incremental dependency and protocol-hardening
batch. It does not claim whole-repository or native-runtime vulnerability zero,
reliable uploader retry/resume, deployment, or production acceptance.

## Changed surface

- Vendored eight provenance-bound MIT modules from public
  `arweave-python-client` 1.0.19.
- Replaced the `python-jose`/`ecdsa` path with PyJWT 2.15.1,
  cryptography 50.0.2 and strict RSA-only canonical JWK parsing.
- Removed import-only PyNaCl and psutil roots.
- Locked seven direct requirements to a 21-package PEP 751 application graph
  for three exact CPython patches on Windows AMD64 and Linux x86_64.
- Added a no-pip, offline, hash/RECORD/tag/metadata/closure-validating bootstrap.
- Updated three templates from Bootstrap 5.0.2 to 5.3.8 with exact SRI.
- Added synthetic crypto/protocol, uploader, Flask route and dependency-lock
  tests. `run.py` and `test.py` remain byte-identical to task intake.

## Functional evidence before closeout

The source-bound functional gate ran on CPython 3.12.15, 3.13.16 and 3.14.8
for both Windows AMD64 and Linux x86_64. Each environment installed exactly 21
application packages into a fresh `--without-pip` venv, ran 18 unit tests,
22 official Arweave JS 2.1 protocol checks, and 21 Flask contract checks with
zero external application requests. Seven supply-chain mutation cases were
rejected before installation. Fresh OSV batch results for all 21 application
and two bootstrap coordinates returned zero advisories with no ignored IDs.

Canonical evidence lives outside the repository under task
`github-security-all-merge-20261007-arweave-source-increment`; the pre-closeout
functional record SHA-256 is
`659f0d49d697befd05936767f6e7279fad7075071c3dbc38c7c4c148636af25f`.
Final validation and independent review must bind the post-closeout snapshot.

## Retained residuals

1. The public 1.0.19 uploader retains unreliable automatic retry and persisted
   resume behavior. Timeout/connection failure is an unknown remote outcome;
   never blind-resend.
2. Native/runtime closure remains incomplete for CPython/base OS,
   OpenSSL/libffi, cffi, cryptography, PyCryptodome, MarkupSafe and
   charset-normalizer.
3. Some exact upstream wheels retain Metadata 2.1 plus `License-File` extension
   fields. Their original bytes, paths and RECORD coverage are validated and
   reported as a conformance residual.
4. Missing `/search` `id` and `/test1` `token` still produce legacy HTTP 500.
5. `templates/main.html` retains an out-of-scope unpinned Vue CDN reference.
6. macOS, ARM, PyPy, older Python, real wallets, live provider delivery,
   deployment and production acceptance are unverified.

Rollback is one normal Git revert of this batch. No wallet, transaction,
upload, database, provider, account or production data migration is involved.