# CLAUDE.md - wxwork-cli 项目指南

## 项目概述

wxwork-cli 是一个企业微信 (WXWork) 本地数据查询 CLI 工具，用于从本地加密数据库中读取企业微信数据。

**技术栈**: Python 3.10+, Click, PyCryptodome, zstandard
**加密方式**: wxSQLite3 AES-128-CBC
**GitHub**: https://github.com/Luchioxy/wxwork-cli

## 项目结构

```
wecom-cli/
├── wxwork_cli/
│   ├── main.py              # Click 入口点
│   ├── core/                # 核心业务逻辑
│   │   ├── config.py        # 配置加载
│   │   ├── context.py       # AppContext 单例
│   │   ├── contacts.py      # 联系人解析
│   │   ├── messages.py      # 消息查询
│   │   ├── departments.py   # 部门层级
│   │   ├── apps.py          # 应用管理
│   │   ├── groups.py        # 群聊操作
│   │   └── media.py         # 媒体文件
│   ├── data/                # 数据访问层
│   │   ├── crypto.py        # wxSQLite3 AES-128 解密
│   │   ├── db_cache.py      # 解密缓存
│   │   └── schema_probe.py  # Schema 发现
│   ├── keys/                # 密钥提取层
│   │   ├── common.py        # 通用验证逻辑
│   │   └── scanner_windows.py  # Windows 内存扫描
│   ├── commands/            # 命令实现
│   └── output/
│       └── formatter.py     # 输出格式化
├── docs/
│   ├── TECHNICAL_GUIDE.md   # 技术文档
│   └── QUICKSTART_CN.md     # 快速入门
└── tools/
    ├── db_inspector.py      # DB Schema 探索器
    └── key_test.py          # 密钥验证工具
```

## 核心功能

### 数据解密

wxwork-cli 使用 wxSQLite3 AES-128-CBC 解密企业微信数据库：

- **密钥长度**: 16 字节
- **页大小**: 4096 字节
- **密钥派生**: `MD5(raw_key + page_no + "sAlT")`
- **IV 生成**: 自定义 PRNG + MD5
- **页 1 特殊处理**: 字节 16-23 为明文

### 数据库结构

企业微信数据库位于: `C:\Users\<用户>\Documents\WXWork\<企业ID>\Data\`

主要数据库:
- `session.db` - 会话数据（conversation_table）
- `message.db` - 消息数据（message_table）
- `user.db` - 用户数据
- `company.db` - 企业数据
- `file.db` - 文件数据

### 消息格式

消息内容使用 protobuf 格式存储，需要解析提取文本内容。

## 开发指南

### 添加新命令

1. 在 `wxwork_cli/commands/` 创建新文件
2. 实现 Click 命令
3. 在 `wxwork_cli/main.py` 注册命令

```python
# wxwork_cli/commands/my_command.py
import click
from wxwork_cli.output.formatter import output

@click.command("my-command")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json")
@click.pass_context
def my_command(ctx, fmt):
    """命令描述"""
    app = ctx.obj["app"]
    # 实现逻辑
    results = []
    output(results, fmt)
```

### 数据库查询

```python
import sqlite3
from wxwork_cli.data.crypto import decrypt_page, PAGE_SZ

# 解密数据库
with open(db_path, 'rb') as f:
    data = f.read()

