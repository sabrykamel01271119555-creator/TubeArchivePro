# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/secure.py
# Version history of this file:
#   2.3.0 - Created: the text files of the online folder (ad list, total_users.txt ...) can be encrypted
# =============================================================================
"""Light encryption of the online text files (standard library only).

File layout:  b"TAE1" + nonce (16 bytes) + cipher text + MAC (32 bytes, HMAC-SHA256 of everything before it)
Cipher: HMAC-SHA256 key stream in counter mode, encrypt-then-MAC. The key is inside the program, so this keeps the files
unreadable for people who just open the link - it is NOT protection against someone who takes the program apart.
Plain (not encrypted) files still work: decrypt_if_needed() returns them unchanged.

The owner encrypts with owner_tools/encrypt_online.py (same functions).
"""
import hashlib
import hmac
import os

MAGIC = b"TAE1"
_SECRET = b"TubeArchivePro/online-files/2026:6f1c9d3e-77b2-4a0e-b1c5-9a4d2e8f03b7"
_KEY = hashlib.sha256(_SECRET).digest()


def _stream(nonce: bytes, n: int) -> bytes:
    out, counter = bytearray(), 0
    while len(out) < n:
        out += hmac.new(_KEY, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:n])


def encrypt(data: bytes, nonce: bytes | None = None) -> bytes:
    nonce = nonce or os.urandom(16)
    ct = bytes(a ^ b for a, b in zip(data, _stream(nonce, len(data))))
    body = MAGIC + nonce + ct
    return body + hmac.new(_KEY, body, hashlib.sha256).digest()


def is_encrypted(data: bytes) -> bool:
    return bool(data) and data[:4] == MAGIC


def decrypt(blob: bytes) -> bytes:
    """Raises ValueError when the file is not encrypted by this program or was changed."""
    if len(blob) < 4 + 16 + 32 or blob[:4] != MAGIC:
        raise ValueError("not an encrypted file")
    body, mac = blob[:-32], blob[-32:]
    if not hmac.compare_digest(mac, hmac.new(_KEY, body, hashlib.sha256).digest()):
        raise ValueError("the file was changed")
    nonce, ct = body[4:20], body[20:]
    return bytes(a ^ b for a, b in zip(ct, _stream(nonce, len(ct))))


def decrypt_if_needed(data: bytes) -> bytes | None:
    """Plain data unchanged; encrypted data decrypted; None when encrypted but damaged."""
    if not is_encrypted(data):
        return data
    try:
        return decrypt(data)
    except ValueError:
        return None
