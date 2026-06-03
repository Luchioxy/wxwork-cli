# wxwork-cli 快速入门指南

> 5 分钟上手企业微信命令行工具

---

## 安装

```bash
# 1. 进入项目目录
cd wxwork-cli

# 2. 安装
pip install -e .

# 3. 验证
wxwork-cli --version
```

## 首次使用

### 步骤 1: 初始化

```bash
# 确保企业微信正在运行并已登录
wxwork-cli init
```

输出示例：
```json
{
  "status": "success",
  "message": "Initialization complete",
  "matched_databases": 15,
  "total_databases": 20,
  "source": "memory_scan"
}
```

### 步骤 2: 查看会话

```bash
wxwork-cli sessions --limit 10 --format text
```

输出示例：
```
Recent sessions (10):

  张三 [3 unread]  2024-06-03 10:30:00
    明天开会

  技术群  2024-06-03 09:15:00
    @所有人 代码评审

  李四  2024-06-02 18:00:00
    收到，谢谢
```

### 步骤 3: 读取聊天记录

```bash
wxwork-cli history "张三" --limit 20 --format text
```

输出示例：
```
Chat history with 张三 (20 messages):

[2024-06-03 10:30:00] 张三: 明天开会
[2024-06-03 10:25:00] 我: 好的，几点？
[2024-06-03 10:20:00] 张三: 下午 3 点
```

## 常用命令速查

### 消息相关

```bash
# 搜索消息
wxwork-cli search "项目进度"

# 在特定群聊中搜索
wxwork-cli search "deadline" --chat "技术群"

# 按时间范围查询
wxwork-cli history "技术群" --start-time "2024-06-01" --end-time "2024-06-03"

# 只看图片
wxwork-cli history "张三" --type image
```

### 通讯录相关

```bash
# 搜索联系人
wxwork-cli contacts --query "张"

# 查看联系人详情
wxwork-cli contacts --detail "zhangsan"

# 查看部门树
wxwork-cli departments --tree --format text

# 查看群成员
wxwork-cli members "技术群"
```

### 企业功能

```bash
# 查看审批
wxwork-cli approval --status pending

# 查看日程
wxwork-cli schedule --date 2024-06-03

# 查看打卡记录
wxwork-cli checkin --date 2024-06-03

# 查看日报
wxwork-cli reports --type daily --date 2024-06-03
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

## AI Agent 集成

### JSON 输出（默认）

```bash
# 所有命令默认输出 JSON
wxwork-cli sessions --limit 5
```

```json
[
  {
    "username": "zhangsan",
    "nickname": "张三",
    "unread_count": 3,
    "last_message": "明天开会"
  }
]
```

### 使用 jq 处理

```bash
# 提取特定字段
wxwork-cli sessions | jq '.[] | {name: .nickname, unread: .unread_count}'

# 统计未读总数
wxwork-cli sessions | jq '[.[].unread_count] | add'

# 搜索并提取内容
wxwork-cli search "deadline" | jq '.[] | .content'
```

### 在 Claude Code 中使用

```bash
# 直接调用
wxwork-cli sessions --limit 10

# 搜索消息
wxwork-cli search "项目进度"

# 获取聊天记录
wxwork-cli history "技术群" --limit 50
```

## 常见问题

### Q: 初始化失败怎么办？

```bash
# 确保企业微信正在运行
# 尝试强制重新初始化
wxwork-cli init --force
```

### Q: 查询返回空结果？

```bash
# 检查数据库结构
wxwork-cli schema

# 重新初始化
wxwork-cli init --force
```

### Q: 如何切换企业？

```bash
# 使用不同的配置文件
wxwork-cli --config ~/.wxwork-cli/config_other.json sessions

# 或设置环境变量
set WXWORK_CLI_CONFIG=~/.wxwork-cli/config_other.json
wxwork-cli sessions
```

## 更多信息

- 完整文档：`docs/TECHNICAL_GUIDE.md`
- 英文文档：`README.md`
- 中文文档：`README_CN.md`

---

**快速参考卡**

| 我想要... | 命令 |
|-----------|------|
| 看最近会话 | `wxwork-cli sessions` |
| 读聊天记录 | `wxwork-cli history "名字"` |
| 搜索消息 | `wxwork-cli search "关键词"` |
| 找联系人 | `wxwork-cli contacts --query "名字"` |
| 看部门结构 | `wxwork-cli departments --tree` |
| 查审批 | `wxwork-cli approval` |
| 导出聊天 | `wxwork-cli export "名字" --format markdown` |
