#!/usr/bin/env python3
"""
经济学人 Telegram Bot
支持自动回复 /read、/help、/list 等命令
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import subprocess
import shlex

# 配置
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # 需要从 BotFather 获取
TELEGRAM_CHAT_ID = "1268358344"
KIMI_API_KEY = "sk-xdLnWGrw3hrjJnNk9QpAN4jYd4gSYRc6675p0aVqa7cO1cY3"

# 状态文件
LAST_UPDATE_FILE = "/home/codespace/.openclaw/workspace/bot_last_update.txt"

def get_last_update_id():
    """获取最后处理的 update_id"""
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                return int(content)
    return 0

def save_last_update_id(update_id):
    """保存最后处理的 update_id"""
    with open(LAST_UPDATE_FILE, 'w') as f:
        f.write(str(update_id))

def send_telegram_message(text, reply_to=None):
    """发送消息到 Telegram"""
    max_len = 4000
    chunks = []
    current = []
    current_len = 0
    
    for line in text.split('\n'):
        line_len = len(line) + 1
        if current_len + line_len > max_len:
            chunks.append('\n'.join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    
    if current:
        chunks.append('\n'.join(current))
    
    for idx, chunk in enumerate(chunks):
        quoted = shlex.quote(chunk)
        cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"发送失败: {result.stderr[:200]}")

def load_article_index():
    """加载文章索引"""
    workspace = "/home/codespace/.openclaw/workspace"
    index_files = [f for f in os.listdir(workspace) if f.startswith('economist_index_') and f.endswith('.json')]
    if not index_files:
        return None
    index_files.sort(reverse=True)
    with open(os.path.join(workspace, index_files[0]), 'r', encoding='utf-8') as f:
        return json.load(f)

def process_read_command(article_num):
    """处理 /read 命令"""
    index = load_article_index()
    if not index:
        return "❌ 未找到文章索引"
    
    article = None
    for item in index:
        if item['number'] == article_num:
            article = item
            break
    
    if not article:
        return f"❌ 未找到编号 {article_num} 的文章。范围: 1-{len(index)}"
    
    # 先发送等待消息
    send_telegram_message(f"⏳ 正在获取文章 #{article_num}: {article['title'][:40]}...")
    
    # 调用 economist_read.py
    result = subprocess.run(
        ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_read.py', str(article_num)],
        capture_output=True,
        text=True,
        timeout=180
    )
    
    if result.returncode == 0:
        return f"✅ 文章 #{article_num} 已发送"
    else:
        return f"❌ 获取失败: {result.stderr[:200]}"

def process_help_command():
    """处理 /help 命令"""
    return """📖 *经济学人阅读助手*

可用命令:
• `/read 编号` - 查看指定编号的文章（中英对照）
• `/list` - 显示文章目录
• `/help` - 显示帮助

示例:
`/read 3` - 查看第3篇文章
`/read 5` - 查看第5篇文章

💡 提示: 共有78篇文章，编号1-78"""

def process_list_command():
    """处理 /list 命令"""
    index = load_article_index()
    if not index:
        return "❌ 未找到文章索引"
    
    lines = ["📋 *文章目录* (前15篇)", "═" * 30]
    
    for item in index[:15]:
        title = item['title'][:30] + "..." if len(item['title']) > 30 else item['title']
        lines.append(f"`{item['number']:2d}`. {title}")
    
    lines.append(f"\n_共 {len(index)} 篇_")
    lines.append("💡 使用 `/read 编号` 查看")
    
    return "\n".join(lines)

def process_command(text, user_id):
    """处理命令"""
    text = text.strip()
    
    if not text.startswith('/'):
        return None
    
    # 解析命令
    parts = text.split()
    command = parts[0].lower()
    
    if command == '/read':
        if len(parts) < 2:
            return "💡 用法: /read 编号\n例如: /read 3"
        try:
            num = int(parts[1])
            process_read_command(num)
            return None  # economist_read.py 会自己发送内容
        except ValueError:
            return "❌ 编号必须是数字"
    
    elif command == '/help' or command == '/start':
        return process_help_command()
    
    elif command == '/list':
        return process_list_command()
    
    elif command == '/menu':
        # 重新发送目录
        subprocess.run(
            ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_interactive.py'],
            capture_output=True
        )
        return "✅ 目录已发送"
    
    else:
        return f"❓ 未知命令: {command}\n使用 /help 查看可用命令"

def check_openclaw_messages():
    """检查 OpenClaw 收到的消息"""
    # 从 OpenClaw Gateway 获取消息
    # 这里使用一个简化的方法：检查特定的消息文件
    msg_file = "/home/codespace/.openclaw/workspace/incoming_messages.txt"
    if not os.path.exists(msg_file):
        return []
    
    with open(msg_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # 清空文件
    with open(msg_file, 'w', encoding='utf-8') as f:
        f.write('')
    
    if not content:
        return []
    
    messages = []
    for line in content.strip().split('\n'):
        if line.strip():
            parts = line.split('|', 1)
            if len(parts) == 2:
                messages.append({
                    'user_id': parts[0],
                    'text': parts[1]
                })
    
    return messages

def main():
    """主循环"""
    print("🤖 经济学人 Bot 已启动")
    print("检查新消息...")
    
    # 获取新消息
    messages = check_openclaw_messages()
    
    if not messages:
        print("没有新消息")
        return 0
    
    print(f"收到 {len(messages)} 条消息")
    
    for msg in messages:
        text = msg.get('text', '')
        user_id = msg.get('user_id', '')
        
        print(f"处理消息: {text[:50]}")
        
        response = process_command(text, user_id)
        
        if response:
            send_telegram_message(response)
            print(f"已回复: {response[:100]}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
