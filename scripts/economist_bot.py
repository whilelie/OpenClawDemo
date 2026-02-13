#!/usr/bin/env python3
"""
Telegram 消息处理器
监听 /read 命令并返回文章内容
"""

import os
import sys
import json
import urllib.request
import subprocess
import time

TELEGRAM_CHAT_ID = "1268358344"
KIMI_API_KEY = "sk-xdLnWGrw3hrjJnNk9QpAN4jYd4gSYRc6675p0aVqa7cO1cY3"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

# 存储已处理的消息ID
processed_messages_file = "/home/codespace/.openclaw/workspace/processed_messages.txt"

def get_last_processed_id():
    """获取最后处理的消息ID"""
    if os.path.exists(processed_messages_file):
        with open(processed_messages_file, 'r') as f:
            content = f.read().strip()
            if content:
                return int(content)
    return 0

def save_last_processed_id(msg_id):
    """保存最后处理的消息ID"""
    with open(processed_messages_file, 'w') as f:
        f.write(str(msg_id))

def send_reply(text, reply_to=None):
    """发送回复消息"""
    import shlex
    
    # 分块发送长消息
    max_len = 3500
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
    
    for chunk in chunks:
        quoted = shlex.quote(chunk)
        cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}'
        subprocess.run(cmd, shell=True, capture_output=True)

def load_article_index():
    """加载文章索引"""
    workspace = "/home/codespace/.openclaw/workspace"
    index_files = [f for f in os.listdir(workspace) if f.startswith('economist_index_') and f.endswith('.json')]
    if not index_files:
        return None
    index_files.sort(reverse=True)
    with open(os.path.join(workspace, index_files[0]), 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_and_translate_article(article_num):
    """提取并翻译文章"""
    index = load_article_index()
    if not index:
        return "❌ 未找到文章索引，请先运行 economist_interactive.py"
    
    article = None
    for item in index:
        if item['number'] == article_num:
            article = item
            break
    
    if not article:
        return f"❌ 未找到编号 {article_num} 的文章。可用范围: 1-{len(index)}"
    
    # 调用 economist_read.py
    result = subprocess.run(
        ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_read.py', str(article_num)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        return f"✅ 已发送文章 [{article_num}]: {article['title']}"
    else:
        return f"❌ 获取文章失败: {result.stderr[:200]}"

def process_command(text):
    """处理命令"""
    text = text.strip()
    
    if text.startswith('/read'):
        parts = text.split()
        if len(parts) < 2:
            return "💡 用法: /read 编号\n例如: /read 1"
        
        try:
            num = int(parts[1])
            extract_and_translate_article(num)
            return None  # economist_read.py 会直接发送消息
        except ValueError:
            return "❌ 编号必须是数字"
    
    elif text.startswith('/help') or text == '/start':
        return """📖 *经济学人阅读助手*

可用命令:
• `/read 编号` - 查看指定编号的文章
• `/list` - 显示文章目录
• `/help` - 显示帮助

示例:
`/read 1` - 查看第1篇文章
`/read 5` - 查看第5篇文章"""
    
    elif text.startswith('/list'):
        # 显示前10篇文章
        index = load_article_index()
        if not index:
            return "❌ 未找到文章索引"
        
        lines = ["📋 *文章目录* (显示前10篇)"]
        lines.append("═" * 30)
        
        for item in index[:10]:
            title = item['title'][:35] + "..." if len(item['title']) > 35 else item['title']
            lines.append(f"`{item['number']:2d}`. {title}")
        
        lines.append(f"\n_共 {len(index)} 篇，使用 `/read 编号` 查看_")
        return "\n".join(lines)
    
    return None  # 不处理其他消息

def main():
    """处理命令行传入的消息"""
    if len(sys.argv) < 2:
        print("用法: python3 economist_bot.py '消息内容'")
        return 1
    
    message_text = sys.argv[1]
    
    # 处理命令
    response = process_command(message_text)
    
    if response:
        send_reply(response)
        print(f"已回复: {response[:100]}...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
