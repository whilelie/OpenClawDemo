#!/usr/bin/env python3
"""
经济学人快速阅读器
用法: python3 economist_quick_read.py <编号>
快速获取指定编号的文章并发送到 Telegram
"""

import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("用法: python3 economist_quick_read.py <编号>")
        print("示例:")
        print("  python3 economist_quick_read.py 1    # 查看第1篇")
        print("  python3 economist_quick_read.py 5    # 查看第5篇")
        print("  python3 economist_quick_read.py 10   # 查看第10篇")
        return 1
    
    try:
        num = int(sys.argv[1])
    except ValueError:
        print("❌ 错误: 编号必须是数字")
        return 1
    
    print(f"🚀 正在获取文章 #{num}...")
    
    result = subprocess.run(
        ['python3', '/home/codespace/.openclaw/workspace/scripts/economist_read.py', str(num)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(result.stdout)
        return 0
    else:
        print("❌ 获取文章失败")
        print(result.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
