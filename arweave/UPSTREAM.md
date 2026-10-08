# Vendored Arweave client provenance

- Public upstream: `arweave-python-client` 1.0.19
- Upstream wheel SHA-256: `281ab937a612f78957f86f975f35d2e62b514cd53b0ef727a6232369b357f6d5`
- License: MIT; exact upstream license is stored in `arweave/LICENSE`.
- The vendored surface is limited to the eight modules listed below.

| Path | Upstream SHA-256 | Candidate SHA-256 | Reviewed delta |
| --- | --- | --- | --- |
| `arweave/__init__.py` | `5d36cd555b79fb9cb3c173ece5af7272975badda68cb3fc1777be67d1fd5785b` | `5d36cd555b79fb9cb3c173ece5af7272975badda68cb3fc1777be67d1fd5785b` | byte-identical |
| `arweave/arweave_lib.py` | `9768ebed1752a9bc73cba9d98f0f1276d0bb8ab6ddf32290d59e94bfd98b337c` | `1aca7bb390ec159e92d9468b5c5569af20b62c9772d01531036a56b690e01f72` | 1.0.19 candidate plus removal of import-only psutil and nacl.bindings |
| `arweave/deep_hash.py` | `686934609948b4aec2e9e8b3b7916ae2e7aeaa363b874db82d3814d039c55836` | `a7014369b29d6e10fa7f54caebece4bb7300f29c34820d59c2114790edba333a` | reviewed Python 3 / JS 2.1 protocol compatibility patch |
| `arweave/file_io.py` | `e8c5645bef39a864a8ebf0bddfa1abc44b124e4b4d7d3e0563d96e177f13545d` | `e8c5645bef39a864a8ebf0bddfa1abc44b124e4b4d7d3e0563d96e177f13545d` | byte-identical |
| `arweave/merkle.py` | `a58c0aeb961559bf1d0fe5d167504e965b84c98a7803212276ea004db76bfb3c` | `9fd8d3ec406f7fe0ed12490213588ce2e594e88a438cff1ac7c56566ff7d3050` | reviewed Python 3 / JS 2.1 protocol compatibility patch |
| `arweave/rsa_jwk.py` | `not present upstream; added adapter` | `b6dbefe03072ed5fb9759c3310613739bc2d549681a23d1285199045ae3e20cd` | RSA-only PyJWT/cryptography adapter with strict canonical base64url and >=2048-bit key checks |
| `arweave/transaction_uploader.py` | `80ee0997815d494e9e224402c3d5ea5066e7ca8edd22a6f71abc4eb85f1d65f7` | `6a138eaa758b3b7f436081d046271419e769b796782cd2753fdf849e2ed5d127` | public 1.0.19 uploader; no retry/resume redesign |
| `arweave/utils.py` | `1c5fc51fa8b543763b5223ca9a82364fcc808903e6be44a13cdb7835f6261b13` | `fdee4ac20685f634508c7b9415ca162f2d54cefd101e42a2b92fb9e2dcf86235` | reviewed Python 3 / JS 2.1 protocol compatibility patch |

The maintenance fork removes the vulnerable `python-jose`/`ecdsa` graph and does not distribute `arweave-python-client` as an installed package. RSA-PSS signing, public API names, transaction serialization, and the public 1.0.19 uploader control flow remain in place.

Known boundary: uploader automatic retry and persisted resume remain unreliable upstream behavior. A timeout has an unknown remote outcome; callers must reconcile before any manual resend.
