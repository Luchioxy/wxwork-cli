#!/usr/bin/env python3
"""Key verification test harness.

Usage: python tools/key_test.py <db_path> <hex_key>
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from wxwork_cli.data.crypto import verify_key


def main():
    if len(sys.argv) < 3:
        print("Usage: python key_test.py <db_path> <hex_key>", file=sys.stderr)
        print("\nVerifies that a hex-encoded key can decrypt a database.", file=sys.stderr)
        sys.exit(1)

    db_path = sys.argv[1]
    hex_key = sys.argv[2]

    try:
        key_bytes = bytes.fromhex(hex_key)
    except ValueError:
        print(f"Error: Invalid hex key: {hex_key}", file=sys.stderr)
        sys.exit(1)

    if len(key_bytes) != 32:
        print(f"Error: Key must be 32 bytes (64 hex chars), got {len(key_bytes)} bytes", file=sys.stderr)
        sys.exit(1)

    print(f"Testing key against: {db_path}")
    print(f"Key: {hex_key}")

    if verify_key(key_bytes, db_path):
        print("✓ Key is VALID - successfully decrypts the database")
    else:
        print("✗ Key is INVALID - cannot decrypt the database")
        sys.exit(1)


if __name__ == "__main__":
    main()
