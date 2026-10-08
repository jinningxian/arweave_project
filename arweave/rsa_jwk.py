"""RSA-only JWK parsing using maintained PyJWT/cryptography, plus base64 helpers.

This adapter performs no JWT token creation or validation. The Arweave client's
existing PyCryptodome RSA-PSS signing and hashing implementation is unchanged.
"""
import base64
import binascii
import re
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm


class ALGORITHMS:
    RS256 = "RS256"


def base64url_encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=")


_BASE64URL = re.compile(rb"^[A-Za-z0-9_-]*$")


def base64url_decode(value):
    """Decode canonical, unpadded base64url and reject ignored junk bytes."""
    if isinstance(value, str):
        try:
            value = value.encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError("base64url input must be ASCII") from error
    if not isinstance(value, bytes):
        raise TypeError("base64url input must be str or bytes")
    if not _BASE64URL.fullmatch(value) or len(value) % 4 == 1:
        raise ValueError("base64url input is malformed or non-canonical")
    try:
        decoded = base64.b64decode(
            value + b"=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as error:
        raise ValueError("base64url input is malformed") from error
    if base64url_encode(decoded) != value:
        raise ValueError("base64url input is non-canonical")
    return decoded


class RSAKey:
    def __init__(self, value):
        if not isinstance(value, dict) or value.get("kty") != "RSA":
            raise ValueError("Only RSA JWK keys are supported")
        if value.get("alg") not in (None, ALGORITHMS.RS256):
            raise ValueError("Only the existing RSA key-import algorithm is supported")
        if not isinstance(value.get("n"), str) or not isinstance(value.get("e"), str):
            raise ValueError("RSA JWK modulus and exponent are required")
        for field in ("n", "e", "d", "p", "q", "dp", "dq", "qi"):
            if field in value:
                decoded = base64url_decode(value[field])
                if not decoded or (len(decoded) > 1 and decoded[0] == 0):
                    raise ValueError("RSA JWK integer is empty or non-canonical")
        try:
            self._key = RSAAlgorithm.from_jwk(value)
        except Exception as error:
            raise ValueError("Malformed RSA JWK") from error
        if self._key.key_size < 2048:
            raise ValueError("RSA JWK keys smaller than 2048 bits are not supported")

    def to_pem(self):
        if hasattr(self._key, "private_bytes"):
            return self._key.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption())
        return self._key.public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo)


def construct(key_data, algorithm):
    if algorithm != ALGORITHMS.RS256:
        raise ValueError("Only the existing RSA key-import algorithm is supported")
    return RSAKey(key_data)
