#!/usr/bin/env python3
"""
Telegram 命令响应系统
定期检查 /tmp/telegram_commands.txt 中的命令并执行
用法：将命令写入 /tmp/telegram_commands.txt，然后运行此脚本
"""

import os
import sys
import subprocess
import shlex

TELEGRAM_CHAT_ID = "1268358344"
COMMAND_FILE = "/tmp/telegram_commands.txt"

def send_reply(text):
    """发送回复到 Telegram"""
    quoted = shlex.quote(text)
    cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}'
    subprocess.run(cmd, shell=True, capture_output=True)

def main():
    # 检查是否有命令文件
    if not os.path.exists(COMMAND_FILE):
        print(f"未找到命令文件: {COMMAND_FILE}")
        print("使用方式：")
        print(f"  echo '/read 3' > {COMMAND_FILE}")
        print(f"  python3 {sys.argv[0]}")
        return 1
    
    with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print("命令文件为空")
        return 0
    
    # 清空命令文件
    with open(COMMAND_FILE, 'w', encoding='utf-8') as f:
        f.write('')
    
    # 处理命令
    for line in content.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        print(f"处理命令: {line}")
        
        if line.startswith('/read'):
            parts = line.split()
            if len(parts) < 2:
                send_reply("❌ 格式错误。用法: /read 编号\n例如: /read 3")
                continue
            
            try:
                num = int(parts[1])
                send_reply(f"⏳ 正在获取文章 #{num}，请稍候...")
                
                result = subprocess.run(
                    ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_read.py', str(num)],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if result.returncode != 0:
                    send_reply(f"❌ 获取文章失败: {result.stderr[:200]}")
                    
            except ValueError:
                send_reply("❌ 编号必须是数字")
            except subprocess.TimeoutExpired:
                send_reply("⏱️ 请求超时，请重试")
        
        elif line.startswith('/list'):
            # 发送目录
            subprocess.run(
                ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_bot.py', '/list'],
                capture_output=True
            )
        
        elif line.startswith('/help'):
            subprocess.run(
                ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_bot.py', '/help'],
                capture_output=True
            )
        
        else:
            print(f"未知命令: {line}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
