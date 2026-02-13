#!/usr/bin/env python3
"""
Telegram 消息轮询器
定期检查新消息并处理 /read 命令
"""

import os
import sys
import json
import urllib.request
import subprocess

TELEGRAM_CHAT_ID = "1268358344"
API_BASE = "http://localhost:8080"  # OpenClaw Gateway 默认端口

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def get_recent_messages():
    """获取最近的 Telegram 消息"""
    # 使用 openclaw api 获取消息
    # 这里简化处理，实际需要通过 Telegram Bot API 获取
    # 由于 OpenClaw 的限制，我们使用另一种方式
    return []

def check_for_commands():
    """检查是否有新命令"""
    # 读取可能的命令文件
    cmd_file = "/home/codespace/.openclaw/workspace/telegram_commands.txt"
    if not os.path.exists(cmd_file):
        return None
    
    with open(cmd_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        return None
    
    # 获取最后一行命令
    last_cmd = lines[-1].strip()
    
    # 清空文件
    with open(cmd_file, 'w', encoding='utf-8') as f:
        f.write('')
    
    return last_cmd

def process_command(cmd_text):
    """处理命令"""
    cmd_text = cmd_text.strip()
    
    if cmd_text.startswith('/read'):
        parts = cmd_text.split()
        if len(parts) < 2:
            return "💡 用法: /read 编号\n例如: /read 1"
        
        try:
            num = int(parts[1])
            # 调用 economist_read.py
            result = subprocess.run(
                ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_read.py', str(num)],
                capture_output=True,
                text=True,
                timeout=180
            )
            if result.returncode == 0:
                return f"✅ 已获取文章 #{num}"
            else:
                return f"❌ 获取失败: {result.stderr[:200]}"
        except ValueError:
            return "❌ 编号必须是数字"
        except subprocess.TimeoutExpired:
            return "⏱️ 请求超时，请重试"
    
    elif cmd_text in ['/help', '/start']:
        return """📖 *经济学人阅读助手*

可用命令:
• `/read 编号` - 查看指定编号的文章
• `/help` - 显示帮助

示例:
`/read 3` - 查看第3篇文章"""
    
    return None

def main():
    """轮询检查命令"""
    cmd = check_for_commands()
    if cmd:
        print(f"收到命令: {cmd}")
        response = process_command(cmd)
        if response:
            # 发送响应
            import shlex
            quoted = shlex.quote(response)
            run(f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}')
            print(f"已回复: {response[:100]}")
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
