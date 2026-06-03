"""Key extraction layer - platform-specific key scanners."""

import sys


def extract_keys(db_dir: str, force: bool = False) -> dict:
    """Extract encryption keys from the running WXWork process.

    Args:
        db_dir: Path to the WXWork data directory.
        force: If True, re-extract even if keys already exist.

    Returns:
        Dict mapping database paths to their encryption keys.
    """
    if sys.platform == "win32":
        from wecom_cli.keys.scanner_windows import extract_keys as _extract
    elif sys.platform == "darwin":
        raise NotImplementedError("macOS key extraction not yet implemented")
    else:
        raise NotImplementedError("Linux key extraction not yet implemented")

    return _extract(db_dir, force=force)
