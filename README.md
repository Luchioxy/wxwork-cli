# wxwork-cli

Enterprise WeChat (WeCom/WXWork) local data query CLI for LLMs and developers.

> AI-first design: all commands output JSON by default. Use `--format text` for human-readable output.

## Features

- **Read local WXWork databases** - Decrypt and query WeCom's SQLCipher-encrypted SQLite databases
- **20+ commands** - Sessions, history, search, contacts, departments, groups, tags, apps, approvals, schedules, check-in, reports, stats, export, favorites, unread, new messages
- **AI-first output** - JSON default for LLM/Agent integration
- **Human-friendly mode** - `--format text` for terminal use
- **Cross-platform** - Windows 11 (primary), macOS/Linux (planned)

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# 1. Initialize (requires WeCom to be running)
wxwork-cli init

# 2. List recent sessions
wxwork-cli sessions --limit 10

# 3. Read chat history
wxwork-cli history "张三" --limit 50 --format text

# 4. Search messages
wxwork-cli search "项目进度" --chat "技术群"

# 5. View contacts
wxwork-cli contacts --query "张"

# 6. Department tree
wxwork-cli departments --tree --format text
```

## Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize: extract encryption keys from WXWork |
| `sessions` | List recent chat sessions |
| `history` | Fetch chat message history |
| `search` | Search messages across chats |
| `contacts` | Contact list and search |
| `departments` | Department hierarchy |
| `members` | Group/department members |
| `groups` | Group chat management |
| `tags` | Contact tag management |
| `schema` | Database schema inspection (dev tool) |

### Enterprise Features

| Command | Description |
|---------|-------------|
| `apps` | List installed WeCom apps |
| `approval` | Query approval workflows |
| `schedule` | Calendar/schedule events |
| `checkin` | Check-in/attendance records |
| `reports` | Daily/weekly reports |

### Utility Commands

| Command | Description |
|---------|-------------|
| `stats` | Chat statistics analysis |
| `export` | Export chat to markdown/txt/json |
| `favorites` | View saved favorites |
| `unread` | Show unread sessions |
| `new-messages` | Incremental new messages (stateful) |

## AI Agent Integration

```bash
# JSON output (default) - pipe to jq or feed to LLM
wxwork-cli sessions --limit 5 | jq '.[] | {name, unread_count}'

# Search and extract
wxwork-cli search "deadline" --format json | jq '.[] | .content'
```

## Configuration

Config file: `~/.wxwork-cli/config.json`

```json
{
  "db_dir": "C:\\Users\\<user>\\Documents\\WXWork\\<corp_id>",
  "keys_file": "~/.wxwork-cli/all_keys.json",
  "corp_id": "ww1234567890"
}
```

## Environment Variables

- `WXWORK_CLI_CONFIG` - Path to config file

## Documentation

- [Technical Guide](docs/TECHNICAL_GUIDE.md) - 完整技术文档
- [Quick Start (中文)](docs/QUICKSTART_CN.md) - 快速入门指南
- [README (中文)](README_CN.md) - 中文文档

## License

Apache-2.0
