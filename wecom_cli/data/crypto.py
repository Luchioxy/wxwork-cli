"""SQLCipher 4 page-level decryption (AES-256-CBC).

Direct port from wechat-cli. WXWork uses the same SQLCipher 4 scheme.
"""

import hashlib
import hmac
import os
import struct

from Cryptodome.Cipher import AES

# SQLCipher 4 constants
PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
RESERVE_SZ = 80  # 16 (IV) + 64 (HMAC-SHA512)
HMAC_SZ = 64
IV_SZ = 16

SQLITE_HEADER = b"SQLite format 3\x00"
HEADER_PLAIN_SZ = len(SQLITE_HEADER)  # 16 bytes plaintext at page start


def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()


def _pbkdf2_hmac_sha512(password: bytes, salt: bytes, iterations: int, dklen: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha512", password, salt, iterations, dklen=dklen)


def decrypt_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    """Decrypt a single 4096-byte SQLCipher 4 page.

    Args:
        enc_key: 32-byte encryption key.
        page_data: Raw encrypted page (4096 bytes).
        pgno: Page number (1-based).

    Returns:
        Decrypted page bytes.
    """
    if len(page_data) != PAGE_SZ:
        raise ValueError(f"Expected {PAGE_SZ} bytes, got {len(page_data)}")

    # Extract salt from page 1 (first 16 bytes), or use page-specific derivation
    if pgno == 1:
        salt = page_data[:SALT_SZ]
    else:
        # For pages > 1, salt is derived from page number
        salt = struct.pack(">I", pgno).rjust(SALT_SZ, b"\x00")

    # Derive per-page key using PBKDF2
    mac_salt = bytes(b ^ 0x3A for b in salt)
    mac_key = _pbkdf2_hmac_sha512(enc_key, mac_salt, 2, dklen=KEY_SZ)

    # Extract IV and HMAC from reserve area
    reserve = page_data[-RESERVE_SZ:]
    iv = reserve[:IV_SZ]
    stored_hmac = reserve[IV_SZ:IV_SZ + HMAC_SZ]

    # Verify HMAC
    # HMAC covers: page data (excluding reserve) + page number (big-endian 4 bytes)
    hmac_data = page_data[:-RESERVE_SZ] + struct.pack(">I", pgno)
    computed_hmac = _hmac_sha512(mac_key, hmac_data)

    if not hmac.compare_digest(computed_hmac, stored_hmac):
        # Try with salt directly (some SQLCipher versions)
        mac_key_alt = _pbkdf2_hmac_sha512(enc_key, salt, 2, dklen=KEY_SZ)
        computed_hmac_alt = _hmac_sha512(mac_key_alt, hmac_data)
        if not hmac.compare_digest(computed_hmac_alt, stored_hmac):
            raise ValueError(f"HMAC verification failed for page {pgno}")

    # Decrypt page content (excluding reserve area and plaintext header for page 1)
    cipher = AES.new(enc_key, AES.MODE_CBC, iv)

    if pgno == 1:
        # Page 1: first 16 bytes are plaintext SQLite header
        encrypted_part = page_data[HEADER_PLAIN_SZ:-RESERVE_SZ]
        decrypted_part = cipher.decrypt(encrypted_part)
        return SQLITE_HEADER + decrypted_part
    else:
        encrypted_part = page_data[:-RESERVE_SZ]
        return cipher.decrypt(encrypted_part)


def decrypt_wal_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    """Decrypt a WAL (Write-Ahead Log) page.

    WAL pages have the same encryption as regular pages.
    """
    return decrypt_page(enc_key, page_data, pgno)


def full_decrypt(db_path: str, out_path: str, enc_key: bytes) -> None:
    """Decrypt an entire SQLCipher database file.

    Args:
        db_path: Path to the encrypted .db file.
        out_path: Path for the decrypted output file.
        enc_key: 32-byte encryption key.
    """
    with open(db_path, "rb") as f:
        data = f.read()

    if len(data) < PAGE_SZ:
        raise ValueError(f"Database file too small: {len(data)} bytes")

    num_pages = len(data) // PAGE_SZ
    remainder = len(data) % PAGE_SZ

    decrypted_pages = []
    for i in range(num_pages):
        page_data = data[i * PAGE_SZ:(i + 1) * PAGE_SZ]
        pgno = i + 1
        try:
            decrypted_page = decrypt_page(enc_key, page_data, pgno)
            decrypted_pages.append(decrypted_page)
        except ValueError as e:
            raise ValueError(f"Failed to decrypt page {pgno}: {e}") from e

    # Write decrypted database
    with open(out_path, "wb") as f:
        for page in decrypted_pages:
            f.write(page)
        # Warn if there's a remainder (shouldn't happen for valid SQLCipher DBs)
        if remainder:
            import sys
            print(f"Warning: Database has {remainder} trailing bytes (not page-aligned)", file=sys.stderr)
            f.write(data[-remainder:])


def decrypt_wal(wal_path: str, out_path: str, enc_key: bytes) -> None:
    """Decrypt a WAL (Write-Ahead Log) file.

    Args:
        wal_path: Path to the encrypted WAL file.
        out_path: Path for the decrypted output WAL.
        enc_key: 32-byte encryption key.
    """
    with open(wal_path, "rb") as f:
        data = f.read()

    if len(data) == 0:
        # Empty WAL, nothing to decrypt
        with open(out_path, "wb") as f:
            pass
        return

    # WAL format: 32-byte header + page frames
    # Each frame: page data (PAGE_SZ) + frame checksum (8 bytes)
    WAL_HEADER_SZ = 32
    FRAME_CHECKSUM_SZ = 8

    if len(data) < WAL_HEADER_SZ:
        raise ValueError(f"WAL file too small: {len(data)} bytes")

    wal_header = data[:WAL_HEADER_SZ]
    frame_data = data[WAL_HEADER_SZ:]

    # Calculate frame size (page + checksum)
    frame_sz = PAGE_SZ + FRAME_CHECKSUM_SZ

    if len(frame_data) % frame_sz != 0:
        # WAL might have different format, try treating all data after header as pages
        # This is a fallback for WXWork's potentially different WAL format
        num_pages = len(frame_data) // PAGE_SZ
        decrypted_frames = []
        for i in range(num_pages):
            page_data = frame_data[i * PAGE_SZ:(i + 1) * PAGE_SZ]
            pgno = i + 1
            try:
                decrypted_page = decrypt_wal_page(enc_key, page_data, pgno)
                decrypted_frames.append(decrypted_page)
            except ValueError:
                # Skip frames that fail to decrypt (may be uncommitted)
                decrypted_frames.append(page_data)

        with open(out_path, "wb") as f:
            f.write(wal_header)
            for frame in decrypted_frames:
                f.write(frame)
        return

    num_frames = len(frame_data) // frame_sz
    decrypted_frames = []

    for i in range(num_frames):
        offset = i * frame_sz
        page_data = frame_data[offset:offset + PAGE_SZ]
        checksum = frame_data[offset + PAGE_SZ:offset + frame_sz]
        pgno = i + 1

        try:
            decrypted_page = decrypt_wal_page(enc_key, page_data, pgno)
            decrypted_frames.append(decrypted_page + checksum)
        except ValueError:
            # Keep original frame if decryption fails
            decrypted_frames.append(page_data + checksum)

    with open(out_path, "wb") as f:
        f.write(wal_header)
        for frame in decrypted_frames:
            f.write(frame)


def verify_key(enc_key: bytes, db_path: str) -> bool:
    """Verify that an encryption key can decrypt a database.

    Reads the first page and checks for the SQLite header after decryption.

    Args:
        enc_key: 32-byte encryption key to verify.
        db_path: Path to an encrypted database file.

    Returns:
        True if the key successfully decrypts the first page.
    """
    try:
        with open(db_path, "rb") as f:
            page1 = f.read(PAGE_SZ)

        if len(page1) < PAGE_SZ:
            return False

        decrypted = decrypt_page(enc_key, page1, 1)
        return decrypted[:HEADER_PLAIN_SZ] == SQLITE_HEADER
    except (ValueError, OSError):
        return False
