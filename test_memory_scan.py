#!/usr/bin/env python3
"""Test script to debug memory scanning for WXWork keys."""

import ctypes
import ctypes.wintypes
import re
import struct
import subprocess
import sys

# Windows API constants
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MEM_COMMIT = 0x1000
PAGE_READABLE = {0x02, 0x04, 0x06, 0x20, 0x40, 0x60, 0x80}

kernel32 = ctypes.windll.kernel32

# Check if we're running 64-bit Python
is_64bit = sys.maxsize > 2**32

# Define MEMORY_BASIC_INFORMATION based on architecture
if is_64bit:
    # 64-bit structure
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
else:
    # 32-bit structure
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

print(f"Running {'64-bit' if is_64bit else '32-bit'} Python")
print(f"MEMORY_BASIC_INFORMATION size: {ctypes.sizeof(MEMORY_BASIC_INFORMATION)} bytes")


def get_wxwork_pids():
    """Get PIDs of running WXWork.exe processes."""
    try:
        # Use a simpler approach - just get all PIDs for WXWork.exe
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WXWork.exe"],
            capture_output=True, text=True, timeout=10
        )
        print(f"tasklist output:\n{result.stdout}")

        # Parse the output manually
        pids = []
        for line in result.stdout.split("\n"):
            if "WXWork.exe" in line:
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        pid = int(parts[1])
                        mem_str = parts[4].replace(",", "").replace("K", "").strip()
                        mem_kb = int(mem_str)
                        pids.append((pid, mem_kb))
                        print(f"Found PID: {pid}, Memory: {mem_kb} KB")
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing line: {line}, error: {e}")
                        continue

        return sorted(pids, key=lambda x: x[1], reverse=True)
    except Exception as e:
        print(f"Error getting PIDs: {e}")
        return []


def read_process_memory(pid):
    """Read readable memory regions from a process."""
    print(f"Opening process {pid}...")

    # Try different access rights
    access_rights = [
        PROCESS_VM_READ | PROCESS_QUERY_INFORMATION,
        PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION,
        PROCESS_QUERY_INFORMATION,
        PROCESS_QUERY_LIMITED_INFORMATION,
    ]

    handle = None
    for access in access_rights:
        handle = kernel32.OpenProcess(access, False, pid)
        if handle:
            print(f"Successfully opened process with access rights: {access:#x}, handle: {handle}")
            break

    if not handle:
        error_code = ctypes.GetLastError()
        raise OSError(f"Cannot open process {pid} (error code: {error_code})")

    try:
        regions = []
        address = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)
        region_count = 0
        max_regions = 10000  # Safety limit

        while region_count < max_regions:
            result = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), mbi_size)
            if result == 0:
                # VirtualQueryEx returns 0 when there are no more regions or on error
                error_code = ctypes.GetLastError()
                if error_code != 0:
                    print(f"VirtualQueryEx failed with error code: {error_code}")
                else:
                    print(f"VirtualQueryEx returned 0 (no more regions)")
                break

            region_count += 1
            if region_count <= 10:  # Print first 10 regions for debugging
                base_addr = mbi.BaseAddress if mbi.BaseAddress is not None else 0
                region_size = mbi.RegionSize if mbi.RegionSize is not None else 0
                print(f"Region {region_count}: Base={base_addr:#x}, Size={region_size:#x}, State={mbi.State:#x}, Protect={mbi.Protect:#x}")

            # Check if we can read this region
            if (mbi.State == MEM_COMMIT and
                mbi.Protect in PAGE_READABLE and
                mbi.RegionSize > 0 and
                mbi.RegionSize < 100 * 1024 * 1024 and
                mbi.BaseAddress is not None):

                buf = ctypes.create_string_buffer(mbi.RegionSize)
                bytes_read = ctypes.c_size_t(0)

                if kernel32.ReadProcessMemory(
                    handle,
                    ctypes.c_void_p(mbi.BaseAddress),
                    buf,
                    mbi.RegionSize,
                    ctypes.byref(bytes_read)
                ):
                    if bytes_read.value > 0:
                        regions.append(buf.raw[:bytes_read.value])
                        if region_count <= 10:
                            print(f"  Read {bytes_read.value} bytes")

            # Move to next region
            if mbi.BaseAddress is None or mbi.RegionSize is None:
                break

            next_address = mbi.BaseAddress + mbi.RegionSize
            if next_address <= mbi.BaseAddress:
                break

            address = next_address

        print(f"Scanned {region_count} regions, read {len(regions)} regions")

        # If we didn't read much memory, try reading from multiple address ranges
        if len(regions) < 10:
            print("\nTrying to read from multiple address ranges...")
            # Try multiple ranges that are likely to contain process data
            address_ranges = [
                (0x1000000, 0x2000000),   # 16 MB range
                (0x10000000, 0x20000000), # 256 MB range
                (0x20000000, 0x30000000), # 512 MB range
                (0x70000000, 0x80000000), # Higher memory range
            ]

            chunk_size = 4096
            total_read = 0

            for start_addr, end_addr in address_ranges:
                range_read = 0
                for addr in range(start_addr, end_addr, chunk_size):
                    try:
                        buf = ctypes.create_string_buffer(chunk_size)
                        bytes_read = ctypes.c_size_t(0)
                        if kernel32.ReadProcessMemory(
                            handle,
                            ctypes.c_void_p(addr),
                            buf,
                            chunk_size,
                            ctypes.byref(bytes_read)
                        ):
                            if bytes_read.value > 0:
                                regions.append(buf.raw[:bytes_read.value])
                                range_read += 1
                                total_read += 1
                    except Exception as e:
                        continue

                if range_read > 0:
                    print(f"  Read {range_read} chunks from range {start_addr:#x}-{end_addr:#x}")

            print(f"  Total regions read: {total_read}")

        return b"".join(regions)

    finally:
        kernel32.CloseHandle(handle)


