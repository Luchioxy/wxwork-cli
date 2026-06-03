"""Output formatting for JSON (AI-first) and text (human-friendly) modes.

Default output is JSON for LLM/Agent integration.
Use --format text for human-readable output.
"""

import json
import sys
from typing import Any


def output_json(data: Any) -> None:
    """Output data as JSON to stdout.

    Args:
        data: Any JSON-serializable data.
    """
    # Ensure proper encoding for Windows terminal
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def output_text(text: str) -> None:
    """Output plain text to stdout.

    Args:
        text: Text to output.
    """
    # Ensure proper encoding for Windows terminal
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


def output_error(message: str, code: int = 1) -> None:
    """Output an error message as JSON and exit.

    Args:
        message: Error message.
        code: Exit code.
    """
    output_json({"error": message, "code": code})
    sys.exit(code)


def output(data: Any, fmt: str = "json") -> None:
    """Output data in the specified format.

    Args:
        data: Data to output. For text format, should be a string.
        fmt: Output format - "json" or "text".
    """
    if fmt == "text":
        if isinstance(data, str):
            output_text(data)
        else:
            # Convert to human-readable text
            output_text(_format_as_text(data))
    else:
        output_json(data)


def _format_as_text(data: Any) -> str:
    """Convert data to human-readable text format.

    Args:
        data: Data to format.

    Returns:
        Formatted text string.
    """
    if isinstance(data, str):
        return data

    if isinstance(data, list):
        if not data:
            return "(empty)"

        lines = []
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                # Format dict items as key-value pairs
                parts = []
                for k, v in item.items():
                    if v is not None and v != "":
                        parts.append(f"  {k}: {v}")
                lines.append(f"[{i}]")
                lines.extend(parts)
                lines.append("")
            else:
                lines.append(f"  {i}. {item}")
        return "\n".join(lines)

    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            if v is not None and v != "":
                lines.append(f"{k}: {v}")
        return "\n".join(lines) if lines else "(empty)"

    return str(data)


def format_session_text(session: dict) -> str:
    """Format a session for text output.

    Args:
        session: Session data dict.

    Returns:
        Formatted text string.
    """
    # Handle WXWork conversation_table format
    name = session.get("name", session.get("username", ""))
    if not name:
        # Try to get name from roomname_remark or id
        name = session.get("roomname_remark", "") or session.get("id", "unknown")

    # Decode bytes if needed
    if isinstance(name, bytes):
        try:
            name = name.decode('utf-8')
        except UnicodeDecodeError:
            name = name.hex()

    unread = session.get("unread_count", 0)
    last_msg = session.get("last_message", "")
    last_time = session.get("last_time", session.get("last_message_time", ""))

    # Format timestamp if it's a Unix timestamp
    if isinstance(last_time, int) and last_time > 0:
        from datetime import datetime
        try:
            last_time = datetime.fromtimestamp(last_time).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            last_time = str(last_time)

    parts = [f"  {name}"]
    if unread:
        parts.append(f" [{unread} unread]")
    if last_time:
        parts.append(f"  {last_time}")
    if last_msg:
        parts.append(f"\n    {last_msg[:80]}")
    return "".join(parts)


def format_message_text(msg: dict) -> str:
    """Format a message for text output.

    Args:
        msg: Message data dict.

    Returns:
        Formatted text string.
    """
    sender = msg.get("sender_name", msg.get("sender", "unknown"))
    time_str = msg.get("time", "")
    content = msg.get("content", "")
    msg_type = msg.get("type", "text")

    prefix = f"[{time_str}] {sender}:"
    if msg_type != "text":
        prefix += f" [{msg_type}]"

    return f"{prefix} {content}"


def format_contact_text(contact: dict) -> str:
    """Format a contact for text output.

    Args:
        contact: Contact data dict.

    Returns:
        Formatted text string.
    """
    # Handle WXWork format
    name = contact.get("name", contact.get("remark", contact.get("nickname", "unknown")))
    english_name = contact.get("english_name", "")
    userid = contact.get("id", contact.get("username", ""))
    position = contact.get("position", "")

    parts = [name]
    if english_name:
        parts.append(f" ({english_name})")
    if userid:
        parts.append(f" [{userid}]")
    if position:
        parts.append(f" | {position}")

    return "".join(parts)
