# wxwork-cli

企业微信 (WeCom/WXWork) 本地数据查询 CLI 工具，面向 LLM Agent 和开发者。

> AI 优先设计：所有命令默认输出 JSON。使用 `--format text` 获取人类可读输出。

## 功能特性

- **读取本地企业微信数据库** — 解密并查询企业微信的 SQLCipher 加密 SQLite 数据库
- **20+ 命令** — 会话、历史记录、搜索、通讯录、部门、群聊、标签、应用、审批、日程、打卡、日报、统计、导出、收藏、未读、新消息
- **AI 优先输出** — JSON 默认输出，适合 LLM/Agent 集成
- **人类友好模式** — `--format text` 终端可读
- **跨平台** — Windows 11（主要），macOS/Linux（计划中）

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 1. 初始化（需要企业微信正在运行）
wxwork-cli init

# 2. 查看最近会话
wxwork-cli sessions --limit 10

# 3. 读取聊天记录
wxwork-cli history "张三" --limit 50 --format text

# 4. 搜索消息
wxwork-cli search "项目进度" --chat "技术群"

# 5. 查看通讯录
wxwork-cli contacts --query "张"

# 6. 部门树
wxwork-cli departments --tree --format text
```

## 命令列表

### 核心命令

| 命令 | 说明 |
|------|------|
| `init` | 初始化：从企业微信提取加密密钥 |
| `sessions` | 最近会话列表 |
| `history` | 聊天记录 |
| `search` | 消息搜索 |
| `contacts` | 通讯录管理 |
| `departments` | 部门层级 |
| `members` | 群成员/部门成员 |
| `groups` | 群聊管理 |
| `tags` | 标签管理 |
| `schema` | 数据库 schema 检查（开发工具） |

### 企业功能

| 命令 | 说明 |
|------|------|
| `apps` | 应用列表 |
| `approval` | 审批流程查询 |
| `schedule` | 日程/日历 |
| `checkin` | 打卡/考勤记录 |
| `reports` | 日报/周报 |

### 工具命令

| 命令 | 说明 |
|------|------|
| `stats` | 聊天统计分析 |
| `export` | 导出为 markdown/txt/json |
| `favorites` | 收藏 |
| `unread` | 未读会话 |
| `new-messages` | 增量新消息（有状态） |

## AI Agent 集成

```bash
# JSON 输出（默认）— 管道到 jq 或喂给 LLM
wxwork-cli sessions --limit 5 | jq '.[] | {name, unread_count}'

# 搜索并提取
wxwork-cli search "deadline" --format json | jq '.[] | .content'
```

## 配置

配置文件：`~/.wxwork-cli/config.json`

```json
{
  "db_dir": "C:\\Users\\<user>\\Documents\\WXWork\\<corp_id>",
  "keys_file": "~/.wxwork-cli/all_keys.json",
  "corp_id": "ww1234567890"
}
```

## 环境变量

- `WXWORK_CLI_CONFIG` — 配置文件路径

## 文档

- [技术文档](docs/TECHNICAL_GUIDE.md) — 完整技术文档和使用指南
- [快速入门](docs/QUICKSTART_CN.md) — 5 分钟上手指南
- [README (English)](README.md) — 英文文档

## 许可证

Apache-2.0