def find_hex_patterns(memory_data):
    """Find hex patterns in memory."""
    # Pattern for 16-byte keys (32 hex chars)
    pattern16 = re.compile(rb"x'([0-9a-fA-F]{32})")
    # Pattern for 32-byte keys (64 hex chars)
    pattern32 = re.compile(rb"x'([0-9a-fA-F]{64})")
    # Pattern for longer hex strings
    pattern_long = re.compile(rb"x'([0-9a-fA-F]{96,192})")

    results = []

    for match in pattern16.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            results.append(("16-byte", raw, match.start()))
        except:
            pass

    for match in pattern32.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            results.append(("32-byte", raw, match.start()))
        except:
            pass

    for match in pattern_long.finditer(memory_data):
        hex_str = match.group(1)
        try:
            raw = bytes.fromhex(hex_str.decode("ascii"))
            results.append(("long", raw, match.start()))
        except:
            pass

    return results


def find_cipher_struct_candidates(memory_data):
    """Find potential wxSQLite3 cipher structure candidates in memory.

    The cipher struct layout (32-bit process):
    - Offset 0x00: flags (non-zero)
    - Offset 0x04: flags (non-zero)
    - Offset 0x08: 16-byte key
    - Offset 0x2C: AES context pointer
    - Offset 0x30: page-size pointer chain
    """
    candidates = []

    # Scan with 4-byte alignment (32-bit process)
    for i in range(0, len(memory_data) - 48, 4):
        try:
            # Check flags at offset 0 and 4
            flag1 = struct.unpack_from("<I", memory_data, i)[0]
            flag2 = struct.unpack_from("<I", memory_data, i + 4)[0]

            if flag1 == 0 or flag2 == 0:
                continue

            # Extract potential key at offset 0x08
            key_candidate = memory_data[i + 8:i + 24]

            # Check key has at least 6 unique bytes (not all zeros or repetitive)
            if len(set(key_candidate)) < 6:
                continue

            # Check for valid page-size pointer chain
            # This is complex, so we'll just check if the key looks valid
            # and let the verification step confirm it

            candidates.append(("cipher_struct", key_candidate, i))

        except (struct.error, IndexError):
            continue

    return candidates


def main():
    print("Getting WXWork PIDs...")
    pids = get_wxwork_pids()
    print(f"Found {len(pids)} WXWork processes: {pids}")

    if not pids:
        print("No WXWork processes found!")
        return

    # Try the first PID (highest memory usage)
    pid, mem_kb = pids[0]
    print(f"\nTrying PID {pid} ({mem_kb} KB memory)...")

    try:
        print("Reading process memory...")
        memory = read_process_memory(pid)
        print(f"Read {len(memory)} bytes of memory")

        print("\nSearching for hex patterns...")
        patterns = find_hex_patterns(memory)

        print(f"Found {len(patterns)} hex patterns:")
        for pattern_type, raw_data, offset in patterns[:20]:  # Show first 20
            print(f"  {pattern_type} at offset {offset}: {raw_data.hex()[:32]}...")

        print("\nSearching for cipher structure candidates...")
        cipher_candidates = find_cipher_struct_candidates(memory)

        print(f"Found {len(cipher_candidates)} cipher structure candidates:")
        for candidate_type, raw_data, offset in cipher_candidates[:20]:  # Show first 20
            print(f"  {candidate_type} at offset {offset}: {raw_data.hex()[:32]}...")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
