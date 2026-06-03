# wxwork-cli 技术文档与使用指南

> 企业微信 (WeCom/WXWork) 命令行数据查询工具
> 面向 LLM Agent 和开发者的 AI-first 设计

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [安装与配置](#3-安装与配置)
4. [快速开始](#4-快速开始)
5. [命令详解](#5-命令详解)
6. [AI Agent 集成](#6-ai-agent-集成)
7. [技术实现细节](#7-技术实现细节)
8. [故障排除](#8-故障排除)
9. [开发指南](#9-开发指南)

---

## 1. 项目概述

### 1.1 什么是 wxwork-cli

wxwork-cli 是一个命令行工具，用于直接从本地企业微信客户端读取和查询数据。它通过解密企业微信的 SQLCipher 加密数据库，提供结构化的数据访问接口。

### 1.2 核心特性

| 特性 | 说明 |
|------|------|
| **AI-first 设计** | 所有命令默认输出 JSON，适合 LLM/Agent 集成 |
| **本地数据访问** | 直接读取本地加密数据库，无需网络请求 |
| **20+ 命令** | 覆盖会话、消息、通讯录、部门、审批、日程等 |
| **双模式输出** | JSON（默认）+ `--format text` 人类可读 |
| **高性能缓存** | 基于 mtime 的智能缓存，避免重复解密 |

### 1.3 使用场景

- **AI Agent 集成**：Claude Code、GPT 等 LLM 直接调用获取企业微信数据
- **开发者工具**：终端快速查询聊天记录、联系人、审批等
- **自动化脚本**：CI/CD、定时任务、数据导出

---

## 2. 架构设计

### 2.1 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Command Layer (命令层)                      │
│  sessions, history, search, contacts, departments, ...      │
├─────────────────────────────────────────────────────────────┤
│                    Core Logic Layer (核心逻辑层)               │
│  messages.py, contacts.py, groups.py, departments.py, ...   │
├─────────────────────────────────────────────────────────────┤
│                    Data Access Layer (数据访问层)              │
│  crypto.py, db_cache.py, key_utils.py, schema_probe.py     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
wxwork-cli/
├── pyproject.toml              # 项目配置和依赖
├── README.md                   # 英文文档
├── README_CN.md                # 中文文档
├── docs/
│   └── TECHNICAL_GUIDE.md      # 本文档
│
├── wxwork_cli/
│   ├── __init__.py             # 版本信息
│   ├── main.py                 # Click 入口点 + 命令注册
│   │
│   ├── core/                   # 核心业务逻辑
│   │   ├── config.py           # 配置加载、路径检测
│   │   ├── context.py          # AppContext 单例
│   │   ├── contacts.py         # 联系人解析
│   │   ├── messages.py         # 消息查询、搜索
│   │   ├── departments.py      # 部门层级
│   │   ├── apps.py             # 应用、审批、日程
│   │   ├── groups.py           # 群聊操作
│   │   └── media.py            # 媒体文件解析
│   │
│   ├── data/                   # 数据访问层
│   │   ├── crypto.py           # SQLCipher 解密
│   │   ├── db_cache.py         # 解密缓存
│   │   ├── key_utils.py        # 密钥工具
│   │   └── schema_probe.py     # Schema 发现
│   │
│   ├── keys/                   # 密钥提取层
│   │   ├── __init__.py         # 平台分发
│   │   ├── common.py           # 通用验证逻辑
│   │   └── scanner_windows.py  # Windows 内存扫描
│   │
│   ├── commands/               # 命令实现
│   │   ├── init.py             # 初始化
│   │   ├── sessions.py         # 会话列表
│   │   ├── history.py          # 聊天记录
│   │   ├── search.py           # 消息搜索
│   │   ├── contacts.py         # 通讯录
│   │   ├── departments.py      # 部门树
│   │   ├── members.py          # 成员列表
│   │   ├── groups.py           # 群聊管理
│   │   ├── tags.py             # 标签管理
│   │   ├── schema.py           # Schema 检查
│   │   ├── stats.py            # 统计分析
│   │   ├── export.py           # 导出
│   │   ├── favorites.py        # 收藏
│   │   ├── unread.py           # 未读会话
│   │   ├── new_messages.py     # 增量新消息
│   │   ├── apps.py             # 应用列表
│   │   ├── approval.py         # 审批查询
│   │   ├── schedule.py         # 日程查询
│   │   ├── checkin.py          # 打卡记录
│   │   └── reports.py          # 日报/周报
│   │
│   └── output/
│       └── formatter.py        # 输出格式化
│
└── tools/
    ├── db_inspector.py         # DB Schema 探索器
    └── key_test.py             # 密钥验证工具
```

### 2.3 数据流

```
用户输入 → Click 命令解析 → AppContext 初始化
                                    ↓
                            加载配置 + 密钥
                                    ↓
                        DBCache 检查缓存
                           ↓              ↓
                      缓存命中        缓存未命中
                           ↓              ↓
                      返回路径      crypto.py 解密
                           ↓              ↓
                           └──────┬───────┘
                                  ↓
                          SQLite 查询数据
                                  ↓
                          格式化输出 (JSON/text)
```

---

## 3. 安装与配置

### 3.1 系统要求

- **操作系统**：Windows 11（主要），macOS/Linux（计划中）
- **Python**：3.10+
- **企业微信**：需要正在运行并登录

### 3.2 安装步骤

```bash
# 1. 克隆或下载项目
cd wxwork-cli

# 2. 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -e .

# 4. 验证安装
wxwork-cli --version
```

### 3.3 依赖说明

| 依赖 | 版本 | 用途 |
|------|------|------|
| `click` | >=8.1 | CLI 框架 |
| `pycryptodome` | >=3.19 | AES-256-CBC 解密 |
| `zstandard` | >=0.22 | 消息内容解压缩 |

### 3.4 配置文件

配置文件位置：`~/.wxwork-cli/config.json`

```json
{
  "db_dir": "C:\\Users\\<username>\\Documents\\WXWork\\<corp_id>",
  "keys_file": "C:\\Users\\<username>\\.wxwork-cli\\all_keys.json",
  "corp_id": "ww1234567890",
  "wxwork_process": "WXWork.exe"
}
```

### 3.5 环境变量

| 变量 | 说明 |
|------|------|
| `WXWORK_CLI_CONFIG` | 自定义配置文件路径 |

---

## 4. 快速开始

### 4.1 首次使用

```bash
# 步骤 1: 确保企业微信正在运行并已登录

# 步骤 2: 初始化（提取加密密钥）
wxwork-cli init

# 步骤 3: 查看最近会话
wxwork-cli sessions --limit 10
```

### 4.2 基本操作流程

```bash
# 查看会话列表
wxwork-cli sessions --format text

# 读取聊天记录
wxwork-cli history "张三" --limit 50 --format text

# 搜索消息
wxwork-cli search "项目进度" --chat "技术群"

# 查看通讯录
wxwork-cli contacts --query "张"

# 查看部门结构
wxwork-cli departments --tree --format text
```

### 4.3 输出格式

**JSON 输出（默认）**：
```bash
wxwork-cli sessions --limit 5
```
```json
[
  {
    "username": "zhangsan",
    "nickname": "张三",
    "unread_count": 3,
    "last_message": "明天开会",
    "last_timestamp": 1717382400
  }
]
```

**Text 输出**：
```bash
wxwork-cli sessions --limit 5 --format text
```
```
Recent sessions (5):

  张三 [3 unread]  2024-06-03 10:30:00
    明天开会

  李四  2024-06-03 09:15:00
    收到，谢谢
```

---

## 5. 命令详解

### 5.1 初始化命令

#### `wxwork-cli init`

从运行中的企业微信进程提取加密密钥。

```bash
wxwork-cli init [--db-dir PATH] [--force] [--corp-id ID]
```

| 参数 | 说明 |
|------|------|
| `--db-dir` | 手动指定 WXWork 数据目录 |
| `--force` | 强制重新提取密钥 |
| `--corp-id` | 指定企业 ID（多企业场景） |

**示例**：
```bash
# 自动检测
wxwork-cli init

# 手动指定目录
wxwork-cli init --db-dir "C:\Users\me\Documents\WXWork\ww123456"

# 强制重新提取
wxwork-cli init --force
```

### 5.2 会话命令

#### `wxwork-cli sessions`

列出最近的聊天会话。

```bash
wxwork-cli sessions [--limit N] [--format json|text]
```

**示例**：
```bash
# 查看最近 20 个会话
wxwork-cli sessions

# 只看 5 个，文本格式
wxwork-cli sessions --limit 5 --format text

# JSON 输出，用 jq 处理
wxwork-cli sessions | jq '.[] | {name: .nickname, unread: .unread_count}'
```

### 5.3 历史记录命令

#### `wxwork-cli history`

获取指定聊天的消息历史。

```bash
wxwork-cli history <chat_name> [OPTIONS]
```

| 参数 | 说明 |
|------|------|
| `chat_name` | 聊天对象名称（支持模糊匹配） |
| `--limit N` | 最大消息数（默认 50） |
| `--offset N` | 跳过前 N 条 |
| `--start-time` | 开始时间（YYYY-MM-DD [HH:MM:SS]） |
| `--end-time` | 结束时间 |
| `--type` | 消息类型过滤 |
| `--media` | 包含媒体文件路径 |
| `--format` | 输出格式 |

**支持的消息类型**：
`text`, `image`, `voice`, `video`, `sticker`, `file`, `link`, `system`, `approval`, `oa`

**示例**：
```bash
# 基本用法
wxwork-cli history "张三" --limit 100

# 时间范围过滤
wxwork-cli history "技术群" --start-time "2024-06-01" --end-time "2024-06-03"

# 只看图片消息
wxwork-cli history "张三" --type image

# 文本格式输出
wxwork-cli history "张三" --limit 20 --format text
```

### 5.4 搜索命令

#### `wxwork-cli search`

在消息中搜索关键词。

```bash
wxwork-cli search <keyword> [OPTIONS]
```

| 参数 | 说明 |
|------|------|
| `keyword` | 搜索关键词 |
| `--chat NAME` | 限制在特定聊天中搜索（可多次使用） |
| `--type` | 消息类型过滤 |
| `--limit N` | 最大结果数 |

**示例**：
```bash
# 全局搜索
wxwork-cli search "项目进度"

# 在特定群聊中搜索
wxwork-cli search "deadline" --chat "技术群" --chat "产品群"

# 搜索文件类型消息
wxwork-cli search "报告" --type file
```

### 5.5 通讯录命令

#### `wxwork-cli contacts`

查询和搜索联系人。

```bash
wxwork-cli contacts [OPTIONS]
```

| 参数 | 说明 |
|------|------|
| `--query` | 按名称/userid 搜索 |
| `--detail` | 查看特定联系人详情 |
| `--department` | 按部门 ID 过滤 |
| `--tag` | 按标签过滤 |
| `--limit N` | 最大结果数 |

**示例**：
```bash
# 列出所有联系人
wxwork-cli contacts --limit 100

# 搜索联系人
wxwork-cli contacts --query "张"

# 查看详情
wxwork-cli contacts --detail "zhangsan"

# 按部门过滤
wxwork-cli contacts --department 1001
```

### 5.6 部门命令

#### `wxwork-cli departments`

查看部门层级结构。

```bash
wxwork-cli departments [OPTIONS]
```

| 参数 | 说明 |
|------|------|
| `--parent ID` | 列出指定部门的子部门 |
| `--tree` | 显示完整树形结构 |

**示例**：
```bash
# 查看所有部门
wxwork-cli departments

# 树形结构
wxwork-cli departments --tree --format text

# 查看子部门
wxwork-cli departments --parent 1001
```

### 5.7 群聊命令

#### `wxwork-cli members`

查看群成员或部门成员。

```bash
wxwork-cli members <group_name> [--department ID] [--format json|text]
```

**示例**：
```bash
# 查看群成员
wxwork-cli members "技术群"

# 查看部门成员
wxwork-cli members --department 1001
```

#### `wxwork-cli groups`

列出群聊。

```bash
wxwork-cli groups [--query KEYWORD] [--limit N]
```

### 5.8 标签命令

#### `wxwork-cli tags`

管理联系人标签。

```bash
wxwork-cli tags [--list] [--members TAG_NAME]
```

### 5.9 统计命令

#### `wxwork-cli stats`

查看聊天统计数据。

```bash
wxwork-cli stats <chat_name> [--start-time TIME] [--end-time TIME]
```

**输出内容**：
- 总消息数
- 消息类型分布
- 发送者排行
- 24 小时活跃度

### 5.10 导出命令

#### `wxwork-cli export`

导出聊天记录到文件。

```bash
wxwork-cli export <chat_name> [--format markdown|txt|json] [--output PATH]
```

**示例**：
```bash
# 导出为 Markdown
wxwork-cli export "技术群" --format markdown --output chat.md

# 导出为 JSON
wxwork-cli export "张三" --format json --output chat.json
```

### 5.11 收藏命令

#### `wxwork-cli favorites`

查看收藏的内容。

```bash
wxwork-cli favorites [--type text|image|file|link|card] [--query KEYWORD]
```

### 5.12 未读命令

#### `wxwork-cli unread`

显示有未读消息的会话。

```bash
wxwork-cli unread [--limit N]
```

### 5.13 新消息命令

#### `wxwork-cli new-messages`

增量获取新消息（有状态）。

```bash
wxwork-cli new-messages
```

**说明**：每次调用只返回自上次检查以来的新消息，状态保存在 `~/.wxwork-cli/last_check.json`。

### 5.14 企业功能命令

#### `wxwork-cli apps`
列出已安装的企业应用。

#### `wxwork-cli approval`
查询审批流程。
```bash
wxwork-cli approval [--status pending|approved|rejected|all]
```

#### `wxwork-cli schedule`
查询日程安排。
```bash
wxwork-cli schedule [--date YYYY-MM-DD] [--range DAYS]
```

#### `wxwork-cli checkin`
查询打卡记录。
```bash
wxwork-cli checkin [--date YYYY-MM-DD] [--user NAME]
```

#### `wxwork-cli reports`
查询日报/周报。
```bash
wxwork-cli reports [--type daily|weekly] [--date YYYY-MM-DD] [--user NAME]
```

### 5.15 Schema 命令

#### `wxwork-cli schema`

检查数据库结构（开发工具）。

```bash
wxwork-cli schema [--db NAME] [--table TABLE] [--sample]
```

**示例**：
```bash
# 列出所有数据库
wxwork-cli schema

# 查看特定数据库的表
wxwork-cli schema --db msg

# 查看表结构
wxwork-cli schema --db contact --table contact

# 包含示例数据
wxwork-cli schema --db contact --table contact --sample
```

---

## 6. AI Agent 集成

### 6.1 设计理念

wxwork-cli 采用 **AI-first** 设计：
- JSON 默认输出，无需额外参数
- 结构化数据，易于解析
- 错误信息也是 JSON 格式
- 退出码语义明确

### 6.2 Claude Code 集成

在 Claude Code 中直接调用 wxwork-cli：

```bash
# 查看最近会话
wxwork-cli sessions --limit 10

# 搜索消息
wxwork-cli search "项目进度" --format json

# 获取聊天记录
wxwork-cli history "技术群" --limit 50 --start-time "2024-06-01"
```

### 6.3 JSON 输出结构

**成功响应**：
```json
[
  {
    "username": "zhangsan",
    "nickname": "张三",
    "unread_count": 3,
    "last_message": "明天开会",
    "last_timestamp": 1717382400
  }
]
```

**错误响应**：
```json
{
  "error": "WXWork.exe is not running",
  "code": 1
}
```

### 6.4 管道处理示例

```bash
# 用 jq 提取特定字段
wxwork-cli sessions | jq '.[] | {name: .nickname, unread: .unread_count}'

# 统计未读消息总数
wxwork-cli sessions | jq '[.[].unread_count] | add'

# 搜索并提取内容
wxwork-cli search "deadline" | jq '.[] | .content'

# 导出特定时间段的消息
wxwork-cli history "技术群" --start-time "2024-06-01" --end-time "2024-06-03" | jq '.[].content'
```

### 6.5 Agent 调用模式

```python
import subprocess
import json

def query_wecom(command, args=None):
    """调用 wxwork-cli 命令"""
    cmd = ["wxwork-cli", command]
    if args:
        cmd.extend(args)

    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

# 使用示例
sessions = query_wecom("sessions", ["--limit", "10"])
messages = query_wecom("history", ["张三", "--limit", "50"])
search_results = query_wecom("search", ["项目进度"])
```

---

## 7. 技术实现细节

### 7.1 SQLCipher 解密

企业微信使用 SQLCipher 4 加密 SQLite 数据库：

**加密参数**：
- 算法：AES-256-CBC
- 页大小：4096 字节
- 密钥长度：32 字节
- 盐值长度：16 字节
- HMAC：SHA-512

**解密流程**：
1. 读取加密页（4096 字节）
2. 提取盐值（页 1 前 16 字节）
3. 派生 MAC 密钥：`PBKDF2-SHA512(key, mac_salt, 2)`
4. 验证 HMAC
5. 解密页内容

**代码位置**：`wxwork_cli/data/crypto.py`

### 7.2 密钥提取

从 WXWork.exe 进程内存中提取加密密钥：

**Windows 实现**：
1. 使用 `tasklist` 获取 WXWork.exe 进程 ID
2. 使用 `kernel32` API 读取进程内存
3. 正则搜索 96 字节十六进制模式（32 字节密钥 + 16 字节盐值）
4. 验证密钥：尝试解密数据库首页，检查 SQLite 头

**代码位置**：`wxwork_cli/keys/scanner_windows.py`

### 7.3 缓存机制

**缓存策略**：
- 缓存目录：系统临时目录 `wxwork_cli_cache/`
- 缓存键：数据库路径的 SHA-256 哈希
- 失效机制：基于文件修改时间（mtime）
- 持久化：`_mtimes.json` 记录缓存元数据

**缓存流程**：
```
请求数据库 → 检查缓存 → mtime 匹配？
                           ↓
                      是 → 返回缓存路径
                      否 → 解密数据库 → 更新缓存 → 返回路径
```

**代码位置**：`wxwork_cli/data/db_cache.py`

### 7.4 消息表发现

企业微信的消息表命名规则：
- 表名格式：`Msg_{md5(username)}`
- 分布在多个数据库文件中：`msg_0.db`, `msg_1.db`, ...

**发现逻辑**：
1. 遍历所有 `msg*.db` 文件
2. 查询 `sqlite_master` 获取所有 `Msg_*` 表
3. 计算目标用户名的 MD5 哈希
4. 匹配对应的表

**代码位置**：`wxwork_cli/core/messages.py`

### 7.5 内容解压

消息内容可能使用 zstd 压缩：

**压缩类型**：
- `0`：无压缩
- `4`：zstd 压缩

**解压逻辑**：
```python
if compress_type == 4:  # zstd
    dctx = zstd.ZstdDecompressor()
    content = dctx.decompress(raw_content)
```

**代码位置**：`wxwork_cli/core/messages.py`

---

## 8. 故障排除

### 8.1 常见问题

#### Q: 初始化失败："WXWork.exe is not running"

**原因**：企业微信未运行或未登录。

**解决**：
1. 确保企业微信正在运行
2. 确保已登录账号
3. 如果刚启动，等待几秒后再试

#### Q: 初始化失败："Could not find encryption key candidates"

**原因**：无法在进程内存中找到密钥。

**解决**：
1. 确保使用的是支持的企业微信版本
2. 尝试以管理员权限运行
3. 检查是否有安全软件阻止内存读取

#### Q: 查询返回空结果

**原因**：数据库路径检测失败或密钥不匹配。

**解决**：
1. 使用 `wxwork-cli schema` 检查数据库结构
2. 使用 `wxwork-cli init --force` 重新提取密钥
3. 手动指定数据库目录：`wxwork-cli init --db-dir <path>`

#### Q: 解密失败："HMAC verification failed"

**原因**：密钥不正确或数据库已损坏。

**解决**：
1. 重新初始化：`wxwork-cli init --force`
2. 检查企业微信是否更新了加密方式

### 8.2 调试技巧

#### 启用详细日志

```bash
# 使用 --verbose 标志（如果支持）
wxwork-cli sessions --verbose

# 检查配置文件
cat ~/.wxwork-cli/config.json

# 检查密钥文件
cat ~/.wxwork-cli/all_keys.json
```

#### 使用 Schema 工具

```bash
# 列出所有数据库
wxwork-cli schema

# 检查特定数据库
wxwork-cli schema --db msg

# 查看表结构和示例数据
wxwork-cli schema --db contact --table contact --sample
```

#### 手动验证密钥

```bash
python tools/key_test.py <db_path> <hex_key>
```

---

## 9. 开发指南

### 9.1 开发环境设置

```bash
# 克隆项目
git clone <repo-url>
cd wxwork-cli

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装开发依赖
pip install -e .
pip install pytest black flake8

# 运行测试
pytest
```

### 9.2 添加新命令

1. **创建命令文件**：`wxwork_cli/commands/my_command.py`

```python
"""My custom command."""

import click
from wxwork_cli.output.formatter import output

@click.command("my-command")
@click.option("--param", default=None, help="Parameter description")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json",
              help="Output format")
@click.pass_context
def my_command(ctx, param, fmt):
    """Command description."""
    app = ctx.obj["app"]

    # Your logic here
    results = []

    output(results, fmt)
```

2. **注册命令**：在 `wxwork_cli/main.py` 中添加

```python
from wxwork_cli.commands.my_command import my_command

cli.add_command(my_command)
```

### 9.3 代码风格

- 使用 Black 格式化代码
- 遵循 PEP 8 规范
- 添加类型注解
- 编写文档字符串

### 9.4 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_crypto.py

# 生成覆盖率报告
pytest --cov=wxwork_cli
```

---

## 附录

### A. 命令速查表

| 命令 | 说明 | 示例 |
|------|------|------|
| `init` | 初始化 | `wxwork-cli init` |
| `sessions` | 会话列表 | `wxwork-cli sessions --limit 10` |
| `history` | 聊天记录 | `wxwork-cli history "张三" --limit 50` |
| `search` | 搜索消息 | `wxwork-cli search "关键词"` |
| `contacts` | 通讯录 | `wxwork-cli contacts --query "张"` |
| `departments` | 部门树 | `wxwork-cli departments --tree` |
| `members` | 成员列表 | `wxwork-cli members "技术群"` |
| `groups` | 群聊列表 | `wxwork-cli groups` |
| `tags` | 标签 | `wxwork-cli tags --list` |
| `stats` | 统计 | `wxwork-cli stats "技术群"` |
| `export` | 导出 | `wxwork-cli export "张三" --format markdown` |
| `favorites` | 收藏 | `wxwork-cli favorites` |
| `unread` | 未读 | `wxwork-cli unread` |
| `new-messages` | 新消息 | `wxwork-cli new-messages` |
| `apps` | 应用 | `wxwork-cli apps` |
| `approval` | 审批 | `wxwork-cli approval --status pending` |
| `schedule` | 日程 | `wxwork-cli schedule --date 2024-06-03` |
| `checkin` | 打卡 | `wxwork-cli checkin --date 2024-06-03` |
| `reports` | 日报 | `wxwork-cli reports --type daily` |
| `schema` | Schema | `wxwork-cli schema --db msg` |

### B. 消息类型对照表

| 类型代码 | 类型名称 | 说明 |
|----------|----------|------|
| 1 | text | 文本消息 |
| 3 | image | 图片 |
| 34 | voice | 语音 |
| 42 | card | 名片 |
| 43 | video | 视频 |
| 47 | sticker | 表情 |
| 48 | location | 位置 |
| 49 | link | 链接 |
| 50 | call | 通话 |
| 10000 | system | 系统消息 |
| 10002 | system | 系统消息 |
| 2001 | approval | 审批 |
| 2002 | oa | OA 消息 |
| 2003 | schedule | 日程 |
| 2004 | checkin | 打卡 |
| 2005 | report | 日报 |

### C. 退出码

| 退出码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 无效输入 |
| 3 | 数据访问错误 |

### D. 相关文件位置

| 文件 | 位置 |
|------|------|
| 配置文件 | `~/.wxwork-cli/config.json` |
| 密钥文件 | `~/.wxwork-cli/all_keys.json` |
| 状态文件 | `~/.wxwork-cli/last_check.json` |
| 缓存目录 | `<tempdir>/wxwork_cli_cache/` |
| 日志 | 标准错误输出 |

---

**文档版本**：1.0.0
**最后更新**：2024-06-03
**维护者**：wxwork-cli 团队
