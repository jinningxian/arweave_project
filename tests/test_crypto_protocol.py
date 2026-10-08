from __future__ import annotations

import copy
import json
import pathlib
import unittest
from unittest import mock

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from jwt.algorithms import RSAAlgorithm

from arweave import Transaction, Wallet
from arweave.deep_hash import deep_hash
from arweave.merkle import generate_transaction_chunks
from arweave.rsa_jwk import base64url_decode, base64url_encode, construct


ROOT = pathlib.Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / "tests" / "protocol_vectors.json").read_text(encoding="utf-8-sig"))


class SyntheticWallet:
    def __init__(self, jwk_data, anchor):
        self.jwk_data = jwk_data
        self._anchor = anchor

    def get_last_transaction_id(self):
        return self._anchor


class CryptoProtocolTests(unittest.TestCase):
    def test_rsa_pss_and_negative_paths(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        wallet = Wallet.from_data(RSAAlgorithm.to_jwk(key, as_dict=True))
        message = b"synthetic offline Arweave security increment"
        signature = wallet.sign(message)
        key.public_key().verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        with self.assertRaises(InvalidSignature):
            key.public_key().verify(
                signature,
                message + b"tampered",
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
                hashes.SHA256(),
            )
        wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(InvalidSignature):
            wrong.public_key().verify(
                signature,
                message,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
                hashes.SHA256(),
            )
        large = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        large_wallet = Wallet.from_data(RSAAlgorithm.to_jwk(large, as_dict=True))
        self.assertTrue(large_wallet.sign(message))

        public = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
        for invalid in (
            {"kty": "oct", "k": "bm90LWEtcmVhbC1rZXk"},
            {"kty": "EC", "crv": "P-256"},
            {"kty": "RSA", "n": "invalid!", "e": "AQAB"},
            {"kty": "RSA", "n": "A", "e": "AQAB"},
            {**public, "n": public["n"] + "="},
        ):
            with self.subTest(invalid=invalid.get("kty")):
                with self.assertRaises(ValueError):
                    construct(invalid, "RS256")
        with self.assertRaises(ValueError):
            construct(public, "HS256")
        small = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        with self.assertRaises(ValueError):
            construct(RSAAlgorithm.to_jwk(small, as_dict=True), "RS256")

    def test_canonical_base64url_boundaries(self):
        for length in (0, 1, 2, 3, 128, 256):
            value = bytes(index % 251 for index in range(length))
            encoded = base64url_encode(value)
            self.assertEqual(base64url_decode(encoded), value)
            self.assertEqual(base64url_decode(encoded.decode("ascii")), value)
        for invalid in (b"=", b"AA=", b"AA!", b"A", b"AA\n"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    base64url_decode(invalid)

    def test_deep_hash_matches_official_js_2_1_vectors(self):
        values = [b"", b"hello", [], [b"2", b"owner", [b"nested", b""]]]
        self.assertEqual(
            [deep_hash(copy.deepcopy(value)).hex() for value in values],
            VECTORS["deep_hash"],
        )

    def test_merkle_matches_official_js_2_1_vectors(self):
        import io

        for vector in VECTORS["chunks"]:
            size = vector["size"]
            data = bytes(index % 251 for index in range(size))
            result = generate_transaction_chunks(io.BytesIO(data))
            self.assertEqual(result["data_root"].hex(), vector["data_root"])
            self.assertEqual(
                [
                    {
                        "data_hash": chunk.data_hash.hex(),
                        "min_byte_range": chunk.min_byte_range,
                        "max_byte_range": chunk.max_byte_range,
                    }
                    for chunk in result["chunks"]
                ],
                vector["chunks"],
            )
            self.assertEqual(
                [{"offset": proof.offset, "proof": proof.proof.hex()} for proof in result["proofs"]],
                vector["proofs"],
            )

    def test_transaction_signature_data_matches_official_js_2_1_vector(self):
        vector = VECTORS["transaction"]
        payload = bytes(index % 251 for index in range(vector["payload_size"]))
        wallet = SyntheticWallet(vector["public_jwk"], vector["last_tx"])
        transaction = Transaction(wallet, data=payload, reward=vector["reward"])
        transaction.add_tag(vector["tag_name"], vector["tag_value"])
        with mock.patch.object(transaction, "get_reward", return_value=vector["reward"]):
            signature_data = transaction.get_signature_data()
        root = transaction.data_root.decode() if isinstance(transaction.data_root, bytes) else transaction.data_root
        self.assertEqual(root, vector["data_root"])
        self.assertEqual(signature_data.hex(), vector["signature_data_hex"])


if __name__ == "__main__":
    unittest.main()
