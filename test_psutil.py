#!/usr/bin/env python3
"""Test script using psutil to read WXWork process memory."""

import psutil
import re


def find_wxwork_processes():
    """Find all WXWork.exe processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if proc.info['name'] and 'WXWork.exe' in proc.info['name']:
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes


def read_process_memory(pid):
    """Read process memory using psutil."""
    try:
        proc = psutil.Process(pid)
        print(f"Process: {proc.name()} (PID: {pid})")
        print(f"Memory info: {proc.memory_info()}")

        # Try to read memory maps
        try:
            maps = proc.memory_maps()
            print(f"Found {len(maps)} memory maps")
            for i, m in enumerate(maps[:10]):  # Show first 10
                print(f"  Map {i}: {m.addr}, perms={m.perms}, path={m.path}")
        except Exception as e:
            print(f"Error reading memory maps: {e}")

        # Try to read memory directly
        try:
            # Read a small chunk of memory
            data = proc.memory_read(0x10000, 4096)
            print(f"Read {len(data)} bytes from address 0x10000")
            return data
        except Exception as e:
            print(f"Error reading memory: {e}")
            return None

    except Exception as e:
        print(f"Error accessing process: {e}")
        return None


def find_hex_patterns(memory_data):
    """Find hex patterns in memory."""
    if not memory_data:
        return []

    # Pattern for 16-byte keys (32 hex chars)
    pattern16 = re.compile(rb"x'([0-9a-fA-F]{32})")
    # Pattern for 32-byte keys (64 hex chars)
    pattern32 = re.compile(rb"x'([0-9a-fA-F]{64})")

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

    return results


def main():
    print("Finding WXWork processes...")
    processes = find_wxwork_processes()
    print(f"Found {len(processes)} WXWork processes")

    if not processes:
        print("No WXWork processes found!")
        return

    # Try the first process
    proc = processes[0]
    pid = proc.pid
    print(f"\nTrying PID {pid}...")

    memory = read_process_memory(pid)
    if memory:
        print(f"\nSearching for hex patterns in {len(memory)} bytes...")
        patterns = find_hex_patterns(memory)
        print(f"Found {len(patterns)} hex patterns:")
        for pattern_type, raw_data, offset in patterns[:10]:
            print(f"  {pattern_type} at offset {offset}: {raw_data.hex()[:32]}...")
    else:
        print("Failed to read memory")


if __name__ == "__main__":
    main()
