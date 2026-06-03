"""Initialize wecom-cli: extract encryption keys and write config."""

import json
import os
import sys

import click

from wxwork_cli.core.config import load_config, save_config, STATE_DIR, KEYS_FILE
from wxwork_cli.output.formatter import output_json, output_text


@click.command("init")
@click.option("--db-dir", default=None, help="Path to WXWork data directory")
@click.option("--force", is_flag=True, help="Re-extract keys even if already initialized")
@click.option("--corp-id", default=None, help="Specify corporate ID when multiple exist")
def init(db_dir, force, corp_id):
    """Initialize wecom-cli by extracting encryption keys from WXWork.

    Must be run once before other commands. Requires WeCom to be running.
    """
    try:
        # Load or create config
        if db_dir:
            if not os.path.isdir(db_dir):
                output_json({"error": f"Directory not found: {db_dir}", "code": 1})
                sys.exit(1)
            cfg = {"db_dir": db_dir}
        else:
            cfg = load_config()

        if corp_id:
            cfg["corp_id"] = corp_id

        output_text("Extracting encryption keys from WXWork...")

        # Extract keys
        from wxwork_cli.keys import extract_keys
        result = extract_keys(cfg["db_dir"], force=force)

        # Save config
        save_config(cfg)

        output_json({
            "status": "success",
            "message": "Initialization complete",
            "matched_databases": result.get("matched_count", 0),
            "total_databases": result.get("total_db_files", 0),
            "source": result.get("source", "unknown"),
            "keys_file": KEYS_FILE,
        })

    except NotImplementedError as e:
        output_json({"error": str(e), "code": 1})
        sys.exit(1)
    except RuntimeError as e:
        output_json({"error": str(e), "code": 1})
        sys.exit(1)
    except Exception as e:
        output_json({"error": f"Initialization failed: {e}", "code": 1})
        sys.exit(1)
