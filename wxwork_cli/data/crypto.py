"""wxSQLite3 AES-128 decryption for WXWork databases.

Based on the wechat-decrypt project's implementation.
WXWork uses wxSQLite3 AES-128-CBC encryption with per-page key derivation.
"""

import hashlib
import os
import struct

from Crypto.Cipher import AES

# wxSQLite3 constants
PAGE_SZ = 4096
KEY_SZ = 16  # AES-128 uses 16-byte keys
SQLITE_HEADER = b"SQLite format 3\x00"
WXSQLITE3_SALT = b"sAlT"


def _modmult(a, b, c, m, s):
    """Modular multiplication for wxSQLite3 IV generation."""
    q = s // a
    s = b * (s - a * q) - c * q
    if s < 0:
        s += m
    return s


def generate_initial_vector(page_no):
    """Generate per-page IV using wxSQLite3's custom PRNG.

    Matches SQLite3MultipleCiphers sqlite3mcGenerateInitialVector().
    """
    z = page_no + 1
    initkey = bytearray(16)
    for idx in range(4):
        z = _modmult(52774, 40692, 3791, 2147483399, z)
        initkey[idx * 4: idx * 4 + 4] = struct.pack("<I", z & 0xFFFFFFFF)
    return hashlib.md5(initkey).digest()


def derive_wxsqlite3_aes128_page_key(raw_key, page_no):
    """Derive the per-page AES-128 key used by wxSQLite3 AES-128-CBC.

    Formula: MD5(raw_key + struct.pack("<I", page_no) + b"sAlT")
    """
    if len(raw_key) != 16:
        raise ValueError("wxSQLite3 AES-128 raw key must be 16 bytes")
    material = raw_key + struct.pack("<I", page_no) + WXSQLITE3_SALT
    return hashlib.md5(material).digest()


def has_wxsqlite3_plain_header_fragment(page):
    """Check if page has wxSQLite3 plain header fragment at bytes 16-23.

    New wxSQLite3 AES mode keeps SQLite header bytes 16..23 in plaintext.
    """
    if len(page) < 24:
        return False
    header = page[16:24]
    page_size = (header[0] << 8) | header[1]
    if page_size == 1:
        page_size = 65536
    return (
        page_size >= 512
        and page_size <= 65536
        and (page_size & (page_size - 1)) == 0
        and header[5] == 0x40
        and header[6] == 0x20
        and header[7] == 0x20
    )


def is_wxsqlite3_aes128_page1(page):
    """Check if page 1 is wxSQLite3 AES-128 encrypted."""
    return not is_plain_sqlite_page(page) and has_wxsqlite3_plain_header_fragment(page)


def is_plain_sqlite_page(page):
    """Check if page is a plain SQLite page (not encrypted)."""
    return page[:len(SQLITE_HEADER)] == SQLITE_HEADER


def _decrypt_aes128_cbc(raw_key, page_no, data):
    """Decrypt data using AES-128-CBC with per-page key and IV."""
    page_key = derive_wxsqlite3_aes128_page_key(raw_key, page_no)
    iv = generate_initial_vector(page_no)
    return AES.new(page_key, AES.MODE_CBC, iv).decrypt(data)


def decrypt_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    """Decrypt a single 4096-byte wxSQLite3 AES-128 page.

    Args:
        enc_key: 16-byte raw encryption key.
        page_data: Raw encrypted page (4096 bytes).
        pgno: Page number (1-based).

    Returns:
        Decrypted page bytes.
    """
    if len(page_data) != PAGE_SZ:
        raise ValueError(f"Expected {PAGE_SZ} bytes, got {len(page_data)}")

    data = bytearray(page_data)

    # Page 1 special handling
    if pgno == 1 and has_wxsqlite3_plain_header_fragment(data):
        db_header_fragment = bytes(data[16:24])
        data[16:24] = data[8:16]
        decrypted_tail = _decrypt_aes128_cbc(enc_key, pgno, bytes(data[16:]))
        data[16:] = decrypted_tail
        if bytes(data[16:24]) != db_header_fragment:
            raise ValueError("wxSQLite3 AES-128 key validation failed")
        data[:16] = SQLITE_HEADER
        return bytes(data)

    # Other pages: decrypt entire page
    return _decrypt_aes128_cbc(enc_key, pgno, bytes(data))


def decrypt_wal_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    """Decrypt a WAL (Write-Ahead Log) page.

    WAL pages use the same encryption as regular pages.
    """
    return decrypt_page(enc_key, page_data, pgno)


def full_decrypt(db_path: str, out_path: str, enc_key: bytes) -> None:
    """Decrypt an entire wxSQLite3 database file.

    Args:
        db_path: Path to the encrypted .db file.
        out_path: Path for the decrypted output file.
        enc_key: 16-byte raw encryption key.
    """
    size = os.path.getsize(db_path)
    total_pages = (size + PAGE_SZ - 1) // PAGE_SZ

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(db_path, "rb") as fin, open(out_path, "wb") as fout:
        for page_no in range(1, total_pages + 1):
            page = fin.read(PAGE_SZ)
            if not page:
                break
            if len(page) < PAGE_SZ:
                page += b"\x00" * (PAGE_SZ - len(page))
            fout.write(decrypt_page(enc_key, page, page_no))


def decrypt_wal(wal_path: str, out_path: str, enc_key: bytes) -> None:
    """Decrypt a WAL (Write-Ahead Log) file.

    Args:
        wal_path: Path to the encrypted WAL file.
        out_path: Path for the decrypted output WAL.
        enc_key: 16-byte raw encryption key.
    """
    with open(wal_path, "rb") as f:
        data = f.read()

    if len(data) == 0:
        with open(out_path, "wb") as f:
            pass
        return

    # WAL format: 32-byte header + page frames
    WAL_HEADER_SZ = 32

    if len(data) < WAL_HEADER_SZ:
        raise ValueError(f"WAL file too small: {len(data)} bytes")

    wal_header = data[:WAL_HEADER_SZ]
    frame_data = data[WAL_HEADER_SZ:]

    # Treat all data after header as pages
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


def looks_like_sqlite_page1(page):
    """Check if decrypted page looks like a valid SQLite page 1."""
    if page[:len(SQLITE_HEADER)] != SQLITE_HEADER:
        return False
    if len(page) < 108:
        return False
    btree_page_type = page[100]
    return btree_page_type in (0x02, 0x05, 0x0A, 0x0D)


def verify_key(enc_key: bytes, db_path: str) -> bool:
    """Verify that an encryption key can decrypt a database.

    For wxSQLite3 AES-128, we verify by:
    1. Decrypting page 1
    2. Checking for SQLite header
    3. Checking for valid B-tree page type at offset 100

    Args:
        enc_key: 16-byte raw encryption key to verify.
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
        return looks_like_sqlite_page1(decrypted)
    except (ValueError, OSError):
        return False
