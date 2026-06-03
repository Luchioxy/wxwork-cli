"""Media file resolution (images, files, voice, video).

Handles resolving media file paths from message content and
decoding image files that may be XOR-encrypted.
"""

import os
import re
from datetime import datetime
from typing import Any


def resolve_media_path(
    db_dir: str,
    content: str,
    msg_type: str,
    create_time: int = 0,
    chat_username: str = "",
) -> str | None:
    """Resolve the local file path for a media message.

    Args:
        db_dir: WXWork data directory.
        content: Message content (may contain XML with file references).
        msg_type: Message type (image, voice, video, file, sticker).
        create_time: Message timestamp for date-based path construction.
        chat_username: Chat username for path construction.

    Returns:
        Absolute path to the media file, or None if not found.
    """
    if msg_type == "image":
        return _resolve_image_path(db_dir, content, create_time, chat_username)
    elif msg_type == "voice":
        return _resolve_voice_path(db_dir, content, create_time, chat_username)
    elif msg_type == "video":
        return _resolve_video_path(db_dir, content, create_time, chat_username)
    elif msg_type == "file":
        return _resolve_file_path(db_dir, content, create_time, chat_username)
    elif msg_type == "sticker":
        return _resolve_sticker_path(db_dir, content)
    return None


def _resolve_image_path(
    db_dir: str, content: str, create_time: int, chat_username: str
) -> str | None:
    """Resolve image file path from message content.

    Images may be stored as .dat files with XOR encryption.
    """
    # Try to extract image path from XML content
    # Common patterns in WeChat/WXWork image messages
    patterns = [
        r"<img\s+.*?cdnurl=['\"]([^'\"]+)['\"]",
        r"<msg>\s*<img\s+.*?src=['\"]([^'\"]+)['\"]",
        r"(\w+/Image/\d{4}-\d{2}/\w+\.\w+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            rel_path = match.group(1)
            full_path = os.path.join(db_dir, rel_path)
            if os.path.exists(full_path):
                return full_path

    # Try date-based directory structure
    if create_time:
        try:
            dt = datetime.fromtimestamp(create_time)
            date_dir = dt.strftime("%Y-%m")
            # Common image directory patterns
            for img_dir in ["Image", "Img", "image", "img"]:
                candidate = os.path.join(db_dir, img_dir, date_dir)
                if os.path.isdir(candidate):
                    # Look for files matching the content hash or chat username
                    for f in os.listdir(candidate):
                        if f.endswith((".jpg", ".png", ".gif", ".dat")):
                            return os.path.join(candidate, f)
        except (ValueError, OSError):
            pass

    return None


def _resolve_voice_path(
    db_dir: str, content: str, create_time: int, chat_username: str
) -> str | None:
    """Resolve voice message file path."""
    patterns = [
        r"voicemsg/\w+/\d{4}-\d{2}/\w+\.amr",
        r"<msg>\s*<voicemsg\s+.*?voicedata=['\"]([^'\"]+)['\"]",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            rel_path = match.group(1) if match.lastindex else match.group(0)
            full_path = os.path.join(db_dir, rel_path)
            if os.path.exists(full_path):
                return full_path

    return None


def _resolve_video_path(
    db_dir: str, content: str, create_time: int, chat_username: str
) -> str | None:
    """Resolve video file path."""
    patterns = [
        r"video/\w+/\d{4}-\d{2}/\w+\.mp4",
        r"<msg>\s*<video\s+.*?src=['\"]([^'\"]+)['\"]",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            rel_path = match.group(1) if match.lastindex else match.group(0)
            full_path = os.path.join(db_dir, rel_path)
            if os.path.exists(full_path):
                return full_path

    return None


def _resolve_file_path(
    db_dir: str, content: str, create_time: int, chat_username: str
) -> str | None:
    """Resolve file attachment path."""
    # Extract filename from XML
    filename_match = re.search(r"<title>([^<]+)</title>", content)
    if filename_match:
        filename = filename_match.group(1)
        # Search in common file directories
        for file_dir in ["File", "file", "Files", "files"]:
            candidate_dir = os.path.join(db_dir, file_dir)
            if os.path.isdir(candidate_dir):
                for root, dirs, files in os.walk(candidate_dir):
                    if filename in files:
                        return os.path.join(root, filename)

    return None


def _resolve_sticker_path(db_dir: str, content: str) -> str | None:
    """Resolve sticker/emoji file path."""
    # Stickers are often referenced by md5 or url
    md5_match = re.search(r"md5=['\"]([^'\"]+)['\"]", content)
    if md5_match:
        md5 = md5_match.group(1)
        for sticker_dir in ["Sticker", "sticker", "Emoji", "emoji"]:
            candidate = os.path.join(db_dir, sticker_dir, f"{md5}.gif")
            if os.path.exists(candidate):
                return candidate

    return None


def decode_image_xor(dat_path: str, key: int = 0) -> bytes | None:
    """Decode a WXWork .dat image file that may be XOR-encrypted.

    WXWork (like WeChat) may store images as .dat files with simple XOR encryption.
    The key varies by version.

    Args:
        dat_path: Path to the .dat file.
        key: XOR key (0 = auto-detect from file header).

    Returns:
        Decoded image bytes, or None if decoding fails.
    """
    try:
        with open(dat_path, "rb") as f:
            data = f.read()

        if not data:
            return None

        # Auto-detect key from known file signatures
        if key == 0:
            # JPEG: starts with FF D8 FF
            # PNG: starts with 89 50 4E 47
            # GIF: starts with 47 49 46 38

            if len(data) >= 3:
                # Try JPEG
                key = data[0] ^ 0xFF
                if data[1] ^ key == 0xD8 and data[2] ^ key == 0xFF:
                    return bytes(b ^ key for b in data)

                # Try PNG
                key = data[0] ^ 0x89
                if data[1] ^ key == 0x50 and data[2] ^ key == 0x4E:
                    return bytes(b ^ key for b in data)

                # Try GIF
                key = data[0] ^ 0x47
                if data[1] ^ key == 0x49 and data[2] ^ key == 0x46:
                    return bytes(b ^ key for b in data)

            # Failed to detect
            return None

        # Apply known key
        return bytes(b ^ key for b in data)

    except OSError:
        return None
