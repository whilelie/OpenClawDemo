#!/usr/bin/env python3
"""
经济学人 Bot - 简单触发器
将命令写入 /tmp/bot_command.txt 即可触发
"""

import os
import sys
import subprocess
import shlex
import time

TELEGRAM_CHAT_ID = "1268358344"
COMMAND_FILE = "/tmp/bot_command.txt"
REPLY_FILE = "/tmp/bot_reply.txt"

def send_message(text):
    """发送消息到 Telegram"""
    quoted = shlex.quote(text)
    cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0

def main():
    # 检查是否有命令
    if not os.path.exists(COMMAND_FILE):
        print("⚠️  使用方法:")
        print(f"   echo 'read 3' > {COMMAND_FILE}")
        print(f"   python3 {sys.argv[0]}")
        print()
        print("支持的命令:")
        print("   read 编号  - 查看文章（如: read 3）")
        print("   help       - 显示帮助")
        print("   list       - 显示文章列表")
        print("   menu       - 发送完整目录")
        return 1
    
    with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # 清空命令文件
    with open(COMMAND_FILE, 'w', encoding='utf-8') as f:
        f.write('')
    
    if not content:
        print("命令文件为空")
        return 0
    
    # 处理命令
    parts = content.split()
    if not parts:
        return 0
    
    command = parts[0].lower()
    
    if command == 'read' and len(parts) >= 2:
        try:
            num = int(parts[1])
            print(f"📖 获取文章 #{num}...")
            send_message(f"⏳ 正在获取文章 #{num}...")
            
            result = subprocess.run(
                ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_read.py', str(num)],
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode == 0:
                print("✅ 已发送")
            else:
                send_message(f"❌ 获取失败: {result.stderr[:200]}")
                
        except ValueError:
            send_message("❌ 编号必须是数字")
    
    elif command == 'help':
        help_text = """📖 *经济学人阅读助手*

命令格式:
• `read 编号` - 查看文章
• `help` - 显示帮助  
• `list` - 显示前10篇
• `menu` - 发送完整目录

示例: `read 3`"""
        send_message(help_text)
        print("已发送帮助")
    
    elif command == 'list':
        subprocess.run(
            ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_bot.py', '/list'],
            capture_output=True
        )
        print("已发送列表")
    
    elif command == 'menu':
        subprocess.run(
            ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_interactive.py'],
            capture_output=True
        )
        print("已发送目录")
    
    else:
        send_message(f"❓ 未知命令: {command}\n使用 `help` 查看帮助")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
