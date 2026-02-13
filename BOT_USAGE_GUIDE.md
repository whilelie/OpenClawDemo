# 📚 经济学人 Telegram Bot 使用指南

## 🚀 快速开始

### 方法 1：直接命令（最简单）
```bash
# 查看帮助
python3 /home/codespace/.openclaw/workspace/scripts/bot_trigger.py

# 查看第3篇文章
python3 /home/codespace/.openclaw/workspace/scripts/economist_read.py 3

# 发送完整目录
python3 /home/codespace/.openclaw/workspace/scripts/economist_interactive.py
```

### 方法 2：使用命令文件
```bash
# 1. 写入命令
echo "read 3" > /tmp/bot_command.txt

# 2. 执行
python3 /home/codespace/.openclaw/workspace/scripts/bot_trigger.py
```

## 📖 支持的命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `read 编号` | 查看指定文章 | `read 3` |
| `help` | 显示帮助 | `help` |
| `list` | 显示前10篇文章 | `list` |
| `menu` | 发送完整目录 | `menu` |

## 📋 文章目录（2026/02/14）

| 编号 | 标题（英文） | 中文翻译 | 页码 |
|------|-------------|---------|------|
| 1 | The weekly cartoon | 本周漫画 | p.15 |
| 2 | Don't ban teenagers from social media | 不要禁止青少年使用社交媒体 | p.17 |
| 3 | The world's most powerful woman | 世界上最有权势的女性 | p.21 |
| 4 | The Epstein files tell a story of justice denied | 爱泼斯坦档案揭示了被拒绝的正义 | p.25 |
| 5 | The rich world should beware Brazilification | 富裕国家应警惕巴西化 | p.28 |
| 6 | How to solve the tenor shortage | 如何解决男高音短缺问题 | p.31 |
| 7 | Britain's predicament will get worse before it gets better | 英国的困境在好转之前会变得更糟 | p.34 |
| 8 | Is education technology mostly useless? | 教育技术是否大多无用？ | p.39 |
| 9 | More and more countries are banning kids from social media | 越来越多的国家禁止儿童使用社交媒体 | p.47 |
| 10 | How Democrats aim to curb ICE without losing votes | 民主党如何旨在遏制ICE而不失去选票 | p.58 |

... 共 78 篇文章

## 🎯 使用示例

### 示例 1：发送帮助
```bash
echo "help" > /tmp/bot_command.txt
python3 scripts/bot_trigger.py
```

### 示例 2：查看第5篇文章
```bash
echo "read 5" > /tmp/bot_command.txt
python3 scripts/bot_trigger.py
```

### 示例 3：查看第10篇文章（快速方式）
```bash
python3 scripts/economist_read.py 10
```

### 示例 4：发送完整目录
```bash
echo "menu" > /tmp/bot_command.txt
python3 scripts/bot_trigger.py
```

## 📝 输出格式

每篇文章包含：
```
==================================================
📰 英文标题
📂 板块名称 ｜ 第 XX 页
==================================================

英文原文段落...
【译】中文翻译...

英文原文段落...
【译】中文翻译...

==================================================
💡 回复 `/read 编号` 查看其他文章
```

## 🔧 脚本文件说明

```
/home/codespace/.openclaw/workspace/scripts/
├── bot_trigger.py                 # 简单的命令触发器 ⭐推荐
├── economist_read.py 编号         # 直接读取文章 ⭐推荐
├── economist_interactive.py       # 发送完整目录
├── economist_bot.py "/help"       # 发送帮助信息
├── economist_toc.py               # 提取完整目录（含翻译）
├── economist_article.py "标题"    # 根据标题提取文章
└── economist_quick_read.py 编号   # 快速阅读快捷方式
```

## 💡 高级用法

### 批量查看多篇文章
```bash
for i in 1 3 5 7 10; do
    python3 scripts/economist_read.py $i
    sleep 5
done
```

### 查找包含关键词的文章
```bash
python3 scripts/economist_toc.py | grep -i "china"
```

### 提取最新一期期刊
```bash
cd /workspaces/awesome-english-ebooks && git pull
python3 scripts/economist_interactive.py
```

## ⚠️ 关于自动回复

由于 Telegram Bot 需要设置 webhook 才能自动接收消息，当前系统使用**命令触发**方式：

1. **您发送消息** → Telegram
2. **运行触发器** → `bot_trigger.py`
3. **Bot 回复** → Telegram

要实现真正的自动回复（无需手动运行脚本），需要：
1. 注册 Telegram Bot（从 BotFather 获取 token）
2. 设置 webhook 指向服务器
3. 部署持续运行的 bot 服务

当前方案的优势：
- ✅ 无需额外配置
- ✅ 随时可用
- ✅ 安全可靠

## 🎉 总结

现在您可以：
1. ✅ 查看带编号的文章目录（已发送到 Telegram）
2. ✅ 通过编号快速查看任意文章（中英对照）
3. ✅ 使用简单的命令系统

**推荐使用方式：**
```bash
# 一键查看文章
python3 /home/codespace/.openclaw/workspace/scripts/economist_read.py 3
```
