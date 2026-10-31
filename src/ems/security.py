"""Versioned password hashes; legacy SHA-256 is accepted only for migration."""

import hashlib
import hmac
import re
import secrets

ITERATIONS = 600_000


def hash_password(password):
    if not 12 <= len(password) <= 128:
        raise ValueError("New passwords must contain 12–128 characters.")
    return _encode(password)


def _encode(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    """Return (valid, needs_upgrade), rejecting malformed hashes and huge work factors."""
    if not isinstance(stored, str) or not 1 <= len(password) <= 128:
        return False, False
    if re.fullmatch(r"[0-9a-fA-F]{64}", stored):
        valid = hmac.compare_digest(
            hashlib.sha256(password.encode()).hexdigest(), stored.lower()
        )
        return valid, valid
    try:
        algorithm, rounds, salt, expected = stored.split("$")
        rounds = int(rounds)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= rounds <= 2_000_000:
            return False, False
        if not re.fullmatch(r"[0-9a-f]{32}", salt) or not re.fullmatch(
            r"[0-9a-f]{64}", expected
        ):
            return False, False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), rounds
        ).hex()
        valid = hmac.compare_digest(actual, expected)
        return valid, valid and rounds < ITERATIONS
    except ValueError, TypeError:
        return False, False


def upgrade_password(password):
    """Rehash a verified legacy password without rejecting its historical length."""
    return _encode(password)