decrypted_data = bytearray()
for i in range(len(data) // PAGE_SZ):
    page = data[i * PAGE_SZ:(i + 1) * PAGE_SZ]
    decrypted = decrypt_page(key, page, i + 1)
    decrypted_data.extend(decrypted)

# 查询数据
conn = sqlite3.connect(decrypted_path)
conn.text_factory = bytes  # 处理二进制数据
cursor = conn.execute("SELECT * FROM table_name")
```

### 消息解析

```python
def parse_wxwork_message(content):
    """解析 WXWork 消息内容（protobuf 格式）"""
    if not content or not isinstance(content, bytes):
        return ''
    
    try:
        # 查找文本内容模式
        idx = content.find(b'\x12')
        if idx > 0:
            remaining = content[idx+1:]
            if len(remaining) > 2:
                length = remaining[0]
                if length < len(remaining):
                    text_bytes = remaining[2:2+length-1]
                    return text_bytes.decode('utf-8')
    except:
        pass
    
    return content.decode('utf-8', errors='ignore')
```

## 常用命令

### 初始化

```bash
# 首次使用需要初始化（提取加密密钥）
wxwork-cli init

# 手动指定数据库目录
wxwork-cli init --db-dir "C:\Users\me\Documents\WXWork\corp_id\Data"
```

### 会话管理

```bash
# 列出最近会话
wxwork-cli sessions --limit 10

# 文本格式输出
wxwork-cli sessions --format text

# JSON 输出（默认）
wxwork-cli sessions --limit 5
```

### 消息查询

```bash
# 读取聊天记录
wxwork-cli history "张三" --limit 50

# 按时间范围查询
wxwork-cli history "技术群" --start-time "2026-06-01" --end-time "2026-06-03"

# 搜索消息
wxwork-cli search "项目进度"

# 在指定群聊中搜索
wxwork-cli search "deadline" --chat "技术群"
```

### 联系人管理

```bash
# 搜索联系人
wxwork-cli contacts --query "张"

# 查看联系人详情
wxwork-cli contacts --detail "zhangsan"

# 按部门过滤
wxwork-cli contacts --department 1001
```

### 部门管理

```bash
# 查看部门树
wxwork-cli departments --tree

# 查看子部门
wxwork-cli departments --parent 1001
```

### 群聊管理

```bash
# 列出群聊
wxwork-cli groups

# 搜索群聊
wxwork-cli groups --query "技术"

# 查看群成员
wxwork-cli members "技术群"
```

### 统计分析

```bash
# 聊天统计
wxwork-cli stats "技术群"

# 按时间范围统计
wxwork-cli stats "张三" --start-time "2026-06-01" --end-time "2026-06-03"
```

### 数据导出

```bash
# 导出为 Markdown
wxwork-cli export "技术群" --format markdown --output chat.md

# 导出为 JSON
wxwork-cli export "张三" --format json --output chat.json

# 导出为纯文本
wxwork-cli export "技术群" --format txt --output chat.txt
```

### 其他功能

```bash
# 查看未读会话
wxwork-cli unread

# 获取新消息（增量）
wxwork-cli new-messages

# 查看收藏
wxwork-cli favorites

# 查看审批
wxwork-cli approval --status pending

# 查看日程
wxwork-cli schedule --date 2026-06-03

# 查看打卡记录
wxwork-cli checkin --date 2026-06-03

# 查看日报
wxwork-cli reports --type daily
```

## AI Agent 集成

### Claude Code 集成

在 CLAUDE.md 中添加：

```markdown
## 企业微信 CLI

你可以使用 `wxwork-cli` 查询我的本地企业微信数据。

常用命令：
- `wxwork-cli sessions --limit 10` — 列出最近会话
- `wxwork-cli history "名称" --limit 20 --format text` — 读取聊天记录
- `wxwork-cli search "关键词" --chat "聊天名"` — 搜索消息
- `wxwork-cli contacts --query "名称"` — 搜索联系人
- `wxwork-cli unread` — 显示未读会话
- `wxwork-cli new-messages` — 获取上次以来的新消息
- `wxwork-cli members "群名"` — 列出群成员
- `wxwork-cli stats "聊天名" --format text` — 聊天统计
```

### 对话示例

```
"帮我看看企业微信有没有未读消息"
"在项目群里搜索关于截止日期的消息"
"看看这周 AI 群里谁发言最多？"
"导出今天的聊天记录"
```

### MCP / OpenClaw 集成

wxwork-cli 兼容任何能执行 shell 命令的 AI 工具：

```bash
# 获取最近会话
wxwork-cli sessions --limit 5

# 读取指定聊天
wxwork-cli history "张三" --limit 30 --format text

# 带过滤条件搜索
wxwork-cli search "报告" --type file --limit 10

# 监控新消息（适合定时任务）
wxwork-cli new-messages --format text
```

## 命令一览

### sessions — 最近会话

```bash
wxwork-cli sessions                        # 最近 20 个会话
wxwork-cli sessions --limit 10             # 最近 10 个
wxwork-cli sessions --format text          # 纯文本输出
```

### history — 聊天记录

```bash
wxwork-cli history "张三"                  # 最近 50 条消息
wxwork-cli history "张三" --limit 100 --offset 50
wxwork-cli history "交流群" --start-time "2026-04-01" --end-time "2026-04-03"
wxwork-cli history "张三" --type link      # 只看链接
wxwork-cli history "张三" --format text
```

选项: `--limit`, `--offset`, `--start-time`, `--end-time`, `--type`, `--format`

### search — 搜索消息

```bash
wxwork-cli search "Claude"                 # 全局搜索
wxwork-cli search "Claude" --chat "交流群"  # 指定聊天搜索
wxwork-cli search "开会" --chat "群A" --chat "群B"  # 多个聊天
wxwork-cli search "报告" --type file        # 只搜文件
```

选项: `--chat`（可多次指定）, `--start-time`, `--end-time`, `--limit`, `--offset`, `--type`, `--format`

### contacts — 联系人搜索与详情

```bash
wxwork-cli contacts --query "李"           # 搜索联系人
wxwork-cli contacts --detail "张三"        # 查看详情
wxwork-cli contacts --detail "wxid_xxx"    # 通过 wxid 查看
```

详情包括: 昵称、备注、微信号、部门、职位。

### departments — 部门层级

```bash
wxwork-cli departments                     # 列出所有部门
wxwork-cli departments --tree              # 树形结构
wxwork-cli departments --parent 1001       # 子部门
```

### members — 群成员列表

```bash
wxwork-cli members "AI交流群"              # 成员列表
wxwork-cli members "AI交流群" --format text
wxwork-cli members --department 1001       # 部门成员
```

### groups — 群聊管理

```bash
wxwork-cli groups                          # 列出所有群聊
wxwork-cli groups --query "技术"           # 搜索群聊
wxwork-cli groups --limit 50               # 限制数量
```

### tags — 标签管理

```bash
wxwork-cli tags                            # 列出所有标签
wxwork-cli tags --list                     # 列出标签
wxwork-cli tags --members "VIP"            # 查看标签成员
```

### stats — 聊天统计

```bash
wxwork-cli stats "AI交流群"
wxwork-cli stats "张三" --start-time "2026-04-01" --end-time "2026-04-03"
wxwork-cli stats "AI交流群" --format text
```

返回: 消息总数、类型分布、发言 Top 10、24 小时活跃分布。

### export — 导出聊天记录

```bash
wxwork-cli export "张三" --format markdown              # 输出到 stdout
wxwork-cli export "张三" --format txt --output chat.txt  # 输出到文件
wxwork-cli export "群聊" --start-time "2026-04-01" --limit 1000
```

选项: `--format markdown|txt|json`, `--output`, `--start-time`, `--end-time`, `--limit`

### favorites — 收藏

```bash
wxwork-cli favorites                       # 最近收藏
wxwork-cli favorites --type article        # 只看文章
wxwork-cli favorites --query "计算机网络"    # 搜索收藏
```

类型: `text`, `image`, `article`, `card`, `video`

### unread — 未读会话

```bash
wxwork-cli unread                          # 所有未读会话
wxwork-cli unread --limit 10 --format text
```

### new-messages — 增量新消息

```bash
wxwork-cli new-messages                    # 首次: 返回未读消息 + 保存状态
wxwork-cli new-messages                    # 后续: 仅返回上次以来的新消息
```

状态保存在 `~/.wxwork-cli/last_check.json`，删除此文件可重置。

### approval — 审批查询

```bash
wxwork-cli approval                        # 所有审批
wxwork-cli approval --status pending       # 待审批
wxwork-cli approval --status approved      # 已通过
wxwork-cli approval --status rejected      # 已拒绝
```

### schedule — 日程查询

```bash
wxwork-cli schedule                        # 今日日程
wxwork-cli schedule --date 2026-06-03      # 指定日期
wxwork-cli schedule --range 7              # 未来 7 天
```

### checkin — 打卡记录

```bash
wxwork-cli checkin                         # 今日打卡
wxwork-cli checkin --date 2026-06-03       # 指定日期
wxwork-cli checkin --user "张三"           # 指定用户
```

### reports — 日报/周报

```bash
wxwork-cli reports --type daily            # 日报
wxwork-cli reports --type weekly           # 周报
wxwork-cli reports --date 2026-06-03       # 指定日期
```

### schema — 数据库结构（开发工具）

```bash
wxwork-cli schema                          # 列出所有数据库
wxwork-cli schema --db session             # 查看 session 数据库
wxwork-cli schema --db message --table message_table  # 查看表结构
wxwork-cli schema --db message --sample    # 包含示例数据
```

## 配置文件

### 配置路径

- 配置文件: `~/.wxwork-cli/config.json`
- 密钥文件: `~/.wxwork-cli/all_keys.json`
- 状态文件: `~/.wxwork-cli/last_check.json`
- 缓存目录: `<tempdir>/wxwork_cli_cache/`

### 配置示例

```json
{
  "db_dir": "C:/Users/<用户>/Documents/WXWork/<企业ID>",
  "keys_file": "C:/Users/<用户>/.wxwork-cli/all_keys.json",
  "corp_id": "<企业ID>",
  "wxwork_process": "WXWork.exe"
}
```

### 环境变量

- `WXWORK_CLI_CONFIG` - 自定义配置文件路径

## 故障排除

### 初始化失败

```bash
# 确保企业微信正在运行
tasklist | findstr WXWork

# 强制重新初始化
wxwork-cli init --force

# 手动指定数据库目录
wxwork-cli init --db-dir "C:\Users\me\Documents\WXWork\corp_id\Data"
```

### 查询返回空结果

```bash
# 检查数据库结构
wxwork-cli schema --db session

# 重新初始化
wxwork-cli init --force
```

### 中文乱码

确保终端使用 UTF-8 编码:

```powershell
# PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```

## 开发笔记

### 关键实现

1. **wxSQLite3 AES-128 解密**: `wxwork_cli/data/crypto.py`
2. **密钥提取**: 集成 wechat-decrypt 项目的逻辑
3. **消息解析**: protobuf 格式解析
4. **会话表**: WXWork 使用 `conversation_table`（不是 `SessionTable`）
5. **图片缓存**: 图片存储在 `Cache/Image/` 目录，未加密

### 数据库结构

| 数据库 | 表名 | 说明 |
|--------|------|------|
| session.db | conversation_table | 会话列表 |
| message.db | message_table | 消息记录 |
| user.db | user_table | 用户信息 |
| file.db | file_table4 | 文件/图片元数据 |
| CacheMapping/*.db | mapping | 图片缓存映射（未加密） |

### 图片获取

图片缓存在 `Cache/Image/` 目录，格式为标准 JPEG/PNG，未加密。

通过 `CacheMapping` 数据库可以关联消息和图片：
- `key` 字段 = `file.db` 中的 `server_id`
- `file_name` 字段 = 本地缓存路径

```python
# 查询图片缓存
conn = sqlite3.connect('CacheMapping/xxx.db')
cursor = conn.execute('''
    SELECT key, file_name, last_modify_time
    FROM mapping
    WHERE type = 2
    ORDER BY last_modify_time DESC
''')
```

### 待完成功能

- [ ] 集成密钥提取到 `init` 命令
- [ ] 实现 `history` 命令的消息查询
- [ ] 实现 `search` 命令的全文搜索
- [ ] 实现图片路径关联到消息查询
- [ ] 实现 `search` 命令的全文搜索
- [ ] 实现 `contacts` 命令的联系人查询
- [ ] 实现 `stats` 命令的统计分析
- [ ] 实现 `export` 命令的数据导出
- [ ] 支持更多消息类型解析
- [ ] 添加图片/文件解密功能

### 参考项目

- [wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt) - 密钥提取和解密算法
- [wechat-cli](https://github.com/huohuoer/wechat-cli) - 个人微信 CLI 工具
