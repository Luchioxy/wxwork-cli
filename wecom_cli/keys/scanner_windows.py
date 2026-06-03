"""Windows key extraction from WXWork.exe process memory.

Uses kernel32 API to read process memory and scan for SQLCipher encryption keys.
"""

import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
from pathlib import Path

from wecom_cli.keys.common import (
    collect_db_files,
    collect_db_pages,
    extract_hex_candidates,
    verify_and_match_keys,
    cross_verify_keys,
    build_keys_json,
)

# Windows API constants
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_READABLE = {0x02, 0x04, 0x06, 0x20, 0x40, 0x60, 0x80}
# PAGE_READWRITE=0x04, PAGE_READONLY=0x02, PAGE_WRITECOPY=0x08,
# PAGE_EXECUTE_READ=0x20, PAGE_EXECUTE_READWRITE=0x40

kernel32 = ctypes.windll.kernel32


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.wintypes.DWORD),
        ("Protect", ctypes.wintypes.DWORD),
        ("Type", ctypes.wintypes.DWORD),
    ]


def _get_wxwork_pids() -> list[tuple[int, int]]:
    """Get PIDs of running WXWork.exe processes.

    Returns:
        List of (pid, memory_kb) tuples, sorted by memory descending.
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WXWork.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []

        pids = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip() or "INFO:" in line:
                continue
            # CSV format: "WXWork.exe","PID","Session#","Mem Usage"
            parts = line.strip().split(",")
            if len(parts) >= 4:
                try:
                    pid = int(parts[1].strip('"'))
                    mem_str = parts[3].strip('"').replace(",", "").replace(" K", "").strip()
                    mem_kb = int(mem_str)
                    pids.append((pid, mem_kb))
                except (ValueError, IndexError):
                    continue

        return sorted(pids, key=lambda x: x[1], reverse=True)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _read_process_memory(pid: int) -> bytes:
    """Read readable memory regions from a process.

    Args:
        pid: Process ID to read from.

    Returns:
        Concatenated bytes from all readable memory regions.
    """
    handle = kernel32.OpenProcess(
        PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
    )
    if not handle:
        raise OSError(f"Cannot open process {pid} (access denied or process exited)")

    try:
        regions = []
        address = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)

        while kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), mbi_size):
            # Only read committed, readable memory
            if (mbi.State == MEM_COMMIT and
                mbi.Protect in PAGE_READABLE and
                mbi.RegionSize > 0 and
                mbi.RegionSize < 100 * 1024 * 1024):  # Skip regions > 100MB

                buf = ctypes.create_string_buffer(mbi.RegionSize)
                bytes_read = ctypes.c_size_t(0)

                if kernel32.ReadProcessMemory(
                    handle,
                    ctypes.c_void_p(mbi.BaseAddress),
                    buf,
                    mbi.RegionSize,
                    ctypes.byref(bytes_read)
                ):
                    regions.append(buf.raw[:bytes_read.value])

            # Move to next region
            address = mbi.BaseAddress + mbi.RegionSize
            if address <= mbi.BaseAddress:
                break  # Overflow protection

        return b"".join(regions)

    finally:
        kernel32.CloseHandle(handle)


def extract_keys(db_dir: str, force: bool = False) -> dict:
    """Extract encryption keys from WXWork.exe process memory.

    Args:
        db_dir: Path to the WXWork data directory.
        force: If True, re-extract even if keys already exist.

    Returns:
        Dict with 'keys' (list of key entries) and 'matched_count'.
    """
    # Check for existing keys
    keys_dir = os.path.join(os.path.expanduser("~"), ".wecom-cli")
    keys_path = os.path.join(keys_dir, "all_keys.json")

    if not force and os.path.exists(keys_path):
        with open(keys_path, encoding="utf-8") as f:
            existing = json.load(f)
        if existing:
            return {"keys": existing, "matched_count": len(existing), "source": "cached"}

    # Find WXWork processes
    pids = _get_wxwork_pids()
    if not pids:
        raise RuntimeError(
            "WXWork.exe is not running. Please start WeCom and log in first."
        )

    # Collect database files and their first pages
    db_files = collect_db_files(db_dir)
    if not db_files:
        raise RuntimeError(f"No .db files found in {db_dir}")

    db_pages = collect_db_pages(db_files)

    # Scan process memory for key candidates
    all_candidates = []
    for pid, mem_kb in pids:
        try:
            memory = _read_process_memory(pid)
            candidates = extract_hex_candidates(memory)
            all_candidates.extend(candidates)
        except OSError:
            continue

    if not all_candidates:
        raise RuntimeError(
            "Could not find encryption key candidates in WXWork memory. "
            "Make sure WeCom is running and logged in."
        )

    # Verify candidates against databases
    matched = verify_and_match_keys(all_candidates, db_pages)

    if not matched:
        raise RuntimeError(
            "Found key candidates but none matched the databases. "
            "The encryption scheme may have changed."
        )

    # Cross-verify against remaining databases
    matched = cross_verify_keys(matched, db_files)

    # Build and save keys
    keys = build_keys_json(matched)

    os.makedirs(keys_dir, exist_ok=True)
    with open(keys_path, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

    return {
        "keys": keys,
        "matched_count": len(matched),
        "total_db_files": len(db_files),
        "source": "memory_scan",
    }
