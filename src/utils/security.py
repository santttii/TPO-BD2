import os
from passlib.context import CryptContext

# Usamos pbkdf2_sha256 para evitar dependencias binarias (bcrypt) en la imagen.
# pbkdf2_sha256 es compatible, seguro y no tiene la limitación de 72 bytes.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False
