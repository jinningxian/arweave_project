# arweave_project

`arweave_project` is a small Flask application for inspecting an Arweave
wallet and uploading documents. Version **0.0.2** vendors the eight public
modules the application uses from `arweave-python-client` 1.0.19 and replaces
its vulnerable `python-jose`/`ecdsa` dependency path with a strict RSA-only
adapter. See [`arweave/UPSTREAM.md`](arweave/UPSTREAM.md) for byte-level
provenance and the upstream MIT license.

## Supported local environment

- CPython `>=3.12,<3.15`; validated patches are 3.12.15, 3.13.16 and 3.14.8.
- Windows AMD64 and Linux x86_64.
- The 21-package application graph is fixed by `pylock.toml`.
- `installer==1.0.1` and `packaging==26.3` are separately fixed by
  `bootstrap-lock.json`.

Create an empty environment without pip, prepare a wheelhouse containing the
exact PyPI files named in both locks, then run the stdlib-first installer:

```bash
python -m venv --without-pip .venv
.venv/Scripts/python tools/bootstrap_locked.py --lock pylock.toml --bootstrap bootstrap-lock.json --wheelhouse <reviewed-wheelhouse> --report validation-output/install.json
```

On Linux use `.venv/bin/python`. The installer rejects network access, source
distributions, unsafe archive paths, incompatible tags, incomplete RECORDs,
missing or extra packages, and any size or SHA-256 mismatch before installing.
The resulting environment contains neither pip nor uv.

Run the offline synthetic checks with no wallet or provider access:

```bash
set ARWEAVE_WHEELHOUSE=<reviewed-wheelhouse>
.venv/Scripts/python -m unittest discover -s tests -v
```

Do not run `test.py` as a validation command; it is legacy application code
that expects a wallet file. Local tests generate ephemeral synthetic RSA keys
in memory and deny external requests.

## Usage

After supplying your own runtime configuration and wallet through the existing
application flow:

```bash
.venv/Scripts/python run.py
```

The existing routes remain unchanged: `/`, `/uploader`, `/wallet`,
`/lastTransaction`, `/upload`, `/search`, and `/test1` with their existing
methods. The three Bootstrap-backed pages now use Bootstrap 5.3.8 with pinned
SHA-384 SRI.

## Security boundary and retained risks

- JWK parsing accepts only canonical unpadded base64url, RSA keys of at least
  2048 bits, and the existing RS256 key-import path. RSA-PSS transaction
  signing remains unchanged.
- A transport exception during upload has an unknown remote outcome. The
  inherited uploader does not provide reliable automatic retry or persisted
  resume; reconcile remotely before any manual resend.
- Missing `id` on `/search` and missing `token` on `/test1` retain their legacy
  HTTP 500 behavior.
- The unused floating Vue script has been removed from the wallet page. Its
  inline JavaScript, forms and server-rendered fields retain the same behavior.
- Native/runtime coverage is not a whole-repository zero claim. Remaining
  boundaries include CPython/base OS, OpenSSL/libffi, cffi, cryptography,
  PyCryptodome, MarkupSafe and charset-normalizer.
- macOS, ARM, PyPy, older Python, live Arweave delivery, deployment and
  production acceptance are unverified.

The complete incremental validation and residual list is in
[`SECURITY_HANDOVER.md`](SECURITY_HANDOVER.md).