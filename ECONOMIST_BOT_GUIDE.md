# 📚 经济学人阅读助手使用指南

## 当前功能

### 1. 查看文章目录（已编号）
```bash
python3 /home/codespace/.openclaw/workspace/scripts/economist_interactive.py
```
效果：发送带编号的文章列表到 Telegram

### 2. 快速查看文章
```bash
python3 /home/codespace/.openclaw/workspace/scripts/economist_read.py 3
```
效果：发送第3篇文章（中英对照）到 Telegram

### 3. 快捷命令
```bash
# 快速查看（别名）
python3 /home/codespace/.openclaw/workspace/scripts/economist_quick_read.py 3

# 查看帮助
python3 /home/codespace/.openclaw/workspace/scripts/economist_bot.py "/help"
```

## 📖 文章列表（2026/02/14 期刊）

| 编号 | 标题（英文） | 中文翻译 | 页码 |
|------|-------------|---------|------|
| 1 | The weekly cartoon | 本周漫画 | p.15 |
| 2 | Don't ban teenagers from social media | 不要禁止青少年使用社交媒体 | p.17 |
| 3 | The world's most powerful woman | 世界上最有权势的女性 | p.21 |
| 4 | The Epstein files tell a story of justice denied | 爱泼斯坦档案揭示了被拒绝的正义 | p.25 |
| 5 | The rich world should beware Brazilification | 富裕国家应警惕巴西化 | p.28 |
| 6 | How to solve the tenor shortage | 如何解决男高音短缺问题 | p.31 |
| ... | ... | ... | ... |

共 78 篇文章

## 🎯 使用示例

### 在 Telegram 中查看目录
运行：
```bash
python3 /home/codespace/.openclaw/workspace/scripts/economist_interactive.py
```

### 查看第5篇文章
运行：
```bash
python3 /home/codespace/.openclaw/workspace/scripts/economist_read.py 5
```

### 查看第10篇文章
运行：
```bash
python3 /home/codespace/.openclaw/workspace/scripts/economist_read.py 10
```

## 📝 输出格式

每篇文章包含：
- 📰 英文标题
- 📂 板块名称 + 页码
- 英文原文段落
- 【译】中文翻译

示例：
```
==================================================
📰 Don't ban teenagers from social media
📂 社论 ｜ 第 17 页
==================================================

People don't agree on much these days...
【译】如今人们在很多事情上意见不一...

The proposals arise from...
【译】这些提议源于...
```

## 🔧 高级用法

### 提取完整文章内容
```bash
python3 /home/codespace/.openclaw/workspace/scripts/economist_article.py "文章标题"
```

### 提取最新期刊目录
```bash
python3 /home/codespace/.openclaw/workspace/scripts/economist_toc.py
```

## 💡 提示

1. 所有文章都已编号（1-78）
2. 回复 `/read 编号` 功能需要设置 Telegram Bot Webhook
3. 目前支持的快捷命令：
   - `/read 编号` - 查看文章
   - `/help` - 显示帮助
   - `/list` - 显示前10篇文章

## 📁 脚本位置

```
/home/codespace/.openclaw/workspace/scripts/
├── economist_toc.py              # 提取目录（中英对照+翻译）
├── economist_interactive.py      # 发送编号目录
├── economist_read.py             # 根据编号阅读文章
├── economist_quick_read.py       # 快速阅读快捷方式
├── economist_article.py          # 根据标题提取文章
├── economist_bot.py              # Telegram 命令处理器
└── economist_poller.py           # 消息轮询器
```

## 🚀 快速开始

```bash
# 1. 发送目录到 Telegram
python3 scripts/economist_interactive.py

# 2. 选择想看的文章编号，例如 3
python3 scripts/economist_read.py 3

# 3. 继续查看其他文章
python3 scripts/economist_read.py 5
python3 scripts/economist_read.py 10
```
