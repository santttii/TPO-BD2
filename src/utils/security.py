import os
import hashlib
import hmac
import secrets
from typing import Tuple


def _generate_salt(length: int = 16) -> str:
    return secrets.token_hex(length)


def hash_password(password: str, iterations: int = 100_000) -> str:
    """
    Hash password using PBKDF2-HMAC-SHA256. Returns a string with format:
      pbkdf2_sha256$iterations$salt$hex
    """
    if password is None:
        raise ValueError("password required")
    salt = _generate_salt(8)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """
    Verify a password against stored hash in format produced by hash_password.
    """
    try:
        algo, iterations_s, salt, hexhash = stored.split("$")
        iterations = int(iterations_s)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False
